import customtkinter as ctk
from tkinter import messagebox
import os
import json
import subprocess  # Модуль для надсилання нативних системних команд закриття процесів
from process_utils import smart_startfile, resolve_program_entry


class PresetManager(ctk.CTkFrame):
    # Ті ж самі значення, що і на головному екрані ("Програми"), щоб
    # категорії та їх позначення виглядали й поводились однаково
    CATEGORY_ALL = "Всі"
    CATEGORY_UNSET = "Без категорії"

    def __init__(self, master, on_hotkeys_changed=None, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self.presets_file = "jsons_saves/presets.json"
        self.all_programs = []
        self.presets = {}
        self.checkboxes = {}
        # Запам'ятовує позначені (галочка) програми за їх назвою — незалежно
        # від того, чи показані вони зараз під поточним фільтром категорій.
        # Без цього перемикання фільтра "губило" б уже зроблений вибір.
        self.program_selection = {}
        # Викликається щоразу, коли гаряча клавіша якогось набору змінилась
        # (додана/змінена/видалена), щоб головний файл лаунчера перереєстрував
        # глобальні хуки клавіатури з актуальними даними
        self.on_hotkeys_changed = on_hotkeys_changed

        os.makedirs("jsons_saves", exist_ok=True)
        self.load_presets()
        self.create_widgets()

    def load_presets(self):
        if os.path.exists(self.presets_file):
            try:
                with open(self.presets_file, "r", encoding="utf-8") as file:
                    self.presets = json.load(file)
            except:
                self.presets = {}
        else:
            self.presets = {}

    def create_widgets(self):
        # Главный скроллируемый контейнер
        self.scroll_container = ctk.CTkScrollableFrame(
            self,
            fg_color="transparent"
        )
        self.scroll_container.pack(fill="both", expand=True)

        # -------------------------------
        # СЕКЦІЯ 1: Створення нового пресету
        # -------------------------------
        create_frame = ctk.CTkFrame(self.scroll_container)
        create_frame.pack(pady=10, fill="x", padx=5)

        ctk.CTkLabel(
            create_frame,
            text="Створити новий набір програм",
            font=("Arial", 13, "bold")
        ).pack(pady=5)

        self.preset_name_entry = ctk.CTkEntry(
            create_frame,
            placeholder_text="Введіть назву (напр: Робота, Ігри)"
        )
        self.preset_name_entry.pack(
            pady=5,
            padx=10,
            fill="x"
        )

        # -------------------------------
        # Фільтр за категорією (той самий принцип, що і на вкладці "Програми")
        # -------------------------------
        category_filter_frame = ctk.CTkFrame(create_frame, fg_color="transparent")
        category_filter_frame.pack(pady=(0, 5), padx=10, fill="x")

        ctk.CTkLabel(category_filter_frame, text="🏷 Категорія:").pack(side="left", padx=(0, 8))

        self.category_filter_dropdown = ctk.CTkOptionMenu(
            category_filter_frame,
            values=[self.CATEGORY_ALL],
            command=lambda choice: self._render_program_checkboxes()
        )
        self.category_filter_dropdown.pack(side="left", fill="x", expand=True)
        self.category_filter_dropdown.set(self.CATEGORY_ALL)

        # Скролл только для списка программ
        self.scroll_programs = ctk.CTkScrollableFrame(
            create_frame,
            height=150
        )
        self.scroll_programs.pack(
            pady=5,
            padx=10,
            fill="x"
        )

        btn_build = ctk.CTkButton(
            create_frame,
            text="💾 Зберегти новий набір",
            command=self.save_new_preset
        )
        btn_build.pack(
            pady=8,
            padx=10,
            fill="x"
        )

        # -------------------------------
        # СЕКЦІЯ 2: Керування пресетами
        # -------------------------------
        manage_frame = ctk.CTkFrame(self.scroll_container)
        manage_frame.pack(
            pady=10,
            fill="x",
            padx=5
        )

        ctk.CTkLabel(
            manage_frame,
            text="Ваші збережені набори",
            font=("Arial", 13, "bold")
        ).pack(pady=5)

        self.preset_dropdown = ctk.CTkOptionMenu(
            manage_frame,
            values=["Немає створених наборів"],
            command=self.on_preset_changed
        )
        self.preset_dropdown.pack(
            pady=5,
            padx=10,
            fill="x"
        )

        # Примітка: гарячі клавіші наборів більше не редагуються тут —
        # усе, що стосується гарячих клавіш (і показу вікна, і наборів),
        # централізовано у вкладці "Налаштування" -> "Керування гарячими
        # клавішами...", щоб не дублювати цю настройку по різних вкладках.

        self.autostart_checkbox = ctk.CTkCheckBox(
            manage_frame,
            text="🚀 Стартовий набір: запускати цей набір одразу при відкритті лаунчера",
            command=self.toggle_preset_autostart
        )
        self.autostart_checkbox.pack(
            pady=(0, 5),
            padx=10,
            fill="x",
            anchor="w"
        )

        # Панель дій
        actions_frame = ctk.CTkFrame(
            manage_frame,
            fg_color="transparent"
        )
        actions_frame.pack(
            pady=8,
            padx=10,
            fill="x"
        )

        self.btn_launch = ctk.CTkButton(
            actions_frame,
            text="🚀 Запустити набір",
            command=self.launch_current_preset
        )
        self.btn_launch.pack(
            side="left",
            expand=True,
            fill="x",
            padx=2
        )

        self.btn_stop = ctk.CTkButton(
            actions_frame,
            text="⛔ Закрити набір",
            command=self.close_current_preset
        )
        self.btn_stop.pack(
            side="left",
            expand=True,
            fill="x",
            padx=2
        )

        self.btn_delete = ctk.CTkButton(
            manage_frame,
            text="❌ Видалити цей набір",
            fg_color="transparent",
            border_width=1,
            text_color=("#001F3F", "#E5E9F0"),
            command=self.delete_preset
        )
        self.btn_delete.pack(
            pady=5,
            padx=10,
            fill="x"
        )

        self.update_dropdown()

    def load_data_from_json(self, programs_list):
        """ Метод оновлює список чекбоксів на основі софту з головного екрана """
        # Перед оновленням списку зберігаємо поточний вибір (галочки),
        # інакше він загубиться разом зі старими віджетами
        self._sync_selection_state()

        self.all_programs = programs_list
        self._update_category_filter_values()
        self._render_program_checkboxes()

    def _get_program_category(self, prog):
        """ Нормалізує категорію програми: порожнє значення -> CATEGORY_UNSET
        (та сама логіка, що і на головному екрані). """
        cat = (prog.get("category") or "").strip()
        return cat if cat else self.CATEGORY_UNSET

    def _get_all_categories(self):
        """ Список усіх категорій, що реально використовуються серед програм. """
        return sorted({self._get_program_category(p) for p in self.all_programs})

    def _update_category_filter_values(self):
        """ Оновлює список значень фільтра відповідно до поточних категорій.
        Якщо обрана категорія зникла — скидає фільтр на "Всі". """
        values = [self.CATEGORY_ALL] + self._get_all_categories()
        current = self.category_filter_dropdown.get()
        self.category_filter_dropdown.configure(values=values)
        if current not in values:
            self.category_filter_dropdown.set(self.CATEGORY_ALL)

    def _sync_selection_state(self):
        """ Запам'ятовує, які програми зараз позначені галочкою, ПЕРЕД тим
        як їхні чекбокси будуть знищені (зміна фільтра категорій, оновлення
        списку з головного екрана тощо) — щоб вибір користувача не губився. """
        for name, (cb_widget, _path, _args) in self.checkboxes.items():
            self.program_selection[name] = (cb_widget.get() == 1)

    def _render_program_checkboxes(self):
        """ Перемальовує список чекбоксів програм відповідно до обраної
        категорії у фільтрі, зберігаючи раніше зроблений вибір (навіть для
        програм, які зараз приховані іншою категорією). """
        self._sync_selection_state()

        for widget in self.scroll_programs.winfo_children():
            widget.destroy()
        self.checkboxes = {}

        selected_category = self.category_filter_dropdown.get()
        if selected_category == self.CATEGORY_ALL:
            visible_programs = self.all_programs
        else:
            visible_programs = [
                p for p in self.all_programs
                if self._get_program_category(p) == selected_category
            ]

        if not visible_programs:
            text = (
                "Немає жодної доданої програми на вкладці 'Програми'."
                if not self.all_programs
                else f"У категорії «{selected_category}» ще немає програм."
            )
            ctk.CTkLabel(self.scroll_programs, text=text, text_color="gray").pack(pady=15, padx=5)
            return

        for prog in visible_programs:
            cat = (prog.get("category") or "").strip()
            display_name = f"[{cat}] {prog['name']}" if cat else prog["name"]

            cb = ctk.CTkCheckBox(self.scroll_programs, text=display_name)
            cb.pack(pady=2, anchor="w", padx=10)
            if self.program_selection.get(prog["name"]):
                cb.select()

            # Зберігаємо і аргументи запуску (якщо задані на головному екрані),
            # щоб вони перенеслись і в набір
            self.checkboxes[prog["name"]] = (cb, prog["path"], prog.get("args", ""))

    def save_new_preset(self):
        name = self.preset_name_entry.get().strip()
        if not name or name == "Немає створених наборів":
            messagebox.showwarning("Помилка", "Введіть коректну назву для набору!")
            return

        # Враховуємо вибір і серед програм, прихованих поточним фільтром
        # категорій, а не лише серед тих, що зараз відображені на екрані
        self._sync_selection_state()

        selected_entries = []
        for prog in self.all_programs:
            if self.program_selection.get(prog["name"]):
                # Зберігаємо як {"path", "args"}, щоб аргументи запуску
                # (задані на головному екрані) працювали і всередині набору
                selected_entries.append({"path": prog["path"], "args": prog.get("args", "")})

        if not selected_entries:
            messagebox.showwarning("Помилка", "Оберіть хоча б одну програму для набору!")
            return

        self.presets[name] = {"programs": selected_entries}

        with open(self.presets_file, "w", encoding="utf-8") as file:
            json.dump(self.presets, file, indent=4, ensure_ascii=False)

        self.preset_name_entry.delete(0, "end")
        self.program_selection = {}
        self._render_program_checkboxes()

        self.update_dropdown()
        self.preset_dropdown.set(name)
        messagebox.showinfo("Успіх", f"Набір '{name}' успішно створено!")

    def update_dropdown(self):
        names = list(self.presets.keys())
        if names:
            self.preset_dropdown.configure(values=names)
            if self.preset_dropdown.get() not in names:
                self.preset_dropdown.set(names[0])
        else:
            self.preset_dropdown.configure(values=["Немає створених наборів"])
            self.preset_dropdown.set("Немає створених наборів")

        self.refresh_autostart_checkbox_state()

    def on_preset_changed(self, choice):
        self.refresh_autostart_checkbox_state()

    def get_preset_hotkeys(self):
        """ Повертає {назва_набору: гаряча_клавіша} лише для наборів,
        яким реально призначена непорожня комбінація. Використовується
        головним файлом лаунчера для реєстрації глобальних хуків. """
        result = {}
        for name, data in self.presets.items():
            if isinstance(data, dict):
                hk = (data.get("hotkey") or "").strip()
                if hk:
                    result[name] = hk
        return result

    def set_preset_hotkey(self, name, hotkey):
        """ Програмно встановлює/прибирає гарячу клавішу набору за назвою
        і одразу зберігає у presets.json. Викликається виключно з
        централізованого вікна "Керування гарячими клавішами" у
        Налаштуваннях (єдине місце в лаунчері, де редагуються гарячі
        клавіші), тому значення сюди вже приходить нормалізованим ззовні.
        Повертає True, якщо набір знайдено і значення збережено. """
        if name not in self.presets:
            return False

        if not isinstance(self.presets[name], dict):
            self.presets[name] = {"programs": []}

        self.presets[name]["hotkey"] = hotkey or ""

        with open(self.presets_file, "w", encoding="utf-8") as file:
            json.dump(self.presets, file, indent=4, ensure_ascii=False)

        if self.on_hotkeys_changed:
            self.on_hotkeys_changed()

        return True

    def refresh_autostart_checkbox_state(self):
        """ Синхронізує стан чекбокса автозапуску з даними обраного пресету """
        selected = self.preset_dropdown.get()

        if not selected or selected == "Немає створених наборів" or selected not in self.presets:
            self.autostart_checkbox.deselect()
            self.autostart_checkbox.configure(state="disabled")
            return

        self.autostart_checkbox.configure(state="normal")

        preset = self.presets.get(selected, {})
        if preset.get("autostart", False):
            self.autostart_checkbox.select()
        else:
            self.autostart_checkbox.deselect()

    def toggle_preset_autostart(self):
        """ Вмикає/вимикає автозапуск для обраного пресету.
        Лаунчер (check_and_run_autostart) очікує лише ОДИН автозапускний
        пресет, тому при увімкненні знімаємо прапорець з усіх інших. """
        selected = self.preset_dropdown.get()

        if not selected or selected == "Немає створених наборів" or selected not in self.presets:
            self.autostart_checkbox.deselect()
            return

        enable = (self.autostart_checkbox.get() == 1)

        if enable:
            for name, data in self.presets.items():
                if isinstance(data, dict):
                    data["autostart"] = (name == selected)
        else:
            self.presets[selected]["autostart"] = False

        with open(self.presets_file, "w", encoding="utf-8") as file:
            json.dump(self.presets, file, indent=4, ensure_ascii=False)

    def _is_smart_launch_enabled(self):
        """ Читає прапорець "Розумний запуск" з jsons_saves/settings.json.
        За замовчуванням (якщо файл ще не створено) — вимкнено. """
        settings_file = "jsons_saves/settings.json"
        if os.path.exists(settings_file):
            try:
                with open(settings_file, "r", encoding="utf-8") as f:
                    return json.load(f).get("smart_launch", False)
            except Exception:
                pass
        return False

    def launch_current_preset(self):
        selected = self.preset_dropdown.get()
        if selected == "Немає створених наборів": return
        self.launch_preset_by_name(selected)

    def launch_preset_by_name(self, name):
        """ Запускає всі програми обраного набору за його назвою.
        Винесено окремо від launch_current_preset, щоб цю саму логіку
        можна було викликати і з випадаючого списку на екрані, і напряму
        з глобальної гарячої клавіші (без відкриття вікна лаунчера). """
        preset = self.presets.get(name)
        if preset and "programs" in preset:
            smart_launch = self._is_smart_launch_enabled()
            for prog_item in preset["programs"]:
                path, args = resolve_program_entry(prog_item)
                if os.path.exists(path):
                    smart_startfile(path, args=args, skip_if_running=smart_launch)

    def close_current_preset(self):
        """ Примусове завершення процесів усіх програм поточного пресету """
        selected = self.preset_dropdown.get()
        if selected == "Немає створених наборів": return

        preset = self.presets.get(selected)
        if not preset or "programs" not in preset: return

        for prog_item in preset["programs"]:
            path, _args = resolve_program_entry(prog_item)
            exe_name = os.path.basename(path)
            if exe_name.lower().endswith(".exe"):
                try:
                    # Примусово і тихо гасимо процес за допомогою рідної Windows утиліти
                    subprocess.run(
                        f'taskkill /F /IM "{exe_name}"',
                        shell=True,
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL
                    )
                except:
                    pass
        print(f"Пресет '{selected}': процеси успішно завершено.")

    def delete_preset(self):
        selected_preset = self.preset_dropdown.get()
        if isinstance(selected_preset, list):
            selected_preset = selected_preset[0] if len(selected_preset) > 0 else ""
        selected_preset = str(selected_preset).strip()

        if not selected_preset or selected_preset == "Немає створених наборів":
            return

        if messagebox.askyesno("Видалення", f"Ви впевнені, що хочете видалити набір '{selected_preset}'?"):
            if selected_preset in self.presets:
                del self.presets[selected_preset]

            with open(self.presets_file, "w", encoding="utf-8") as file:
                json.dump(self.presets, file, indent=4, ensure_ascii=False)

            if self.on_hotkeys_changed:
                self.on_hotkeys_changed()

            self.update_dropdown()

            new_selected = self.preset_dropdown.get()
            if isinstance(new_selected, list):
                new_selected = new_selected[0] if len(new_selected) > 0 else ""
            new_selected = str(new_selected).strip()

            if new_selected and new_selected != "Немає створених наборів":
                try:
                    self.on_preset_changed(new_selected)
                except:
                    pass
            else:
                try:
                    self.on_preset_changed("")
                except:
                    pass