import customtkinter as ctk
import os
import sys
import json
import time
import threading
from datetime import datetime
from process_utils import smart_startfile, resolve_program_entry
from locale_manager import t

# Канонічні (мовонезалежні) ключі днів тижня. Саме вони зберігаються у
# schedule.json як start_day/end_day, щоб уже збережений розклад не ламався
# при зміні мови інтерфейсу — на екрані показується переклад (day_labels),
# а на диск завжди пишеться цей стабільний ключ.
DAY_KEYS = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]

# Старі версії лаунчера зберігали start_day/end_day як українські назви
# напряму — підтримуємо їх на читання, щоб уже збережені розклади не злетіли.
_LEGACY_UK_TO_KEY = {
    "Понеділок": "mon", "Вівторок": "tue", "Середа": "wed", "Четвер": "thu",
    "П'ятниця": "fri", "Субота": "sat", "Неділя": "sun",
}


def get_base_dir():
    """ Повертає теку, де реально лежить .exe (при білді) або .py скрипт.
    Це важливо для портативного білда без інсталятора: exe можуть запустити
    не з його "рідної" робочої директорії (наприклад, через ярлик автозавантаження
    з іншим "Start in"), тож шляхи до jsons_saves треба рахувати від sys.executable,
    а не покладатися на відносний шлях. """
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


class ScheduleManager(ctk.CTkFrame):
    def __init__(self, parent, exit_program_callback):
        super().__init__(parent, fg_color="transparent")
        self.exit_program_callback = exit_program_callback

        self.base_dir = get_base_dir()
        self.db_path = os.path.join(self.base_dir, "jsons_saves", "schedule.json")

        # Лок для безпечного читання/запису json одночасно з головного потоку (UI)
        # та фонового потоку перевірки розкладу
        self._file_lock = threading.Lock()
        self._stop_event = threading.Event()
        self._worker_thread = None

        self.available_programs = []
        self.available_presets = []

        # Переклад днів для показу в UI (мовозалежний) + зворотні мапи, щоб
        # конвертувати обраний у випадайці підпис назад у канонічний ключ.
        self.day_labels = [t(f"schedule.day_{key}") for key in DAY_KEYS]
        self.day_label_to_key = dict(zip(self.day_labels, DAY_KEYS))
        self.day_key_to_label = dict(zip(DAY_KEYS, self.day_labels))
        self.day_key_to_index = {key: i for i, key in enumerate(DAY_KEYS)}

        # Сталі підписи-заглушки — рахуємо один раз, щоб порівнювати з ними
        # (обраний елемент, тип запуску) далі по коду без повторних викликів t().
        self.type_label_program = t("schedule.type_program")
        self.type_label_preset = t("schedule.type_preset")
        self.no_programs_yet_label = t("schedule.no_programs_yet")
        self.programs_list_empty_label = t("schedule.programs_list_empty")
        self.create_preset_first_label = t("schedule.create_preset_first")

        os.makedirs(os.path.join(self.base_dir, "jsons_saves"), exist_ok=True)

        # --- UI ЕЛЕМЕНТИ ---
        title = ctk.CTkLabel(self, text=t("schedule.title"), font=ctk.CTkFont(size=16, weight="bold"))
        title.pack(pady=10)

        # 1. Вибір днів тижня (З якого по який)
        days_frame = ctk.CTkFrame(self)
        days_frame.pack(pady=5, fill="x", padx=10)

        ctk.CTkLabel(days_frame, text=t("schedule.days_from")).pack(side="left", padx=5, pady=10)
        self.start_day_chooser = ctk.CTkOptionMenu(days_frame, values=self.day_labels, width=120)
        self.start_day_chooser.pack(side="left", padx=2)
        self.start_day_chooser.set(self.day_key_to_label["mon"])

        ctk.CTkLabel(days_frame, text=t("schedule.days_to")).pack(side="left", padx=5)
        self.end_day_chooser = ctk.CTkOptionMenu(days_frame, values=self.day_labels, width=120)
        self.end_day_chooser.pack(side="left", padx=2)
        self.end_day_chooser.set(self.day_key_to_label["fri"])

        # 2. Вибір часу
        time_frame = ctk.CTkFrame(self)
        time_frame.pack(pady=5, fill="x", padx=10)

        ctk.CTkLabel(time_frame, text=t("schedule.time_label")).pack(side="left", padx=10, pady=10)
        self.hour_entry = ctk.CTkEntry(time_frame, width=50, placeholder_text="09")
        self.hour_entry.pack(side="left", padx=2)
        ctk.CTkLabel(time_frame, text=":").pack(side="left")
        self.minute_entry = ctk.CTkEntry(time_frame, width=50, placeholder_text="00")
        self.minute_entry.pack(side="left", padx=2)

        # 3. Перемикач: Програма чи Набір
        type_frame = ctk.CTkFrame(self)
        type_frame.pack(pady=5, fill="x", padx=10)

        ctk.CTkLabel(type_frame, text=t("schedule.what_label")).pack(side="left", padx=10, pady=10)
        self.type_var = ctk.StringVar(value=self.type_label_program)
        self.type_switch = ctk.CTkSegmentedButton(
            type_frame,
            values=[self.type_label_program, self.type_label_preset],
            variable=self.type_var,
            command=self.on_type_changed
        )
        self.type_switch.pack(side="left", padx=10, fill="x", expand=True)

        # 4. Вибір конкретного елементу
        target_frame = ctk.CTkFrame(self)
        target_frame.pack(pady=5, fill="x", padx=10)

        ctk.CTkLabel(target_frame, text=t("schedule.target_label")).pack(side="left", padx=10, pady=10)
        self.item_chooser = ctk.CTkOptionMenu(target_frame, values=[self.no_programs_yet_label])
        self.item_chooser.pack(side="left", fill="x", expand=True, padx=10)

        # Кнопка збереження завдання (Без fg_color — колір береться з теми автоматично)
        self.btn_save = ctk.CTkButton(self, text=t("schedule.add_btn"), command=self.save_schedule_task)
        self.btn_save.pack(pady=10, fill="x", padx=10)

        # Список поточних завдань у розкладі
        ctk.CTkLabel(self, text=t("schedule.current_list_title"), font=ctk.CTkFont(weight="bold")).pack(pady=5, anchor="w", padx=10)

        self.tasks_list_frame = ctk.CTkScrollableFrame(self)
        self.tasks_list_frame.pack(pady=5, fill="both", expand=True, padx=10)

        self.load_and_refresh_ui()
        self.start_checking_loop()

    def _make_responsive(self, container, label, label_padx=10):
        """ Прив'язує wraplength підпису до реальної ширини контейнера,
        щоб довгі назви програм/пресетів переносились, а не обрізались
        чи вилазили за межі рядка на вузьких вікнах. """

        def _on_container_resize(event):
            scaling = ctk.ScalingTracker.get_widget_scaling(label) or 1
            usable = event.width - (label_padx * 2)
            new_width = max(int(usable / scaling), 120)
            label.configure(wraplength=new_width)

        container.bind("<Configure>", _on_container_resize)

    def update_data_lists(self, current_programs):
        self.available_programs = current_programs
        self.available_presets = []
        presets_file = os.path.join(self.base_dir, "jsons_saves", "presets.json")
        if os.path.exists(presets_file):
            try:
                with open(presets_file, "r", encoding="utf-8") as f:
                    self.available_presets = list(json.load(f).keys())
            except:
                pass
        self.on_type_changed(self.type_var.get())

    def on_type_changed(self, current_type):
        if current_type == self.type_label_program:
            names = [p["name"] for p in self.available_programs]
            if names:
                self.item_chooser.configure(values=names)
                self.item_chooser.set(names[0])
            else:
                self.item_chooser.configure(values=[self.programs_list_empty_label])
                self.item_chooser.set(self.programs_list_empty_label)
        else:
            if self.available_presets:
                self.item_chooser.configure(values=self.available_presets)
                self.item_chooser.set(self.available_presets[0])
            else:
                self.item_chooser.configure(values=[self.create_preset_first_label])
                self.item_chooser.set(self.create_preset_first_label)

    def save_schedule_task(self):
        h = self.hour_entry.get().strip().zfill(2)
        m = self.minute_entry.get().strip().zfill(2)
        # У схованку (schedule.json) пишемо канонічний ключ дня (mon..sun),
        # а не поточний переклад — інакше збережений розклад "зламається"
        # після зміни мови інтерфейсу.
        start_day = self.day_label_to_key.get(self.start_day_chooser.get(), "mon")
        end_day = self.day_label_to_key.get(self.end_day_chooser.get(), "fri")
        selected_item = self.item_chooser.get()
        current_type = self.type_var.get()

        if not h.isdigit() or not m.isdigit() or int(h) > 23 or int(m) > 59:
            return

        if selected_item in [self.programs_list_empty_label, self.no_programs_yet_label, self.create_preset_first_label]:
            return

        tasks = self.read_json()

        task_entry = {
            "time": f"{h}:{m}",
            "start_day": start_day,
            "end_day": end_day,
            "type": "preset" if current_type == self.type_label_preset else "single",
            "name": selected_item,
            "triggered_today": False
        }

        if current_type == self.type_label_program:
            prog_path = ""
            prog_args = ""
            for p in self.available_programs:
                if p["name"] == selected_item:
                    prog_path = p["path"]
                    prog_args = p.get("args", "")
                    break
            task_entry["path"] = prog_path
            task_entry["args"] = prog_args

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
            ctk.CTkLabel(self.tasks_list_frame, text=t("schedule.tasks_empty"), text_color="gray").pack(pady=20)
            return

        for idx, task in enumerate(tasks):
            row = ctk.CTkFrame(self.tasks_list_frame, fg_color="transparent")
            row.pack(fill="x", pady=4)

            icon = "⚙" if task.get("type") == "preset" else "📱"
            # Красиво виводимо дні, наприклад: Пн-Пт ⏰ 09:00
            start_label = self.day_key_to_label[self._normalize_day_key(task.get("start_day", "mon"))]
            end_label = self.day_key_to_label[self._normalize_day_key(task.get("end_day", "fri"))]
            days_str = f"{start_label[:2]}-{end_label[:2]}"

            lbl = ctk.CTkLabel(
                row, text=f"🗓 {days_str}  ⏰ {task['time']}  [{icon}] {task['name']}",
                anchor="w", justify="left"
            )
            lbl.pack(side="left", fill="x", expand=True, padx=5)
            self._make_responsive(row, lbl, label_padx=45)

            # Кнопка видалення прозора (використовує border_width замість заливки),
            # тому колір тексту задаємо явно під обидві теми — інакше він лишається
            # світлим (кольором тексту звичайної кнопки) навіть у світлій темі,
            # і на світлому фоні фрейму стає майже невидимим
            btn_del = ctk.CTkButton(
                row,
                text="❌",
                width=30,
                fg_color="transparent",
                border_width=1,
                text_color=("#001F3F", "#E5E9F0"),
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
        # Лок тут, бо цей метод викликається і з головного потоку (UI),
        # і з фонового потоку перевірки розкладу
        with self._file_lock:
            if os.path.exists(self.db_path):
                try:
                    with open(self.db_path, "r", encoding="utf-8") as f:
                        return json.load(f)
                except:
                    pass
            return []

    def write_json(self, data):
        with self._file_lock:
            with open(self.db_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4, ensure_ascii=False)

    def _normalize_day_key(self, value):
        """ Приводить будь-яке значення дня (новий канонічний ключ, або
        старий запис українською з попередніх версій лаунчера) до
        канонічного ключа mon..sun. Невідоме значення -> "mon". """
        if value in self.day_key_to_index:
            return value
        return _LEGACY_UK_TO_KEY.get(value, "mon")

    def is_current_day_in_range(self, start_day_name, end_day_name):
        """ Перевіряє, чи входить сьогоднішній день у налаштований діапазон """
        current_day_idx = datetime.now().weekday()  # Понеділок = 0, Неділя = 6

        start_idx = self.day_key_to_index.get(self._normalize_day_key(start_day_name), 0)
        end_idx = self.day_key_to_index.get(self._normalize_day_key(end_day_name), 4)

        if start_idx <= end_idx:
            # Звичайний діапазон (наприклад, з Пн(0) по Пт(4))
            return start_idx <= current_day_idx <= end_idx
        else:
            # Діапазон з переходом через неділю (наприклад, з Пт(4) по Вт(1))
            return current_day_idx >= start_idx or current_day_idx <= end_idx

    def start_checking_loop(self):
        """ Запускає фоновий потік перевірки розкладу.
        UI (customtkinter/Tkinter) залишається повністю відповідним,
        навіть якщо запуск пресету з великою затримкою між програмами
        триває довго — бо time.sleep() тепер виконується НЕ в головному потоці. """
        if self._worker_thread and self._worker_thread.is_alive():
            return  # Потік уже запущено — не дублюємо

        self._stop_event.clear()
        self._worker_thread = threading.Thread(target=self._background_worker, daemon=True)
        self._worker_thread.start()

    def stop_checking_loop(self):
        """ Коректна зупинка фонового потоку. Бажано викликати перед виходом
        з програми (наприклад, з exit_program() у ProgramLauncherStart.py),
        хоча потік і так daemon і не завадить процесу завершитись. """
        self._stop_event.set()

    def _background_worker(self):
        """ !!! ЦЯ ФУНКЦІЯ ВИКОНУЄТЬСЯ У ФОНОВОМУ ПОТОЦІ, А НЕ В ГОЛОВНОМУ !!!
        Тут можна безпечно робити time.sleep() на довільний час — інтерфейс
        від цього не "зависне", бо Tkinter mainloop працює окремо в головному потоці.
        Напряму чіпати CTk-віджети звідси НЕ МОЖНА — будь-яке оновлення UI
        повертаємо в головний потік через self.after(0, ...). """
        while not self._stop_event.is_set():
            try:
                self._check_and_run_tasks()
            except Exception as e:
                print(t("schedule.bg_worker_error", error=e))

            # Чекаємо 20 секунд між перевірками, але перериваємось миттєво,
            # якщо надійшла команда зупинки (stop_checking_loop)
            self._stop_event.wait(20)

    def _check_and_run_tasks(self):
        now = datetime.now()
        current_time_str = now.strftime("%H:%M")

        tasks = self.read_json()
        updated = False

        if current_time_str == "00:00":
            for task_item in tasks:
                if task_item.get("triggered_today", True):
                    task_item["triggered_today"] = False
                    updated = True

        settings_file = os.path.join(self.base_dir, "jsons_saves", "settings.json")
        delay = 0
        close_after = False
        smart_launch = False
        if os.path.exists(settings_file):
            try:
                with open(settings_file, "r", encoding="utf-8") as sf:
                    st = json.load(sf)
                    delay = st.get("delay", 0)
                    close_after = st.get("close_after_launch", False)
                    smart_launch = st.get("smart_launch", False)
            except:
                pass

        launched_something = False

        for task_item in tasks:
            if task_item["time"] == current_time_str and not task_item.get("triggered_today", False):

                # Чи підходить сьогоднішній день тижня під налаштування завдання?
                s_day = task_item.get("start_day", "mon")
                e_day = task_item.get("end_day", "fri")

                if not self.is_current_day_in_range(s_day, e_day):
                    continue  # Якщо сьогодні вихідний, а треба було в будні — просто пропускаємо

                # Запуск поодинокої програми
                if task_item.get("type", "single") == "single":
                    if os.path.exists(task_item.get("path", "")):
                        status = smart_startfile(task_item["path"], args=task_item.get("args", ""), skip_if_running=smart_launch)
                        if status in ("launched", "skipped_running"):
                            task_item["triggered_today"] = True
                            updated = True
                            launched_something = True

                # Запуск пресету
                elif task_item.get("type") == "preset":
                    presets_file = os.path.join(self.base_dir, "jsons_saves", "presets.json")
                    if os.path.exists(presets_file):
                        try:
                            with open(presets_file, "r", encoding="utf-8") as pf:
                                all_presets = json.load(pf)
                                target_preset = all_presets.get(task_item["name"])

                                if target_preset and "programs" in target_preset:
                                    did_fresh_launch = False
                                    for prog_item in target_preset["programs"]:
                                        p_path, p_args = resolve_program_entry(prog_item)
                                        if did_fresh_launch and delay > 0:
                                            # Безпечно: ми в фоновому потоці, GUI не завмирає
                                            time.sleep(delay)
                                        status = smart_startfile(p_path, args=p_args, skip_if_running=smart_launch)
                                        if status == "launched":
                                            did_fresh_launch = True

                                    task_item["triggered_today"] = True
                                    updated = True
                                    launched_something = True
                        except:
                            pass

        if updated:
            self.write_json(tasks)
            # Оновлення списку завдань у вкладці "Розклад" — обов'язково
            # через after(), щоб виконати цей код у головному (UI) потоці
            self.after(0, self.load_and_refresh_ui)

        if launched_something and close_after:
            # Так само: закриття програми теж повертаємо в головний потік
            self.after(0, self.exit_program_callback)