import customtkinter as ctk
import tkinter as tk
from src.components.draggable_component import DraggableComponent
from src.components.tooltip import Tooltip

class ModeSelectionComponent:
    def __init__(self, parent, colors, mode_var, settings, separator_var=None, slash_replacement_var=None, gui_reference=None):
        self.parent = parent
        self.colors = colors
        self.mode_var = mode_var
        self.settings = settings
        self.separator_var = separator_var
        self.slash_replacement_var = slash_replacement_var
        self.gui_reference = gui_reference
        self.components = []
        self.component_order = []
        self.selected_component = None
        self.tooltips = []

        # Pemetaan untuk konversi display ke nilai aktual
        self.option_mapping = {
            "(spasi)": " ",
            "-": "-",
            "_": "_"
        }
        self.reverse_mapping = {v: k for k, v in self.option_mapping.items()}

        # Settings card
        self.settings_card = ctk.CTkFrame(
            self.parent,
            fg_color=self.colors["surface"],
            border_width=1,
            border_color=self.colors["border"],
            corner_radius=16
        )
        self.settings_card.grid(row=3, column=0, sticky="ew", pady=(0, 16), padx=4)
        self.settings_card.grid_columnconfigure(0, weight=1)

        # Card header with toggle button
        self.header_frame = ctk.CTkFrame(self.settings_card, fg_color="transparent")
        self.header_frame.grid(row=0, column=0, sticky="ew", padx=24, pady=(20, 16))
        self.header_frame.grid_columnconfigure(0, weight=1)
        self.header_frame.grid_columnconfigure(1, weight=0)
        
        self.card_header = ctk.CTkLabel(
            self.header_frame,
            text="⚙️ Pengaturan Proses",
            font=("Inter", 18, "bold"),
            text_color=self.colors["fg"],
            anchor="w"
        )
        self.card_header.grid(row=0, column=0, sticky="ew")
        
        # Load expandable state from settings
        from src.utils.settings_manager import SettingsManager
        settings_manager = SettingsManager()
        saved_settings = settings_manager.load_settings()
        self.is_expanded = saved_settings.get("settings_expanded", True)  # Default expanded
        
        # Toggle button with chevron
        self.toggle_btn = ctk.CTkButton(
            self.header_frame,
            text="🔽",  # Down arrow when expanded
            command=self.toggle_expand,
            fg_color="transparent",
            text_color=self.colors["text_muted"],
            hover_color=self.colors["surface_light"],
            font=("Inter", 16),
            width=32,
            height=32,
            corner_radius=8
        )
        self.toggle_btn.grid(row=0, column=1, sticky="e", padx=(12, 0))

        # Mode selection section
        self.mode_section = ctk.CTkFrame(self.settings_card, fg_color="transparent")
        self.mode_section.grid(row=1, column=0, sticky="ew", padx=24, pady=(0, 20))
        self.mode_section.grid_columnconfigure(0, weight=0)
        self.mode_section.grid_columnconfigure(1, weight=1)
        self.mode_section.grid_rowconfigure(0, weight=1)

        self.mode_label = ctk.CTkLabel(
            self.mode_section,
            text="🎯 Mode Pemrosesan:",
            font=("Inter", 13, "bold"),
            text_color=self.colors["fg"],
            anchor="w"
        )
        self.mode_label.grid(row=0, column=0, sticky="w", padx=(0, 20), pady=2)

        self.mode_menu = ctk.CTkOptionMenu(
            self.mode_section,
            values=["Rename Saja", "Rename dan Merge"],
            variable=self.mode_var,
            command=self.toggle_mode_options,
            fg_color=self.colors["primary"],
            text_color="#FFFFFF",
            font=("Inter", 12, "bold"),
            dropdown_fg_color=self.colors["surface"],
            dropdown_text_color=self.colors["fg"],
            dropdown_hover_color=self.colors["surface_light"],
            button_color=self.colors["primary_hover"],
            button_hover_color=self.colors["primary"],
            width=180,
            height=40,
            corner_radius=12
        )
        self.mode_menu.grid(row=0, column=1, sticky="w")

        # Components section header
        self.components_header = ctk.CTkLabel(
            self.settings_card,
            text="📝 Komponen Nama File (untuk mode 'Rename Saja')",
            font=("Inter", 13, "bold"),
            text_color=self.colors["fg"]
        )
        self.components_header.grid(row=2, column=0, sticky="w", padx=24, pady=(0, 12))

        # Advanced settings section
        self.advanced_section = ctk.CTkFrame(self.settings_card, fg_color="transparent")
        self.advanced_section.grid(row=3, column=0, sticky="ew", padx=24, pady=(0, 20))
        self.advanced_section.grid_columnconfigure(0, weight=1)
        self.advanced_section.grid_columnconfigure(1, weight=1)

        # Separator settings
        self.separator_frame = ctk.CTkFrame(self.advanced_section, fg_color="transparent")
        self.separator_frame.grid(row=0, column=0, sticky="ew", padx=(0, 16))
        self.separator_frame.grid_columnconfigure(1, weight=1)

        self.separator_label = ctk.CTkLabel(
            self.separator_frame,
            text="🔗 Pemisah:",
            font=("Inter", 12, "bold"),
            text_color=self.colors["fg"],
            anchor="w"
        )
        self.separator_label.grid(row=0, column=0, sticky="w", pady=(0, 10))

        separator_tooltip_btn = ctk.CTkButton(
            self.separator_frame,
            text="ℹ️",
            width=24,
            height=24,
            fg_color=self.colors["info"],
            text_color="#FFFFFF",
            font=("Inter", 10),
            corner_radius=12,
            command=lambda: None
        )
        separator_tooltip_btn.grid(row=0, column=1, sticky="e", pady=(0, 8))

        separator_tooltip = Tooltip(
            separator_tooltip_btn,
            "Pilih pemisah untuk memisahkan komponen nama file PDF\n(contoh: Nama-Tanggal atau Nama_Tanggal)",
            self.colors,
            self,
            self.tooltips,
            self.separator_frame
        )
        self.tooltips.append(separator_tooltip)

        self.separator_menu = ctk.CTkOptionMenu(
            self.separator_frame,
            values=["-", "_", "(spasi)"],
            variable=self.separator_var,
            fg_color=self.colors["secondary"],
            text_color="#FFFFFF",
            font=("Inter", 11),
            dropdown_fg_color=self.colors["surface"],
            dropdown_text_color=self.colors["fg"],
            width=120,
            height=36,
            corner_radius=10
        )
        self.separator_menu.grid(row=1, column=0, columnspan=2, sticky="ew")

        # Slash replacement settings
        self.slash_frame = ctk.CTkFrame(self.advanced_section, fg_color="transparent")
        self.slash_frame.grid(row=0, column=1, sticky="ew", padx=(16, 0))
        self.slash_frame.grid_columnconfigure(1, weight=1)

        self.slash_label = ctk.CTkLabel(
            self.slash_frame,
            text="↗️ Pengganti '/':",
            font=("Inter", 12, "bold"),
            text_color=self.colors["fg"],
            anchor="w"
        )
        self.slash_label.grid(row=0, column=0, sticky="w", pady=(0, 10))

        slash_tooltip_btn = ctk.CTkButton(
            self.slash_frame,
            text="ℹ️",
            width=24,
            height=24,
            fg_color=self.colors["info"],
            text_color="#FFFFFF",
            font=("Inter", 10),
            corner_radius=12,
            command=lambda: None
        )
        slash_tooltip_btn.grid(row=0, column=1, sticky="e", pady=(0, 8))

        slash_tooltip = Tooltip(
            slash_tooltip_btn,
            "Pilih karakter untuk mengganti garis miring (/) di referensi\n(contoh: Ref/123 → Ref_123)",
            self.colors,
            self,
            self.tooltips,
            self.slash_frame
        )
        self.tooltips.append(slash_tooltip)

        self.slash_replacement_menu = ctk.CTkOptionMenu(
            self.slash_frame,
            values=["-", "_", "(spasi)"],
            variable=self.slash_replacement_var,
            fg_color=self.colors["secondary"],
            text_color="#FFFFFF",
            font=("Inter", 11),
            dropdown_fg_color=self.colors["surface"],
            dropdown_text_color=self.colors["fg"],
            width=120,
            height=36,
            corner_radius=10
        )
        self.slash_replacement_menu.grid(row=1, column=0, columnspan=2, sticky="ew")

        # Reference options
        self.reference_options_frame = ctk.CTkFrame(self.advanced_section, fg_color="transparent")
        self.reference_options_frame.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(12, 0))
        self.reference_options_frame.grid_columnconfigure(0, weight=1)

        self.wrap_ref_checkbox = ctk.CTkCheckBox(
            self.reference_options_frame,
            text="Bungkus Referensi dengan Kurung ( )",
            variable=self.settings.get("wrap_reference"),
            corner_radius=4,
            border_width=2,
            fg_color=self.colors["primary"],
            hover_color=self.colors["primary_hover"],
            border_color=self.colors["border_light"]
        )
        self.wrap_ref_checkbox.grid(row=0, column=0, sticky="w")

        # Draggable components container
        self.components_container_frame = ctk.CTkFrame(
            self.settings_card,
            fg_color=self.colors["bg"],
            border_width=1,
            border_color=self.colors["border_light"],
            corner_radius=12
        )
        self.components_container_frame.grid(row=4, column=0, sticky="ew", padx=24, pady=(0, 16))

        self.components_container = ctk.CTkFrame(self.components_container_frame, fg_color="transparent")
        self.components_container.pack(pady=16, padx=16, fill="x")

        # Instruction label with better text wrapping
        self.instruction_label = ctk.CTkLabel(
            self.settings_card,
            text="💡 Tip: Klik komponen untuk memilih, lalu gunakan panah ←/→ untuk mengatur urutan",
            font=("Inter", 11, "italic"),
            text_color=self.colors["text_muted"],
            anchor="w",
            wraplength=800
        )
        self.instruction_label.grid(row=5, column=0, sticky="ew", padx=24, pady=(0, 20))

        # Load saved component order or use default
        saved_order = saved_settings.get("component_order", [
            "Nama Lawan Transaksi",
            "Tanggal Faktur Pajak", 
            "Referensi",
            "Nomor Faktur Pajak"
        ])
        
        # Map component names to their variables
        component_map = {
            "Nama Lawan Transaksi": self.settings["use_name"],
            "Tanggal Faktur Pajak": self.settings["use_date"],
            "Referensi": self.settings["use_reference"],
            "Nomor Faktur Pajak": self.settings["use_faktur"]
        }
        
        # Build component_order using saved order
        self.component_order = [(name, component_map[name]) for name in saved_order if name in component_map]
        self._create_components()

        self.parent.bind("<Left>", self.move_left)
        self.parent.bind("<Right>", self.move_right)

        self.toggle_mode_options(self.mode_var.get())
        
        # Apply initial expanded/collapsed state based on saved settings
        if not self.is_expanded:
            self.toggle_btn.configure(text="▶️")  # Right arrow for collapsed
            self.mode_section.grid_remove()
            self.components_header.grid_remove()
            self.advanced_section.grid_remove()
            self.components_container_frame.grid_remove()
            self.instruction_label.grid_remove()
        else:
            self.toggle_btn.configure(text="🔽")  # Down arrow for expanded

    def _create_components(self):
        self.components = []
        for i, (text, var) in enumerate(self.component_order):
            if not hasattr(var, 'get'):
                raise ValueError(f"Komponen {text} memiliki variabel yang tidak valid: {var}")
            component = DraggableComponent(self.components_container, text, var, self._on_select, self.colors)
            # Better spacing between components
            padx = (0, 12) if i < len(self.component_order) - 1 else (0, 0)
            component.pack(side="left", padx=padx, pady=8)
            self.components.append(component)
        self._update_order()

    def _on_select(self, selected_component):
        for component in self.components:
            if component != selected_component:
                component.deselect()
        self.selected_component = selected_component

    def move_left(self, event):
        if self.selected_component and self.mode_var.get() == "Rename Saja":
            current_index = self.components.index(self.selected_component)
            if current_index > 0:
                self.components[current_index], self.components[current_index - 1] = self.components[current_index - 1], self.components[current_index]
                self._refresh_layout()
                self._update_order()

    def move_right(self, event):
        if self.selected_component and self.mode_var.get() == "Rename Saja":
            current_index = self.components.index(self.selected_component)
            if current_index < len(self.components) - 1:
                self.components[current_index], self.components[current_index + 1] = self.components[current_index + 1], self.components[current_index]
                self._refresh_layout()
                self._update_order()

    def _refresh_layout(self):
        for component in self.components:
            component.pack_forget()
        for i, component in enumerate(self.components):
            # Maintain consistent spacing after reordering
            padx = (0, 12) if i < len(self.components) - 1 else (0, 0)
            component.pack(side="left", padx=padx, pady=8)

    def _update_order(self):
        self.component_order = [(comp.text, comp.variable) for comp in self.components]
        # Save component order change to settings
        if self.gui_reference and hasattr(self.gui_reference, '_throttled_save'):
            self.gui_reference._throttled_save()

    def get_component_order(self):
        return [text for text, _ in self.component_order]

    def get_separator(self):
        """Mengembalikan nilai aktual pemisah berdasarkan pilihan user."""
        return self.option_mapping.get(self.separator_var.get(), "-")

    def get_slash_replacement(self):
        """Mengembalikan nilai aktual pengganti garis miring berdasarkan pilihan user."""
        return self.option_mapping.get(self.slash_replacement_var.get(), "_")

    def toggle_expand(self):
        """Toggle expand/collapse of settings sections"""
        self.is_expanded = not self.is_expanded
        
        if self.is_expanded:
            # Show all sections
            self.toggle_btn.configure(text="🔽")  # Down arrow
            self.mode_section.grid()
            self.toggle_mode_options(self.mode_var.get())  # Show mode-specific options
        else:
            # Hide all sections except header
            self.toggle_btn.configure(text="▶️")  # Right arrow
            self.mode_section.grid_remove()
            self.components_header.grid_remove()
            self.advanced_section.grid_remove()
            self.components_container_frame.grid_remove()
            self.instruction_label.grid_remove()
        
        # Save expanded state if GUI reference available
        if self.gui_reference and hasattr(self.gui_reference, '_throttled_save'):
            self.gui_reference._throttled_save()
    
    def toggle_mode_options(self, mode):
        """Show/hide components based on selected mode (only if expanded)"""
        if not self.is_expanded:
            return  # Don't show anything if collapsed
            
        if mode == "Rename Saja":
            self.components_header.grid()
            self.advanced_section.grid()
            self.components_container_frame.grid()
            self.instruction_label.grid()
        else:
            self.components_header.grid_remove()
            self.advanced_section.grid_remove()
            self.components_container_frame.grid_remove()
            self.instruction_label.grid_remove()

    def update_theme(self, colors):
        """Update theme colors for all components"""
        self.colors = colors
        
        # Temporarily disable tooltips during theme update
        for tooltip in self.tooltips:
            tooltip.disable()
        
        # Update main card
        self.settings_card.configure(
            fg_color=self.colors["surface"],
            border_color=self.colors["border"]
        )
        
        # Update headers and labels
        self.card_header.configure(text_color=self.colors["fg"])
        self.components_header.configure(text_color=self.colors["fg"])
        self.instruction_label.configure(text_color=self.colors["text_muted"])
        self.mode_label.configure(text_color=self.colors["fg"])
        self.separator_label.configure(text_color=self.colors["fg"])
        self.slash_label.configure(text_color=self.colors["fg"])
        if hasattr(self, 'wrap_ref_checkbox'):
            self.wrap_ref_checkbox.configure(text_color=self.colors["fg"],
                                             fg_color=self.colors["primary"],
                                             hover_color=self.colors["primary_hover"],
                                             border_color=self.colors["border_light"]) 
        
        # Update toggle button
        self.toggle_btn.configure(
            text_color=self.colors["text_muted"],
            hover_color=self.colors["surface_light"]
        )
        
        # Update mode menu
        self.mode_menu.configure(
            fg_color=self.colors["primary"],
            button_color=self.colors["primary_hover"],
            button_hover_color=self.colors["primary"],
            dropdown_fg_color=self.colors["surface"],
            dropdown_text_color=self.colors["fg"],
            dropdown_hover_color=self.colors["surface_light"]
        )
        
        # Update separator and slash replacement menus
        self.separator_menu.configure(
            fg_color=self.colors["secondary"],
            dropdown_fg_color=self.colors["surface"],
            dropdown_text_color=self.colors["fg"]
        )
        self.slash_replacement_menu.configure(
            fg_color=self.colors["secondary"],
            dropdown_fg_color=self.colors["surface"],
            dropdown_text_color=self.colors["fg"]
        )
        
        # Update components container
        self.components_container_frame.configure(
            fg_color=self.colors["bg"],
            border_color=self.colors["border_light"]
        )
        
        # Update draggable components
        for component in self.components:
            component.update_theme(colors)
        
        # Re-enable tooltips
        for tooltip in self.tooltips:
            tooltip.enable()
