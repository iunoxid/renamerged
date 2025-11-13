import customtkinter as ctk

class ProgressBarComponent:
    def __init__(self, parent, colors, progress_var, progress_percentage_var):
        self.parent = parent
        self.colors = colors
        self.progress_var = progress_var
        self.progress_percentage_var = progress_percentage_var

        # Progress Bar
        self.progress_frame = ctk.CTkFrame(self.parent, fg_color="transparent")
        self.progress_frame.grid(row=10, column=0, columnspan=2, sticky="ew", padx=5, pady=(0, 10))

        # Berikan lebar minimum untuk kolom 1 agar label persentase tidak terpotong
        self.progress_frame.grid_columnconfigure(0, weight=1)  # Kolom 0 untuk progress bar, ambil sisa ruang
        self.progress_frame.grid_columnconfigure(1, weight=0, minsize=50)  # Kolom 1 untuk persentase, lebar minimum 50px

        ctk.CTkLabel(self.progress_frame, text="Progress:", font=("Roboto", 12),
                     text_color=self.colors["fg"]).grid(row=0, column=0, sticky="w", pady=(0, 5))

        # Konfigurasi CTkProgressBar
        self.progress_bar = ctk.CTkProgressBar(self.progress_frame,
                                               mode="determinate",
                                               progress_color="#00FF00",
                                               fg_color="#555555",
                                               width=750, height=30, corner_radius=15)
        self.progress_bar.set(0)  # Set nilai awal ke 0
        self.progress_bar.grid(row=1, column=0, sticky="ew", padx=(5, 5))

        # Label persentase dengan padding yang disesuaikan
        ctk.CTkLabel(self.progress_frame, textvariable=self.progress_percentage_var, font=("Roboto", 12),
                     text_color=self.colors["fg"]).grid(row=1, column=1, padx=(10, 10))  # Tambah padding untuk ruang lebih

    def set_progress(self, value):
        """Mengatur nilai progress bar secara langsung (skala 0 hingga 1)."""
        # Clamp and sanitize value to avoid rendering issues
        try:
            v = float(value)
        except (TypeError, ValueError):
            v = 0.0
        # Handle NaN/inf
        if v != v or v == float("inf") or v == float("-inf"):
            v = 0.0
        v = max(0.0, min(1.0, v))
        # Only set; do not call update()/update_idletasks() to avoid re-entrant mainloop
        self.progress_bar.set(v)

    def update_theme(self, colors):
        self.colors = colors
        for child in self.progress_frame.winfo_children():
            if isinstance(child, ctk.CTkLabel):
                child.configure(text_color=self.colors["fg"])
        self.progress_bar.configure(fg_color="#555555", progress_color="#00FF00")
