"""
Статистика запусків програм.

Легкий лічильник: скільки разів кожна програма РЕАЛЬНО була запущена
через лаунчер — вручну зі списку "Програми", з набору (пресету), за
розкладом чи в автозапуску. Мета — допомогти користувачу побачити,
яким софтом він дійсно користується, а який можна прибрати зі списку.

Зберігається окремо від checkbox_programs.json/presets.json, у
jsons_saves/launch_stats.json (шлях береться через app_paths, щоб файл
завжди лежав поруч із launcher'ом, а не в поточній робочій директорії).
Ключ запису — нормалізований абсолютний шлях до файлу програми, тому
той самий .exe рахується однаково незалежно від того, з головного
списку, набору чи розкладу його запустили.
"""

import os
import json

from app_paths import saves_path

STATS_FILENAME = "launch_stats.json"


def _normalize(path):
    if not path:
        return ""
    return os.path.normcase(os.path.abspath(path))


def _load():
    stats_file = saves_path(STATS_FILENAME)
    if os.path.exists(stats_file):
        try:
            with open(stats_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict):
                    return data
        except Exception:
            pass
    return {}


def _save(stats):
    try:
        with open(saves_path(STATS_FILENAME), "w", encoding="utf-8") as f:
            json.dump(stats, f, indent=4, ensure_ascii=False)
    except Exception:
        # Статистика — не критична функція: якщо запис не вдався
        # (немає прав на диск тощо), запуск програми все одно не
        # повинен через це впасти.
        pass


def get_count(path):
    """ Скільки разів програму за цим шляхом було реально запущено. """
    key = _normalize(path)
    if not key:
        return 0
    return _load().get(key, 0)


def increment(path):
    """ Збільшує лічильник запусків програми за шляхом на 1 і одразу
    зберігає. Викликати лише коли процес РЕАЛЬНО стартував (не при
    "skipped_running" — вона й так вже відкрита — і не при "failed"),
    щоб цифра відображала кількість фактичних запусків, а не кліків. """
    key = _normalize(path)
    if not key:
        return
    stats = _load()
    stats[key] = stats.get(key, 0) + 1
    _save(stats)


def reset(path):
    """ Скидає лічильник конкретної програми (напр. з контекстного
    меню програми). """
    key = _normalize(path)
    if not key:
        return
    stats = _load()
    if key in stats:
        del stats[key]
        _save(stats)


def reset_all():
    """ Повністю очищає всю статистику запусків. """
    _save({})
