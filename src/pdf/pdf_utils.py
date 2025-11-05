import pdfplumber
import re
import os
import shutil
from pypdf import PdfWriter, PdfReader
from src.utils.utils import log_message, Fore

def validate_pdf(pdf_path):
    """Memvalidasi apakah file PDF dapat dibaca (tidak korup)."""
    try:
        with pdfplumber.open(pdf_path) as pdf:
            if pdf.pages:
                return True
        return False
    except (IOError, OSError, ImportError, AttributeError) as e:
        return False
    except Exception:
        # Unknown error, PDF is likely invalid
        return False

def extract_info_from_pdf(pdf_path, log_callback=None):
    """Mengambil informasi dari PDF: ID TKU, Nama Partner, Nomor Faktur, Tanggal, dan Referensi."""
    try:
        with pdfplumber.open(pdf_path) as pdf:
            text = "".join(page.extract_text() + "\n" for page in pdf.pages if page.extract_text())

        partner_match = re.search(r'Pembeli Barang Kena Pajak\s*/\s*Penerima Jasa Kena Pajak:\s*Nama\s*:\s*(.+?)\s*Alamat', text, re.DOTALL)
        partner_name = partner_match.group(1).strip().title() if partner_match else "Nama tidak ditemukan"

        id_tku_seller_match = re.search(r'#?(\d{22})', text)
        id_tku_seller = id_tku_seller_match.group(1).strip() if id_tku_seller_match else "IDTKU_Tidak_Ditemukan"

        date_match = re.search(r'(\d{1,2})\s+([A-Za-z]+)\s+(\d{4})', text)
        month_dict = {
            "Januari": "01", "Februari": "02", "Maret": "03", "April": "04", "Mei": "05", "Juni": "06",
            "Juli": "07", "Agustus": "08", "September": "09", "Oktober": "10", "November": "11", "Desember": "12"
        }
        date = f"{date_match.group(1)}-{month_dict.get(date_match.group(2), '00')}-{date_match.group(3)}" if date_match else "Tanggal tidak ditemukan"

        # Perbaiki regex untuk nomor faktur dengan batasan panjang dan format yang lebih spesifik
        faktur_match = re.search(r'Faktur Pajak:\s*([\w\d\-/.]{1,50}?)(?:\s|$|\n)', text, re.IGNORECASE)
        faktur_number = faktur_match.group(1).strip() if faktur_match else "NoFaktur"
        
        # Tambahan validasi untuk nomor faktur
        if faktur_number and faktur_number != "NoFaktur":
            # Hapus karakter kontrol dan whitespace berlebih
            faktur_number = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', faktur_number)
            faktur_number = re.sub(r'\s+', ' ', faktur_number).strip()
            # Batasi panjang maksimal 50 karakter
            if len(faktur_number) > 50:
                faktur_number = faktur_number[:50].strip()
        
        if faktur_number == "" or not faktur_number:
            faktur_number = "NoFaktur"

        # Perbaikan regex referensi: menangani multi-line dan posisi tidak stabil
        # Pattern yang lebih fleksibel untuk menangkap referensi yang bisa multi-line
        ref_patterns = [
            r'Referensi:\s*([^}]*?)(?:\n\s*\n|\n\s*[A-Z][^:]*:|$)',  # Pattern utama
            r'Referensi:\s*([^}]*?)(?:\n\s*Pembeli|$)',              # Alternative pattern
            r'Referensi:\s*(.*?)(?:\n\s*(?:[A-Z][^:]*:|$))',         # Fallback pattern
        ]
        
        reference = ""
        for pattern in ref_patterns:
            ref_match = re.search(pattern, text, re.MULTILINE | re.DOTALL)
            if ref_match and ref_match.group(1).strip():
                reference = ref_match.group(1).strip()
                break
        
        # Tambahan validasi dan sanitasi untuk referensi
        if reference:
            # Hapus karakter kontrol
            reference = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', reference)
            # Ganti newline dan tab dengan spasi
            reference = re.sub(r'[\n\r\t]+', ' ', reference)
            # Normalisasi whitespace berlebih
            reference = re.sub(r'\s+', ' ', reference).strip()
            # Ganti karakter yang tidak bisa digunakan untuk nama file dengan spasi
            # Biarkan '/' tetap ada agar bisa diganti sesuai pilihan user (slash_replacement) di generate_filename
            invalid_chars = r'[<>:"\\|?*()]'  # Tanpa '/'
            reference = re.sub(invalid_chars, ' ', reference)
            # Hapus karakter trailing yang tidak diinginkan
            reference = re.sub(r'[)\]\}]+$', '', reference).strip()
            # Normalisasi spasi lagi setelah penggantian
            reference = re.sub(r'\s+', ' ', reference).strip()
            # Batasi panjang maksimal 200 karakter (diperbesar untuk referensi panjang)
            if len(reference) > 200:
                reference = reference[:200].strip()
        

        return id_tku_seller, partner_name, faktur_number, date, reference
    except (FileNotFoundError, PermissionError) as e:
        if log_callback:
            log_callback(f"❌ File access error {os.path.basename(pdf_path)}: {str(e)}")
        raise
    except (ImportError, AttributeError) as e:
        if log_callback:
            log_callback(f"❌ PDF library error {os.path.basename(pdf_path)}: {str(e)}")
        raise
    except Exception as e:
        if log_callback:
            log_callback(f"❌ Unexpected error reading {os.path.basename(pdf_path)}: {str(e)}")
        raise

def generate_filename(partner_name, faktur_number, date, reference, settings, component_order=None, separator="-", slash_replacement="_", max_length=None):
    """Membuat nama file berdasarkan urutan komponen dari GUI dengan pemisah dan pengganti garis miring."""
    invalid_chars = '<>:"/\\|?*'
    if any(char in separator for char in invalid_chars) or any(char in slash_replacement for char in invalid_chars):
        log_message(f"Error: Pemisah '{separator}' atau pengganti garis miring '{slash_replacement}' mengandung karakter tidak valid!", Fore.RED)
        raise ValueError("Pemisah atau pengganti garis miring mengandung karakter tidak valid!")

    # Penanganan karakter invalid untuk referensi sudah dilakukan di extract_info_from_pdf
    # Tambahan penanganan slash jika masih ada
    if reference and "/" in reference:
        reference = reference.replace("/", slash_replacement)

    parts = []
    # Opsi bungkus referensi dalam kurung
    wrap_ref_var = settings.get("wrap_reference") if isinstance(settings, dict) else None
    wrap_reference = False
    if wrap_ref_var is not None:
        try:
            wrap_reference = bool(wrap_ref_var.get()) if hasattr(wrap_ref_var, 'get') else bool(wrap_ref_var)
        except Exception:
            wrap_reference = False

    # Siapkan nilai referensi untuk ditampilkan (setelah penggantian slash)
    display_reference = reference if reference else "NoRef"
    if display_reference and display_reference != "NoRef" and wrap_reference:
        display_reference = f"({display_reference})"
    component_values = {
        "Nama Lawan Transaksi": (partner_name, settings.get("use_name")),
        "Tanggal Faktur Pajak": (date, settings.get("use_date")),
        "Referensi": (display_reference, settings.get("use_reference")),
        "Nomor Faktur Pajak": (faktur_number, settings.get("use_faktur"))
    }


    if component_order:
        for component_name in component_order:
            value, var = component_values.get(component_name, ("", None))
            if var and hasattr(var, 'get') and var.get():
                # Validasi nilai untuk Nomor Faktur Pajak
                if component_name == "Nomor Faktur Pajak" and value == "NoFaktur":
                    continue
                parts.append(value)
    else:
        for key, (value, var) in component_values.items():
            if var and hasattr(var, 'get') and var.get():
                # Validasi nilai untuk Nomor Faktur Pajak
                if key == "Nomor Faktur Pajak" and value == "NoFaktur":
                    continue
                parts.append(value)

    if not parts:
        parts.append("unnamed")

    filename = separator.join(parts) + ".pdf"
    
    # Gunakan max_length yang dipilih user, atau default conservative
    if max_length is not None:
        max_filename_length = max_length
    else:
        # VERY AGGRESSIVE filename length limiting untuk Windows compatibility
        max_filename_length = 130  # Default conservative untuk semua separator
    
    if len(filename) > max_filename_length:
        
        extension = ".pdf"
        available_length = max_filename_length - len(extension)
        
        # Strategy BARU: Prioritaskan nama, tanggal, dan nomor faktur - potong referensi
        if len(parts) >= 2:  # Minimal ada nama dan komponen lain
            nama = parts[0]
            tanggal = ""
            referensi = ""
            nomor_faktur = ""
            
            # Identifikasi komponen berdasarkan urutan (bisa berbeda karena component_order)
            # Cari tanggal (format DD-MM-YYYY)
            # Cari nomor faktur (biasanya angka panjang atau format khusus)
            # Sisanya adalah referensi
            
            tanggal_found = False
            faktur_found = False
            
            for i, part in enumerate(parts[1:], 1):  # Skip nama (index 0)
                # Deteksi tanggal (format DD-MM-YYYY atau DD-MM-YY)
                if not tanggal_found and re.match(r'\d{1,2}-\d{1,2}-\d{2,4}', part):
                    tanggal = part
                    tanggal_found = True
                    continue
                    
                # Deteksi nomor faktur (biasanya angka panjang atau alphanumeric dengan pola tertentu)
                # Nomor faktur biasanya di akhir dan berupa angka panjang
                if not faktur_found and (part.isdigit() or re.match(r'^[\d\w\-/]{8,}$', part)) and i == len(parts) - 1:
                    nomor_faktur = part
                    faktur_found = True
                    continue
                    
                # Sisanya dianggap referensi
                if referensi:
                    referensi += separator + part
                else:
                    referensi = part
            
            # Jika tidak ada nomor faktur terdeteksi, ambil komponen terakhir sebagai faktur
            if not nomor_faktur and len(parts) > 1:
                nomor_faktur = parts[-1]
                # Hapus dari referensi jika sudah diambil sebagai faktur
                referensi_parts = referensi.split(separator) if referensi else []
                if referensi_parts and referensi_parts[-1] == nomor_faktur:
                    referensi = separator.join(referensi_parts[:-1])
            
            # Hitung ruang yang tersedia untuk referensi
            # Format target: {nama}-{tanggal}-{referensi...} {nomor_faktur}.pdf
            fixed_parts = [nama]
            if tanggal:
                fixed_parts.append(tanggal)
            
            faktur_suffix = f" {nomor_faktur}" if nomor_faktur else ""
            fixed_length = len(separator.join(fixed_parts)) + len(faktur_suffix) + 4  # +4 for .pdf
            
            if separator and len(fixed_parts) > 1:
                fixed_length += len(separator)  # For separator before referensi
            
            remaining_length = available_length - fixed_length
            
            if remaining_length > 10 and referensi:  # Minimal 10 char untuk referensi
                # Potong referensi jika terlalu panjang dengan visual delimiter {}
                if len(referensi) > remaining_length - 5:  # -5 untuk {...}
                    referensi_dipotong = referensi[:remaining_length-5] + "..."
                    referensi_final = f"{{{referensi_dipotong}}}"  # Wrap dengan kurung kurawal
                else:
                    referensi_final = referensi  # Tidak dipotong, tidak perlu kurung kurawal
                
                # Build filename
                base_parts = fixed_parts + [referensi_final]
                filename = separator.join(base_parts) + faktur_suffix + ".pdf"
            else:
                # Hanya nama, tanggal, dan faktur
                filename = separator.join(fixed_parts) + faktur_suffix + ".pdf"
        else:
            # Fallback: potong filename secara brutal
            filename_without_ext = filename[:-4]  # Remove .pdf
            filename = filename_without_ext[:available_length-3] + "....pdf"
        
    
    return filename

def copy_file_with_unique_name(source_path, destination_path, log_callback=None):
    """Menyalin file ke lokasi tujuan dengan menambahkan nomor unik jika file sudah ada."""
    counter = 1
    original_destination = destination_path
    max_attempts = 1000  # Safety limit to prevent infinite loop
    
    while os.path.exists(destination_path) and counter <= max_attempts:
        base, ext = os.path.splitext(original_destination)
        destination_path = f"{base} ({counter}){ext}"
        counter += 1
    
    # If we hit the max attempts, use timestamp to ensure uniqueness
    if counter > max_attempts:
        import time
        timestamp = int(time.time())
        base, ext = os.path.splitext(original_destination)
        destination_path = f"{base}__{timestamp}{ext}"
        log_message(f"⚠️ Hit max naming attempts, using timestamp for {os.path.basename(destination_path)}", Fore.YELLOW, log_callback=log_callback)

    try:
        # Check if source file is accessible and not locked
        if not os.access(source_path, os.R_OK):
            raise PermissionError(f"Cannot read source file: {source_path}")
            
        # Check if destination directory is writable
        dest_dir = os.path.dirname(destination_path)
        if not os.access(dest_dir, os.W_OK):
            raise PermissionError(f"Cannot write to destination directory: {dest_dir}")
        
        # Try to detect if file is locked by attempting to open it
        try:
            with open(source_path, 'rb') as test_file:
                # Try to read first few bytes to ensure file is not locked
                test_file.read(1024)
        except (PermissionError, IOError) as e:
            if "being used by another process" in str(e) or "access denied" in str(e).lower():
                raise IOError(f"File {os.path.basename(source_path)} is currently open in another application. Please close it and try again.")
            raise
        
        # Perform the actual copy with retry mechanism
        max_retries = 3
        retry_delay = 0.5
        
        for attempt in range(max_retries):
            try:
                shutil.copy2(source_path, destination_path)  # copy2 preserves metadata
                log_message(f"📂 {os.path.basename(destination_path)} dipindahkan ke {os.path.dirname(destination_path)}", Fore.BLUE, log_callback=log_callback)
                return 1
                
            except (PermissionError, IOError) as e:
                if attempt < max_retries - 1:
                    import time
                    log_message(f"⚠️ Copy attempt {attempt + 1} failed, retrying in {retry_delay}s...", Fore.YELLOW, log_callback=log_callback)
                    time.sleep(retry_delay)
                    retry_delay *= 2  # Exponential backoff
                    continue
                else:
                    raise
                    
    except PermissionError as e:
        log_message(f"❌ Permission error copying {os.path.basename(source_path)}: {str(e)}", Fore.RED, log_callback=log_callback)
        raise
    except (IOError, OSError, shutil.Error) as e:
        log_message(f"❌ Error copying file {os.path.basename(source_path)}: {str(e)}", Fore.RED, log_callback=log_callback)
        raise

def merge_pdfs(pdf_paths, output_path, log_callback=None):
    """Menggabungkan beberapa file PDF menjadi satu file."""
    merger = None
    pdf_readers = []
    
    try:
        merger = PdfWriter()
        
        # Open each PDF file and keep track of readers
        for pdf_path in pdf_paths:
            try:
                reader = PdfReader(pdf_path)
                pdf_readers.append(reader)
                for page in reader.pages:
                    merger.add_page(page)
            except (FileNotFoundError, PermissionError) as e:
                log_message(f"⚠️ File access error {os.path.basename(pdf_path)}: {str(e)}", Fore.YELLOW, log_callback=log_callback)
                continue
            except (ImportError, AttributeError) as e:
                log_message(f"⚠️ PDF library error {os.path.basename(pdf_path)}: {str(e)}", Fore.YELLOW, log_callback=log_callback)
                continue
            except Exception as e:
                log_message(f"⚠️ Unexpected error reading {os.path.basename(pdf_path)}: {str(e)}", Fore.YELLOW, log_callback=log_callback)
                continue
                
        # Write merged PDF
        with open(output_path, 'wb') as output_file:
            merger.write(output_file)
            
        log_message(f"✅ File digabungkan ke {output_path}", Fore.GREEN, log_callback=log_callback)
        
    except (FileNotFoundError, PermissionError) as e:
        log_message(f"❌ File access error during merge {os.path.basename(output_path)}: {str(e)}", Fore.RED, log_callback=log_callback)
        raise
    except (IOError, OSError) as e:
        log_message(f"❌ I/O error during merge {os.path.basename(output_path)}: {str(e)}", Fore.RED, log_callback=log_callback)
        raise
    except Exception as e:
        log_message(f"❌ Unexpected error during merge {os.path.basename(output_path)}: {str(e)}", Fore.RED, log_callback=log_callback)
        raise
        
    finally:
        # Explicitly close all resources in reverse order
        # Close all PDF readers first
        for reader in pdf_readers:
            try:
                # Close stream if it exists
                if hasattr(reader, 'stream') and reader.stream:
                    reader.stream.close()
                # Close reader if it has close method
                if hasattr(reader, 'close'):
                    reader.close()
            except Exception as e:
                if log_callback:
                    log_message(f"⚠️ Error closing PDF reader: {str(e)}", Fore.YELLOW, log_callback=log_callback)
                
        # Clear the readers list to free memory references
        pdf_readers.clear()
        
        # Close merger last
        if merger:
            try:
                merger.close()
            except Exception as e:
                if log_callback:
                    log_message(f"⚠️ Error closing PDF merger: {str(e)}", Fore.YELLOW, log_callback=log_callback)
