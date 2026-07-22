import customtkinter as ctk
from tkinter import Menu, messagebox
import os
import json
import time
import sys

# Використовуємо вбудовані можливості Windows для 100% стабільності
import ctypes
from ctypes import wintypes

# Бібліотеки для трею
import pystray
from pystray import MenuItem as item
from PIL import Image, ImageDraw

# Імпортуємо всі менеджери з окремих файлів
from preset_manager import PresetManager
from settings_manager import SettingsManager
from info_manager import InfoManager
from schedule_manager import ScheduleManager

# "Розумний запуск": не відкривати програму повторно, якщо вона вже працює
from process_utils import smart_startfile, resolve_program_entry

# --- НАЛАШТУВАННЯ CTYPES ДЛЯ DRAG & DROP НА WINDOWS ---
# Зберігаємо глобальне посилання на callback-функцію, щоб її не видалив GC (Garbage Collector)
_global_wndproc_ref = None


def setup_windows_dnd(window, callback):
    """ Реєструє вікно для прийому файлів через Win32 API """
    global _global_wndproc_ref
    window.update_idletasks()

    # Отримуємо правильний дескриптор вікна
    hwnd = ctypes.windll.user32.GetParent(window.winfo_id())
    if not hwnd:
        hwnd = window.winfo_id()

    # Дозволяємо перетягування файлів
    ctypes.windll.shell32.DragAcceptFiles(hwnd, True)

    shell32 = ctypes.windll.shell32
    user32 = ctypes.windll.user32

    # Сигнатура функції зворотного виклику (WNDPROC)
    WNDPROC = ctypes.WINFUNCTYPE(ctypes.c_void_p, wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM)

    user32.CallWindowProcW.argtypes = [ctypes.c_void_p, wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
    user32.CallWindowProcW.restype = ctypes.c_void_p

    shell32.DragQueryFileW.argtypes = [ctypes.c_void_p, wintypes.UINT, wintypes.LPWSTR, wintypes.UINT]
    shell32.DragQueryFileW.restype = wintypes.UINT

    shell32.DragFinish.argtypes = [ctypes.c_void_p]
    shell32.DragFinish.restype = None

    WM_DROPFILES = 0x0233
    GWLP_WNDPROC = -4

    # Правильний вибір функцій залежно від розрядності ОС
    if ctypes.sizeof(ctypes.c_void_p) == 8:
        GetWindowLong = user32.GetWindowLongPtrW
        SetWindowLong = user32.SetWindowLongPtrW
        GetWindowLong.restype = ctypes.c_void_p
        SetWindowLong.restype = ctypes.c_void_p
        GetWindowLong.argtypes = [wintypes.HWND, ctypes.c_int]
        SetWindowLong.argtypes = [wintypes.HWND, ctypes.c_int, ctypes.c_void_p]
    else:
        GetWindowLong = user32.GetWindowLongW
        SetWindowLong = user32.SetWindowLongW
        GetWindowLong.restype = ctypes.c_long
        SetWindowLong.restype = ctypes.c_long
        GetWindowLong.argtypes = [wintypes.HWND, ctypes.c_int]
        SetWindowLong.argtypes = [wintypes.HWND, ctypes.c_int, ctypes.c_long]

    orig_wndproc = GetWindowLong(hwnd, GWLP_WNDPROC)

    def new_wndproc(hwnd_win, msg, wparam, lparam):
        if msg == WM_DROPFILES:
            hdrop = ctypes.c_void_p(wparam)
            num_files = shell32.DragQueryFileW(hdrop, 0xFFFFFFFF, None, 0)
            files = []

            for i in range(num_files):
                length = shell32.DragQueryFileW(hdrop, i, None, 0)
                buf = ctypes.create_unicode_buffer(length + 1)
                shell32.DragQueryFileW(hdrop, i, buf, length + 1)
                files.append(buf.value)

            shell32.DragFinish(hdrop)
            # Використовуємо чергу головного вікна для безпечного оновлення Tkinter інтерфейсу
            window.after(10, lambda: callback(files))
            return 0

        return user32.CallWindowProcW(orig_wndproc, hwnd_win, msg, wparam, lparam)

    # Зберігаємо жорстке посилання, щоб уникнути Garbage Collection вильоту
    _global_wndproc_ref = WNDPROC(new_wndproc)
    SetWindowLong(hwnd, GWLP_WNDPROC, _global_wndproc_ref)


# --- ФУНКЦІЯ СТАРТОВОГО ПІДВАНТАЖЕННЯ ТЕМИ ---
def pre_apply_theme():
    if getattr(sys, "frozen", False):
        base_dir = os.path.dirname(sys.executable)
    else:
        base_dir = os.path.dirname(os.path.abspath(__file__))

    settings_dir = os.path.join(base_dir, "jsons_saves")
    themes_dir = os.path.join(base_dir, "themes")
    settings_file = os.path.join(settings_dir, "settings.json")

    os.makedirs(themes_dir, exist_ok=True)
    os.makedirs(settings_dir, exist_ok=True)

    if os.path.exists(settings_file):
        try:
            with open(settings_file, "r", encoding="utf-8") as f:
                st = json.load(f)

            ctk.set_appearance_mode(st.get("theme", "Dark"))
            color_theme = st.get("color_theme", "blue")

            if color_theme not in ["blue", "green", "dark-blue"]:
                theme_path = os.path.join(themes_dir, f"{color_theme}.json")
                if os.path.exists(theme_path):
                    ctk.set_default_color_theme(theme_path)
                    return

            ctk.set_default_color_theme(color_theme)
            return

        except Exception:
            pass

    ctk.set_appearance_mode("Dark")
    ctk.set_default_color_theme("blue")

pre_apply_theme()

app = ctk.CTk()
app.title("Program Launcher")
app.geometry("520x720")
app.minsize(480, 620)

programs = []
context_menu = Menu(app, tearoff=0)
tray_icon = None


def create_tray_image():
    image = Image.new('RGB', (64, 64), color=(0, 46, 93))
    dc = ImageDraw.Draw(image)
    dc.rectangle((16, 16, 48, 48), fill=(225, 225, 225))
    return image


def show_window():
    app.after(0, app.deiconify)


def withdraw_window():
    app.withdraw()


def exit_program():
    global tray_icon
    if tray_icon:
        tray_icon.stop()
    # Коректно зупиняємо фоновий потік перевірки розкладу перед виходом
    try:
        schedule_manager_frame.stop_checking_loop()
    except Exception:
        pass
    app.quit()
    sys.exit(0)


# --- ФУНКЦІЯ ПЕРЕЗАПУСКУ ПРОГРАМИ (ПРАЦЮЄ В .EXE) ---
def restart_program():
    global tray_icon
    if tray_icon:
        tray_icon.stop()
    app.quit()

    # Визначаємо, чи запущено як скрипт чи як скомпільований .exe
    if getattr(sys, 'frozen', False):
        # Якщо це білд (.exe)
        os.startfile(sys.executable)
    else:
        # Якщо це звичайний .py скрипт
        os.execl(sys.executable, sys.executable, *sys.argv)
    sys.exit(0)


def setup_tray():
    global tray_icon
    menu = pystray.Menu(
        item('📱 Відкрити лаунчер', show_window, default=True),
        item('❌ Повний вихід', exit_program)
    )
    tray_icon = pystray.Icon("launcher_tray", create_tray_image(), "Program Launcher", menu)
    tray_icon.run_detached()


app.withdraw_window = withdraw_window
app.exit_program = exit_program
app.protocol('WM_DELETE_WINDOW', withdraw_window)

setup_tray()


def toggle_interface(value):
    main_ui_frame.pack_forget()
    preset_manager_frame.pack_forget()
    schedule_manager_frame.pack_forget()
    settings_manager_frame.pack_forget()
    info_manager_frame.pack_forget()

    if value == "📱 Програми":
        main_ui_frame.pack(pady=5, padx=20, fill="both", expand=True)
    elif value == "⚙ Набори":
        preset_manager_frame.pack(pady=5, padx=20, fill="both", expand=True)
        preset_manager_frame.load_data_from_json(programs)
    elif value == "⏰ Розклад":
        schedule_manager_frame.pack(pady=5, padx=20, fill="both", expand=True)
        schedule_manager_frame.update_data_lists(programs)
    elif value == "🛠 Налаштування":
        settings_manager_frame.pack(pady=5, padx=20, fill="both", expand=True)
    elif value == "ℹ Довідка":
        info_manager_frame.pack(pady=5, padx=20, fill="both", expand=True)


mode_toggle = ctk.CTkSegmentedButton(
    app,
    values=["📱 Програми", "⚙ Набори", "⏰ Розклад", "🛠 Налаштування", "ℹ Довідка"],
    command=toggle_interface
)
mode_toggle.pack(pady=15, padx=15, fill="x")
mode_toggle.set("📱 Програми")

main_ui_frame = ctk.CTkFrame(app, fg_color="transparent")
main_ui_frame.pack(pady=5, padx=20, fill="both", expand=True)

# --- ФІЛЬТР ЗА КАТЕГОРІЯМИ ---
# Дозволяє групувати програми у категорії (теги) на кшталт "Робота",
# "Ігри", "Дизайн", і фільтрувати список кліком по випадаючому списку —
# щоб довгий список (50+ програм) не перетворювався на нескінченний скрол.
CATEGORY_ALL = "Всі"
CATEGORY_UNSET = "Без категорії"

category_filter_frame = ctk.CTkFrame(main_ui_frame, fg_color="transparent")
category_filter_frame.pack(pady=(0, 8), fill="x")

ctk.CTkLabel(category_filter_frame, text="🏷 Категорія:").pack(side="left", padx=(0, 8))

category_filter_dropdown = ctk.CTkOptionMenu(
    category_filter_frame,
    values=[CATEGORY_ALL],
    command=lambda choice: refresh_programs()
)
category_filter_dropdown.pack(side="left", fill="x", expand=True)
category_filter_dropdown.set(CATEGORY_ALL)

# Кнопка керування категоріями (перегляд та видалення) поруч із фільтром
manage_categories_btn = ctk.CTkButton(
    category_filter_frame, text="🗑", width=32,
    fg_color="transparent", border_width=1,
    command=lambda: manage_categories_dialog()
)
manage_categories_btn.pack(side="left", padx=(8, 0))

program_frame = ctk.CTkScrollableFrame(main_ui_frame)
program_frame.pack(pady=5, fill="both", expand=True)


def on_files_dropped_native(files_list):
    for path in files_list:
        if not os.path.exists(path):
            continue
        name = os.path.basename(path)
        for ext in [".exe", ".lnk", ".bat", ".cmd"]:
            if name.lower().endswith(ext):
                name = name[:-len(ext)]
        if any(p["path"] == path for p in programs):
            continue
        programs.append({"name": name, "path": path, "checkbox": None, "args": "", "category": ""})
    save_programs()
    refresh_programs()


# Ініціалізуємо Drag & Drop
setup_windows_dnd(app, on_files_dropped_native)


def save_programs():
    if getattr(sys, "frozen", False):
        base_dir = os.path.dirname(sys.executable)
    else:
        base_dir = os.path.dirname(os.path.abspath(__file__))

    settings_dir = os.path.join(base_dir, "jsons_saves")
    os.makedirs(settings_dir, exist_ok=True)

    programs_file = os.path.join(settings_dir, "checkbox_programs.json")

    data = [
        {"name": p["name"], "path": p["path"], "args": p.get("args", ""), "category": p.get("category", "")}
        for p in programs
    ]

    with open(programs_file, "w", encoding="utf-8") as file:
        json.dump(data, file, indent=4, ensure_ascii=False)


def get_program_category(program):
    """ Нормалізує категорію програми: порожнє значення -> CATEGORY_UNSET. """
    cat = (program.get("category") or "").strip()
    return cat if cat else CATEGORY_UNSET


def get_all_categories():
    """ Список усіх категорій, що реально використовуються серед програм. """
    return sorted({get_program_category(p) for p in programs})


def update_category_filter_values():
    """ Оновлює список значень фільтра відповідно до поточних категорій.
    Якщо категорія, яку обрав користувач, зникла (наприклад, видалили
    останню програму з неї) — скидає фільтр на "Всі". """
    values = [CATEGORY_ALL] + get_all_categories()
    current = category_filter_dropdown.get()
    category_filter_dropdown.configure(values=values)
    if current not in values:
        category_filter_dropdown.set(CATEGORY_ALL)


def refresh_programs():
    update_category_filter_values()
    selected_category = category_filter_dropdown.get()

    for widget in program_frame.winfo_children():
        widget.destroy()

    # Скидаємо посилання на чекбокси для ВСІХ програм: попередні віджети щойно
    # знищені вище, і якщо програма зараз прихована фільтром, її "checkbox"
    # не повинен вказувати на видалений об'єкт (інакше launch/delete впадуть).
    for p in programs:
        p["checkbox"] = None

    if not programs:
        placeholder = ctk.CTkLabel(
            program_frame,
            text="✨ Список порожній...\n\nПеретягніть сюди ярлики файлів мишкою\nабо скористайтеся кнопкою 'Додати'",
            text_color="gray", justify="center"
        )
        placeholder.pack(pady=40, fill="x")
        return

    if selected_category == CATEGORY_ALL:
        visible_programs = programs
    else:
        visible_programs = [p for p in programs if get_program_category(p) == selected_category]

    if not visible_programs:
        placeholder = ctk.CTkLabel(
            program_frame,
            text=f"У категорії «{selected_category}» ще немає програм.",
            text_color="gray", justify="center"
        )
        placeholder.pack(pady=40, fill="x")
        return

    for program in visible_programs:
        display_name = program["name"]
        cat = (program.get("category") or "").strip()
        if cat:
            display_name = f"[{cat}] {display_name}"
        if program.get("args"):
            display_name += "  ⚙"  # Позначка, що для програми задані аргументи запуску
        checkbox = ctk.CTkCheckBox(program_frame, text=display_name)
        checkbox.pack(anchor="w", pady=5, padx=10, fill="x")
        program["checkbox"] = checkbox
        checkbox.bind("<Button-3>", lambda event, p=program: show_context_menu(event, p))


def show_context_menu(event, program):
    context_menu.delete(0, "end")
    context_menu.add_command(label=f"Перейменувати '{program['name']}'", command=lambda: rename_program(program))
    context_menu.add_command(label="⚙ Параметри запуску...", command=lambda: edit_program_args(program))
    context_menu.add_command(label="🏷 Категорія...", command=lambda: edit_program_category(program))
    context_menu.add_separator()
    context_menu.add_command(label="Видалити зі списку", command=lambda: delete_single_program(program))
    context_menu.tk_popup(event.x_root, event.y_root)


def rename_program(program):
    dialog = ctk.CTkInputDialog(text=f"Введіть нову назву для {program['name']}:", title="Перейменування")
    new_name = dialog.get_input()
    if new_name and new_name.strip():
        program["name"] = new_name.strip()
        save_programs()
        refresh_programs()


def edit_program_args(program):
    """ Дозволяє задати рядок аргументів командного рядка для програми,
    наприклад "-windowed" для гри або URL для браузера. Порожній рядок
    прибирає аргументи — програма запускатиметься звичайно. """
    current_args = program.get("args", "")
    hint = f"Аргументи запуску для '{program['name']}':\n"
    if current_args:
        hint += f"Поточне значення: {current_args}\n"
    hint += "Залиште порожнім, щоб прибрати аргументи (напр. -windowed, або URL для браузера)."

    dialog = ctk.CTkInputDialog(text=hint, title="Параметри запуску")
    new_args = dialog.get_input()
    if new_args is not None:
        program["args"] = new_args.strip()
        save_programs()
        refresh_programs()


def ask_category_dialog(parent_window, program_name, current_value, existing_categories):
    """ Спливаюче вікно вибору категорії: існуючі категорії показані як
    кнопки-теги (клік підставляє назву в поле), а поле вводу дозволяє
    ввести будь-яку нову назву — вона просто створиться при збереженні,
    окремого "створення категорії" не потрібно.
    Повертає введений/обраний рядок, або None якщо натиснули "Скасувати". """
    result = {"value": None, "confirmed": False}

    dialog = ctk.CTkToplevel(parent_window)
    dialog.title("Категорія програми")
    dialog.geometry("380x340")
    dialog.minsize(320, 260)
    dialog.transient(parent_window)

    # Центруємо діалог відносно головного вікна
    parent_window.update_idletasks()
    px = parent_window.winfo_rootx() + (parent_window.winfo_width() // 2) - 190
    py = parent_window.winfo_rooty() + (parent_window.winfo_height() // 2) - 170
    dialog.geometry(f"+{max(px, 0)}+{max(py, 0)}")

    ctk.CTkLabel(
        dialog,
        text=f"Категорія для «{program_name}»:",
        wraplength=340, justify="left", anchor="w"
    ).pack(pady=(15, 8), padx=15, anchor="w")

    entry = ctk.CTkEntry(dialog, placeholder_text="Назва категорії (нова або вже наявна)")
    entry.pack(pady=(0, 4), padx=15, fill="x")
    if current_value:
        entry.insert(0, current_value)

    ctk.CTkLabel(
        dialog,
        text="Порожнє поле прибере категорію.",
        font=(None, 11), text_color="gray", anchor="w"
    ).pack(pady=(0, 10), padx=15, anchor="w")

    if existing_categories:
        ctk.CTkLabel(
            dialog, text="Або оберіть зі списку створених:",
            font=(None, 11, "bold"), anchor="w"
        ).pack(padx=15, anchor="w")

        list_frame = ctk.CTkScrollableFrame(dialog, height=110)
        list_frame.pack(pady=(4, 10), padx=15, fill="both", expand=True)

        def pick(cat):
            entry.delete(0, "end")
            entry.insert(0, cat)
            entry.focus_set()

        for cat in existing_categories:
            is_current = (cat == current_value)
            ctk.CTkButton(
                list_frame, text=("✓ " if is_current else "") + cat,
                fg_color=("gray75", "gray28") if is_current else "transparent",
                border_width=1, anchor="w",
                command=lambda c=cat: pick(c)
            ).pack(pady=2, fill="x")
    else:
        ctk.CTkLabel(
            dialog, text="Категорій ще немає — просто введіть нову назву вище,\nвона створиться автоматично.",
            font=(None, 11), text_color="gray", justify="left", anchor="w"
        ).pack(pady=(4, 10), padx=15, anchor="w", fill="x")

    btns_frame = ctk.CTkFrame(dialog, fg_color="transparent")
    btns_frame.pack(pady=(5, 15), padx=15, fill="x", side="bottom")

    def confirm():
        result["value"] = entry.get().strip()
        result["confirmed"] = True
        dialog.destroy()

    def cancel():
        dialog.destroy()

    ctk.CTkButton(btns_frame, text="💾 Зберегти", command=confirm).pack(
        side="left", expand=True, fill="x", padx=(0, 5)
    )
    ctk.CTkButton(btns_frame, text="Скасувати", fg_color="transparent", border_width=1, command=cancel).pack(
        side="left", expand=True, fill="x", padx=(5, 0)
    )

    entry.bind("<Return>", lambda e: confirm())
    dialog.protocol("WM_DELETE_WINDOW", cancel)

    entry.focus_set()
    dialog.grab_set()
    parent_window.wait_window(dialog)

    return result["value"] if result["confirmed"] else None


def delete_category(cat_name):
    """ Видаляє категорію: знімає її з усіх програм, яким вона присвоєна
    (такі програми повертаються у "Без категорії"). Сама категорія ніде
    окремо не зберігається — вона й так існує лише як рядок у полі
    "category" тих програм, які нею позначені, тож "видалення" зводиться
    до очищення цього поля. Самі програми при цьому нікуди не зникають. """
    changed = False
    for p in programs:
        if get_program_category(p) == cat_name:
            p["category"] = ""
            changed = True
    if changed:
        save_programs()
        refresh_programs()


def manage_categories_dialog():
    """ Спливаюче вікно зі списком усіх наявних категорій та кнопкою
    видалення навпроти кожної. """
    existing = [c for c in get_all_categories() if c != CATEGORY_UNSET]

    dialog = ctk.CTkToplevel(app)
    dialog.title("Керування категоріями")
    dialog.geometry("360x380")
    dialog.minsize(300, 260)
    dialog.transient(app)

    app.update_idletasks()
    px = app.winfo_rootx() + (app.winfo_width() // 2) - 180
    py = app.winfo_rooty() + (app.winfo_height() // 2) - 190
    dialog.geometry(f"+{max(px, 0)}+{max(py, 0)}")

    ctk.CTkLabel(
        dialog, text="🏷 Керування категоріями", font=(None, 14, "bold")
    ).pack(pady=(15, 5), padx=15, anchor="w")

    ctk.CTkLabel(
        dialog,
        text="Видалення категорії не стирає самі програми — вони\n"
             "просто повертаються у стан «Без категорії».",
        font=(None, 11), text_color="gray", justify="left", anchor="w"
    ).pack(pady=(0, 10), padx=15, anchor="w")

    list_frame = ctk.CTkScrollableFrame(dialog)
    list_frame.pack(pady=(0, 10), padx=15, fill="both", expand=True)

    def do_delete(cat_name):
        if messagebox.askyesno(
            "Видалення категорії",
            f"Видалити категорію «{cat_name}»?\n\n"
            f"Програми, що мали цю категорію, стануть «Без категорії»."
        ):
            delete_category(cat_name)
            dialog.destroy()
            manage_categories_dialog()  # перевідкриваємо вікно з оновленим списком

    if existing:
        for cat in existing:
            row = ctk.CTkFrame(list_frame, fg_color="transparent")
            row.pack(pady=3, fill="x")
            ctk.CTkLabel(row, text=cat, anchor="w").pack(side="left", fill="x", expand=True, padx=(2, 5))
            ctk.CTkButton(
                row, text="🗑 Видалити", width=100,
                fg_color="transparent", border_width=1,
                command=lambda c=cat: do_delete(c)
            ).pack(side="right")
    else:
        ctk.CTkLabel(
            list_frame, text="Категорій ще немає.\nСтворити категорію можна через\nправий клік по програмі -> \"🏷 Категорія...\"",
            text_color="gray", justify="center"
        ).pack(pady=20, padx=5)

    ctk.CTkButton(dialog, text="Закрити", command=dialog.destroy).pack(pady=(0, 15), padx=15, fill="x")

    dialog.grab_set()


def edit_program_category(program):
    """ Дозволяє задати категорію (тег) для програми — напр. "Робота",
    "Ігри", "Дизайн" — щоб потім фільтрувати список за допомогою
    випадаючого списку над списком програм. Порожнє значення прибирає
    категорію (програма повертається до "Без категорії"). """
    existing = [c for c in get_all_categories() if c != CATEGORY_UNSET]
    new_cat = ask_category_dialog(app, program["name"], program.get("category", ""), existing)

    if new_cat is not None:
        program["category"] = new_cat.strip()
        save_programs()
        refresh_programs()


def delete_single_program(program_to_delete):
    global programs
    programs = [p for p in programs if p != program_to_delete]
    save_programs()
    refresh_programs()


def load_programs():
    global programs

    if getattr(sys, "frozen", False):
        base_dir = os.path.dirname(sys.executable)
    else:
        base_dir = os.path.dirname(os.path.abspath(__file__))

    settings_dir = os.path.join(base_dir, "jsons_saves")
    programs_file = os.path.join(settings_dir, "checkbox_programs.json")

    try:
        with open(programs_file, "r", encoding="utf-8") as file:
            raw_data = json.load(file)
            programs = [
                {
                    "name": item["name"],
                    "path": item["path"],
                    "checkbox": None,
                    "args": item.get("args", ""),
                    "category": item.get("category", "")
                }
                for item in raw_data
            ]
    except:
        programs = []

    refresh_programs()


def check_and_run_autostart():
    if getattr(sys, "frozen", False):
        base_dir = os.path.dirname(sys.executable)
    else:
        base_dir = os.path.dirname(os.path.abspath(__file__))

    settings_dir = os.path.join(base_dir, "jsons_saves")
    presets_file = os.path.join(settings_dir, "presets.json")
    settings_file = os.path.join(settings_dir, "settings.json")

    if os.path.exists(presets_file) and os.path.getsize(presets_file) > 0:
        try:
            delay = 0
            close_after = False
            smart_launch = False

            if os.path.exists(settings_file):
                with open(settings_file, "r", encoding="utf-8") as sf:
                    st = json.load(sf)
                    delay = st.get("delay", 0)
                    close_after = st.get("close_after_launch", False)
                    smart_launch = st.get("smart_launch", False)

            with open(presets_file, "r", encoding="utf-8") as file:
                presets = json.load(file)

            for name, data in presets.items():
                if isinstance(data, dict) and data.get("autostart", False):
                    did_fresh_launch = False
                    for prog_item in data.get("programs", []):
                        path, prog_args = resolve_program_entry(prog_item)
                        if did_fresh_launch and delay > 0:
                            time.sleep(delay)

                        status = smart_startfile(path, args=prog_args, skip_if_running=smart_launch)
                        if status == "launched":
                            did_fresh_launch = True
                        elif status == "failed":
                            print(f"Не вдалося запустити {path}")

                    if close_after:
                        exit_program()

                    break

        except Exception as e:
            print(f"Помилка зчитування автозапуску: {e}")


def add_program():
    from tkinter import filedialog
    path = filedialog.askopenfilename(filetypes=[("Executable or Shortcut", "*.exe;*.lnk"), ("All files", "*.*")])
    if not path: return
    name = os.path.basename(path)
    for ext in [".exe", ".lnk"]:
        if name.endswith(ext): name = name.replace(ext, "")
    programs.append({"name": name, "path": path, "checkbox": None, "args": "", "category": ""})
    save_programs()
    refresh_programs()


def launch_selected():
    if getattr(sys, "frozen", False):
        base_dir = os.path.dirname(sys.executable)
    else:
        base_dir = os.path.dirname(os.path.abspath(__file__))

    settings_file = os.path.join(base_dir, "jsons_saves", "settings.json")

    delay = 0
    close_after = False
    smart_launch = False

    if os.path.exists(settings_file):
        try:
            with open(settings_file, "r", encoding="utf-8") as f:
                st = json.load(f)
                delay = st.get("delay", 0)
                close_after = st.get("close_after_launch", False)
                smart_launch = st.get("smart_launch", False)
        except:
            pass

    launched_any = False   # чи хоч одна програма зараз реально відкрита (запущена або вже працювала)
    did_fresh_launch = False  # чи був хоч один РЕАЛЬНИЙ новий запуск (для витримки затримки)

    for program in programs:
        if program["checkbox"] and program["checkbox"].get() == 1:
            if did_fresh_launch and delay > 0:
                time.sleep(delay)

            status = smart_startfile(program["path"], args=program.get("args", ""), skip_if_running=smart_launch)
            if status == "launched":
                did_fresh_launch = True
                launched_any = True
            elif status == "skipped_running":
                # Програма вже відкрита — мета користувача досягнута,
                # але затримку перед наступною програмою чекати не треба
                launched_any = True

    if launched_any and close_after:
        exit_program()


def delete_selected():
    global programs
    # Програми, приховані поточним фільтром категорій, мають checkbox=None —
    # їх не можна прибирати, інакше "Видалити" стирала б і невидимі елементи.
    # Видаляємо лише ті, чий (видимий) чекбокс реально відмічений.
    programs = [p for p in programs if not (p["checkbox"] and p["checkbox"].get() == 1)]
    save_programs()
    refresh_programs()


# Ініціалізація менеджерів (Передаємо посилання на перезапуск у SettingsManager)
preset_manager_frame = PresetManager(app)
schedule_manager_frame = ScheduleManager(app, exit_program)
settings_manager_frame = SettingsManager(app, restart_callback=restart_program)  # <--- ПЕРЕДАЛИ ФУНКЦІЮ
info_manager_frame = InfoManager(app)

button_frame = ctk.CTkFrame(main_ui_frame, fg_color="transparent")
button_frame.pack(pady=10, fill="x")

ctk.CTkButton(button_frame, text="Додати", command=add_program).pack(side="left", padx=5, expand=True, fill="x")
ctk.CTkButton(button_frame, text="Запустити", command=launch_selected).pack(side="left", padx=5, expand=True, fill="x")
ctk.CTkButton(button_frame, text="Видалити", command=delete_selected).pack(side="left", padx=5, expand=True, fill="x")

exit_button_frame = ctk.CTkFrame(app, fg_color="transparent")
exit_button_frame.pack(side="bottom", fill="x", padx=20, pady=15)

global_exit_btn = ctk.CTkButton(
    exit_button_frame,
    text="❌ Повний вихід з програми",
    fg_color="transparent",
    border_width=1,
    command=exit_program
)
global_exit_btn.pack(fill="x", ipady=3)

load_programs()
check_and_run_autostart()
app.mainloop()