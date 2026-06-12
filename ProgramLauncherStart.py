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
    settings_file = "jsons_saves/settings.json"
    os.makedirs("themes", exist_ok=True)

    if os.path.exists(settings_file):
        try:
            with open(settings_file, "r", encoding="utf-8") as f:
                st = json.load(f)
                ctk.set_appearance_mode(st.get("theme", "Dark"))
                color_theme = st.get("color_theme", "blue")
                if color_theme not in ["blue", "green", "dark-blue"]:
                    theme_path = f"themes/{color_theme}.json"
                    if os.path.exists(theme_path):
                        ctk.set_default_color_theme(theme_path)
                        return
                ctk.set_default_color_theme(color_theme)
                return
        except:
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
        programs.append({"name": name, "path": path, "checkbox": None})
    save_programs()
    refresh_programs()


# Ініціалізуємо Drag & Drop
setup_windows_dnd(app, on_files_dropped_native)


def save_programs():
    data = [{"name": p["name"], "path": p["path"]} for p in programs]
    with open("jsons_saves/checkbox_programs.json", "w", encoding="utf-8") as file:
        json.dump(data, file, indent=4, ensure_ascii=False)


def refresh_programs():
    for widget in program_frame.winfo_children():
        widget.destroy()

    if not programs:
        placeholder = ctk.CTkLabel(
            program_frame,
            text="✨ Список порожній...\n\nПеретягніть сюди ярлики файлів мишкою\nабо скористайтеся кнопкою 'Додати'",
            text_color="gray", justify="center"
        )
        placeholder.pack(pady=40, fill="x")
        return

    for program in programs:
        checkbox = ctk.CTkCheckBox(program_frame, text=program["name"])
        checkbox.pack(anchor="w", pady=5, padx=10, fill="x")
        program["checkbox"] = checkbox
        checkbox.bind("<Button-3>", lambda event, p=program: show_context_menu(event, p))


def show_context_menu(event, program):
    context_menu.delete(0, "end")
    context_menu.add_command(label=f"Перейменувати '{program['name']}'", command=lambda: rename_program(program))
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


def delete_single_program(program_to_delete):
    global programs
    programs = [p for p in programs if p != program_to_delete]
    save_programs()
    refresh_programs()


def load_programs():
    global programs
    try:
        with open("jsons_saves/checkbox_programs.json", "r", encoding="utf-8") as file:
            raw_data = json.load(file)
            programs = [{"name": item["name"], "path": item["path"], "checkbox": None} for item in raw_data]
    except:
        programs = []
    refresh_programs()


def check_and_run_autostart():
    presets_file = "jsons_saves/presets.json"
    settings_file = "jsons_saves/settings.json"

    if os.path.exists(presets_file) and os.path.getsize(presets_file) > 0:
        try:
            delay = 0
            close_after = False
            if os.path.exists(settings_file):
                with open(settings_file, "r") as sf:
                    st = json.load(sf)
                    delay = st.get("delay", 0)
                    close_after = st.get("close_after_launch", False)

            with open(presets_file, "r", encoding="utf-8") as file:
                presets = json.load(file)
                for name, data in presets.items():
                    if isinstance(data, dict) and data.get("autostart", False):
                        for idx, path in enumerate(data.get("programs", [])):
                            if idx > 0 and delay > 0:
                                time.sleep(delay)
                            try:
                                os.startfile(path)
                            except Exception as e:
                                print(f"Не вдалося запустити {path}: {e}")
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
    programs.append({"name": name, "path": path, "checkbox": None})
    save_programs()
    refresh_programs()


def launch_selected():
    delay = 0
    close_after = False
    if os.path.exists("jsons_saves/settings.json"):
        try:
            with open("jsons_saves/settings.json", "r") as f:
                st = json.load(f)
                delay = st.get("delay", 0)
                close_after = st.get("close_after_launch", False)
        except:
            pass

    launched_any = False
    for program in programs:
        if program["checkbox"] and program["checkbox"].get() == 1:
            if launched_any and delay > 0:
                time.sleep(delay)
            try:
                os.startfile(program["path"])
                launched_any = True
            except:
                pass
    if launched_any and close_after:
        exit_program()


def delete_selected():
    global programs
    programs = [p for p in programs if p["checkbox"].get() == 0]
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