"""
Єдине джерело правди для шляхів застосунку.

Мета: папки jsons_saves/ та themes/ повинні ЗАВЖДИ створюватися поруч
із launcher'ом (.exe або .py), а не в поточній робочій директорії (cwd) і
не в системних папках. Це критично, бо cwd може відрізнятися від
розташування .exe, якщо застосунок запущено:
  - ярликом з іншим полем "Start in";
  - через Планувальник завдань Windows;
  - подвійним кліком по .py, коли IDE/термінал стоїть в іншій папці.

Завдяки прив'язці саме до sys.executable (у зібраному .exe) або до
розташування головного файлу (у розробці), всю папку з програмою можна
вільно переносити на інший диск чи в іншу теку — jsons_saves і themes
"переїдуть" разом з нею без жодних додаткових дій.
"""

import os
import sys


def get_base_dir():
    """ Повертає директорію, в якій фізично лежить launcher. """
    if getattr(sys, "frozen", False):
        # Зібраний PyInstaller .exe — беремо папку самого .exe
        return os.path.dirname(sys.executable)

    # Режим розробки (запуск через python).
    # Пріоритет — файл, яким запущено процес (ProgramLauncherStart.py),
    # а не __file__ цього модуля, щоб усі частини програми (навіть якщо
    # колись розʼїдуться по підпапках) вказували на одну й ту саму базу.
    main_module = sys.modules.get("__main__")
    if main_module is not None and hasattr(main_module, "__file__"):
        return os.path.dirname(os.path.abspath(main_module.__file__))

    return os.path.dirname(os.path.abspath(__file__))


def get_saves_dir():
    """ Папка jsons_saves/, створюється за потреби. """
    path = os.path.join(get_base_dir(), "jsons_saves")
    os.makedirs(path, exist_ok=True)
    return path


def get_themes_dir():
    """ Папка themes/, створюється за потреби. """
    path = os.path.join(get_base_dir(), "themes")
    os.makedirs(path, exist_ok=True)
    return path


def saves_path(filename):
    """ Повний шлях до файлу всередині jsons_saves/ (папка гарантовано існує). """
    return os.path.join(get_saves_dir(), filename)


def themes_path(filename=None):
    """ Повний шлях до файлу всередині themes/ (папка гарантовано існує).
    Без filename повертає саму директорію themes/. """
    themes_dir = get_themes_dir()
    return os.path.join(themes_dir, filename) if filename else themes_dir
