import os
from src.pdf.pdf_utils import extract_info_from_pdf, generate_filename, validate_pdf
from src.utils.utils import log_message, Fore

def check_long_filenames(input_directory, settings, log_callback=None):
    """
    Periksa apakah ada file yang akan menghasilkan nama file terlalu panjang
    Return: (has_long_filenames, long_filename_list, sample_filenames)
    """
    
    # Ambil pengaturan separator
    separator = settings.get("separator", "-")
    slash_replacement = settings.get("slash_replacement", "_")
    # Wrap reference option
    wrap_ref_var = settings.get("wrap_reference") if isinstance(settings, dict) else None
    try:
        wrap_reference = bool(wrap_ref_var.get()) if hasattr(wrap_ref_var, 'get') else bool(wrap_ref_var)
    except Exception:
        wrap_reference = False
    
    pdf_files = [f for f in os.listdir(input_directory) if f.endswith('.pdf')]
    
    long_filenames = []
    sample_filenames = []
    max_safe_length = 150  # Batas aman untuk checking
    
    for filename in pdf_files[:5]:  # Check hanya 5 file pertama untuk sample
        pdf_path = os.path.join(input_directory, filename)
        
        if not validate_pdf(pdf_path):
            continue
            
        try:
            id_tku_seller, partner_name, faktur_number, date, reference = extract_info_from_pdf(pdf_path, log_callback)
            
            if partner_name == "Nama tidak ditemukan":
                continue
                
            # Generate filename tanpa batasan untuk check panjang asli
            # Kita perlu test dengan original generator tanpa truncation
            parts = []
            component_values = {
                "Nama Lawan Transaksi": (partner_name, settings.get("use_name")),
                "Tanggal Faktur Pajak": (date, settings.get("use_date")),
                # Terapkan penggantian '/' dan opsi bungkus kurung untuk referensi
                "Referensi": ( 
                    (f"({reference.replace('/', slash_replacement)})" if (reference and wrap_reference) else 
                     (reference.replace('/', slash_replacement) if reference else "NoRef")),
                    settings.get("use_reference")
                ),
                "Nomor Faktur Pajak": (faktur_number, settings.get("use_faktur"))
            }
            
            component_order = settings.get("component_order", None)
            if component_order:
                for component_name in component_order:
                    value, var = component_values.get(component_name, ("", None))
                    if var and hasattr(var, 'get') and var.get():
                        if component_name == "Nomor Faktur Pajak" and value == "NoFaktur":
                            continue
                        parts.append(value)
            else:
                for key, (value, var) in component_values.items():
                    if var and hasattr(var, 'get') and var.get():
                        if key == "Nomor Faktur Pajak" and value == "NoFaktur":
                            continue
                        parts.append(value)
            
            if not parts:
                parts.append("unnamed")
            
            test_filename = separator.join(parts) + ".pdf"
            
            # Jika filename asli > max_safe_length, tambahkan ke list
            if len(test_filename) > max_safe_length:
                long_filenames.append({
                    'original_file': filename,
                    'generated_filename': test_filename,
                    'length': len(test_filename),
                    'partner_name': partner_name,
                    'reference': reference
                })
            
            # Simpan sample (3 file pertama)
            if len(sample_filenames) < 3:
                sample_filenames.append({
                    'original_file': filename,
                    'generated_filename': test_filename,
                    'length': len(test_filename)
                })
                
        except Exception as e:
            log_message(f"Error checking {filename}: {str(e)}", Fore.YELLOW, log_callback=log_callback)
            continue
    
    has_long_filenames = len(long_filenames) > 0
    
    if has_long_filenames:
        log_message(f"Warning: Ditemukan {len(long_filenames)} file dengan nama terlalu panjang (>{max_safe_length} chars)", 
                   Fore.YELLOW, log_callback=log_callback)
    
    return has_long_filenames, long_filenames, sample_filenames
