import customtkinter as ctk
from tkinter import filedialog, messagebox
import os
import json
import sys
import shutil
import threading
import zipfile  # Модуль для роботи з резервними копіями
import tempfile  # Для безпечної перевірки бекапу перед його застосуванням
import winreg  # Модуль для роботи з автозапуском Windows
import subprocess
import hotkey_manager
import stats_manager


class ThemeCreatorWindow(ctk.CTkToplevel):
    def __init__(self, parent, on_save_callback):
        super().__init__(parent)
        self.title("Гнучкий конструктор теми")
        self.geometry("480x820")
        self.minsize(400, 500)
        self.resizable(True, True)

        self.transient(parent)
        self.grab_set()

        self.on_save_callback = on_save_callback

        self.colors = {
            "Кнопки": {"main": (0, 46, 93), "hover": (0, 64, 128)},
            "Фон вікна": {"main": (0, 31, 63)},
            "Фон фреймів": {"main": (67, 78, 90)},
            "Текстові поля": {"main": (0, 43, 91)},
            "Чекбокси/Світчі": {"main": (0, 46, 93)},
            "Текст": {"main": (229, 233, 240)}
        }

        self.current_target = "Кнопки"
        self.create_widgets()
        self.update_preview()

    def create_widgets(self):
        # Усе всередині — прокручуваний контейнер, а не напряму self (Toplevel).
        # Це гарантує, що при зменшенні вікна до minsize (400x500) вміст
        # ніколи не обрізається "мовчки" — просто з'являється вертикальний скрол.
        self.scroll_container = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.scroll_container.pack(fill="both", expand=True)

        ctk.CTkLabel(self.scroll_container, text="Назва теми (англійською):").pack(pady=(10, 2), padx=20, anchor="w")
        self.name_entry = ctk.CTkEntry(self.scroll_container, placeholder_text="напр: mega_style")
        self.name_entry.pack(pady=5, padx=20, fill="x")

        self.preview_window = ctk.CTkFrame(self.scroll_container, border_width=1)
        self.preview_window.pack(pady=10, padx=20, fill="x")
        ctk.CTkLabel(self.preview_window, text="Попередній перегляд:").pack(pady=2)

        self.preview_frame = ctk.CTkFrame(self.preview_window)
        self.preview_frame.pack(pady=5, padx=15, fill="x")

        self.preview_label = ctk.CTkLabel(self.preview_frame, text="Приклад текста (Label)")
        self.preview_label.pack(pady=2)

        self.preview_entry = ctk.CTkEntry(self.preview_frame, placeholder_text="Поле введення...")
        self.preview_entry.insert(0, "Текст у полі")
        self.preview_entry.pack(pady=2, padx=10, fill="x")

        preview_row = ctk.CTkFrame(self.preview_frame, fg_color="transparent")
        preview_row.pack(pady=2, fill="x", padx=10)

        self.preview_checkbox = ctk.CTkCheckBox(preview_row, text="Чекбокс")
        self.preview_checkbox.select()
        self.preview_checkbox.pack(side="left", expand=True)

        self.preview_switch = ctk.CTkSwitch(preview_row, text="Світч")
        self.preview_switch.select()
        self.preview_switch.pack(side="right", expand=True)

        self.btn_preview = ctk.CTkButton(self.preview_frame, text="Приклад кнопки")
        self.btn_preview.pack(pady=6, padx=10)

        mode_frame = ctk.CTkFrame(self.scroll_container)
        mode_frame.pack(pady=5, padx=20, fill="x")
        self.mode_selector = ctk.CTkSegmentedButton(mode_frame, values=["До обох", "Тільки Dark", "Тільки Light"])
        self.mode_selector.set("До обох")
        self.mode_selector.pack(pady=5, padx=10, fill="x")

        font_frame = ctk.CTkFrame(self.scroll_container)
        font_frame.pack(pady=5, padx=20, fill="x")
        available_fonts = ["Roboto", "Segoe UI", "Arial", "Consolas", "Verdana"]
        self.font_dropdown = ctk.CTkOptionMenu(font_frame, values=available_fonts, command=self.update_preview)
        self.font_dropdown.set("Roboto")
        self.font_dropdown.pack(side="left", fill="x", expand=True, pady=5, padx=5)

        self.font_size_slider = ctk.CTkSlider(font_frame, from_=10, to=18, number_of_steps=8,
                                              command=self.update_preview)
        self.font_size_slider.set(13)
        self.font_size_slider.pack(side="right", fill="x", expand=True, pady=5, padx=5)

        target_frame = ctk.CTkFrame(self.scroll_container)
        target_frame.pack(pady=5, padx=20, fill="x")
        ctk.CTkLabel(target_frame, text="Оберіть елемент для редагування:").pack(pady=2, padx=10, anchor="w")

        self.target_selector = ctk.CTkOptionMenu(target_frame, values=list(self.colors.keys()),
                                                 command=self.on_target_changed)
        self.target_selector.set("Кнопки")
        self.target_selector.pack(pady=5, padx=10, fill="x")

        self.sliders_frame = ctk.CTkFrame(self.scroll_container)
        self.sliders_frame.pack(pady=5, padx=20, fill="x")

        self.slider_title = ctk.CTkLabel(self.sliders_frame, text="Основний колір (RGB):", font=(None, 11, "bold"))
        self.slider_title.pack(pady=2, padx=10, anchor="w")

        self.slider_r = ctk.CTkSlider(self.sliders_frame, from_=0, to=255, number_of_steps=255,
                                      command=self.update_colors_from_sliders)
        self.slider_r.pack(pady=2, padx=10, fill="x")
        self.slider_g = ctk.CTkSlider(self.sliders_frame, from_=0, to=255, number_of_steps=255,
                                      command=self.update_colors_from_sliders)
        self.slider_g.pack(pady=2, padx=10, fill="x")
        self.slider_b = ctk.CTkSlider(self.sliders_frame, from_=0, to=255, number_of_steps=255,
                                      command=self.update_colors_from_sliders)
        self.slider_b.pack(pady=2, padx=10, fill="x")

        self.hover_title = ctk.CTkLabel(self.sliders_frame, text="Колір при наведенні (RGB):", font=(None, 11, "bold"))
        self.slider_rh = ctk.CTkSlider(self.sliders_frame, from_=0, to=255, number_of_steps=255,
                                       command=self.update_colors_from_sliders)
        self.slider_gh = ctk.CTkSlider(self.sliders_frame, from_=0, to=255, number_of_steps=255,
                                       command=self.update_colors_from_sliders)
        self.slider_bh = ctk.CTkSlider(self.sliders_frame, from_=0, to=255, number_of_steps=255,
                                       command=self.update_colors_from_sliders)

        self.on_target_changed("Кнопки")
        btn_save = ctk.CTkButton(self.scroll_container, text="💾 Зберегти тему та застосувати", fg_color="green", hover_color="darkgreen",
                                 command=self.save_theme)
        btn_save.pack(pady=15, padx=20, fill="x")

    def rgb_to_hex(self, rgb_tuple):
        return f"#{int(rgb_tuple[0]):02x}{int(rgb_tuple[1]):02x}{int(rgb_tuple[2]):02x}"

    def on_target_changed(self, choice):
        self.current_target = choice
        main_rgb = self.colors[choice]["main"]
        self.slider_r.set(main_rgb[0])
        self.slider_g.set(main_rgb[1])
        self.slider_b.set(main_rgb[2])

        if choice == "Кнопки":
            self.slider_title.configure(text="Основний колір кнопок (RGB):")
            hover_rgb = self.colors[choice]["hover"]
            self.slider_rh.set(hover_rgb[0])
            self.slider_gh.set(hover_rgb[1])
            self.slider_bh.set(hover_rgb[2])
            self.hover_title.pack(pady=2, padx=10, anchor="w")
            self.slider_rh.pack(pady=2, padx=10, fill="x")
            self.slider_gh.pack(pady=2, padx=10, fill="x")
            self.slider_bh.pack(pady=2, padx=10, fill="x")
        else:
            self.slider_title.configure(text=f"Колір елемента '{choice}' (RGB):")
            self.hover_title.pack_forget()
            self.slider_rh.pack_forget()
            self.slider_gh.pack_forget()
            self.slider_bh.pack_forget()

    def update_colors_from_sliders(self, _=None):
        r, g, b = self.slider_r.get(), self.slider_g.get(), self.slider_b.get()
        self.colors[self.current_target]["main"] = (r, g, b)
        if self.current_target == "Кнопки":
            rh, gh, bh = self.slider_rh.get(), self.slider_gh.get(), self.slider_bh.get()
            self.colors["Кнопки"]["hover"] = (rh, gh, bh)
        self.update_preview()

    def update_preview(self, _=None):
        hex_colors = {k: self.rgb_to_hex(v["main"]) for k, v in self.colors.items()}
        hex_hover = self.rgb_to_hex(self.colors["Кнопки"]["hover"])
        font_name = self.font_dropdown.get()
        font_size = int(self.font_size_slider.get())

        self.preview_window.configure(fg_color=hex_colors["Фон вікна"])
        self.preview_frame.configure(fg_color=hex_colors["Фон фреймів"])
        self.preview_label.configure(text_color=hex_colors["Текст"], font=(font_name, font_size))
        self.preview_entry.configure(fg_color=hex_colors["Текстові поля"], text_color=hex_colors["Текст"],
                                     font=(font_name, font_size))
        self.preview_checkbox.configure(fg_color=hex_colors["Чекбокси/Світчі"], hover_color=hex_colors["Кнопки"],
                                        text_color=hex_colors["Текст"], font=(font_name, font_size))
        self.preview_switch.configure(progress_color=hex_colors["Чекбокси/Світчі"], text_color=hex_colors["Текст"],
                                      font=(font_name, font_size))
        self.btn_preview.configure(fg_color=hex_colors["Кнопки"], hover_color=hex_hover, text_color="#FFFFFF",
                                   font=(font_name, font_size))

    def save_theme(self):
        name = self.name_entry.get().strip().replace(" ", "_")
        if not name:
            messagebox.showwarning("Помилка", "Введіть назву теми!")
            return

        h = {k: self.rgb_to_hex(v["main"]) for k, v in self.colors.items()}
        h_hover = self.rgb_to_hex(self.colors["Кнопки"]["hover"])
        font_name = self.font_dropdown.get()
        font_size = int(self.font_size_slider.get())
        mode = self.mode_selector.get()

        def make_color(custom_color, default_light, default_dark):
            if mode == "До обох":
                return [custom_color, custom_color]
            elif mode == "Тільки Dark":
                return [default_light, custom_color]
            else:
                return [custom_color, default_dark]

        theme_structure = {
            "CTk": {"fg_color": make_color(h["Фон вікна"], "#DCE4EE", "#001F3F")},
            "CTkToplevel": {"fg_color": make_color(h["Фон вікна"], "#DCE4EE", "#001F3F")},
            "CTkFrame": {"corner_radius": 6, "border_width": 0,
                         "fg_color": make_color(h["Фон фреймів"], "#BCC6D0", "#434E5A"),
                         "top_fg_color": ["#AAB0B6", "#003366"], "border_color": ["#5A5C66", "#003B6C"]},
            "CTkButton": {"corner_radius": 6, "border_width": 0,
                          "fg_color": make_color(h["Кнопки"], "#003F6C", "#002E5D"),
                          "hover_color": make_color(h_hover, "#004080", "#00214B"),
                          "border_color": ["#003D4E", "#7F8C8D"], "text_color": ["#E5E9F0", "#E5E9F0"],
                          "text_color_disabled": ["#C0C6CE", "#A6A9AE"]},
            "CTkLabel": {"corner_radius": 0, "fg_color": "transparent",
                         "text_color": make_color(h["Текст"], "#001F3F", "#E5E9F0")},
            "CTkEntry": {"corner_radius": 6, "border_width": 2,
                         "fg_color": make_color(h["Текстові поля"], "#F2F4F7", "#002B5B"),
                         "border_color": ["#7D8B92", "#004060"],
                         "text_color": make_color(h["Текст"], "#001F3F", "#E5E9F0"),
                         "placeholder_text_color": ["#7D8B92", "#8B8F92"]},
            "CTkCheckBox": {"corner_radius": 6, "border_width": 3,
                            "fg_color": make_color(h["Чекбокси/Світчі"], "#003F6C", "#002E5D"),
                            "border_color": ["#003D4E", "#7F8C8D"],
                            "hover_color": make_color(h["Кнопки"], "#003F6C", "#002E5D"),
                            "checkmark_color": ["#E5E9F0", "#BCC6D0"],
                            "text_color": make_color(h["Текст"], "#001F3F", "#E5E9F0"),
                            "text_color_disabled": ["#A6A9AE", "#8C8D8F"]},
            "CTkSwitch": {"corner_radius": 1000, "border_width": 3, "button_length": 0,
                          "fg_color": ["#7D8B92", "#003B6C"],
                          "progress_color": make_color(h["Чекбокси/Світчі"], "#003F6C", "#002E5D"),
                          "button_color": ["#002B5B", "#E5E9F0"], "button_hover_color": ["#003366", "#E5E9F0"],
                          "text_color": make_color(h["Текст"], "#001F3F", "#E5E9F0"),
                          "text_color_disabled": ["#A6A9AE", "#8C8D8F"]},
            "CTkRadioButton": {"corner_radius": 1000, "border_width_checked": 6, "border_width_unchecked": 3,
                               "fg_color": make_color(h["Чекбокси/Світчі"], "#003F6C", "#002E5D"),
                               "border_color": ["#003D4E", "#7F8C8D"],
                               "hover_color": make_color(h_hover, "#004080", "#00214B"),
                               "text_color": make_color(h["Текст"], "#001F3F", "#E5E9F0"),
                               "text_color_disabled": ["#A6A9AE", "#8C8D8F"]},
            "CTkProgressBar": {"corner_radius": 1000, "border_width": 0, "fg_color": ["#7D8B92", "#003B6C"],
                               "progress_color": make_color(h["Кнопки"], "#003F6C", "#002E5D"),
                               "border_color": ["gray", "gray"]},
            "CTkSlider": {"corner_radius": 1000, "button_corner_radius": 1000, "border_width": 6, "button_length": 0,
                          "fg_color": ["#7D8B92", "#003B6C"], "progress_color": ["#003D4E", "#B0B3B6"],
                          "button_color": make_color(h["Кнопки"], "#003F6C", "#002E5D"),
                          "button_hover_color": make_color(h_hover, "#004080", "#00214B")},
            "CTkOptionMenu": {"corner_radius": 6, "fg_color": make_color(h["Кнопки"], "#003F6C", "#002E5D"),
                              "button_color": make_color(h_hover, "#004080", "#00214B"),
                              "button_hover_color": make_color(h["Кнопки"], "#002E5D", "#001F3F"),
                              "text_color": ["#E5E9F0", "#E5E9F0"], "text_color_disabled": ["#C0C6CE", "#A6A9AE"]},
            "CTkComboBox": {"corner_radius": 6, "border_width": 2,
                            "fg_color": make_color(h["Текстові поля"], "#F2F4F7", "#002B5B"),
                            "border_color": ["#7D8B92", "#004060"], "button_color": ["#7D8B92", "#004060"],
                            "button_hover_color": ["#4F5B66", "#5B6C77"],
                            "text_color": make_color(h["Текст"], "#001F3F", "#E5E9F0"),
                            "text_color_disabled": ["#8C8D8F", "#8C8D8F"]},
            "CTkScrollbar": {"corner_radius": 1000, "border_spacing": 4, "fg_color": "transparent",
                             "button_color": ["#8C8D8F", "#6D6E70"], "button_hover_color": ["#7D8B92", "#5A5B5C"]},
            "CTkSegmentedButton": {"corner_radius": 6, "border_width": 2, "fg_color": ["#7D8B92", "#003B6C"],
                                   "selected_color": make_color(h["Кнопки"], "#003F6C", "#002E5D"),
                                   "selected_hover_color": make_color(h_hover, "#004080", "#00214B"),
                                   "unselected_color": ["#7D8B92", "#003B6C"],
                                   "unselected_hover_color": ["#7F8C8D", "#5A5B5C"],
                                   "text_color": ["#E5E9F0", "#E5E9F0"], "text_color_disabled": ["#C0C6CE", "#A6A9AE"]},
            "CTkTextbox": {"corner_radius": 6, "border_width": 0,
                           "fg_color": make_color(h["Текстові поля"], "#F2F4F7", "#002B5B"),
                           "border_color": ["#7D8B92", "#004060"],
                           "text_color": make_color(h["Текст"], "#001F3F", "#E5E9F0"),
                           "scrollbar_button_color": ["#8C8D8F", "#6D6E70"],
                           "scrollbar_button_hover_color": ["#7D8B92", "#5A5B5C"]},
            "CTkScrollableFrame": {"label_fg_color": ["#BCC6D0", "#003B6C"]},
            "DropdownMenu": {"fg_color": make_color(h["Фон вікна"], "#DCE4EE", "#003B6C"),
                             "hover_color": make_color(h["Фон фреймів"], "#BCC6D0", "#003B6C"),
                             "text_color": make_color(h["Текст"], "#001F3F", "#DCE4EE")},
            "CTkFont": {
                "macOS": {"family": font_name, "size": font_size, "weight": "normal"},
                "Windows": {"family": font_name, "size": font_size, "weight": "normal"},
                "Linux": {"family": font_name, "size": font_size, "weight": "normal"}
            }
        }

        try:
            base_dir = os.path.dirname(sys.executable) if getattr(sys, "frozen", False) else os.path.dirname(
                os.path.abspath(__file__))
            themes_dir = os.path.join(base_dir, "themes")
            os.makedirs(themes_dir, exist_ok=True)
            with open(os.path.join(themes_dir, f"{name}.json"), "w", encoding="utf-8") as f:
                json.dump(theme_structure, f, indent=4)
            self.on_save_callback(name)
            self.destroy()
        except Exception as e:
            messagebox.showerror("Помилка", f"Не вдалося зберегти тему: {e}")


class HotkeyManagerDialog(ctk.CTkToplevel):
    """ Єдине вікно, де зібрані УСІ гарячі клавіші лаунчера: і глобальна
    клавіша показу вікна з трею, і клавіші кожного окремого набору —
    щоб не шукати їх по різних вкладках, а редагувати все в одному місці. """

    def __init__(self, parent, settings_manager, preset_manager_ref):
        super().__init__(parent)
        self.settings_manager = settings_manager
        self.preset_manager_ref = preset_manager_ref

        self.title("Керування гарячими клавішами")
        self.geometry("440x560")
        self.minsize(360, 380)
        self.transient(parent)

        parent.update_idletasks()
        px = parent.winfo_rootx() + (parent.winfo_width() // 2) - 220
        py = parent.winfo_rooty() + (parent.winfo_height() // 2) - 280
        self.geometry(f"+{max(px, 0)}+{max(py, 0)}")

        self.create_widgets()
        self.grab_set()

    def create_widgets(self):
        scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=5, pady=5)

        if not hotkey_manager.is_available():
            warn = ctk.CTkLabel(
                scroll,
                text="⚠ Бібліотека 'keyboard' не встановлена — гарячі клавіші не "
                     "працюватимуть, поки її не встановити.\nКоманда: pip install keyboard",
                font=(None, 11), text_color=("#B22222", "#FF7B7B"),
                justify="left", anchor="w", wraplength=380
            )
            warn.pack(pady=(10, 5), padx=15, anchor="w", fill="x")

        # --- Показ вікна лаунчера ---
        show_box = ctk.CTkFrame(scroll)
        show_box.pack(pady=(10, 8), padx=10, fill="x")
        ctk.CTkLabel(
            show_box, text="🖥 Показати вікно лаунчера з трею", font=(None, 12, "bold")
        ).pack(pady=(8, 2), padx=10, anchor="w")
        ctk.CTkLabel(
            show_box, text="Спрацьовує завжди, навіть якщо вікно згорнуте.",
            font=(None, 10), text_color="gray", anchor="w"
        ).pack(pady=(0, 5), padx=10, anchor="w")

        self._build_hotkey_row(
            show_box,
            initial_value=self.settings_manager.get_show_hotkey(),
            on_save=self._save_show_hotkey
        )

        # --- Набори ---
        presets_box = ctk.CTkFrame(scroll)
        presets_box.pack(pady=(0, 10), padx=10, fill="x")
        ctk.CTkLabel(
            presets_box, text="🚀 Миттєвий запуск наборів", font=(None, 12, "bold")
        ).pack(pady=(8, 2), padx=10, anchor="w")
        ctk.CTkLabel(
            presets_box, text="Запускає весь набір програм без відкриття вікна лаунчера.",
            font=(None, 10), text_color="gray", anchor="w"
        ).pack(pady=(0, 5), padx=10, anchor="w")

        presets = self.preset_manager_ref.presets if self.preset_manager_ref else {}
        preset_names = [n for n, d in presets.items() if isinstance(d, dict)]

        if not preset_names:
            ctk.CTkLabel(
                presets_box,
                text="Немає жодного набору. Створіть набір у вкладці 'Набори',\n"
                     "щоб можна було призначити йому гарячу клавішу.",
                font=(None, 11), text_color="gray", justify="left", anchor="w"
            ).pack(pady=(0, 12), padx=10, anchor="w", fill="x")
        else:
            for name in preset_names:
                row_box = ctk.CTkFrame(presets_box, fg_color="transparent")
                row_box.pack(pady=(2, 8), padx=10, fill="x")
                ctk.CTkLabel(row_box, text=name, anchor="w", font=(None, 11, "bold")).pack(anchor="w", padx=2)

                current_hk = presets.get(name, {}).get("hotkey", "")
                self._build_hotkey_row(
                    row_box,
                    initial_value=current_hk,
                    on_save=lambda hk, n=name: self._save_preset_hotkey(n, hk)
                )

        ctk.CTkButton(self, text="Закрити", command=self.destroy).pack(pady=(0, 12), padx=15, fill="x")

    def _build_hotkey_row(self, container, initial_value, on_save):
        """ Створює один рядок "поле вводу + 🎙 записати + 💾 зберегти".
        Уся логіка збереження замикається через callback on_save(hotkey),
        завдяки чому цей самий рядок обслуговує і клавішу показу вікна,
        і клавішу будь-якого окремого набору без дублювання коду. """
        row = ctk.CTkFrame(container, fg_color="transparent")
        row.pack(pady=(0, 8), padx=10, fill="x")

        entry = ctk.CTkEntry(row, placeholder_text="напр: ctrl+alt+l")
        entry.pack(side="left", fill="x", expand=True, padx=(0, 6))
        if initial_value:
            entry.insert(0, initial_value)

        record_btn = ctk.CTkButton(row, text="🎙", width=32, fg_color="transparent", border_width=1,
                                    text_color=("#001F3F", "#E5E9F0"))
        record_btn.pack(side="left", padx=(0, 4))

        def do_record():
            if not hotkey_manager.is_available():
                messagebox.showwarning(
                    "Недоступно",
                    "Бібліотека 'keyboard' не встановлена.\nВстановіть: pip install keyboard"
                )
                return
            record_btn.configure(text="...", state="disabled")

            def listen():
                combo = hotkey_manager.record_hotkey()
                self.after(0, lambda: _on_recorded(combo))

            def _on_recorded(combo):
                record_btn.configure(text="🎙", state="normal")
                if combo:
                    entry.delete(0, "end")
                    entry.insert(0, combo)

            threading.Thread(target=listen, daemon=True).start()

        record_btn.configure(command=do_record)

        def do_save():
            raw = entry.get().strip()
            normalized = hotkey_manager.normalize_hotkey(raw) if raw else ""
            if raw and normalized is None:
                messagebox.showerror(
                    "Некоректна комбінація",
                    f"Не вдалося розпізнати «{raw}».\nПриклад: ctrl+alt+l"
                )
                return
            on_save(normalized or "")

        ctk.CTkButton(row, text="💾", width=32, command=do_save).pack(side="left")

    def _save_show_hotkey(self, normalized):
        self.settings_manager.set_show_hotkey(normalized)
        if normalized:
            messagebox.showinfo("Готово", f"Гаряча клавіша «{normalized}» тепер відкриває лаунчер.")
        else:
            messagebox.showinfo("Готово", "Глобальну гарячу клавішу показу вікна вимкнено.")

    def _save_preset_hotkey(self, name, normalized):
        """ Зберігає гарячу клавішу набору через PresetManager (єдине
        джерело правди для presets.json), попереджаючи про конфлікти
        з уже зайнятими комбінаціями. """
        if not self.preset_manager_ref:
            return

        if normalized:
            conflicts = []
            if self.settings_manager.get_show_hotkey() == normalized:
                conflicts.append("показу вікна лаунчера")
            for other_name, other_data in self.preset_manager_ref.presets.items():
                if other_name != name and isinstance(other_data, dict) and \
                        (other_data.get("hotkey") or "").strip().lower() == normalized:
                    conflicts.append(f"набору «{other_name}»")
            if conflicts:
                messagebox.showwarning(
                    "Комбінація вже використовується",
                    f"Клавіша «{normalized}» вже призначена для: {', '.join(conflicts)}.\n\n"
                    "Можна залишити так, але спрацюють ОБИДВІ дії одночасно."
                )

        self.preset_manager_ref.set_preset_hotkey(name, normalized)
        if normalized:
            messagebox.showinfo("Готово", f"Гаряча клавіша «{normalized}» тепер запускає набір «{name}».")
        else:
            messagebox.showinfo("Готово", f"Гарячу клавішу для набору «{name}» прибрано.")


class StatsDialog(ctk.CTkToplevel):
    """ Єдине вікно статистики використання: показує, скільки разів
    реально було запущено кожну програму через лаунчер (з головного
    списку, з наборів, за розкладом чи в автозапуску) — у вигляді
    простого горизонтального графіка, від найбільш використовуваної
    до найменш використовуваної. Допомагає користувачу побачити, який
    софт йому дійсно потрібен, а який можна прибрати зі списку. """

    MAX_BAR_WIDTH = 220

    def __init__(self, parent, programs_provider, on_reset=None):
        super().__init__(parent)
        # programs_provider — функція без аргументів, що повертає АКТУАЛЬНИЙ
        # список програм (з головного екрана), щоб зіставити збережені у
        # stats_manager шляхи з людськими назвами програм
        self.programs_provider = programs_provider
        # Викликається після скидання статистики, щоб головний екран одразу
        # оновив лічильники (▶ N) біля програм, не чекаючи наступної дії
        self.on_reset = on_reset

        self.title("Статистика використання")
        self.geometry("480x580")
        self.minsize(380, 380)
        self.transient(parent)

        parent.update_idletasks()
        px = parent.winfo_rootx() + (parent.winfo_width() // 2) - 240
        py = parent.winfo_rooty() + (parent.winfo_height() // 2) - 290
        self.geometry(f"+{max(px, 0)}+{max(py, 0)}")

        self.create_widgets()
        self.grab_set()

    def _get_ranked_stats(self):
        """ Повертає [(назва, кількість запусків), ...] для програм з
        поточного списку, відсортовані за спаданням. Записи статистики
        для вже видалених програм (яких немає у programs_provider)
        просто ігноруються — показуємо тільки актуальний список. """
        programs = self.programs_provider() if self.programs_provider else []
        result = [(p["name"], stats_manager.get_count(p["path"])) for p in programs]
        result.sort(key=lambda item: item[1], reverse=True)
        return result

    def create_widgets(self):
        ctk.CTkLabel(
            self, text="📊 Скільки разів запущено кожну програму", font=(None, 13, "bold")
        ).pack(pady=(12, 4), padx=15, anchor="w")

        hint = ctk.CTkLabel(
            self,
            text="Рахуються лише реальні запуски через лаунчер — зі списку 'Програми', "
                 "з наборів, за розкладом чи в автозапуску. Допомагає побачити, який софт "
                 "дійсно потрібен, а який можна прибрати зі списку.",
            font=(None, 10), text_color="gray", justify="left", anchor="w", wraplength=440
        )
        hint.pack(pady=(0, 10), padx=15, anchor="w", fill="x")

        self.scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.scroll.pack(fill="both", expand=True, padx=10, pady=(0, 5))

        self.render_chart()

        ctk.CTkButton(
            self, text="🗑 Скинути всю статистику", fg_color="transparent", border_width=1,
            text_color=("#001F3F", "#E5E9F0"),
            command=self.confirm_reset_all
        ).pack(pady=(5, 5), padx=15, fill="x")

        ctk.CTkButton(self, text="Закрити", command=self.destroy).pack(pady=(0, 12), padx=15, fill="x")

    def render_chart(self):
        """ (Пере)малює графік з нуля — викликається і при першому відкритті,
        і одразу після скидання статистики, щоб вікно показувало актуальні дані. """
        for widget in self.scroll.winfo_children():
            widget.destroy()

        data = self._get_ranked_stats()

        if not data:
            ctk.CTkLabel(
                self.scroll,
                text="Немає жодної доданої програми на вкладці 'Програми'.",
                text_color="gray"
            ).pack(pady=20)
            return

        max_count = max(count for _, count in data) or 1

        for name, count in data:
            display_name = name if len(name) <= 22 else name[:21] + "…"

            row = ctk.CTkFrame(self.scroll, fg_color="transparent")
            row.pack(fill="x", pady=3)

            ctk.CTkLabel(row, text=display_name, anchor="w", width=150).pack(side="left", padx=(0, 8))

            bar_track = ctk.CTkFrame(
                row, height=16, width=self.MAX_BAR_WIDTH,
                fg_color=("#DCE4EE", "#001F3F"), corner_radius=3
            )
            bar_track.pack(side="left", padx=(0, 8))
            bar_track.pack_propagate(False)

            bar_width = max(int(self.MAX_BAR_WIDTH * count / max_count), 2) if count else 0
            if bar_width:
                ctk.CTkFrame(
                    bar_track, height=16, width=bar_width,
                    fg_color=("#003F6C", "#5B9BD5"), corner_radius=3
                ).place(x=0, y=0)

            ctk.CTkLabel(row, text=str(count), width=28, anchor="w").pack(side="left")

    def confirm_reset_all(self):
        if messagebox.askyesno(
            "Скинути статистику",
            "Скинути лічильники запусків для ВСІХ програм?\nЦю дію не можна скасувати."
        ):
            stats_manager.reset_all()
            self.render_chart()
            if self.on_reset:
                self.on_reset()


class SettingsManager(ctk.CTkFrame):
    def __init__(self, master, restart_callback=None, hotkeys_changed_callback=None, preset_manager_ref=None,
                 programs_provider=None, stats_reset_callback=None, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self.app = master
        self.restart_callback_func = restart_callback
        # Викликається щоразу, коли глобальна гаряча клавіша (показ вікна)
        # змінюється, щоб головний файл лаунчера перереєстрував хуки клавіатури
        self.hotkeys_changed_callback = hotkeys_changed_callback
        # Посилання на PresetManager — потрібне централізованому вікну
        # "Керування гарячими клавішами", щоб показувати і редагувати
        # гарячі клавіші всіх наборів прямо з Налаштувань
        self.preset_manager_ref = preset_manager_ref
        # Функція без аргументів, що повертає актуальний список програм —
        # потрібна вікну статистики, щоб зіставити шляхи (ключі stats_manager)
        # з людськими назвами програм
        self.programs_provider = programs_provider
        # Викликається після скидання статистики у вікні "Статистика
        # використання", щоб головний екран одразу оновив лічильники (▶ N)
        self.stats_reset_callback = stats_reset_callback
        # Валідована (перевірена keyboard.parse_hotkey) комбінація — саме вона
        # йде у settings.json, а не сирий текст із поля вводу "на льоту"
        self._validated_show_hotkey = "ctrl+alt+l"

        # Базовая папка программы
        if getattr(sys, "frozen", False):
            self.base_dir = os.path.dirname(sys.executable)
        else:
            self.base_dir = os.path.dirname(os.path.abspath(__file__))

        self.settings_dir = os.path.join(self.base_dir, "jsons_saves")
        self.themes_dir = os.path.join(self.base_dir, "themes")
        self.settings_file = os.path.join(self.settings_dir, "settings.json")

        os.makedirs(self.themes_dir, exist_ok=True)
        os.makedirs(self.settings_dir, exist_ok=True)

        self.default_settings = {
            "theme": "Dark",
            "color_theme": "default_launcher",
            "close_after_launch": False,
            "minimize_to_tray": True,
            "delay": 0,
            "windows_autostart": False,
            "show_hotkey": "ctrl+alt+l"
        }

        self.ensure_base_theme_exists()
        self.create_widgets()
        # Якщо лаунчер вже в автозапуску, але його перемістили/оновили —
        # актуалізуємо шлях у реєстрі ДО того, як зчитаємо стан чекбоксів,
        # щоб автозапуск не "мовчки" ламався через застарілий шлях.
        self.sync_autostart_path()
        self.load_and_apply_saved_widgets()

    def ensure_base_theme_exists(self):
        base_theme_path = os.path.join(self.themes_dir, "default_launcher.json")
        if not os.path.exists(base_theme_path):
            base_structure = {
                "CTk": {"fg_color": ["#DCE4EE", "#001F3F"]},
                "CTkToplevel": {"fg_color": ["#DCE4EE", "#001F3F"]},
                "CTkFrame": {"corner_radius": 6, "border_width": 0, "fg_color": ["#BCC6D0", "#434E5A"],
                             "top_fg_color": ["#AAB0B6", "#003366"], "border_color": ["#5A5C66", "#003B6C"]},
                "CTkButton": {"corner_radius": 6, "border_width": 0, "fg_color": ["#003F6C", "#002E5D"],
                              "hover_color": ["#004080", "#00214B"], "border_color": ["#003D4E", "#7F8C8D"],
                              "text_color": ["#E5E9F0", "#E5E9F0"], "text_color_disabled": ["#C0C6CE", "#A6A9AE"]},
                "CTkLabel": {"corner_radius": 0, "fg_color": "transparent", "text_color": ["#001F3F", "#E5E9F0"]},
                "CTkEntry": {"corner_radius": 6, "border_width": 2, "fg_color": ["#F2F4F7", "#002B5B"],
                             "border_color": ["#7D8B92", "#004060"], "text_color": ["#001F3F", "#E5E9F0"],
                             "placeholder_text_color": ["#7D8B92", "#8B8F92"]},
                "CTkCheckBox": {"corner_radius": 6, "border_width": 3, "fg_color": ["#003F6C", "#002E5D"],
                                "border_color": ["#003D4E", "#7F8C8D"], "hover_color": ["#003F6C", "#002E5D"],
                                "checkmark_color": ["#E5E9F0", "#BCC6D0"], "text_color": ["#001F3F", "#E5E9F0"],
                                "text_color_disabled": ["#A6A9AE", "#8C8D8F"]},
                "CTkSwitch": {"corner_radius": 1000, "border_width": 3, "button_length": 0,
                              "fg_color": ["#7D8B92", "#003B6C"], "progress_color": ["#003F6C", "#002E5D"],
                              "button_color": ["#002B5B", "#E5E9F0"], "button_hover_color": ["#003366", "#E5E9F0"],
                              "text_color": ["#001F3F", "#E5E9F0"], "text_color_disabled": ["#A6A9AE", "#8C8D8F"]},
                "CTkRadioButton": {"corner_radius": 1000, "border_width_checked": 6, "border_width_unchecked": 3,
                                   "fg_color": ["#003F6C", "#002E5D"], "border_color": ["#003D4E", "#7F8C8D"],
                                   "hover_color": ["#004080", "#00214B"], "text_color": ["#001F3F", "#E5E9F0"],
                                   "text_color_disabled": ["#A6A9AE", "#8C8D8F"]},
                "CTkProgressBar": {"corner_radius": 1000, "border_width": 0, "fg_color": ["#7D8B92", "#003B6C"],
                                   "progress_color": ["#003F6C", "#002E5D"], "border_color": ["gray", "gray"]},
                "CTkSlider": {"corner_radius": 1000, "button_corner_radius": 1000, "border_width": 6,
                              "button_length": 0, "fg_color": ["#7D8B92", "#003B6C"],
                              "progress_color": ["#003D4E", "#B0B3B6"], "button_color": ["#003F6C", "#002E5D"],
                              "button_hover_color": ["#004080", "#00214B"]},
                "CTkOptionMenu": {"corner_radius": 6, "fg_color": ["#003F6C", "#002E5D"],
                                  "button_color": ["#004080", "#00214B"], "button_hover_color": ["#002E5D", "#001F3F"],
                                  "text_color": ["#E5E9F0", "#E5E9F0"], "text_color_disabled": ["#C0C6CE", "#A6A9AE"]},
                "CTkComboBox": {"corner_radius": 6, "border_width": 2, "fg_color": ["#F2F4F7", "#002B5B"],
                                "border_color": ["#7D8B92", "#004060"], "button_color": ["#7D8B92", "#004060"],
                                "button_hover_color": ["#4F5B66", "#5B6C77"], "text_color": ["#001F3F", "#E5E9F0"],
                                "text_color_disabled": ["#8C8D8F", "#8C8D8F"]},
                "CTkScrollbar": {"corner_radius": 1000, "border_spacing": 4, "fg_color": "transparent",
                                 "button_color": ["#8C8D8F", "#6D6E70"], "button_hover_color": ["#7D8B92", "#5A5B5C"]},
                "CTkSegmentedButton": {"corner_radius": 6, "border_width": 2, "fg_color": ["#7D8B92", "#003B6C"],
                                       "selected_color": ["#003F6C", "#002E5D"],
                                       "selected_hover_color": ["#004080", "#00214B"],
                                       "unselected_color": ["#7D8B92", "#003B6C"],
                                       "unselected_hover_color": ["#7F8C8D", "#5A5B5C"],
                                       "text_color": ["#E5E9F0", "#E5E9F0"],
                                       "text_color_disabled": ["#C0C6CE", "#A6A9AE"]},
                "CTkTextbox": {"corner_radius": 6, "border_width": 0, "fg_color": ["#F2F4F7", "#002B5B"],
                               "border_color": ["#7D8B92", "#004060"], "text_color": ["#001F3F", "#E5E9F0"],
                               "scrollbar_button_color": ["#8C8D8F", "#6D6E70"],
                               "scrollbar_button_hover_color": ["#7D8B92", "#5A5B5C"]},
                "CTkScrollableFrame": {"label_fg_color": ["#BCC6D0", "#003B6C"]},
                "DropdownMenu": {"fg_color": ["#DCE4EE", "#003B6C"], "hover_color": ["#BCC6D0", "#003B6C"],
                                 "text_color": ["#001F3F", "#DCE4EE"]},
                "CTkFont": {
                    "macOS": {"family": "Roboto", "size": 13, "weight": "normal"},
                    "Windows": {"family": "Roboto", "size": 13, "weight": "normal"},
                    "Linux": {"family": "Roboto", "size": 13, "weight": "normal"}
                }
            }
            with open(base_theme_path, "w", encoding="utf-8") as f:
                json.dump(base_structure, f, indent=4)

    def _make_responsive(self, container, label, label_padx=12):
        """ Прив'язує wraplength підпису до реальної ширини його контейнера,
        а не до одного жорсткого числа. Компенсує widget_scaling (DPI-масштаб
        Windows), яке CTkLabel.configure(wraplength=...) сам домножує. """

        def _on_container_resize(event):
            scaling = ctk.ScalingTracker.get_widget_scaling(label) or 1
            usable = event.width - (label_padx * 2)
            new_width = max(int(usable / scaling), 150)
            label.configure(wraplength=new_width)

        container.bind("<Configure>", _on_container_resize)

    def get_available_themes(self):
        themes = ["blue", "green", "dark-blue"]
        if os.path.exists(self.themes_dir):
            for file in os.listdir(self.themes_dir):
                if file.endswith(".json"):
                    themes.append(file.replace(".json", ""))
        return themes

    def create_widgets(self):
        # Створюємо прокручуваний фрейм, який розтягується на все доступне місце менеджера
        self.scroll_container = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.scroll_container.pack(fill="both", expand=True, padx=2, pady=2)

        # 1. Тема (тепер кріпиться до self.scroll_container)
        self.theme_box = ctk.CTkFrame(self.scroll_container)
        self.theme_box.pack(pady=8, fill="x")
        ctk.CTkLabel(self.theme_box, text="Візуальна тема програми:").pack(pady=5, padx=10, anchor="w")
        self.theme_dropdown = ctk.CTkOptionMenu(self.theme_box, values=["Dark", "Light"], command=self.change_theme)
        self.theme_dropdown.pack(pady=5, padx=10, fill="x")

        # 2. Колір
        self.color_box = ctk.CTkFrame(self.scroll_container)
        self.color_box.pack(pady=8, fill="x")
        ctk.CTkLabel(self.color_box, text="Колір та шрифт стилю (потребує перезапуску):").pack(pady=5, padx=10,
                                                                                               anchor="w")

        self.color_dropdown = ctk.CTkOptionMenu(self.color_box, values=self.get_available_themes(),
                                                command=self.change_color_theme)
        self.color_dropdown.pack(pady=5, padx=10, fill="x")

        theme_btn_frame = ctk.CTkFrame(self.color_box, fg_color="transparent")
        theme_btn_frame.pack(pady=5, padx=10, fill="x")

        ctk.CTkButton(theme_btn_frame, text="📁 Імпортувати .json", command=self.import_theme_file, height=24).pack(
            side="left", expand=True, fill="x", padx=2)
        ctk.CTkButton(theme_btn_frame, text="🎨 FK Конструктор теми", command=self.open_theme_creator, height=24).pack(
            side="right", expand=True, fill="x", padx=2)

        self.btn_reset_themes = ctk.CTkButton(self.color_box, text="💥 Скинути всі кастомні теми",
                                              fg_color="transparent", border_width=1, height=24,
                                              text_color=("#001F3F", "#E5E9F0"),
                                              command=self.reset_to_factory_themes)
        self.btn_reset_themes.pack(pady=(2, 5), padx=12, fill="x")

        # 3. Поведінка
        self.behavior_box = ctk.CTkFrame(self.scroll_container)
        self.behavior_box.pack(pady=8, fill="x")
        ctk.CTkLabel(self.behavior_box, text="Поведінка лаунчера:").pack(pady=5, padx=10, anchor="w")

        self.close_checkbox = ctk.CTkCheckBox(self.behavior_box, text="Закривати лаунчер після запуску програм",
                                              command=self.save_settings)
        self.close_checkbox.pack(pady=4, padx=10, fill="x", anchor="w")

        self.tray_checkbox = ctk.CTkCheckBox(
            self.behavior_box,
            text="Не закривати, а згортати у фоновий режим (трей) при натисканні ❌",
            command=self.update_close_protocol
        )
        self.tray_checkbox.pack(pady=(4, 0), padx=10, fill="x", anchor="w")

        tray_hint = ctk.CTkLabel(
            self.behavior_box,
            text="Трей — це значок біля годинника Windows. Потрібно увімкнути,\n"
                 "щоб розклад продовжував працювати після закриття вікна.",
            font=(None, 10), text_color="gray", justify="left", anchor="w"
        )
        tray_hint.pack(pady=(0, 6), padx=28, fill="x", anchor="w")
        self._make_responsive(self.behavior_box, tray_hint, label_padx=28)

        self.autostart_checkbox = ctk.CTkCheckBox(
            self.behavior_box,
            text="Автоматично запускати лаунчер при вмиканні Windows",
            command=self.toggle_windows_autostart
        )
        self.autostart_checkbox.pack(pady=4, padx=10, fill="x", anchor="w")

        self.smart_launch_checkbox = ctk.CTkCheckBox(
            self.behavior_box,
            text="🧠 Розумний запуск: не відкривати повторно, якщо вже запущено",
            command=self.save_settings
        )
        self.smart_launch_checkbox.pack(pady=(4, 0), padx=10, fill="x", anchor="w")

        smart_launch_hint = ctk.CTkLabel(
            self.behavior_box,
            text="Перед запуском лаунчер перевірить список запущених процесів\n"
                 "(через psutil) і пропустить програму, якщо вона вже відкрита —\n"
                 "щоб не плодити зайві вікна при повторних кліках чи спрацюванні розкладу.",
            font=(None, 10), text_color="gray", justify="left", anchor="w"
        )
        smart_launch_hint.pack(pady=(0, 6), padx=28, fill="x", anchor="w")
        self._make_responsive(self.behavior_box, smart_launch_hint, label_padx=28)

        # 4. Затримка
        self.delay_box = ctk.CTkFrame(self.scroll_container)
        self.delay_box.pack(pady=8, fill="x")
        self.delay_label = ctk.CTkLabel(self.delay_box, text="Затримка між запуском програм: 0 сек.")
        self.delay_label.pack(pady=5, padx=10, anchor="w")
        self.delay_slider = ctk.CTkSlider(self.delay_box, from_=0, to=10, number_of_steps=10,
                                          command=self.on_slider_move)
        self.delay_slider.pack(pady=8, padx=10, fill="x")

        # 4.5 Гарячі клавіші (централізоване керування — окреме вікно)
        self.hotkey_box = ctk.CTkFrame(self.scroll_container)
        self.hotkey_box.pack(pady=8, fill="x")
        ctk.CTkLabel(
            self.hotkey_box, text="⌨️ Гарячі клавіші:", font=(None, 12, "bold")
        ).pack(pady=(5, 2), padx=10, anchor="w")

        hotkey_hint = ctk.CTkLabel(
            self.hotkey_box,
            text="Показ вікна лаунчера з трею та миттєвий запуск окремих\n"
                 "наборів без відкриття вікна — усі комбінації клавіш\n"
                 "зібрані і редагуються в одному вікні.",
            font=(None, 10), text_color="gray", justify="left", anchor="w"
        )
        hotkey_hint.pack(pady=(0, 6), padx=10, anchor="w", fill="x")
        self._make_responsive(self.hotkey_box, hotkey_hint)

        ctk.CTkButton(
            self.hotkey_box,
            text="🎹 Керування гарячими клавішами...",
            command=self.open_hotkeys_dialog
        ).pack(pady=(0, 10), padx=10, fill="x")

        if not hotkey_manager.is_available():
            ctk.CTkLabel(
                self.hotkey_box,
                text="⚠ Бібліотека 'keyboard' не знайдена — гарячі клавіші не "
                     "працюватимуть.\nВстановіть командою: pip install keyboard",
                font=(None, 10), text_color=("#B22222", "#FF7B7B"),
                justify="left", anchor="w"
            ).pack(pady=(0, 8), padx=10, anchor="w", fill="x")

        # 4.7 Статистика використання (централізоване керування — окреме вікно)
        self.stats_box = ctk.CTkFrame(self.scroll_container)
        self.stats_box.pack(pady=8, fill="x")
        ctk.CTkLabel(
            self.stats_box, text="📊 Статистика використання:", font=(None, 12, "bold")
        ).pack(pady=(5, 2), padx=10, anchor="w")

        stats_hint = ctk.CTkLabel(
            self.stats_box,
            text="Скільки разів кожну програму реально було запущено через\n"
                 "лаунчер — щоб було видно, який софт дійсно потрібен.",
            font=(None, 10), text_color="gray", justify="left", anchor="w"
        )
        stats_hint.pack(pady=(0, 6), padx=10, anchor="w", fill="x")
        self._make_responsive(self.stats_box, stats_hint)

        ctk.CTkButton(
            self.stats_box,
            text="📊 Переглянути статистику...",
            command=self.open_stats_dialog
        ).pack(pady=(0, 10), padx=10, fill="x")

        # 5. Резервне копіювання
        self.backup_box = ctk.CTkFrame(self.scroll_container)
        self.backup_box.pack(pady=8, fill="x")
        ctk.CTkLabel(self.backup_box, text="📦 Резервне копіювання конфігурацій:", font=(None, 12, "bold")).pack(pady=4,
                                                                                                                padx=10,
                                                                                                                anchor="w")

        backup_btn_frame = ctk.CTkFrame(self.backup_box, fg_color="transparent")
        backup_btn_frame.pack(pady=4, padx=10, fill="x")

        ctk.CTkButton(backup_btn_frame, text="💾 Створити бекап (ZIP)", command=self.create_backup, height=26).pack(
            side="left", expand=True, fill="x", padx=2)
        ctk.CTkButton(backup_btn_frame, text="📂 Відновити з бекапу", command=self.restore_backup, height=26).pack(
            side="right", expand=True, fill="x", padx=2)

        # 6. Кнопка перезапуску
        self.btn_restart = ctk.CTkButton(self.scroll_container, text="🔄 Перезапустити програму",
                                         command=self.restart_program)
        self.btn_restart.pack(pady=15, fill="x")

    def restart_program(self):
        if self.restart_callback_func:
            self.restart_callback_func()
        else:
            messagebox.showwarning("Помилка", "Функцію перезапуску не було передано.")

    def toggle_windows_autostart(self):
        enable = (self.autostart_checkbox.get() == 1)

        if getattr(sys, 'frozen', False):
            file_path = sys.executable
        else:
            file_path = os.path.abspath(sys.argv[0])

        key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
        app_name = "CustomProgramLauncher"

        try:
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_SET_VALUE)
            if enable:
                winreg.SetValueEx(key, app_name, 0, winreg.REG_SZ, f'"{file_path}"')
            else:
                try:
                    winreg.DeleteValue(key, app_name)
                except FileNotFoundError:
                    pass
            winreg.CloseKey(key)
            self.save_settings()
        except Exception as e:
            messagebox.showerror("Автозапуск", f"Не вдалося змінити налаштування в реєстрі Windows: {e}")

    def is_windows_autostart_active(self):
        key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
        app_name = "CustomProgramLauncher"
        try:
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_READ)
            winreg.QueryValueEx(key, app_name)
            winreg.CloseKey(key)
            return True
        except FileNotFoundError:
            return False

    def sync_autostart_path(self):
        """ Якщо лаунчер вже прописаний в автозапуск Windows, перевіряє,
        чи шлях у реєстрі відповідає поточному розташуванню файлу.
        Якщо папку з програмою перемістили або оновили версію (exe
        перезібрали в іншу теку) — шлях у реєстрі стає застарілим,
        і автозапуск перестає працювати без жодної помилки для
        користувача. Тому при кожному старті звіряємо і, якщо треба,
        тихо оновлюємо значення в реєстрі на актуальне. """
        key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
        app_name = "CustomProgramLauncher"

        if getattr(sys, 'frozen', False):
            current_path = sys.executable
        else:
            current_path = os.path.abspath(sys.argv[0])
        expected_value = f'"{current_path}"'

        try:
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_READ)
            try:
                saved_value, _ = winreg.QueryValueEx(key, app_name)
            finally:
                winreg.CloseKey(key)
        except FileNotFoundError:
            # Автозапуск вимкнено — синхронізувати нічого
            return
        except Exception as e:
            print(f"Автозапуск: не вдалося прочитати шлях з реєстру: {e}")
            return

        if saved_value == expected_value:
            return

        try:
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_SET_VALUE)
            winreg.SetValueEx(key, app_name, 0, winreg.REG_SZ, expected_value)
            winreg.CloseKey(key)
            print(f"Автозапуск: шлях у реєстрі застарів і був оновлений на '{current_path}'.")
        except Exception as e:
            print(f"Автозапуск: не вдалося оновити застарілий шлях у реєстрі: {e}")

    def create_backup(self):
        source_dir = self.settings_dir
        if not os.path.exists(source_dir) or not os.listdir(source_dir):
            messagebox.showwarning("Бекап", "Немає збережених налаштувань чи розкладів для резервного копіювання!")
            return

        file_path = filedialog.asksaveasfilename(
            defaultextension=".zip",
            filetypes=[("ZIP Архів", "*.zip")],
            title="Зберегти резервну копію як..."
        )
        if not file_path: return

        try:
            with zipfile.ZipFile(file_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for root, dirs, files in os.walk(source_dir):
                    for file in files:
                        zipf.write(os.path.join(root, file), file)
            messagebox.showinfo("Успіх", "Резервну копію налаштувань та розкладу успешно створено!")
        except Exception as e:
            messagebox.showerror("Помилка", f"Не вдалося створити файл бекапу: {e}")

    def restore_backup(self):
        file_path = filedialog.askopenfilename(
            filetypes=[("ZIP Архів", "*.zip")],
            title="Оберіть файл резервної копії"
        )
        if not file_path: return

        if messagebox.askyesno("Відновлення",
                               "Поточні налаштування, розклад та наборы будуть повністю замінені даними з архіву. Продовжити?"):
            # Спочатку розпаковуємо у тимчасову папку (а не одразу в робочу
            # директорію) і перевіряємо коректність усіх json-файлів.
            # Це захищає від ситуації, коли пошкоджений/невірний архів
            # затирає робочі дані і ламає запуск програми наступного разу.
            with tempfile.TemporaryDirectory() as tmp_dir:
                try:
                    with zipfile.ZipFile(file_path, 'r') as zipf:
                        zipf.extractall(tmp_dir)
                except Exception as e:
                    messagebox.showerror("Помилка", f"Не вдалося розархівувати дані: {e}")
                    return

                is_valid, error_msg = self.validate_backup_data(tmp_dir)
                if not is_valid:
                    messagebox.showerror(
                        "Помилка",
                        "Файл резервної копії пошкоджений або має невірний формат.\n"
                        f"{error_msg}\n\nВідновлення скасовано, поточні дані не змінено."
                    )
                    return

                try:
                    target_dir = self.settings_dir
                    os.makedirs(target_dir, exist_ok=True)

                    for file in os.listdir(tmp_dir):
                        src = os.path.join(tmp_dir, file)
                        if os.path.isfile(src):
                            shutil.copy2(src, os.path.join(target_dir, file))

                    messagebox.showinfo("Успіх",
                                        "Конфігурацію відновлено! Натисніть кнопку перезапуску програми для застосування змін.")
                except Exception as e:
                    messagebox.showerror("Помилка", f"Не вдалося застосувати дані з бекапу: {e}")

    def validate_backup_data(self, folder):
        """ Перевіряє json-файли з бекапу (settings.json, presets.json,
        schedule.json) на валідність та очікувану структуру ПЕРЕД тим,
        як вони замінять робочі дані лаунчера. Файли, яких немає в
        архіві, пропускаються — це не критично (стара версія бекапу). """
        expected_structure = {
            "settings.json": dict,
            "presets.json": dict,
            "schedule.json": list,
        }

        for filename, expected_type in expected_structure.items():
            path = os.path.join(folder, filename)
            if not os.path.exists(path):
                continue

            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
            except (json.JSONDecodeError, UnicodeDecodeError) as e:
                return False, f"Файл '{filename}' не є коректним JSON ({e})"
            except Exception as e:
                return False, f"Не вдалося прочитати файл '{filename}' ({e})"

            if not isinstance(data, expected_type):
                return False, f"Файл '{filename}' має неочікувану структуру даних"

        return True, ""

    def open_theme_creator(self):
        ThemeCreatorWindow(self, self.on_custom_theme_created)

    def on_custom_theme_created(self, theme_name):
        all_themes = self.get_available_themes()
        self.color_dropdown.configure(values=all_themes)
        self.color_dropdown.set(theme_name)
        self.change_color_theme(theme_name)
        messagebox.showinfo("Успіх", f"Тему '{theme_name}' створено! Натисніть кнопку перезапуску.")

    # --- ВСІ ТВОЇ ОРИГІНАЛЬНІ ФУНКЦІЇ БЕЗ ЗМІН ---
    def import_theme_file(self):
        file_path = filedialog.askopenfilename(filetypes=[("CustomTkinter Theme", "*.json")])
        if not file_path: return

        is_valid, error_msg = self.validate_theme_file(file_path)
        if not is_valid:
            messagebox.showerror("Помилка", f"Некоректний файл теми:\n{error_msg}")
            return

        try:
            shutil.copy(file_path, self.themes_dir)
            theme_name = os.path.basename(file_path).replace(".json", "")
            all_themes = self.get_available_themes()
            self.color_dropdown.configure(values=all_themes)
            self.color_dropdown.set(theme_name)
            self.change_color_theme(theme_name)
            messagebox.showinfo("Успіх", f"Тему '{theme_name}' успішно імпортовано! Перезапустіть лаунчер.")
        except Exception as e:
            messagebox.showerror("Помилка", f"Не вдалося імпортувати тему: {e}")

    def validate_theme_file(self, file_path):
        """ Перевіряє, що обраний .json файл — валідний JSON-об'єкт
        з ключами, очікуваними для теми CustomTkinter, перш ніж
        копіювати його в themes_dir. Захищає від пошкодженого файлу,
        який зламав би вибір кольорової теми при наступному запуску. """
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except (json.JSONDecodeError, UnicodeDecodeError) as e:
            return False, f"Файл не є коректним JSON ({e})"
        except Exception as e:
            return False, f"Не вдалося прочитати файл ({e})"

        if not isinstance(data, dict) or not data:
            return False, "Файл порожній або має невірну структуру (очікується JSON-об'єкт)"

        # Тема CustomTkinter завжди описує стилі базових віджетів —
        # якщо жодного з очікуваних ключів немає, це, ймовірно, не тема.
        required_keys = {"CTk", "CTkButton", "CTkFrame", "CTkLabel"}
        if not required_keys.intersection(data.keys()):
            return False, "Файл не схожий на тему CustomTkinter (відсутні очікувані ключі стилів)"

        return True, ""

    def change_theme(self, choice):
        ctk.set_appearance_mode(choice)
        self.save_settings()

    def change_color_theme(self, choice):
        self.save_settings()

    def reset_to_factory_themes(self):
        if messagebox.askyesno("Скидання", "Ви впевнені, що хочете видалити ВСІ створені та імпортовані теми?"):
            try:
                for file in os.listdir(self.themes_dir):
                    if file != "default_launcher.json" and file.endswith(".json"):
                        os.remove(os.path.join(self.themes_dir, file))
                self.color_dropdown.configure(values=self.get_available_themes())
                self.color_dropdown.set("default_launcher")
                self.change_color_theme("default_launcher")
                messagebox.showinfo("Скидання", "Кастомні теми видалено! Застосовано стандартний стиль.")
            except Exception as e:
                messagebox.showerror("Помилка", f"Помилка очищення тем: {e}")

    def on_slider_move(self, value):
        self.delay_label.configure(text=f"Затримка між запуском програм: {int(value)} сек.")
        self.save_settings()

    def update_close_protocol(self):
        """ Реально перемикає обробник хрестика вікна між 'ховати в трей'
        та 'повністю виходити', відповідно до стану чекбокса. """
        if self.tray_checkbox.get() == 1:
            self.app.protocol('WM_DELETE_WINDOW', self.app.withdraw_window)
        else:
            self.app.protocol('WM_DELETE_WINDOW', self.app.exit_program)
        self.save_settings()

    def open_hotkeys_dialog(self):
        """ Відкриває окреме вікно, де зібрані УСІ гарячі клавіші лаунчера
        (показ вікна + всі набори) в одному місці. """
        HotkeyManagerDialog(self.app, self, self.preset_manager_ref)

    def open_stats_dialog(self):
        """ Відкриває окреме вікно статистики використання (графік запусків
        + кнопка повного скидання) — так само централізовано, як і вікно
        гарячих клавіш вище. """
        if not self.programs_provider:
            messagebox.showwarning(
                "Недоступно",
                "Список програм недоступний — спробуйте перезапустити лаунчер."
            )
            return
        StatsDialog(self.app, self.programs_provider, on_reset=self.stats_reset_callback)

    def get_show_hotkey(self):
        """ Поточна (валідована) гаряча клавіша показу вікна лаунчера. """
        return self._validated_show_hotkey

    def set_show_hotkey(self, normalized_hotkey):
        """ Зберігає нову гарячу клавішу показу вікна (порожній рядок —
        вимкнути) та одразу перереєстровує глобальні хуки клавіатури. """
        self._validated_show_hotkey = normalized_hotkey or ""
        self.save_settings()
        if self.hotkeys_changed_callback:
            self.hotkeys_changed_callback()

    def save_settings(self):
        settings = {
            "theme": self.theme_dropdown.get(),
            "color_theme": self.color_dropdown.get(),
            "close_after_launch": self.close_checkbox.get() == 1,
            "minimize_to_tray": self.tray_checkbox.get() == 1,
            "delay": int(self.delay_slider.get()),
            "windows_autostart": self.autostart_checkbox.get() == 1,
            "smart_launch": self.smart_launch_checkbox.get() == 1,
            "show_hotkey": self._validated_show_hotkey
        }
        try:
            with open(self.settings_file, "w", encoding="utf-8") as f:
                json.dump(settings, f, indent=4, ensure_ascii=False)
        except Exception as e:
            print(f"Помилка збереження налаштувань: {e}")

    def load_and_apply_saved_widgets(self):
        if os.path.exists(self.settings_file):
            try:
                with open(self.settings_file, "r", encoding="utf-8") as f:
                    st = json.load(f)

                self.theme_dropdown.set(st.get("theme", "Dark"))
                self.color_dropdown.set(st.get("color_theme", "default_launcher"))

                if st.get("close_after_launch", False):
                    self.close_checkbox.select()
                else:
                    self.close_checkbox.deselect()

                if st.get("minimize_to_tray", True):
                    self.tray_checkbox.select()
                else:
                    self.tray_checkbox.deselect()

                if self.is_windows_autostart_active():
                    self.autostart_checkbox.select()
                else:
                    self.autostart_checkbox.deselect()

                if st.get("smart_launch", False):
                    self.smart_launch_checkbox.select()
                else:
                    self.smart_launch_checkbox.deselect()

                delay_val = st.get("delay", 0)
                self.delay_slider.set(delay_val)
                self.delay_label.configure(text=f"Затримка між запуском програм: {delay_val} сек.")

                self._validated_show_hotkey = (st.get("show_hotkey", "ctrl+alt+l") or "").strip().lower()
            except Exception as e:
                print(f"Помилка завантаження налаштувань: {e}")
        else:
            self.theme_dropdown.set("Dark")
            self.color_dropdown.set("default_launcher")
            self.tray_checkbox.select()
            if self.is_windows_autostart_active():
                self.autostart_checkbox.select()

        # select()/deselect() вище НЕ викликають command, тому протокол
        # закриття вікна потрібно застосувати вручну одразу після завантаження
        if self.tray_checkbox.get() == 1:
            self.app.protocol('WM_DELETE_WINDOW', self.app.withdraw_window)
        else:
            self.app.protocol('WM_DELETE_WINDOW', self.app.exit_program)