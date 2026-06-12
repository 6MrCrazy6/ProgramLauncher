import customtkinter as ctk
import os
import json
import time
from datetime import datetime


class ScheduleManager(ctk.CTkFrame):
    def __init__(self, parent, exit_program_callback):
        super().__init__(parent, fg_color="transparent")
        self.exit_program_callback = exit_program_callback
        self.db_path = "jsons_saves/schedule.json"

        self.available_programs = []
        self.available_presets = []

        # Словник для переведення днів тижня з тексту в індекси Python (0 = Понеділок, 6 = Неділя)
        self.days_map = {
            "Понеділок": 0, "Вівторок": 1, "Середа": 2, "Четвер": 3,
            "П'ятниця": 4, "Субота": 5, "Неділя": 6
        }
        self.days_list = list(self.days_map.keys())

        os.makedirs("jsons_saves", exist_ok=True)

        # --- UI ЕЛЕМЕНТИ ---
        title = ctk.CTkLabel(self, text="⏰ Налаштування розкладу та днів", font=ctk.CTkFont(size=16, weight="bold"))
        title.pack(pady=10)

        # 1. Вибір днів тижня (З якого по який)
        days_frame = ctk.CTkFrame(self)
        days_frame.pack(pady=5, fill="x", padx=10)

        ctk.CTkLabel(days_frame, text="Дні: з").pack(side="left", padx=5, pady=10)
        self.start_day_chooser = ctk.CTkOptionMenu(days_frame, values=self.days_list, width=120)
        self.start_day_chooser.pack(side="left", padx=2)
        self.start_day_chooser.set("Понеділок")

        ctk.CTkLabel(days_frame, text="по").pack(side="left", padx=5)
        self.end_day_chooser = ctk.CTkOptionMenu(days_frame, values=self.days_list, width=120)
        self.end_day_chooser.pack(side="left", padx=2)
        self.end_day_chooser.set("П'ятниця")

        # 2. Вибір часу
        time_frame = ctk.CTkFrame(self)
        time_frame.pack(pady=5, fill="x", padx=10)

        ctk.CTkLabel(time_frame, text="Час запуску (ГГ:ХХ):").pack(side="left", padx=10, pady=10)
        self.hour_entry = ctk.CTkEntry(time_frame, width=50, placeholder_text="09")
        self.hour_entry.pack(side="left", padx=2)
        ctk.CTkLabel(time_frame, text=":").pack(side="left")
        self.minute_entry = ctk.CTkEntry(time_frame, width=50, placeholder_text="00")
        self.minute_entry.pack(side="left", padx=2)

        # 3. Перемикач: Програма чи Набір
        type_frame = ctk.CTkFrame(self)
        type_frame.pack(pady=5, fill="x", padx=10)

        ctk.CTkLabel(type_frame, text="Що запускати:").pack(side="left", padx=10, pady=10)
        self.type_var = ctk.StringVar(value="Програма")
        self.type_switch = ctk.CTkSegmentedButton(
            type_frame,
            values=["Програма", "Набір (Пресет)"],
            variable=self.type_var,
            command=self.on_type_changed
        )
        self.type_switch.pack(side="left", padx=10, fill="x", expand=True)

        # 4. Вибір конкретного елементу
        target_frame = ctk.CTkFrame(self)
        target_frame.pack(pady=5, fill="x", padx=10)

        ctk.CTkLabel(target_frame, text="Виберіть ціль:").pack(side="left", padx=10, pady=10)
        self.item_chooser = ctk.CTkOptionMenu(target_frame, values=["Спочатку додайте програми"])
        self.item_chooser.pack(side="left", fill="x", expand=True, padx=10)

        # Кнопка збереження завдання (Без fg_color — колір береться з теми автоматично)
        self.btn_save = ctk.CTkButton(self, text="➕ Додати до розкладу", command=self.save_schedule_task)
        self.btn_save.pack(pady=10, fill="x", padx=10)

        # Список поточних завдань у розкладі
        ctk.CTkLabel(self, text="Поточний розклад:", font=ctk.CTkFont(weight="bold")).pack(pady=5, anchor="w", padx=10)

        self.tasks_list_frame = ctk.CTkScrollableFrame(self)
        self.tasks_list_frame.pack(pady=5, fill="both", expand=True, padx=10)

        self.load_and_refresh_ui()
        self.start_checking_loop()

    def update_data_lists(self, current_programs):
        self.available_programs = current_programs
        self.available_presets = []
        presets_file = "jsons_saves/presets.json"
        if os.path.exists(presets_file):
            try:
                with open(presets_file, "r", encoding="utf-8") as f:
                    self.available_presets = list(json.load(f).keys())
            except:
                pass
        self.on_type_changed(self.type_var.get())

    def on_type_changed(self, current_type):
        if current_type == "Програма":
            names = [p["name"] for p in self.available_programs]
            if names:
                self.item_chooser.configure(values=names)
                self.item_chooser.set(names[0])
            else:
                self.item_chooser.configure(values=["Список програм порожній"])
                self.item_chooser.set("Список програм порожній")
        else:
            if self.available_presets:
                self.item_chooser.configure(values=self.available_presets)
                self.item_chooser.set(self.available_presets[0])
            else:
                self.item_chooser.configure(values=["Створіть хоча б один набір"])
                self.item_chooser.set("Створіть хоча б один набір")

    def save_schedule_task(self):
        h = self.hour_entry.get().strip().zfill(2)
        m = self.minute_entry.get().strip().zfill(2)
        start_day = self.start_day_chooser.get()
        end_day = self.end_day_chooser.get()
        selected_item = self.item_chooser.get()
        current_type = self.type_var.get()

        if not h.isdigit() or not m.isdigit() or int(h) > 23 or int(m) > 59:
            return

        if selected_item in ["Список програм порожній", "Спочатку додайте програми", "Створіть хоча б один набір"]:
            return

        tasks = self.read_json()

        task_entry = {
            "time": f"{h}:{m}",
            "start_day": start_day,
            "end_day": end_day,
            "type": "preset" if current_type == "Набір (Пресет)" else "single",
            "name": selected_item,
            "triggered_today": False
        }

        if current_type == "Програма":
            prog_path = ""
            for p in self.available_programs:
                if p["name"] == selected_item:
                    prog_path = p["path"]
                    break
            task_entry["path"] = prog_path

        tasks.append(task_entry)
        self.write_json(tasks)
        self.load_and_refresh_ui()

        self.hour_entry.delete(0, "end")
        self.minute_entry.delete(0, "end")

    def load_and_refresh_ui(self):
        for widget in self.tasks_list_frame.winfo_children():
            widget.destroy()

        tasks = self.read_json()
        if not tasks:
            ctk.CTkLabel(self.tasks_list_frame, text="Завдань немає", text_color="gray").pack(pady=20)
            return

        for idx, task in enumerate(tasks):
            row = ctk.CTkFrame(self.tasks_list_frame, fg_color="transparent")
            row.pack(fill="x", pady=4)

            icon = "⚙" if task.get("type") == "preset" else "📱"
            # Красиво виводимо дні, наприклад: Пн-Пт ⏰ 09:00
            days_str = f"{task.get('start_day', 'Пн')[:2]}-{task.get('end_day', 'Пт')[:2]}"

            lbl = ctk.CTkLabel(row, text=f"🗓 {days_str}  ⏰ {task['time']}  [{icon}] {task['name']}", anchor="w")
            lbl.pack(side="left", fill="x", expand=True, padx=5)

            # Кнопка видалення тепер адаптивна (без жорстких кольорів, використовує border_width)
            btn_del = ctk.CTkButton(
                row,
                text="❌",
                width=30,
                fg_color="transparent",
                border_width=1,
                command=lambda i=idx: self.delete_task(i)
            )
            btn_del.pack(side="right", padx=5)

    def delete_task(self, idx):
        tasks = self.read_json()
        if 0 <= idx < len(tasks):
            tasks.pop(idx)
        self.write_json(tasks)
        self.load_and_refresh_ui()

    def read_json(self):
        if os.path.exists(self.db_path):
            try:
                with open(self.db_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except:
                pass
        return []

    def write_json(self, data):
        with open(self.db_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)

    def is_current_day_in_range(self, start_day_name, end_day_name):
        """ Перевіряє, чи входить сьогоднішній день у налаштований діапазон """
        current_day_idx = datetime.now().weekday()  # Понеділок = 0, Неділя = 6

        start_idx = self.days_map.get(start_day_name, 0)
        end_idx = self.days_map.get(end_day_name, 4)

        if start_idx <= end_idx:
            # Звичайний діапазон (наприклад, з Пн(0) по Пт(4))
            return start_idx <= current_day_idx <= end_idx
        else:
            # Діапазон з переходом через неділю (наприклад, з Пт(4) по Вт(1))
            return current_day_idx >= start_idx or current_day_idx <= end_idx

    def start_checking_loop(self):
        now = datetime.now()
        current_time_str = now.strftime("%H:%M")

        tasks = self.read_json()
        updated = False

        if current_time_str == "00:00":
            for t in tasks:
                if t.get("triggered_today", True):
                    t["triggered_today"] = False
                    updated = True

        settings_file = "jsons_saves/settings.json"
        delay = 0
        close_after = False
        if os.path.exists(settings_file):
            try:
                with open(settings_file, "r") as sf:
                    st = json.load(sf)
                    delay = st.get("delay", 0)
                    close_after = st.get("close_after_launch", False)
            except:
                pass

        launched_something = False

        for t in tasks:
            if t["time"] == current_time_str and not t.get("triggered_today", False):

                # НОВА ПЕРЕВІРКА: Чи підходить сьогоднішній день тижня під налаштування завдання?
                s_day = t.get("start_day", "Понеділок")
                e_day = t.get("end_day", "П'ятниця")

                if not self.is_current_day_in_range(s_day, e_day):
                    continue  # Якщо сьогодні вихідний, а треба було в будні — просто пропускаємо

                # Запуск поодинокої програми
                if t.get("type", "single") == "single":
                    if os.path.exists(t.get("path", "")):
                        try:
                            os.startfile(t["path"])
                            t["triggered_today"] = True
                            updated = True
                            launched_something = True
                        except:
                            pass

                # Запуск пресету
                elif t.get("type") == "preset":
                    presets_file = "jsons_saves/presets.json"
                    if os.path.exists(presets_file):
                        try:
                            with open(presets_file, "r", encoding="utf-8") as pf:
                                all_presets = json.load(pf)
                                target_preset = all_presets.get(t["name"])

                                if target_preset and "programs" in target_preset:
                                    for idx, p_path in enumerate(target_preset["programs"]):
                                        if idx > 0 and delay > 0:
                                            time.sleep(delay)
                                        try:
                                            os.startfile(p_path)
                                        except:
                                            pass

                                    t["triggered_today"] = True
                                    updated = True
                                    launched_something = True
                        except:
                            pass

        if updated:
            self.write_json(tasks)

        if launched_something and close_after:
            self.exit_program_callback()
            return

        self.after(20000, self.start_checking_loop)