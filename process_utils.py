"""
Допоміжні функції для "розумного запуску" — перевірка через psutil,
чи програма вже запущена, щоб не плодити дублікати вікон при повторному
натисканні "Запустити" (вручну, у пресеті, за розкладом чи в автозапуску).

Порівняння відбувається у два етапи:
  1. За повним шляхом до .exe (найнадійніше) — якщо psutil зміг його
     прочитати. На процесах з підвищеними правами доступ до exe-шляху
     може бути заборонений (AccessDenied) — тоді тихо переходимо до
     порівняння за назвою.
  2. За назвою процесу без розширення — рятує ситуацію з .lnk-ярликами,
     для яких заздалегідь невідомий реальний .exe: ми порівнюємо назву
     самого ярлика з назвами запущених процесів.

Обмеження: якщо ярлик і процес називаються по-різному (наприклад, ярлик
"Мій браузер.lnk" запускає chrome.exe) — збіг за назвою не спрацює,
і програма запуститься повторно. Найнадійніше працює для .exe напряму.
"""

import os

try:
    import psutil
    _PSUTIL_AVAILABLE = True
except ImportError:
    _PSUTIL_AVAILABLE = False


def _target_name(path):
    name = os.path.basename(path)
    for ext in (".exe", ".lnk", ".bat", ".cmd"):
        if name.lower().endswith(ext):
            name = name[: -len(ext)]
            break
    return name.lower()


def is_process_running(path):
    """ True, якщо процес з таким .exe (за шляхом або за назвою) вже виконується.
    Якщо psutil недоступний з якоїсь причини — завжди повертає False
    (тобто поведінка деградує до звичайного запуску, без збоїв). """
    if not _PSUTIL_AVAILABLE or not path:
        return False

    target_path = os.path.normcase(os.path.abspath(path))
    target_name = _target_name(path)

    for proc in psutil.process_iter(["name", "exe"]):
        try:
            info = proc.info
            exe = info.get("exe")
            if exe and os.path.normcase(os.path.abspath(exe)) == target_path:
                return True

            proc_name = info.get("name") or ""
            proc_name_no_ext = os.path.splitext(proc_name)[0].lower()
            if proc_name_no_ext and proc_name_no_ext == target_name:
                return True
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            continue

    return False


def resolve_program_entry(item):
    """ Пресети можуть зберігати програми у двох форматах:
      - старий: просто рядок зі шляхом ("C:\\...\\app.exe")
      - новий: {"path": "...", "args": "..."} — щоб підтримувати
        аргументи запуску й для програм всередині наборів.
    Ця функція повертає (path, args) в уніфікованому вигляді, незалежно
    від того, який формат зустрівся, — для сумісності зі старими
    presets.json, створеними до появи аргументів запуску. """
    if isinstance(item, dict):
        return item.get("path", ""), item.get("args", "")
    return item, ""


def smart_startfile(path, args="", skip_if_running=True):
    """ Обгортка над os.startfile з перевіркою "чи вже запущено" ТА
    підтримкою аргументів запуску (наприклад, "-windowed" для гри, або
    URL для браузера).
    Повертає один із трьох статусів:
      "launched"        — реально запустили новий процес
      "skipped_running" — пропустили, бо програма вже працює (це теж
                           "успіх" з точки зору мети користувача: програма
                           відкрита; але це НЕ привід чекати "затримку між
                           запусками" перед наступною програмою)
      "failed"          — сталася помилка запуску (шлях не існує,
                           немає прав тощо)

    Примітка: якщо задані аргументи, перевірка "чи вже запущено" все одно
    відбувається лише за .exe/назвою процесу, без урахування аргументів —
    тобто якщо той самий браузер вже відкритий БЕЗ потрібного сайту,
    "розумний запуск" все одно пропустить повторне відкриття з аргументом.
    Якщо для конкретної програми це небажано — вимкніть "Розумний запуск"
    в Налаштуваннях або для цієї програми окремо не задавайте аргументи. """
    if skip_if_running and is_process_running(path):
        return "skipped_running"

    try:
        if args:
            try:
                os.startfile(path, arguments=args)
            except TypeError:
                # os.startfile отримав параметр "arguments" лише з Python 3.10.
                # На старіших версіях запускаємо через ShellExecute напряму.
                import ctypes
                ctypes.windll.shell32.ShellExecuteW(None, "open", path, args, None, 1)
        else:
            os.startfile(path)
        return "launched"
    except Exception:
        return "failed"
