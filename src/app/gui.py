import customtkinter as ctk
import tkinter as tk
import threading
from src.utils.styles import Theme
from src.utils.settings_manager import SettingsManager
from src.components.header import HeaderComponent
from src.components.mode_selection import ModeSelectionComponent
from src.components.file_input_output import FileInputOutputComponent
from src.components.pdf_counter import PDFCounterComponent
from src.components.file_list import FileListComponent
from src.components.progress_bar import ProgressBarComponent
from src.components.statistics import StatisticsComponent
from src.components.output_location import OutputLocationComponent
from src.components.process_button import ProcessButtonComponent

def run_gui():
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("blue")
    root = ctk.CTk()
    VERSION = "2.2.0"  # Ganti dengan versi yang diinginkan
    root.title(f"RENAMERGED v{VERSION} - Rename & Merge PDFs")
    root.geometry("1100x800")
    root.resizable(True, True)
    root.minsize(900, 700)
    app = RenamergedGUI(root)
    root.mainloop()

class RenamergedGUI:
    def __init__(self, root):
        self.root = root
        self.theme = Theme()
        self.settings_manager = SettingsManager()
        
        # Load user settings
        saved_settings = self.settings_manager.load_settings()
        
        self.current_theme = saved_settings.get("theme", "dark")
        self.colors = self.theme.get_colors(self.current_theme)
        self.mode_var = ctk.StringVar(value=saved_settings.get("mode", "Rename dan Merge"))
        # Path variables - not saved in user settings (session-specific)
        self.input_path_var = tk.StringVar(value="")
        self.output_path_var = tk.StringVar(value="")
        
        # Auto-save untuk checkbox settings dengan throttling
        self._save_timer = None
        self._save_timer_lock = threading.Lock()
        self._cleanup_done = False
        self._background_threads = []  # Track background threads
        self._trace_ids = []  # Track trace IDs for cleanup
        
        # Setup trace callbacks with cleanup tracking
        def create_trace_callback(callback_func):
            def wrapper(*args):
                if not self._cleanup_done:
                    callback_func()
            return wrapper
        
        # Setup auto-save untuk perubahan settings dengan throttling (exclude paths)
        trace_id = self.mode_var.trace('w', create_trace_callback(self._throttled_save))
        self._trace_ids.append((self.mode_var, trace_id))
        
        self.progress_var = tk.DoubleVar(value=0)
        self.progress_percentage_var = tk.StringVar(value="0%")
        self.separator_var = tk.StringVar(value=saved_settings.get("separator", "-"))
        self.slash_replacement_var = tk.StringVar(value=saved_settings.get("slash_replacement", "_"))
        
        # Auto-save untuk separator dan slash replacement dengan throttling
        trace_id = self.separator_var.trace('w', create_trace_callback(self._throttled_save))
        self._trace_ids.append((self.separator_var, trace_id))
        trace_id = self.slash_replacement_var.trace('w', create_trace_callback(self._throttled_save))
        self._trace_ids.append((self.slash_replacement_var, trace_id))

        self.settings = {
            "use_name": tk.BooleanVar(value=saved_settings.get("use_name", True)),
            "use_date": tk.BooleanVar(value=saved_settings.get("use_date", True)),
            "use_reference": tk.BooleanVar(value=saved_settings.get("use_reference", True)),
            "use_faktur": tk.BooleanVar(value=saved_settings.get("use_faktur", True)),
            "wrap_reference": tk.BooleanVar(value=saved_settings.get("wrap_reference", False)),
            "component_order": saved_settings.get("component_order", None)
        }
        
        for key, var in self.settings.items():
            if hasattr(var, 'trace'):  # Hanya untuk StringVar, BooleanVar, dll
                trace_id = var.trace('w', create_trace_callback(self._throttled_save))
                self._trace_ids.append((var, trace_id))

        # Create scrollable main container
        self.main_frame = ctk.CTkScrollableFrame(
            self.root, 
            fg_color=self.colors["bg"],
            scrollbar_fg_color=self.colors["surface"],
            scrollbar_button_color=self.colors["primary"],
            scrollbar_button_hover_color=self.colors["primary_hover"]
        )
        self.main_frame.pack(expand=True, fill="both", padx=self.theme.spacing["lg"], pady=self.theme.spacing["lg"])
        
        # Configure responsive grid
        self.main_frame.grid_columnconfigure(0, weight=1)

        self.header = HeaderComponent(self.main_frame, self.colors, self.switch_theme)
        self.mode_selection = ModeSelectionComponent(self.main_frame, self.colors, self.mode_var, self.settings, self.separator_var, self.slash_replacement_var, self)
        self.file_input_output = FileInputOutputComponent(self.main_frame, self.colors, self.input_path_var, self.output_path_var)
        self.pdf_counter = PDFCounterComponent(self.main_frame, self.colors, self.input_path_var)
        self.file_list = FileListComponent(self.main_frame, self.colors, self.input_path_var)
        self.progress_bar = ProgressBarComponent(self.main_frame, self.colors, self.progress_var, self.progress_percentage_var)
        self.statistics = StatisticsComponent(self.main_frame, self.colors)
        self.output_location = OutputLocationComponent(self.main_frame, self.colors)
        
        # Create process button logic (but use the button in file_input_output)
        self.process_button = ProcessButtonComponent(
            self.main_frame, self.colors, self.input_path_var, self.output_path_var,
            self.mode_var, self.settings, self.progress_var, self.progress_percentage_var,
            self.statistics, self.output_location, self.mode_selection, self
        )
        
        # Connect the process command to the new button in file_input_output
        self.file_input_output.set_process_command(self.process_button.process)
        
        # Add other components here (will be positioned later)
        # Copyright footer - moved to bottom after all other components
        self.footer_card = ctk.CTkFrame(
            self.main_frame,
            fg_color=self.colors["surface"],
            border_width=1,
            border_color=self.colors["border"],
            corner_radius=12
        )
        self.footer_card.grid(row=14, column=0, sticky="ew", pady=(20, 16), padx=4)
        
        self.copyright_label = ctk.CTkLabel(
            self.footer_card,
            text="© 2025 Renamerged - Made with ❤️",
            font=("Inter", 10),
            text_color=self.colors["text_muted"],
            anchor="center"
        )
        self.copyright_label.pack(pady=16, padx=24)

        self.root.bind("<Left>", lambda event: self.mode_selection.move_left(event))
        self.root.bind("<Right>", lambda event: self.mode_selection.move_right(event))
        
        # Setup window close handler untuk save settings
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

    def switch_theme(self):
        """Switch between dark and light themes"""
        self.current_theme = "light" if self.current_theme == "dark" else "dark"
        ctk.set_appearance_mode(self.current_theme)
        self.colors = self.theme.get_colors(self.current_theme)
        
        # Update main frame colors
        self.main_frame.configure(fg_color=self.colors["bg"])
        
        # Update footer
        self.footer_card.configure(
            fg_color=self.colors["surface"],
            border_color=self.colors["border"]
        )
        self.copyright_label.configure(text_color=self.colors["text_muted"])
        
        # Update all components
        self.header.update_theme(self.colors)
        self.mode_selection.update_theme(self.colors)
        self.file_input_output.update_theme(self.colors)
        self.pdf_counter.update_theme(self.colors)
        
        # Update other components if they have update_theme method
        if hasattr(self.file_list, 'update_theme'):
            self.file_list.update_theme(self.colors)
        if hasattr(self.progress_bar, 'update_theme'):
            self.progress_bar.update_theme(self.colors)
        if hasattr(self.statistics, 'update_theme'):
            self.statistics.update_theme(self.colors)
        if hasattr(self.output_location, 'update_theme'):
            self.output_location.update_theme(self.colors)
        
        # Save theme preference
        self._throttled_save()
    
    def _throttled_save(self):
        """Save settings dengan delay untuk menghindari terlalu sering save"""
        with self._save_timer_lock:
            if self._save_timer and self._save_timer.is_alive():
                self._save_timer.cancel()
                try:
                    self._save_timer.join(timeout=0.1)  # Wait briefly for timer to finish
                except:
                    pass
            
            self._save_timer = threading.Timer(1.0, self.save_current_settings)
            self._save_timer.daemon = True  # Make timer thread daemon
            self._save_timer.start()
    
    def save_current_settings(self):
        """Simpan settings saat ini ke file (tanpa path yang bersifat session-specific)"""
        current_settings = {
            "theme": self.current_theme,
            "mode": self.mode_var.get() if hasattr(self.mode_var, 'get') else self.mode_var,
            "separator": self.separator_var.get() if hasattr(self.separator_var, 'get') else self.separator_var,
            "slash_replacement": self.slash_replacement_var.get() if hasattr(self.slash_replacement_var, 'get') else self.slash_replacement_var,
            "use_name": self.settings["use_name"].get() if hasattr(self.settings["use_name"], 'get') else self.settings["use_name"],
            "use_date": self.settings["use_date"].get() if hasattr(self.settings["use_date"], 'get') else self.settings["use_date"],
            "use_reference": self.settings["use_reference"].get() if hasattr(self.settings["use_reference"], 'get') else self.settings["use_reference"],
            "use_faktur": self.settings["use_faktur"].get() if hasattr(self.settings["use_faktur"], 'get') else self.settings["use_faktur"],
            "wrap_reference": self.settings["wrap_reference"].get() if hasattr(self.settings["wrap_reference"], 'get') else self.settings["wrap_reference"],
            "component_order": self.mode_selection.get_component_order() if hasattr(self.mode_selection, 'get_component_order') else self.settings.get("component_order", None),
            "settings_expanded": self.mode_selection.is_expanded if hasattr(self.mode_selection, 'is_expanded') else True
        }
        
        return self.settings_manager.save_settings(current_settings)
    
    def cleanup_resources(self):
        """Clean up all resources before closing"""
        if self._cleanup_done:
            return
            
        self._cleanup_done = True
        
        try:
            # Cancel and wait for timer thread
            with self._save_timer_lock:
                if self._save_timer and self._save_timer.is_alive():
                    self._save_timer.cancel()
                    try:
                        self._save_timer.join(timeout=2.0)
                    except:
                        pass
                        
            # Clean up any background threads
            for thread in self._background_threads:
                if thread and thread.is_alive():
                    try:
                        if hasattr(thread, 'cancel'):
                            thread.cancel()
                        thread.join(timeout=1.0)
                    except:
                        pass
                        
            # Save settings immediately
            self.save_current_settings()
            
            # Clean up trace callbacks to prevent memory leaks
            for var, trace_id in self._trace_ids:
                try:
                    var.trace_vdelete('w', trace_id)
                except:
                    pass
            self._trace_ids.clear()
            
            # Close any open file handles in components
            if hasattr(self, 'pdf_counter') and self.pdf_counter:
                self.pdf_counter.stop_monitoring()
                
        except Exception as e:
            # Use logging instead of print for GUI apps
            try:
                from src.utils.utils import log_message, Fore
                log_message(f"Error during cleanup: {str(e)}", Fore.RED)
            except:
                pass
    
    def on_closing(self):
        """Handler ketika aplikasi ditutup"""
        try:
            self.cleanup_resources()
        finally:
            try:
                self.root.quit()  # Stop mainloop
            except:
                pass
            try:
                self.root.destroy()  # Destroy window
            except:
                pass
