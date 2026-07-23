"""
Глобальні гарячі клавіші (Global Hotkeys).

Дозволяють:
  - миттєво розгорнути головне вікно лаунчера з трею (навіть якщо
    воно згорнуте) однією комбінацією клавіш, наприклад Ctrl+Alt+L;
  - запустити конкретний набір (пресет) напряму, без відкриття вікна —
    комбінація задається окремо для кожного набору у вкладці "Набори".

Реалізовано на основі бібліотеки `keyboard` (низькорівневий системний
хук клавіатури, працює навіть коли вікно лаунчера не в фокусі чи
згорнуте в трей). Бібліотека ОПЦІОНАЛЬНА і не входить в стандартну
поставку — якщо вона не встановлена (`pip install keyboard`) або хук
не вдалось зареєструвати (наприклад, немає прав адміністратора), весь
функціонал гарячих клавіш просто мовчки вимикається: жодна інша частина
лаунчера від цього не ламається.

Примітка щодо прав доступу: на Windows реєстрація глобального хука
клавіатури зазвичай не потребує прав адміністратора, АЛЕ якщо сам
лаунчер (.exe) запущено від імені адміністратора, а натискання клавіш
відбувається у вікні звичайного (не-адмінського) процесу — Windows може
не пропустити подію через різницю рівнів цілісності процесів. У такому
разі запустіть лаунчер без підвищених прав.
"""

import threading

try:
    import keyboard
    _KEYBOARD_AVAILABLE = True
except ImportError:
    _KEYBOARD_AVAILABLE = False


def is_available():
    """ True, якщо бібліотека 'keyboard' встановлена і готова до використання. """
    return _KEYBOARD_AVAILABLE


def normalize_hotkey(text):
    """ Перевіряє, чи є рядок коректною комбінацією клавіш для `keyboard`
    (напр. "ctrl+alt+l"), і повертає нормалізований рядок у нижньому
    регістрі. Повертає None, якщо комбінація некоректна.
    Якщо сама бібліотека недоступна — перевірити синтаксис неможливо,
    тож рядок повертається як є (довіряємо користувачу). """
    text = (text or "").strip().lower()
    if not text:
        return None
    if not _KEYBOARD_AVAILABLE:
        return text
    try:
        keyboard.parse_hotkey(text)
        return text
    except Exception:
        return None


def record_hotkey():
    """ Блокуюче очікування наступної комбінації клавіш від користувача.
    ВАЖЛИВО: викликати лише з фонового потоку (не з головного потоку
    Tkinter/CTk), інакше інтерфейс лаунчера зависне на весь час
    очікування натискання. Повертає рядок комбінації, або None, якщо
    бібліотека недоступна чи сталася помилка. """
    if not _KEYBOARD_AVAILABLE:
        return None
    try:
        return keyboard.read_hotkey(suppress=False)
    except Exception:
        return None


class HotkeyManager:
    """ Централізовано (пере)реєструє всі глобальні гарячі клавіші
    лаунчера. rebuild(...) щоразу знімає геть усі попередньо зареєстровані
    комбінації і ставить нові — тому його безпечно викликати повторно
    (наприклад, одразу після того як користувач змінив налаштування чи
    гарячу клавішу набору). """

    def __init__(self):
        self._lock = threading.Lock()

    def rebuild(self, show_hotkey, show_callback, preset_hotkeys, launch_preset_callback):
        """
        show_hotkey: рядок комбінації для показу вікна лаунчера, або
                     порожній рядок/None щоб цю комбінацію вимкнути.
        show_callback: функція без аргументів — показує головне вікно.
        preset_hotkeys: dict {назва_набору: рядок_комбінації}.
        launch_preset_callback: функція(назва_набору) — запускає набір.

        Обидва callback'и викликаються з фонового потоку хука клавіатури,
        а НЕ з головного потоку Tkinter — виклики, що торкаються
        інтерфейсу, мають самі подбати про безпечну передачу в головний
        потік (наприклад, через app.after(0, ...)).
        """
        if not _KEYBOARD_AVAILABLE:
            return

        with self._lock:
            try:
                keyboard.unhook_all_hotkeys()
            except Exception:
                pass

            if show_hotkey:
                self._safe_add(show_hotkey, show_callback)

            for preset_name, hk in (preset_hotkeys or {}).items():
                if not hk:
                    continue
                # default-аргумент лямбди захоплює preset_name за значенням
                # на момент створення, а не за посиланням на змінну циклу
                self._safe_add(hk, lambda name=preset_name: launch_preset_callback(name))

    def _safe_add(self, hotkey_str, callback):
        try:
            keyboard.add_hotkey(hotkey_str, callback)
        except Exception:
            # Некоректна комбінація чи конфлікт реєстрації — пропускаємо,
            # це не має валити застосунок
            pass

    def stop(self):
        """ Знімає всі гарячі клавіші лаунчера. Викликати перед повним
        виходом чи перезапуском програми, щоб не лишати "висячий" хук. """
        if not _KEYBOARD_AVAILABLE:
            return
        with self._lock:
            try:
                keyboard.unhook_all_hotkeys()
            except Exception:
                pass
