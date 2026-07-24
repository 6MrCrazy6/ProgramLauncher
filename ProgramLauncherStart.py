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
from info_manager import InfoManager, create_corner_menu_button
from schedule_manager import ScheduleManager

# "Розумний запуск": не відкривати програму повторно, якщо вона вже працює
from process_utils import smart_startfile, resolve_program_entry
import stats_manager

# Глобальні гарячі клавіші (показ вікна лаунчера, запуск наборів) —
# опціональний функціонал на базі бібліотеки 'keyboard'
import hotkey_manager

# Локалізація інтерфейсу (українська/англійська). Мова визначається
# одразу при імпорті модуля (читає settings.json) — тому t(...) вже
# повертає правильну мову навіть для тексту, створеного до появи
# SettingsManager (заголовок вікна, іконка трею тощо).
from locale_manager import t

# --- ЗАХИСТ ВІД ПОДВІЙНОГО ЗАПУСКУ ---
# Якщо клацнути по .exe/ярлику двічі поспіль (або запустити ще раз,
# поки перша копія вже працює чи ще завантажується) — друга копія
# одразу завершується з нативним повідомленням Windows, замість того
# щоб відкривати другий повноцінний лаунчер.
#
# Іменований мьютекс Windows — найнадійніший спосіб перевірити це:
# перша копія процесу створює мьютекс з унікальною назвою; будь-яка
# наступна спроба створити мьютекс з тією ж назвою одразу повертає
# helper-код ERROR_ALREADY_EXISTS (183), навіть якщо перша копія ще
# не встигла показати вікно (на відміну від перевірки "чи є вікно з
# такою назвою", яка спрацює лише ПІСЛЯ появи вікна).
#
# Перевірка стоїть одразу після імпортів і ДО створення CTk-вікна —
# тому друга копія закривається миттєво, не витрачаючи час на
# ініціалізацію customtkinter (теми, шрифти, всі вкладки).
_SINGLE_INSTANCE_MUTEX_NAME = "ProgramLauncher_SingleInstance_38f2b6c1"
_ERROR_ALREADY_EXISTS = 183

_single_instance_mutex = ctypes.windll.kernel32.CreateMutexW(None, False, _SINGLE_INSTANCE_MUTEX_NAME)
if ctypes.windll.kernel32.GetLastError() == _ERROR_ALREADY_EXISTS:
    ctypes.windll.user32.MessageBoxW(
        None,
        t("main.already_running_text"),
        t("main.already_running_title"),
        0x40,  # MB_ICONINFORMATION
    )
    sys.exit(0)

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

def resource_path(relative_path):
    """ Повертає коректний шлях до "вшитого" ресурсу (іконки тощо) —
    працює однаково і при запуску .py напряму, і в зібраному .exe
    (PyInstaller розпаковує --add-data файли в sys._MEIPASS). """
    base_path = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base_path, relative_path)


app = ctk.CTk()
app.title("Program Launcher")
app.geometry("560x720")
app.minsize(520, 620)
# Явно дозволяємо вільно змінювати розмір вікна в обидва боки — весь
# інтерфейс (top_row, mode_toggle, program_frame тощо) зібраний через
# pack(fill=..., expand=True), тож коректно розтягується/стискається
# при будь-якому розмірі вікна чи екрана.
app.resizable(True, True)

try:
    app.iconbitmap(resource_path(os.path.join("assets", "launcher.ico")))
except Exception:
    # Немає файлу іконки, або .ico некоректний — тихо лишаємо іконку
    # за замовчуванням, це не критично для роботи програми
    pass

programs = []
context_menu = Menu(app, tearoff=0)
tray_icon = None


def create_tray_image():
    """ Іконка для системного трею. Завантажує той самий launcher.ico,
    що й іконка вікна/exe — трей вимагає растрове зображення (PIL.Image),
    тож .ico конвертується через Image.open (Pillow вміє читати .ico
    напряму, включно з багаторозмірними файлами — сам обере найбільший
    кадр). Якщо файл не знайдено чи він пошкоджений — тихо повертаємось
    до простого намальованого квадрата, щоб трей не зламався. """
    try:
        return Image.open(resource_path(os.path.join("assets", "launcher.ico")))
    except Exception:
        image = Image.new('RGB', (64, 64), color=(0, 46, 93))
        dc = ImageDraw.Draw(image)
        dc.rectangle((16, 16, 48, 48), fill=(225, 225, 225))
        return image


def show_window():
    app.after(0, app.deiconify)


def withdraw_window():
    app.withdraw()


# Централізований менеджер глобальних гарячих клавіш (показ вікна +
# запуск конкретних наборів). Створюється один раз при старті і
# перереєстровується щоразу, коли користувач змінює якусь комбінацію.
hotkey_mgr = hotkey_manager.HotkeyManager()


def rebuild_global_hotkeys():
    """ Перечитує гарячу клавішу показу вікна з settings.json та гарячі
    клавіші наборів з preset_manager_frame і перереєстровує глобальні
    хуки клавіатури. Викликається один раз при старті лаунчера, а також
    щоразу, коли користувач змінює будь-яку з комбінацій (у вкладках
    'Налаштування' чи 'Набори').

    Callback'и, що надходять від бібліотеки 'keyboard', виконуються у
    фоновому потоці системного хука — тому виклики, що торкаються
    інтерфейсу Tkinter (показ вікна, запуск набору), обов'язково
    передаються в головний потік через app.after(0, ...), інакше
    можливе зависання чи збій CTk. """
    if getattr(sys, "frozen", False):
        base_dir = os.path.dirname(sys.executable)
    else:
        base_dir = os.path.dirname(os.path.abspath(__file__))

    settings_file = os.path.join(base_dir, "jsons_saves", "settings.json")

    show_hotkey = "ctrl+alt+l"
    if os.path.exists(settings_file):
        try:
            with open(settings_file, "r", encoding="utf-8") as f:
                show_hotkey = json.load(f).get("show_hotkey", "ctrl+alt+l")
        except Exception:
            pass

    preset_hotkeys = preset_manager_frame.get_preset_hotkeys()

    hotkey_mgr.rebuild(
        show_hotkey=show_hotkey,
        show_callback=lambda: app.after(0, show_window),
        preset_hotkeys=preset_hotkeys,
        launch_preset_callback=lambda name: app.after(
            0, lambda n=name: preset_manager_frame.launch_preset_by_name(n)
        )
    )


def exit_program():
    global tray_icon
    if tray_icon:
        tray_icon.stop()
    # Знімаємо всі гарячі клавіші, щоб не лишати "висячий" системний хук
    hotkey_mgr.stop()
    # Коректно зупиняємо фоновий потік перевірки розкладу перед виходом
    try:
        schedule_manager_frame.stop_checking_loop()
    except Exception:
        pass
    app.quit()
    sys.exit(0)


# --- ФУНКЦІЯ ПЕРЕЗАПУСКУ ПРОГРАМИ (ПРАЦЮЄ В .EXE) ---
def restart_program():
    """ Порядок дій тут навмисно інший, ніж у exit_program(): спочатку
    ховаємо вікно і одразу стартуємо НОВИЙ процес, і лише ПІСЛЯ цього
    прибираємо за старим (трей, хоткеї, потік розкладу). Якщо зробити
    навпаки (спершу дочекатись зупинки трея/хоткеїв і лише тоді
    запускати новий .exe) — новий процес довго й повільно ініціалізує
    свій CTk-інтерфейс (теми, локаль, віджети) ПІСЛЯ того, як стара
    копія вже витратила час на власне прибирання, тобто дві повільні
    речі йдуть одна за одною замість паралельно. Тут вони йдуть
    одночасно, і вікно ховається миттєво — тому перезапуск відчувається
    швидшим, хоча сумарний обсяг роботи не змінився. """
    global tray_icon

    # Миттєва візуальна реакція на "Так" в діалозі підтвердження —
    # користувач одразу бачить, що щось відбувається, а не бачить
    # старе вікно, що "зависло" на секунду-дві.
    try:
        app.withdraw()
    except Exception:
        pass

    # Явно звільняємо мьютекс однократного запуску ПЕРЕД стартом нової
    # копії — інакше нова копія побачить, що мьютекс ще "зайнятий"
    # старою копією (яка в цей момент ще завершує прибирання нижче),
    # і помилково вирішить, що лаунчер вже запущено.
    try:
        ctypes.windll.kernel32.CloseHandle(_single_instance_mutex)
    except Exception:
        pass

    if getattr(sys, 'frozen', False):
        # Білд (.exe): запускаємо нову копію одразу, паралельно з
        # прибиранням старої нижче.
        os.startfile(sys.executable)
    else:
        # Звичайний .py-скрипт: execl підміняє поточний процес одразу
        # на місці (код нижче для цієї гілки вже не виконається — це
        # нормально, ОС сама звільнить хендли/треди разом зі старим
        # образом процесу).
        os.execl(sys.executable, sys.executable, *sys.argv)

    # Прибирання старої копії — вже не впливає на швидкість появи
    # нового вікна користувачу, тож порядок і час виконання тут не
    # критичні.
    try:
        schedule_manager_frame.stop_checking_loop()
    except Exception:
        pass
    if tray_icon:
        tray_icon.stop()
    hotkey_mgr.stop()
    app.quit()
    sys.exit(0)


def setup_tray():
    global tray_icon
    menu = pystray.Menu(
        item(t("main.tray_open"), show_window, default=True),
        item(t("main.tray_exit"), exit_program)
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

    if value == t("main.tab_programs"):
        main_ui_frame.pack(pady=5, padx=20, fill="both", expand=True)
        # Лічильники запусків (▶ N) могли змінитися, поки користувач був
        # на вкладці "Набори" чи "Розклад" (звідти теж можна запускати
        # програми) — оновлюємо підписи, щоб цифри не були застарілими
        refresh_programs()
    elif value == t("main.tab_presets"):
        preset_manager_frame.pack(pady=5, padx=20, fill="both", expand=True)
        preset_manager_frame.load_data_from_json(programs)
    elif value == t("main.tab_schedule"):
        schedule_manager_frame.pack(pady=5, padx=20, fill="both", expand=True)
        schedule_manager_frame.update_data_lists(programs)
    elif value == t("main.tab_settings"):
        settings_manager_frame.pack(pady=5, padx=20, fill="both", expand=True)
    elif value == t("main.tab_info"):
        info_manager_frame.pack(pady=5, padx=20, fill="both", expand=True)


# Один рядок: зліва кнопка "⋮" (інфо-меню — наразі лише "Про програму"
# з даними з version_info.txt), праворуч від неї — перемикач вкладок,
# що займає весь залишок ширини. Обидва в одному рядку "pady=15" —
# нічого нижче через це не зсувається, і кнопка завжди лишається точно
# зліва від "Програми" незалежно від ширини вікна.
top_row = ctk.CTkFrame(app, fg_color="transparent")
top_row.pack(pady=15, padx=(10, 15), fill="x")

create_corner_menu_button(top_row, root=app)

mode_toggle = ctk.CTkSegmentedButton(
    top_row,
    values=[t("main.tab_programs"), t("main.tab_presets"), t("main.tab_schedule"),
            t("main.tab_settings"), t("main.tab_info")],
    command=toggle_interface
)
mode_toggle.pack(side="left", fill="x", expand=True)
mode_toggle.set(t("main.tab_programs"))

main_ui_frame = ctk.CTkFrame(app, fg_color="transparent")
main_ui_frame.pack(pady=5, padx=20, fill="both", expand=True)

# --- ФІЛЬТР ЗА КАТЕГОРІЯМИ ---
# Дозволяє групувати програми у категорії (теги) на кшталт "Робота",
# "Ігри", "Дизайн", і фільтрувати список кліком по випадаючому списку —
# щоб довгий список (50+ програм) не перетворювався на нескінченний скрол.
CATEGORY_ALL = t("main.category_all")
CATEGORY_UNSET = t("main.category_unset")

category_filter_frame = ctk.CTkFrame(main_ui_frame, fg_color="transparent")
category_filter_frame.pack(pady=(0, 8), fill="x")

ctk.CTkLabel(category_filter_frame, text=t("main.category_label")).pack(side="left", padx=(0, 8))

category_filter_dropdown = ctk.CTkOptionMenu(
    category_filter_frame,
    values=[CATEGORY_ALL],
    command=lambda choice: refresh_programs()
)
category_filter_dropdown.pack(side="left", fill="x", expand=True)
category_filter_dropdown.set(CATEGORY_ALL)

# Кнопка керування категоріями (перегляд та видалення) поруч із фільтром
manage_categories_btn = ctk.CTkButton(
    category_filter_frame, text=t("main.manage_categories_btn"), width=32,
    fg_color="transparent", border_width=1,
    text_color=("#001F3F", "#E5E9F0"),
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


def build_program_display_name(program):
    """ Формує текст підпису чекбокса програми: назва (+ категорія,
    позначка ⚙ за наявності аргументів запуску, і лічильник ▶ N —
    скільки разів програму реально було запущено через лаунчер). """
    display_name = program["name"]
    cat = (program.get("category") or "").strip()
    if cat:
        display_name = f"[{cat}] {display_name}"
    if program.get("args"):
        display_name += "  ⚙"  # Позначка, що для програми задані аргументи запуску
    launch_count = stats_manager.get_count(program["path"])
    display_name += f"   ▶ {launch_count}"
    return display_name


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
            text=t("main.empty_list"),
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
            text=t("main.empty_category", category=selected_category),
            text_color="gray", justify="center"
        )
        placeholder.pack(pady=40, fill="x")
        return

    for program in visible_programs:
        display_name = build_program_display_name(program)
        checkbox = ctk.CTkCheckBox(program_frame, text=display_name)
        checkbox.pack(anchor="w", pady=5, padx=10, fill="x")
        program["checkbox"] = checkbox
        checkbox.bind("<Button-3>", lambda event, p=program: show_context_menu(event, p))


def show_context_menu(event, program):
    context_menu.delete(0, "end")
    context_menu.add_command(label=t("main.ctx_rename", name=program['name']), command=lambda: rename_program(program))
    context_menu.add_command(label=t("main.ctx_args"), command=lambda: edit_program_args(program))
    context_menu.add_command(label=t("main.ctx_category"), command=lambda: edit_program_category(program))
    context_menu.add_command(label=t("main.ctx_reset_stats"), command=lambda: reset_program_stats(program))
    context_menu.add_separator()
    context_menu.add_command(label=t("main.ctx_delete"), command=lambda: delete_single_program(program))
    context_menu.tk_popup(event.x_root, event.y_root)


def reset_program_stats(program):
    """ Скидає лічильник запусків (▶ N) для конкретної програми на 0. """
    stats_manager.reset(program["path"])
    if program["checkbox"]:
        program["checkbox"].configure(text=build_program_display_name(program))


def rename_program(program):
    dialog = ctk.CTkInputDialog(text=t("main.rename_prompt", name=program['name']), title=t("main.rename_title"))
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
    hint = t("main.args_prompt_header", name=program['name'])
    if current_args:
        hint += t("main.args_prompt_current", args=current_args)
    hint += t("main.args_prompt_hint")

    dialog = ctk.CTkInputDialog(text=hint, title=t("main.args_title"))
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
    dialog.title(t("main.category_dialog_title"))
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
        text=t("main.category_dialog_label", name=program_name),
        wraplength=340, justify="left", anchor="w"
    ).pack(pady=(15, 8), padx=15, anchor="w")

    entry = ctk.CTkEntry(dialog, placeholder_text=t("main.category_dialog_placeholder"))
    entry.pack(pady=(0, 4), padx=15, fill="x")
    if current_value:
        entry.insert(0, current_value)

    ctk.CTkLabel(
        dialog,
        text=t("main.category_dialog_clear_hint"),
        font=(None, 11), text_color="gray", anchor="w"
    ).pack(pady=(0, 10), padx=15, anchor="w")

    if existing_categories:
        ctk.CTkLabel(
            dialog, text=t("main.category_dialog_pick_hint"),
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
                text_color=("#001F3F", "#E5E9F0"),
                command=lambda c=cat: pick(c)
            ).pack(pady=2, fill="x")
    else:
        ctk.CTkLabel(
            dialog, text=t("main.category_dialog_none_yet"),
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

    ctk.CTkButton(btns_frame, text=t("main.category_dialog_save"), command=confirm).pack(
        side="left", expand=True, fill="x", padx=(0, 5)
    )
    ctk.CTkButton(btns_frame, text=t("main.category_dialog_cancel"), fg_color="transparent", border_width=1,
                  text_color=("#001F3F", "#E5E9F0"), command=cancel).pack(
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
    dialog.title(t("main.manage_categories_title"))
    dialog.geometry("360x380")
    dialog.minsize(300, 260)
    dialog.transient(app)

    app.update_idletasks()
    px = app.winfo_rootx() + (app.winfo_width() // 2) - 180
    py = app.winfo_rooty() + (app.winfo_height() // 2) - 190
    dialog.geometry(f"+{max(px, 0)}+{max(py, 0)}")

    ctk.CTkLabel(
        dialog, text=t("main.manage_categories_header"), font=(None, 14, "bold")
    ).pack(pady=(15, 5), padx=15, anchor="w")

    ctk.CTkLabel(
        dialog,
        text=t("main.manage_categories_hint"),
        font=(None, 11), text_color="gray", justify="left", anchor="w"
    ).pack(pady=(0, 10), padx=15, anchor="w")

    list_frame = ctk.CTkScrollableFrame(dialog)
    list_frame.pack(pady=(0, 10), padx=15, fill="both", expand=True)

    def do_delete(cat_name):
        if messagebox.askyesno(
            t("main.delete_category_confirm_title"),
            t("main.delete_category_confirm_text", category=cat_name)
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
                row, text=t("main.manage_categories_delete_btn"), width=100,
                fg_color="transparent", border_width=1,
                text_color=("#001F3F", "#E5E9F0"),
                command=lambda c=cat: do_delete(c)
            ).pack(side="right")
    else:
        ctk.CTkLabel(
            list_frame, text=t("main.manage_categories_empty"),
            text_color="gray", justify="center"
        ).pack(pady=20, padx=5)

    ctk.CTkButton(dialog, text=t("main.manage_categories_close"), command=dialog.destroy).pack(pady=(0, 15), padx=15, fill="x")

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
            smart_launch = True

            if os.path.exists(settings_file):
                with open(settings_file, "r", encoding="utf-8") as sf:
                    st = json.load(sf)
                    delay = st.get("delay", 0)
                    close_after = st.get("close_after_launch", False)
                    smart_launch = st.get("smart_launch", True)

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

                    if did_fresh_launch:
                        refresh_programs()

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
    smart_launch = True

    if os.path.exists(settings_file):
        try:
            with open(settings_file, "r", encoding="utf-8") as f:
                st = json.load(f)
                delay = st.get("delay", 0)
                close_after = st.get("close_after_launch", False)
                smart_launch = st.get("smart_launch", True)
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
        return

    if did_fresh_launch:
        # Оновлюємо лише текст підписів (лічильник ▶ N), НЕ перемальовуючи
        # чекбокси заново — інакше поточний вибір користувача (галочки)
        # загубився б одразу після запуску
        for program in programs:
            if program["checkbox"]:
                program["checkbox"].configure(text=build_program_display_name(program))


def delete_selected():
    global programs
    # Програми, приховані поточним фільтром категорій, мають checkbox=None —
    # їх не можна прибирати, інакше "Видалити" стирала б і невидимі елементи.
    # Видаляємо лише ті, чий (видимий) чекбокс реально відмічений.
    programs = [p for p in programs if not (p["checkbox"] and p["checkbox"].get() == 1)]
    save_programs()
    refresh_programs()


# Ініціалізація менеджерів (Передаємо посилання на перезапуск у SettingsManager,
# а також колбек rebuild_global_hotkeys — щоб гарячі клавіші миттєво
# перереєстровувались одразу після їх зміни у Наборах чи Налаштуваннях)
preset_manager_frame = PresetManager(app, on_hotkeys_changed=rebuild_global_hotkeys)
schedule_manager_frame = ScheduleManager(app, exit_program)
settings_manager_frame = SettingsManager(
    app,
    restart_callback=restart_program,
    hotkeys_changed_callback=rebuild_global_hotkeys,
    preset_manager_ref=preset_manager_frame,
    programs_provider=lambda: programs,
    stats_reset_callback=lambda: refresh_programs()
)
info_manager_frame = InfoManager(app)

button_frame = ctk.CTkFrame(main_ui_frame, fg_color="transparent")
button_frame.pack(pady=10, fill="x")

ctk.CTkButton(button_frame, text=t("main.btn_add"), command=add_program).pack(side="left", padx=5, expand=True, fill="x")
ctk.CTkButton(button_frame, text=t("main.btn_launch"), command=launch_selected).pack(side="left", padx=5, expand=True, fill="x")
ctk.CTkButton(button_frame, text=t("main.btn_delete"), command=delete_selected).pack(side="left", padx=5, expand=True, fill="x")

exit_button_frame = ctk.CTkFrame(app, fg_color="transparent")
exit_button_frame.pack(side="bottom", fill="x", padx=20, pady=15)

global_exit_btn = ctk.CTkButton(
    exit_button_frame,
    text=t("main.btn_full_exit"),
    fg_color="transparent",
    border_width=1,
    text_color=("#001F3F", "#E5E9F0"),
    command=exit_program
)
global_exit_btn.pack(fill="x", ipady=3)

load_programs()
check_and_run_autostart()

# Реєструємо глобальні гарячі клавіші (показ вікна + всі набори з
# призначеною комбінацією) вже після того, як усі дані завантажені
rebuild_global_hotkeys()

app.mainloop()