import customtkinter as ctk
from tkinter import messagebox
import os
import json
import subprocess  # Модуль для надсилання нативних системних команд закриття процесів


class PresetManager(ctk.CTkFrame):
    def __init__(self, master, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self.presets_file = "jsons_saves/presets.json"
        self.all_programs = []
        self.presets = {}
        self.checkboxes = {}

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
        self.all_programs = programs_list

        for widget in self.scroll_programs.winfo_children():
            widget.destroy()

        self.checkboxes = {}
        for prog in self.all_programs:
            cb = ctk.CTkCheckBox(self.scroll_programs, text=prog["name"])
            cb.pack(pady=2, anchor="w", padx=10)
            self.checkboxes[prog["name"]] = (cb, prog["path"])

    def save_new_preset(self):
        name = self.preset_name_entry.get().strip()
        if not name or name == "Немає створених наборів":
            messagebox.showwarning("Помилка", "Введіть коректну назву для набору!")
            return

        selected_paths = []
        for cb_name, (cb_widget, cb_path) in self.checkboxes.items():
            if cb_widget.get() == 1:
                selected_paths.append(cb_path)

        if not selected_paths:
            messagebox.showwarning("Помилка", "Оберіть хоча б одну програму для набору!")
            return

        self.presets[name] = {"programs": selected_paths}

        with open(self.presets_file, "w", encoding="utf-8") as file:
            json.dump(self.presets, file, indent=4, ensure_ascii=False)

        self.preset_name_entry.delete(0, "end")
        for cb_widget, _ in self.checkboxes.values():
            cb_widget.deselect()

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

    def on_preset_changed(self, choice):
        pass

    def launch_current_preset(self):
        selected = self.preset_dropdown.get()
        if selected == "Немає створених наборів": return

        preset = self.presets.get(selected)
        if preset and "programs" in preset:
            for path in preset["programs"]:
                if os.path.exists(path):
                    try:
                        os.startfile(path)
                    except:
                        pass

    def close_current_preset(self):
        """ Примусове завершення процесів усіх програм поточного пресету """
        selected = self.preset_dropdown.get()
        if selected == "Немає створених наборів": return

        preset = self.presets.get(selected)
        if not preset or "programs" not in preset: return

        for path in preset["programs"]:
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