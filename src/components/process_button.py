import customtkinter as ctk
import tkinter as tk
import os
import time
import threading
from tkinter import messagebox
from src.pdf.pdf_processor import process_pdfs as process_pdfs_merge
from src.pdf.pdf_processor_rename import process_pdfs as process_pdfs_rename
from src.utils.utils import log_message, Fore

class ProcessButtonComponent:
    def __init__(self, parent, colors, input_path_var, output_path_var, mode_var, settings, progress_var, progress_percentage_var, statistics, output_location, mode_selection, gui):
        self.parent = parent
        self.colors = colors
        self.input_path_var = input_path_var
        self.output_path_var = output_path_var
        self.mode_var = mode_var
        self.settings = settings
        self.progress_var = progress_var
        self.progress_percentage_var = progress_percentage_var
        self.statistics = statistics
        self.output_location = output_location
        self.mode_selection = mode_selection
        self.gui = gui
        
        # Processing thread management
        self.processing_thread = None
        self.cancel_flag = threading.Event()
        self.processing_lock = threading.Lock()

        # No UI creation - this component now only provides logic
        # The actual button is created in FileInputOutputComponent

    def process(self):
        """Start processing in background thread or cancel if already running"""
        with self.processing_lock:
            if self.processing_thread and self.processing_thread.is_alive():
                # Cancel current processing
                self.cancel_processing()
                return
            
            # Start new processing
            self._start_processing()
    
    def _start_processing(self):
        """Initialize and start processing thread"""
        input_dir = self.input_path_var.get()
        output_dir = self.output_path_var.get()
        mode = self.mode_var.get()

        # Enhanced path validation
        if not input_dir or not isinstance(input_dir, str) or input_dir.strip() == "":
            messagebox.showerror("Error", "Pilih folder input terlebih dahulu!")
            return
            
        # Normalize path and check existence
        input_dir = os.path.normpath(input_dir.strip())
        if not os.path.exists(input_dir):
            messagebox.showerror("Error", "Folder input tidak ditemukan!")
            return
            
        if not os.path.isdir(input_dir):
            messagebox.showerror("Error", "Path yang dipilih bukan folder!")
            return
            
        # Check read permissions
        if not os.access(input_dir, os.R_OK):
            messagebox.showerror("Error", "Tidak memiliki izin untuk membaca folder input!")
            return
            
        # Check if directory is empty of PDF files
        try:
            pdf_files = [f for f in os.listdir(input_dir) if f.lower().endswith('.pdf')]
            if not pdf_files:
                messagebox.showwarning("Warning", "Tidak ada file PDF ditemukan di folder input!")
                return
        except (PermissionError, OSError) as e:
            messagebox.showerror("Error", f"Error mengakses folder input: {str(e)}")
            return

        # Reset cancel flag and update UI
        self.cancel_flag.clear()
        self.set_button_text("❌ Cancel")
        self.set_button_state("normal")

        if not output_dir or output_dir.strip() == "":
            output_dir = os.path.join(input_dir, "ProcessedPDFs")
            os.makedirs(output_dir, exist_ok=True)
            self.output_path_var.set(output_dir)

        # Start background processing thread
        self.processing_thread = threading.Thread(
            target=self._process_in_background,
            args=(input_dir, output_dir, mode),
            daemon=True
        )
        self.processing_thread.start()
        
        # Track thread in GUI for cleanup
        if hasattr(self.gui, '_background_threads'):
            self.gui._background_threads.append(self.processing_thread)
    
    def _process_in_background(self, input_dir, output_dir, mode):
        """Background processing method"""
        try:
            # Validate settings
            required_keys = ["use_name", "use_date", "use_reference", "use_faktur"]
            for key in required_keys:
                if not hasattr(self.settings.get(key), 'get'):
                    self._show_error_safe("Error", f"Pengaturan {key} tidak valid!")
                    return

            self.settings["component_order"] = self.mode_selection.get_component_order()
            self.settings["separator"] = self.mode_selection.get_separator()
            self.settings["slash_replacement"] = self.mode_selection.get_slash_replacement()

            # Check for long filenames before processing
            from src.utils.filename_checker import check_long_filenames
            from src.components.filename_warning_dialog import FilenameWarningDialog
        
            has_long_filenames, long_filenames, sample_filenames = check_long_filenames(input_dir, self.settings, self.log_callback)
            
            if has_long_filenames and not self.cancel_flag.is_set():
                # Handle filename dialog on main thread
                dialog_result = [None]
                
                def show_dialog():
                    dialog = FilenameWarningDialog(self.parent, self.gui.colors, len(long_filenames))
                    dialog_result[0] = dialog.show_warning()
                
                self.parent.after(0, show_dialog)
                
                # Wait for dialog result
                while dialog_result[0] is None and not self.cancel_flag.is_set():
                    time.sleep(0.1)
                    
                if self.cancel_flag.is_set():
                    return
                    
                if dialog_result[0] == "cancel":
                    log_message("Proses dibatalkan oleh user karena filename terlalu panjang", Fore.YELLOW, log_callback=self.log_callback)
                    self._reset_button_safe()
                    return
                elif dialog_result[0] == "ok":
                    self.settings["max_filename_length"] = 150
                    log_message(f"User memilih melanjutkan dengan penyesuaian referensi otomatis (max 150 karakter, berlaku untuk semua file)", Fore.CYAN, log_callback=self.log_callback)

            # Check for cancellation
            if self.cancel_flag.is_set():
                return

            # Reset UI on main thread
            self.parent.after(0, self._reset_ui_for_processing)

            # Actual PDF processing with cancellation support
            try:
                if self.cancel_flag.is_set():
                    return
                    
                if mode == "Rename dan Merge":
                    total, renamed, merged, errors = process_pdfs_merge(
                        input_dir, output_dir, self._thread_safe_progress_callback, 
                        self.log_callback, self.settings, self.cancel_flag
                    )
                else:
                    total, renamed, merged, errors = process_pdfs_rename(
                        input_dir, output_dir, self._thread_safe_progress_callback, 
                        self.log_callback, self.settings, self.cancel_flag
                    )

                if not self.cancel_flag.is_set():
                    # Update UI on main thread
                    self.parent.after(0, lambda: self.statistics.update_statistics(total, renamed, merged, errors))
                    self.parent.after(0, lambda: self.output_location.set_output_path(output_dir))
                    # Force progress to 100% completion - this should always work
                    def force_complete():
                        log_message("🎯 Forcing progress to 100% completion", Fore.GREEN, log_callback=self.log_callback)
                        self._set_progress_complete()
                    self.parent.after(100, force_complete)  # Small delay to ensure it's the last update

            except (FileNotFoundError, PermissionError) as e:
                if not self.cancel_flag.is_set():
                    error_message = f"File access error: {str(e)}\n\nSolusi:\n• Periksa izin akses folder\n• Pastikan file tidak sedang dibuka aplikasi lain\n• Jalankan sebagai administrator jika perlu"
                    self._show_error_safe("File Access Error", error_message)
                    log_message(f"File access error: {str(e)}", Fore.RED, log_callback=self.log_callback)
            except (IOError, OSError) as e:
                if not self.cancel_flag.is_set():
                    error_message = f"I/O error: {str(e)}\n\nSolusi:\n• Periksa ruang disk tersedia\n• Pastikan path folder valid\n• Restart aplikasi jika perlu"
                    self._show_error_safe("I/O Error", error_message)
                    log_message(f"I/O error: {str(e)}", Fore.RED, log_callback=self.log_callback)
            except MemoryError as e:
                if not self.cancel_flag.is_set():
                    error_message = "Memory error: Tidak cukup memori untuk memproses file.\n\nSolusi:\n• Tutup aplikasi lain\n• Proses file dalam batch kecil\n• Restart komputer jika perlu"
                    self._show_error_safe("Memory Error", error_message)
                    log_message(f"Memory error: {str(e)}", Fore.RED, log_callback=self.log_callback)
            except Exception as e:
                if not self.cancel_flag.is_set():
                    error_message = self.get_detailed_error_message(e)
                    self._show_error_safe("Unexpected Error", error_message)
                    log_message(f"Unexpected error: {str(e)}", Fore.RED, log_callback=self.log_callback)
        
        except Exception as e:
            # Outer exception handler for background thread setup errors
            if not self.cancel_flag.is_set():
                self._show_error_safe("Error", f"Failed to start processing: {str(e)}")
                log_message(f"Processing setup error: {str(e)}", Fore.RED, log_callback=self.log_callback)
        finally:
            # Always reset button when processing is done/cancelled
            self._reset_button_safe()

    def cancel_processing(self):
        """Cancel current processing"""
        if self.processing_thread and self.processing_thread.is_alive():
            log_message("🛑 Membatalkan proses...", Fore.YELLOW, log_callback=self.log_callback)
            self.cancel_flag.set()
            
            # Give thread some time to finish gracefully
            self.processing_thread.join(timeout=2.0)
            
            if self.processing_thread.is_alive():
                log_message("⚠️ Thread tidak merespons, proses mungkin masih berjalan di background", Fore.YELLOW, log_callback=self.log_callback)
            else:
                log_message("✅ Proses berhasil dibatalkan", Fore.GREEN, log_callback=self.log_callback)
    
    def _reset_ui_for_processing(self):
        """Reset UI elements for processing start"""
        self.statistics.reset()
        self.progress_var.set(0)
        self.progress_percentage_var.set("0%")
        self.gui.progress_bar.set_progress(0)
    
    def _set_progress_complete(self):
        """Set progress to 100% completion"""
        self.gui.progress_bar.set_progress(1.0)
        self.progress_var.set(100)
        self.progress_percentage_var.set("100%")
    
    def _reset_button_safe(self):
        """Thread-safe button reset"""
        def reset_button():
            self.set_button_text("🚀 Mulai Proses")
            self.set_button_state("normal")
            # Progress should already be at 100% from completion
        
        self.parent.after(0, reset_button)
    
    def _show_error_safe(self, title, message):
        """Thread-safe error dialog"""
        self.parent.after(0, lambda: messagebox.showerror(title, message))
    
    def _thread_safe_progress_callback(self, stage, current, total_files, total_to_merge, total_to_finalize):
        """Thread-safe progress callback"""
        if self.cancel_flag.is_set():
            return  # Stop updating progress if cancelled
            
        # Debug logging
        log_message(f"Progress Debug: stage={stage}, current={current}, total_files={total_files}, total_to_merge={total_to_merge}, total_to_finalize={total_to_finalize}", Fore.CYAN, log_callback=self.log_callback)
            
        # Calculate progress same as before
        if stage == "reading":
            percentage = (current / max(total_files, 1)) * 40
        elif stage == "processing":
            percentage = 40 + (current / max(total_to_merge, 1)) * 40
        else:  # finalizing
            if total_to_finalize > 0:
                percentage = 80 + (current / max(total_to_finalize, 1)) * 20
            else:
                percentage = 100  # If no finalization needed, go to 100%

        percentage = min(max(percentage, 0), 100)
        normalized_progress = percentage / 100
        
        log_message(f"Progress calculated: {percentage:.1f}%", Fore.CYAN, log_callback=self.log_callback)

        # Update UI on main thread
        def update_ui():
            if not self.cancel_flag.is_set():
                self.gui.progress_bar.set_progress(normalized_progress)
                self.progress_var.set(percentage)
                self.progress_percentage_var.set(f"{percentage:.1f}%")
        
        self.parent.after(0, update_ui)

    def log_callback(self, message):
        if self.statistics:
            self.statistics.log_message(message)

    def progress_callback(self, stage, current, total_files, total_to_merge, total_to_finalize):
        if stage == "reading":
            percentage = (current / max(total_files, 1)) * 40  # Prevent division by zero
        elif stage == "processing":
            percentage = 40 + (current / max(total_to_merge, 1)) * 40  # Prevent division by zero
        else:
            percentage = 80 + (current / max(total_to_finalize, 1)) * 20  # Prevent division by zero

        percentage = min(max(percentage, 0), 100)
        normalized_progress = percentage / 100
        # Schedule UI update on main thread; avoid direct update()/sleep
        def _ui_update():
            self.gui.progress_bar.set_progress(normalized_progress)
            self.progress_var.set(normalized_progress)
            self.progress_percentage_var.set(f"{int(percentage)}%")
        self.parent.after(0, _ui_update)
    
    def get_detailed_error_message(self, exception):
        """Memberikan pesan error yang lebih jelas untuk user"""
        error_str = str(exception).lower()
        
        if "permission denied" in error_str or "access is denied" in error_str:
            return (f"❌ Error Akses File:\n"
                   f"Tidak dapat mengakses file atau folder.\n\n"
                   f"Solusi:\n"
                   f"• Tutup file PDF yang sedang terbuka\n"
                   f"• Pastikan folder tidak readonly\n"
                   f"• Jalankan sebagai administrator\n"
                   f"• Periksa antivirus yang mungkin memblokir\n\n"
                   f"Detail: {str(exception)}")
        
        elif "no such file or directory" in error_str or "cannot find" in error_str:
            return (f"❌ Error File Tidak Ditemukan:\n"
                   f"File atau folder yang dipilih tidak ada.\n\n"
                   f"Solusi:\n"
                   f"• Periksa apakah folder input masih ada\n"
                   f"• Pilih ulang folder input\n"
                   f"• Pastikan tidak ada file yang dipindah/dihapus\n\n"
                   f"Detail: {str(exception)}")
        
        elif "memory" in error_str or "out of memory" in error_str:
            return (f"❌ Error Memori:\n"
                   f"Tidak cukup memori untuk memproses file.\n\n"
                   f"Solusi:\n"
                   f"• Tutup aplikasi lain yang tidak perlu\n"
                   f"• Proses file dalam batch yang lebih kecil\n"
                   f"• Restart aplikasi jika perlu\n\n"
                   f"Detail: {str(exception)}")
        
        elif "corrupted" in error_str or "invalid pdf" in error_str:
            return (f"❌ Error File PDF Rusak:\n"
                   f"Ada file PDF yang rusak atau tidak valid.\n\n"
                   f"Solusi:\n"
                   f"• Periksa file PDF secara manual\n"
                   f"• Pisahkan file yang bermasalah\n"
                   f"• Coba repair PDF dengan tools lain\n\n"
                   f"Detail: {str(exception)}")
        
        elif "filename too long" in error_str or "path too long" in error_str:
            return (f"❌ Error Nama File Terlalu Panjang:\n"
                   f"Nama file hasil melebihi batas Windows (260 karakter).\n\n"
                   f"Solusi:\n"
                   f"• Gunakan referensi yang lebih pendek\n"
                   f"• Pindah ke folder dengan path lebih pendek\n"
                   f"• Aktifkan 'Long Path Support' di Windows\n\n"
                   f"Detail: {str(exception)}")
        
        elif "division by zero" in error_str:
            return (f"❌ Error Perhitungan Progress:\n"
                   f"Terjadi kesalahan dalam menghitung progress.\n\n"
                   f"Solusi:\n"
                   f"• Pastikan ada file PDF di folder input\n"
                   f"• Coba restart aplikasi\n"
                   f"• Pilih ulang folder input\n\n"
                   f"Detail: {str(exception)}")
        
        else:
            return (f"❌ Error Tidak Terduga:\n"
                   f"Terjadi kesalahan yang tidak diketahui.\n\n"
                   f"Solusi:\n"
                   f"• Restart aplikasi\n"
                   f"• Periksa file log untuk detail\n"
                   f"• Hubungi developer jika masalah berlanjut\n\n"
                   f"Detail: {str(exception)}")

    def set_button_state(self, state):
        """Enable or disable the process button through GUI reference"""
        if hasattr(self.gui, 'file_input_output') and hasattr(self.gui.file_input_output, 'process_btn'):
            self.gui.file_input_output.process_btn.configure(state=state)
    
    def set_button_text(self, text):
        """Set button text through GUI reference"""
        if hasattr(self.gui, 'file_input_output') and hasattr(self.gui.file_input_output, 'process_btn'):
            self.gui.file_input_output.process_btn.configure(text=text)
