"""
Локалізація (мультимова) інтерфейсу лаунчера.

Рядки інтерфейсу зберігаються не в коді, а в JSON-файлах у папці
locales/ (створюється поруч із launcher'ом через app_paths — так само,
як jsons_saves/ і themes/, — щоб пережити перенесення програми на
інший диск чи в іншу теку). Кожна мова — окремий плаский файл
{"ключ.з.крапками": "переклад рядка"}, напр. locales/uk.json,
locales/en.json. Якщо файл мови відсутній чи пошкоджений — він
автоматично створюється заново з вбудованих значень за замовчуванням
(DEFAULT_STRINGS), тож лаунчер ніколи не лишиться без інтерфейсу.

Обрана мова зберігається в settings.json (ключ "language"), поруч з
рештою налаштувань. Оскільки практично весь текст інтерфейсу
створюється один раз при побудові CustomTkinter-віджетів, зміна мови
(як і зміна кольорової теми) застосовується повним перезапуском
лаунчера — SettingsManager викликає той самий restart_callback, що й
для теми.

Використання в будь-якому файлі лаунчера:
    from locale_manager import t
    ctk.CTkLabel(parent, text=t("settings.theme_label"))

Якщо для ключа немає перекладу в обраній мові — підстраховуємось
англійською (мова за замовчуванням), а якщо немає і там — повертаємо
сам ключ, щоб інтерфейс не падав через відсутній рядок.
"""

import os
import json

from app_paths import locales_path, saves_path

DEFAULT_LANGUAGE = "en"

AVAILABLE_LANGUAGES = {
    "uk": "Українська",
    "en": "English",
}

# Вбудовані рядки за замовчуванням — джерело правди для генерації
# locales/*.json при першому запуску чи якщо файл мови пошкоджений/
# видалений. Ключі організовані по модулях (main.*, settings.*,
# categories.*, dialogs.*), щоб не губитися серед сотень рядків.
DEFAULT_STRINGS = {
    "uk": {
        # --- Головне вікно: перемикач вкладок ---
        "main.tab_programs": "📱 Програми",
        "main.tab_presets": "⚙ Набори",
        "main.tab_schedule": "⏰ Розклад",
        "main.tab_settings": "🛠 Налаштування",
        "main.tab_info": "ℹ Довідка",

        # --- Головне вікно: список програм ---
        "main.category_label": "🏷 Категорія:",
        "main.category_all": "Всі",
        "main.category_unset": "Без категорії",
        "main.manage_categories_btn": "🗑",
        "main.btn_add": "Додати",
        "main.btn_launch": "Запустити",
        "main.btn_delete": "Видалити",
        "main.btn_full_exit": "❌ Повний вихід з програми",
        "main.empty_list": "✨ Список порожній...\n\nПеретягніть сюди ярлики файлів мишкою\nабо скористайтеся кнопкою 'Додати'",
        "main.empty_category": "У категорії «{category}» ще немає програм.",

        # --- Контекстне меню програми ---
        "main.ctx_rename": "Перейменувати '{name}'",
        "main.ctx_args": "⚙ Параметри запуску...",
        "main.ctx_category": "🏷 Категорія...",
        "main.ctx_reset_stats": "🔄 Скинути лічильник запусків",
        "main.ctx_delete": "Видалити зі списку",

        # --- Діалоги перейменування / аргументів ---
        "main.rename_prompt": "Введіть нову назву для {name}:",
        "main.rename_title": "Перейменування",
        "main.args_title": "Параметри запуску",
        "main.args_prompt_header": "Аргументи запуску для '{name}':\n",
        "main.args_prompt_current": "Поточне значення: {args}\n",
        "main.args_prompt_hint": "Залиште порожнім, щоб прибрати аргументи (напр. -windowed, або URL для браузера).",

        # --- Діалог категорії програми ---
        "main.category_dialog_title": "Категорія програми",
        "main.category_dialog_label": "Категорія для «{name}»:",
        "main.category_dialog_placeholder": "Назва категорії (нова або вже наявна)",
        "main.category_dialog_clear_hint": "Порожнє поле прибере категорію.",
        "main.category_dialog_pick_hint": "Або оберіть зі списку створених:",
        "main.category_dialog_none_yet": "Категорій ще немає — просто введіть нову назву вище,\nвона створиться автоматично.",
        "main.category_dialog_save": "💾 Зберегти",
        "main.category_dialog_cancel": "Скасувати",

        # --- Діалог керування категоріями ---
        "main.manage_categories_title": "Керування категоріями",
        "main.manage_categories_header": "🏷 Керування категоріями",
        "main.manage_categories_hint": "Видалення категорії не стирає самі програми — вони\nпросто повертаються у стан «Без категорії».",
        "main.manage_categories_empty": "Категорій ще немає.\nСтворити категорію можна через\nправий клік по програмі -> \"🏷 Категорія...\"",
        "main.manage_categories_delete_btn": "🗑 Видалити",
        "main.manage_categories_close": "Закрити",
        "main.delete_category_confirm_title": "Видалення категорії",
        "main.delete_category_confirm_text": "Видалити категорію «{category}»?\n\nПрограми, що мали цю категорію, стануть «Без категорії».",

        # --- Трей ---
        "main.tray_open": "📱 Відкрити лаунчер",
        "main.tray_exit": "❌ Повний вихід",
        "main.already_running_title": "Program Launcher",
        "main.already_running_text": "Лаунчер вже запущено (або він ще завантажується).\n\nБудь ласка, зачекайте — друга копія програми не потрібна.",

        # ============== SETTINGS TAB ==============
        "settings.theme_label": "Візуальна тема програми:",
        "settings.color_label": "Колір та шрифт стилю (потребує перезапуску):",
        "settings.import_json": "📁 Імпортувати .json",
        "settings.theme_creator": "🎨 FK Конструктор теми",
        "settings.reset_themes": "💥 Скинути всі кастомні теми",

        "settings.language_label": "Мова інтерфейсу (потребує перезапуску):",

        "settings.behavior_label": "Поведінка лаунчера:",
        "settings.close_after_launch": "Закривати лаунчер після запуску програм",
        "settings.minimize_to_tray": "Не закривати, а згортати у фоновий режим (трей) при натисканні ❌",
        "settings.tray_hint": "Трей — це значок біля годинника Windows. Потрібно увімкнути,\nщоб розклад продовжував працювати після закриття вікна.",
        "settings.windows_autostart": "Автоматично запускати лаунчер при вмиканні Windows",
        "settings.smart_launch": "🧠 Розумний запуск: не відкривати повторно, якщо вже запущено",
        "settings.smart_launch_hint": "Перед запуском лаунчер перевірить список запущених процесів\n(через psutil) і пропустить програму, якщо вона вже відкрита —\nщоб не плодити зайві вікна при повторних кліках чи спрацюванні розкладу.",

        "settings.delay_label": "Затримка між запуском програм: {seconds} сек.",

        "settings.hotkeys_label": "⌨️ Гарячі клавіші:",
        "settings.hotkeys_hint": "Показ вікна лаунчера з трею та миттєвий запуск окремих\nнаборів без відкриття вікна — усі комбінації клавіш\nзібрані і редагуються в одному вікні.",
        "settings.hotkeys_btn": "🎹 Керування гарячими клавішами...",
        "settings.hotkeys_missing_lib": "⚠ Бібліотека 'keyboard' не знайдена — гарячі клавіші не працюватимуть.\nВстановіть командою: pip install keyboard",

        "settings.stats_label": "📊 Статистика використання:",
        "settings.stats_hint": "Скільки разів кожну програму реально було запущено через\nлаунчер — щоб було видно, який софт дійсно потрібен.",
        "settings.stats_btn": "📊 Переглянути статистику...",

        "settings.backup_label": "📦 Резервне копіювання конфігурацій:",
        "settings.backup_create": "💾 Створити бекап (ZIP)",
        "settings.backup_restore": "📂 Відновити з бекапу",

        "settings.restart_btn": "🔄 Перезапустити програму",
        "settings.restart_error": "Функцію перезапуску не було передано.",
        "settings.error_title": "Помилка",

        # ============== PRESETS TAB ==============
        "presets.section_create_title": "Створити новий набір програм",
        "presets.name_placeholder": "Введіть назву (напр: Робота, Ігри)",
        "presets.save_new_btn": "💾 Зберегти новий набір",
        "presets.section_manage_title": "Ваші збережені набори",
        "presets.none_created": "Немає створених наборів",
        "presets.autostart_checkbox": "🚀 Стартовий набір: запускати цей набір одразу при відкритті лаунчера",
        "presets.launch_btn": "🚀 Запустити набір",
        "presets.stop_btn": "⛔ Закрити набір",
        "presets.delete_btn": "❌ Видалити цей набір",
        "presets.error_invalid_name": "Введіть коректну назву для набору!",
        "presets.error_no_programs": "Оберіть хоча б одну програму для набору!",
        "presets.success_title": "Успіх",
        "presets.success_created": "Набір '{name}' успішно створено!",
        "presets.delete_confirm_title": "Видалення",
        "presets.delete_confirm_text": "Ви впевнені, що хочете видалити набір '{name}'?",
        "presets.empty_no_programs": "Немає жодної доданої програми на вкладці 'Програми'.",

        # ============== SCHEDULE TAB ==============
        "schedule.title": "⏰ Налаштування розкладу та днів",
        "schedule.days_from": "Дні: з",
        "schedule.days_to": "по",
        "schedule.day_mon": "Понеділок",
        "schedule.day_tue": "Вівторок",
        "schedule.day_wed": "Середа",
        "schedule.day_thu": "Четвер",
        "schedule.day_fri": "П'ятниця",
        "schedule.day_sat": "Субота",
        "schedule.day_sun": "Неділя",
        "schedule.time_label": "Час запуску (ГГ:ХХ):",
        "schedule.what_label": "Що запускати:",
        "schedule.type_program": "Програма",
        "schedule.type_preset": "Набір (Пресет)",
        "schedule.target_label": "Виберіть ціль:",
        "schedule.no_programs_yet": "Спочатку додайте програми",
        "schedule.add_btn": "➕ Додати до розкладу",
        "schedule.current_list_title": "Поточний розклад:",
        "schedule.programs_list_empty": "Список програм порожній",
        "schedule.create_preset_first": "Створіть хоча б один набір",
        "schedule.tasks_empty": "Завдань немає",
        "schedule.bg_worker_error": "Помилка фонового потоку розкладу: {error}",

        # ============== THEME CREATOR WINDOW ==============
        "theme_creator.window_title": "Гнучкий конструктор теми",
        "theme_creator.target_buttons": "Кнопки",
        "theme_creator.target_window_bg": "Фон вікна",
        "theme_creator.target_frames_bg": "Фон фреймів",
        "theme_creator.target_entries": "Текстові поля",
        "theme_creator.target_checks_switches": "Чекбокси/Світчі",
        "theme_creator.target_text": "Текст",
        "theme_creator.mode_both": "До обох",
        "theme_creator.mode_dark_only": "Тільки Dark",
        "theme_creator.mode_light_only": "Тільки Light",
        "theme_creator.name_label": "Назва теми (англійською):",
        "theme_creator.name_placeholder": "напр: mega_style",
        "theme_creator.preview_label": "Попередній перегляд:",
        "theme_creator.preview_sample_label": "Приклад текста (Label)",
        "theme_creator.preview_entry_placeholder": "Поле введення...",
        "theme_creator.preview_entry_text": "Текст у полі",
        "theme_creator.preview_checkbox": "Чекбокс",
        "theme_creator.preview_switch": "Світч",
        "theme_creator.preview_button": "Приклад кнопки",
        "theme_creator.target_select_label": "Оберіть елемент для редагування:",
        "theme_creator.main_color_label": "Основний колір (RGB):",
        "theme_creator.hover_color_label": "Колір при наведенні (RGB):",
        "theme_creator.main_color_buttons_label": "Основний колір кнопок (RGB):",
        "theme_creator.element_color_label": "Колір елемента '{element}' (RGB):",
        "theme_creator.save_btn": "💾 Зберегти тему та застосувати",
        "theme_creator.error_empty_name": "Введіть назву теми!",
        "theme_creator.error_save_failed": "Не вдалося зберегти тему: {error}",

        # ============== HOTKEY MANAGER DIALOG ==============
        "hotkeys.window_title": "Керування гарячими клавішами",
        "hotkeys.missing_lib_warning": "⚠ Бібліотека 'keyboard' не встановлена — гарячі клавіші не працюватимуть, поки її не встановити.\nКоманда: pip install keyboard",
        "hotkeys.show_window_title": "🖥 Показати вікно лаунчера з трею",
        "hotkeys.show_window_hint": "Спрацьовує завжди, навіть якщо вікно згорнуте.",
        "hotkeys.presets_title": "🚀 Миттєвий запуск наборів",
        "hotkeys.presets_hint": "Запускає весь набір програм без відкриття вікна лаунчера.",
        "hotkeys.no_presets": "Немає жодного набору. Створіть набір у вкладці 'Набори',\nщоб можна було призначити йому гарячу клавішу.",
        "hotkeys.hotkey_placeholder": "напр: ctrl+alt+l",
        "hotkeys.unavailable_title": "Недоступно",
        "hotkeys.unavailable_text": "Бібліотека 'keyboard' не встановлена.\nВстановіть: pip install keyboard",
        "hotkeys.invalid_combo_title": "Некоректна комбінація",
        "hotkeys.invalid_combo_text": "Не вдалося розпізнати «{value}».\nПриклад: ctrl+alt+l",
        "hotkeys.done_title": "Готово",
        "hotkeys.show_hotkey_set": "Гаряча клавіша «{hotkey}» тепер відкриває лаунчер.",
        "hotkeys.show_hotkey_disabled": "Глобальну гарячу клавішу показу вікна вимкнено.",
        "hotkeys.conflict_show_window": "показу вікна лаунчера",
        "hotkeys.conflict_preset": "набору «{name}»",
        "hotkeys.conflict_title": "Комбінація вже використовується",
        "hotkeys.conflict_text": "Клавіша «{hotkey}» вже призначена для: {list}.\n\nМожна залишити так, але спрацюють ОБИДВІ дії одночасно.",
        "hotkeys.preset_hotkey_set": "Гаряча клавіша «{hotkey}» тепер запускає набір «{name}».",
        "hotkeys.preset_hotkey_removed": "Гарячу клавішу для набору «{name}» прибрано.",

        # ============== STATS DIALOG ==============
        "stats.window_title": "Статистика використання",
        "stats.chart_title": "📊 Скільки разів запущено кожну програму",
        "stats.hint": "Рахуються лише реальні запуски через лаунчер — зі списку 'Програми', з наборів, за розкладом чи в автозапуску. Допомагає побачити, який софт дійсно потрібен, а який можна прибрати зі списку.",
        "stats.reset_all_btn": "🗑 Скинути всю статистику",
        "stats.reset_confirm_title": "Скинути статистику",
        "stats.reset_confirm_text": "Скинути лічильники запусків для ВСІХ програм?\nЦю дію не можна скасувати.",

        # ============== SETTINGS: autostart / backup / theme import ==============
        "settings.autostart_error_title": "Автозапуск",
        "settings.autostart_error_text": "Не вдалося змінити налаштування в реєстрі Windows: {error}",
        "settings.autostart_read_error": "Автозапуск: не вдалося прочитати шлях з реєстру: {error}",
        "settings.autostart_path_updated": "Автозапуск: шлях у реєстрі застарів і був оновлений на '{path}'.",
        "settings.autostart_update_error": "Автозапуск: не вдалося оновити застарілий шлях у реєстрі: {error}",
        "settings.backup_title": "Бекап",
        "settings.backup_nothing_to_backup": "Немає збережених налаштувань чи розкладів для резервного копіювання!",
        "settings.zip_filter_label": "ZIP Архів",
        "settings.backup_save_dialog_title": "Зберегти резервну копію як...",
        "settings.backup_created": "Резервну копію налаштувань та розкладу успішно створено!",
        "settings.backup_create_failed": "Не вдалося створити файл бекапу: {error}",
        "settings.backup_open_dialog_title": "Оберіть файл резервної копії",
        "settings.restore_confirm_title": "Відновлення",
        "settings.restore_confirm_text": "Поточні налаштування, розклад та набори будуть повністю замінені даними з архіву. Продовжити?",
        "settings.backup_extract_failed": "Не вдалося розархівувати дані: {error}",
        "settings.backup_invalid": "Файл резервної копії пошкоджений або має невірний формат.\n{details}\n\nВідновлення скасовано, поточні дані не змінено.",
        "settings.restore_success": "Конфігурацію відновлено! Натисніть кнопку перезапуску програми для застосування змін.",
        "settings.backup_apply_failed": "Не вдалося застосувати дані з бекапу: {error}",
        "settings.backup_file_not_json": "Файл '{filename}' не є коректним JSON ({error})",
        "settings.backup_file_read_failed": "Не вдалося прочитати файл '{filename}' ({error})",
        "settings.backup_file_bad_structure": "Файл '{filename}' має неочікувану структуру даних",
        "settings.theme_created": "Тему '{name}' створено! Натисніть кнопку перезапуску.",
        "settings.theme_file_filter_label": "Тема CustomTkinter",
        "settings.import_success": "Імпортовано тем: {count} ({names}).\nПерезапустіть лаунчер, щоб застосувати обрану.",
        "settings.import_partial_title": "Імпортовано частково",
        "settings.import_partial_text": "Успішно імпортовано ({success_count}): {names}.\n\nНе вдалося імпортувати ({fail_count}):\n{errors}\n\nПерезапустіть лаунчер, щоб застосувати обрану тему.",
        "settings.import_all_failed": "Жодну тему не вдалося імпортувати:\n{errors}",
        "settings.theme_file_not_json": "Файл не є коректним JSON ({error})",
        "settings.theme_file_read_failed": "Не вдалося прочитати файл ({error})",
        "settings.theme_file_empty": "Файл порожній або має невірну структуру (очікується JSON-об'єкт)",
        "settings.theme_file_not_theme": "Файл не схожий на тему CustomTkinter (відсутні очікувані ключі стилів)",
        "settings.reset_themes_confirm_title": "Скидання",
        "settings.reset_themes_confirm_text": "Ви впевнені, що хочете видалити ВСІ створені та імпортовані теми?",
        "settings.reset_themes_done_text": "Кастомні теми видалено! Застосовано стандартний стиль.",
        "settings.reset_themes_error": "Помилка очищення тем: {error}",
        "settings.stats_unavailable_title": "Недоступно",
        "settings.stats_unavailable_text": "Список програм недоступний — спробуйте перезапустити лаунчер.",
        "settings.save_error": "Помилка збереження налаштувань: {error}",
        "settings.load_error": "Помилка завантаження налаштувань: {error}",

        # ============== INFO TAB ==============
        "info.window_title": "ℹ️Про програму та інструкція",
        "info.about_title": "🚀 Що це за додаток?",
        "info.about_text": "Це ваш персональний гнучкий лаунчер для автоматизації рутини.\n\nВін дозволяє групувати програми, ігри чи скрипти у пресети, налаштовувати автоматичний запуск за днями тижня та часом, запускати софт з власними аргументами командного рядка і запускати все необхідне в один клік або за розкладом.",
        "info.guide_label": "📖 Покрокове керівництво",

        "info.step1_title": "1. Керування програмами (Drag & Drop)",
        "info.step1_text": "На вкладці 'Програми' ви можете керувати окремими ярликами.\n\n• Просто перетягніть файли (.exe, .lnk, .bat) мишкою у вікно лаунчера — вони додадуться автоматично.\n• Також можна скористатися кнопкою 'Додати'.\n• Правий клік по будь-якій програмі відкриває контекстне меню для перейменування, видалення, налаштування '⚙ Параметри запуску' — власних аргументів командного рядка (наприклад, -windowed для гри або посилання на сайт для браузера) — або призначення '🏷 Категорія...' для групування схожих програм. Програми з заданими аргументами позначаються значком ⚙ у списку.",

        "info.step2_title": "2. Створення наборів (Пресетів)",
        "info.step2_text": "Перейдіть у вкладку 'Набори', щоб об'єднати софт у групи.\n\nВиберіть галочками потрібні програми на головному екрані, введіть назву для нового набору та натисніть 'Зберегти новий набір'. Тепер ви зможете запустити всю групу програм одночасно кнопкою 'Запустити набір' або примусово завершити всі їх процеси кнопкою 'Закрити набір'.\n\nЩоб один із наборів запускався одразу при відкритті лаунчера — оберіть його у списку та увімкніть чекбокс '🚀 Стартовий набір'. Автозапуск завжди лише в одного набору: увімкнення для нового автоматично вимикає його в попереднього.",

        "info.step3_title": "3. Категорії програм (групування та фільтр)",
        "info.step3_text": "Щоб довгий список програм не перетворювався на нескінченний скрол, кожній програмі можна призначити категорію — довільну назву-тег на кшталт 'Робота', 'Ігри' чи 'Дизайн'.\n\nПравий клік по програмі → '🏷 Категорія...' — введіть нову назву або оберіть уже створену зі списку. Порожнє поле прибирає категорію, і програма повертається у стан 'Без категорії'.\n\nНад списком програм з'являється випадаючий список '🏷 Категорія' — обравши в ньому потрібну назву, ви побачите лише програми цієї категорії; пункт 'Всі' знову показує повний список.\n\nКнопка 🗑 поруч із фільтром відкриває вікно керування категоріями, де можна видалити непотрібну категорію. Видалення категорії не видаляє самі програми — вони просто повертаються у 'Без категорії'.",

        "info.step4_title": "4. Автоматизація та Розклад завдання",
        "info.step4_text": "Вкладка 'Розклад' дозволяє автоматично запускати софт у визначений час.\n\nВиберіть діапазон днів (наприклад, з Понеділка по П'ятницю), вкажіть точний час (ГГ:ХХ), оберіть тип цілі (одиночна програма чи цілий пресет) та натисніть 'Додати до розкладу'. Програма працює у фоні та запустить софт точно у вказану хвилину.",

        "info.step5_title": "5. Затримка, Розумне закриття та Розумний запуск",
        "info.step5_text": "Якщо ваш ПК важко переносить одночасний старт багатьох програм, зайдіть в 'Налаштування' та виставте повзунок затримки запуску (у секундах).\n\nОпція 'Закривати лаунчер після запуску програм' автоматично вимикає лаунчер, щойно він виконав свою роботу.\n\nОпція '🧠 Розумний запуск' перевіряє список запущених процесів перед стартом і пропускає програму, якщо вона вже відкрита — щоб не плодити зайві вікна при повторних кліках чи спрацюванні розкладу. Не працює зі 100% точністю для ярликів (.lnk), якщо їхня назва відрізняється від назви процесу.",

        "info.step6_title": "6. Робота в системному треї",
        "info.step6_text": "У 'Налаштуваннях' є перемикач 'Не закривати, а згортати у фоновий режим (трей) при натисканні ❌'.\n\nЯкщо він увімкнений — натискання на звичайний 'хрестик' вікна не закриває застосунок повністю, а ховає його в трей (біля годинника), щоб розклад продовжував працювати у фоні. Якщо вимкнений — хрестик одразу повністю закриває лаунчер.\n\nДля повного виходу незалежно від цього перемикача використовуйте кнопку '❌ Повний вихід з програми' внизу лаунчера або правий клік по іконці в треї.",

        "info.step7_title": "7. Глобальні гарячі клавіші",
        "info.step7_text": "У вкладці 'Налаштування' є кнопка '🎹 Керування гарячими клавішами...' — це єдине місце, де зібрані й редагуються всі комбінації клавіш лаунчера.\n\n• Одна комбінація (наприклад, Ctrl+Alt+L) миттєво розгортає головне вікно лаунчера з трею, навіть якщо воно згорнуте чи не в фокусі.\n• Кожному набору (пресету) можна окремо призначити свою комбінацію, щоб запускати його напряму, без відкриття вікна взагалі.\n\nЩоб задати клавішу — натисніть 🎙 і одразу натисніть потрібну комбінацію на клавіатурі, або впишіть її вручну (напр. ctrl+alt+1), і збережіть кнопкою 💾. Функція працює лише за наявності бібліотеки 'keyboard' (pip install keyboard) — якщо її не встановлено, лаунчер про це попередить, а решта функціоналу продовжить працювати як завжди.",

        "info.step8_title": "8. Статистика використання",
        "info.step8_text": "Біля кожної програми у списку 'Програми' тепер видно позначку '▶ N' — скільки разів цю програму реально було запущено через лаунчер (вручну, з набору, за розкладом чи в автозапуску). Це допомагає зрозуміти, який софт дійсно потрібен під рукою, а який давно не використовується і його можна прибрати зі списку.\n\nПовний графік по всіх програмах доступний у вкладці 'Налаштування' — кнопка '📊 Переглянути статистику...' відкриває окреме вікно з наочним графіком використання та кнопкою '🗑 Скинути всю статистику', якщо захочеться почати відлік заново.\n\nСкинути лічильник окремої програми можна і без цього вікна — правий клік по програмі → '🔄 Скинути лічильник запусків'.",

        "info.step9_title": "9. Кастомізація інтерфейсу та готові теми",
        "info.step9_part1": "Набрид стандартний колір? Ви можете завантажити готові стилі від спільноти! Для цього введіть в Google запит \"CustomTkinter-Themes\" або перейдіть за офіційним паком тем на GitHub за посиланням нижче:",
        "info.step9_link_text": "🔗 Відкрити CTkThemesPack на GitHub",
        "info.step9_part2": "Завантажений .json файл теми просто імпортуйте через кнопку '📁 Імпортувати .json' у вкладці Налаштувань.",

        "info.version_label": "Версія: {version}",
        "info.author_label": "Розробник: {author}",
        "info.version_details_unavailable_title": "Недоступно",
        "info.version_details_unavailable_text": "Властивості файлу доступні лише в зібраному .exe.\nПри запуску через Python цю інформацію показати неможливо.",

        # --- Кутова кнопка "..." (глобальне меню) ---
        "info.corner_menu_about_item": "ℹ️ Про програму",
        "info.about_window_title": "Про програму",
        "info.about_field_product": "Назва продукту",
        "info.about_field_description": "Опис",
        "info.about_field_version": "Версія",
        "info.about_field_internal_name": "Внутрішня назва",
        "info.about_field_filename": "Ім'я файлу",
        "info.about_field_developer": "Розробник",
        "info.about_field_license": "Ліцензія",
        "info.about_field_copyright": "Авторське право",
        "info.about_license_link_text": "🔗 Повний текст ліцензії PolyForm Noncommercial",
        "info.about_contact_text": "Пропозиції чи питання? Пишіть на:",
        "info.about_close_btn": "Закрити",
    },
    "en": {
        # --- Main window: tab switcher ---
        "main.tab_programs": "📱 Programs",
        "main.tab_presets": "⚙ Presets",
        "main.tab_schedule": "⏰ Schedule",
        "main.tab_settings": "🛠 Settings",
        "main.tab_info": "ℹ Help",

        # --- Main window: program list ---
        "main.category_label": "🏷 Category:",
        "main.category_all": "All",
        "main.category_unset": "No category",
        "main.manage_categories_btn": "🗑",
        "main.btn_add": "Add",
        "main.btn_launch": "Launch",
        "main.btn_delete": "Delete",
        "main.btn_full_exit": "❌ Exit the program completely",
        "main.empty_list": "✨ The list is empty...\n\nDrag file shortcuts here with your mouse\nor use the 'Add' button",
        "main.empty_category": "There are no programs in the «{category}» category yet.",

        # --- Program context menu ---
        "main.ctx_rename": "Rename '{name}'",
        "main.ctx_args": "⚙ Launch options...",
        "main.ctx_category": "🏷 Category...",
        "main.ctx_reset_stats": "🔄 Reset launch counter",
        "main.ctx_delete": "Remove from list",

        # --- Rename / args dialogs ---
        "main.rename_prompt": "Enter a new name for {name}:",
        "main.rename_title": "Rename",
        "main.args_title": "Launch options",
        "main.args_prompt_header": "Launch arguments for '{name}':\n",
        "main.args_prompt_current": "Current value: {args}\n",
        "main.args_prompt_hint": "Leave empty to remove the arguments (e.g. -windowed, or a URL for a browser).",

        # --- Program category dialog ---
        "main.category_dialog_title": "Program category",
        "main.category_dialog_label": "Category for «{name}»:",
        "main.category_dialog_placeholder": "Category name (new or existing)",
        "main.category_dialog_clear_hint": "An empty field removes the category.",
        "main.category_dialog_pick_hint": "Or pick from the existing ones:",
        "main.category_dialog_none_yet": "There are no categories yet — just type a new name above,\nit will be created automatically.",
        "main.category_dialog_save": "💾 Save",
        "main.category_dialog_cancel": "Cancel",

        # --- Manage categories dialog ---
        "main.manage_categories_title": "Manage categories",
        "main.manage_categories_header": "🏷 Manage categories",
        "main.manage_categories_hint": "Deleting a category doesn't delete the programs themselves —\nthey simply go back to «No category».",
        "main.manage_categories_empty": "There are no categories yet.\nYou can create one via\nright-click on a program -> \"🏷 Category...\"",
        "main.manage_categories_delete_btn": "🗑 Delete",
        "main.manage_categories_close": "Close",
        "main.delete_category_confirm_title": "Delete category",
        "main.delete_category_confirm_text": "Delete the «{category}» category?\n\nPrograms that had this category will become «No category».",

        # --- Tray ---
        "main.tray_open": "📱 Open launcher",
        "main.tray_exit": "❌ Exit completely",
        "main.already_running_title": "Program Launcher",
        "main.already_running_text": "The launcher is already running (or is still starting up).\n\nPlease wait — a second copy is not needed.",

        # ============== SETTINGS TAB ==============
        "settings.theme_label": "App visual theme:",
        "settings.color_label": "Color & font style (requires restart):",
        "settings.import_json": "📁 Import .json",
        "settings.theme_creator": "🎨 Theme constructor",
        "settings.reset_themes": "💥 Reset all custom themes",

        "settings.language_label": "Interface language (requires restart):",

        "settings.behavior_label": "Launcher behavior:",
        "settings.close_after_launch": "Close the launcher after launching programs",
        "settings.minimize_to_tray": "Minimize to background (tray) instead of closing on ❌",
        "settings.tray_hint": "The tray is the icon next to the Windows clock. Enable it so the\nschedule keeps working after the window is closed.",
        "settings.windows_autostart": "Automatically start the launcher when Windows starts",
        "settings.smart_launch": "🧠 Smart launch: don't reopen a program that's already running",
        "settings.smart_launch_hint": "Before launching, the launcher checks the list of running processes\n(via psutil) and skips a program that's already open — so repeated\nclicks or schedule triggers don't spawn extra windows.",

        "settings.delay_label": "Delay between launching programs: {seconds} sec.",

        "settings.hotkeys_label": "⌨️ Hotkeys:",
        "settings.hotkeys_hint": "Showing the launcher window from the tray and instantly launching\nindividual presets without opening the window — all key combos\nare gathered and edited in one place.",
        "settings.hotkeys_btn": "🎹 Manage hotkeys...",
        "settings.hotkeys_missing_lib": "⚠ The 'keyboard' library was not found — hotkeys won't work.\nInstall it with: pip install keyboard",

        "settings.stats_label": "📊 Usage statistics:",
        "settings.stats_hint": "How many times each program was actually launched through the\nlauncher — so you can see which software you really use.",
        "settings.stats_btn": "📊 View statistics...",

        "settings.backup_label": "📦 Configuration backup:",
        "settings.backup_create": "💾 Create backup (ZIP)",
        "settings.backup_restore": "📂 Restore from backup",

        "settings.restart_btn": "🔄 Restart the program",
        "settings.restart_error": "The restart function was not provided.",
        "settings.error_title": "Error",

        # ============== PRESETS TAB ==============
        "presets.section_create_title": "Create a new set of programs",
        "presets.name_placeholder": "Enter a name (e.g.: Work, Games)",
        "presets.save_new_btn": "💾 Save new set",
        "presets.section_manage_title": "Your saved sets",
        "presets.none_created": "No sets created",
        "presets.autostart_checkbox": "🚀 Startup set: launch this set right away when the launcher opens",
        "presets.launch_btn": "🚀 Launch set",
        "presets.stop_btn": "⛔ Close set",
        "presets.delete_btn": "❌ Delete this set",
        "presets.error_invalid_name": "Enter a valid name for the set!",
        "presets.error_no_programs": "Select at least one program for the set!",
        "presets.success_title": "Success",
        "presets.success_created": "Set '{name}' successfully created!",
        "presets.delete_confirm_title": "Deletion",
        "presets.delete_confirm_text": "Are you sure you want to delete the set '{name}'?",
        "presets.empty_no_programs": "There are no programs added on the 'Programs' tab yet.",

        # ============== SCHEDULE TAB ==============
        "schedule.title": "⏰ Schedule and days settings",
        "schedule.days_from": "Days: from",
        "schedule.days_to": "to",
        "schedule.day_mon": "Monday",
        "schedule.day_tue": "Tuesday",
        "schedule.day_wed": "Wednesday",
        "schedule.day_thu": "Thursday",
        "schedule.day_fri": "Friday",
        "schedule.day_sat": "Saturday",
        "schedule.day_sun": "Sunday",
        "schedule.time_label": "Launch time (HH:MM):",
        "schedule.what_label": "What to launch:",
        "schedule.type_program": "Program",
        "schedule.type_preset": "Set (Preset)",
        "schedule.target_label": "Choose target:",
        "schedule.no_programs_yet": "Add programs first",
        "schedule.add_btn": "➕ Add to schedule",
        "schedule.current_list_title": "Current schedule:",
        "schedule.programs_list_empty": "Program list is empty",
        "schedule.create_preset_first": "Create at least one set first",
        "schedule.tasks_empty": "No tasks",
        "schedule.bg_worker_error": "Schedule background thread error: {error}",

        # ============== THEME CREATOR WINDOW ==============
        "theme_creator.window_title": "Flexible theme builder",
        "theme_creator.target_buttons": "Buttons",
        "theme_creator.target_window_bg": "Window background",
        "theme_creator.target_frames_bg": "Frames background",
        "theme_creator.target_entries": "Text fields",
        "theme_creator.target_checks_switches": "Checkboxes/Switches",
        "theme_creator.target_text": "Text",
        "theme_creator.mode_both": "Both",
        "theme_creator.mode_dark_only": "Dark only",
        "theme_creator.mode_light_only": "Light only",
        "theme_creator.name_label": "Theme name (in English):",
        "theme_creator.name_placeholder": "e.g.: mega_style",
        "theme_creator.preview_label": "Preview:",
        "theme_creator.preview_sample_label": "Sample text (Label)",
        "theme_creator.preview_entry_placeholder": "Input field...",
        "theme_creator.preview_entry_text": "Text in field",
        "theme_creator.preview_checkbox": "Checkbox",
        "theme_creator.preview_switch": "Switch",
        "theme_creator.preview_button": "Sample button",
        "theme_creator.target_select_label": "Choose an element to edit:",
        "theme_creator.main_color_label": "Main color (RGB):",
        "theme_creator.hover_color_label": "Hover color (RGB):",
        "theme_creator.main_color_buttons_label": "Buttons main color (RGB):",
        "theme_creator.element_color_label": "Color of '{element}' (RGB):",
        "theme_creator.save_btn": "💾 Save theme and apply",
        "theme_creator.error_empty_name": "Enter a theme name!",
        "theme_creator.error_save_failed": "Failed to save the theme: {error}",

        # ============== HOTKEY MANAGER DIALOG ==============
        "hotkeys.window_title": "Manage hotkeys",
        "hotkeys.missing_lib_warning": "⚠ The 'keyboard' library is not installed — hotkeys won't work until you install it.\nCommand: pip install keyboard",
        "hotkeys.show_window_title": "🖥 Show launcher window from tray",
        "hotkeys.show_window_hint": "Always triggers, even if the window is minimized.",
        "hotkeys.presets_title": "🚀 Instant preset launch",
        "hotkeys.presets_hint": "Launches the whole preset without opening the launcher window.",
        "hotkeys.no_presets": "There are no sets yet. Create a set on the 'Presets' tab\nso you can assign it a hotkey.",
        "hotkeys.hotkey_placeholder": "e.g.: ctrl+alt+l",
        "hotkeys.unavailable_title": "Unavailable",
        "hotkeys.unavailable_text": "The 'keyboard' library is not installed.\nInstall it with: pip install keyboard",
        "hotkeys.invalid_combo_title": "Invalid combination",
        "hotkeys.invalid_combo_text": "Could not recognize «{value}».\nExample: ctrl+alt+l",
        "hotkeys.done_title": "Done",
        "hotkeys.show_hotkey_set": "The hotkey «{hotkey}» now opens the launcher.",
        "hotkeys.show_hotkey_disabled": "The global hotkey for showing the window has been disabled.",
        "hotkeys.conflict_show_window": "showing the launcher window",
        "hotkeys.conflict_preset": "the set «{name}»",
        "hotkeys.conflict_title": "Combination already in use",
        "hotkeys.conflict_text": "The hotkey «{hotkey}» is already assigned to: {list}.\n\nYou can leave it as is, but BOTH actions will trigger at once.",
        "hotkeys.preset_hotkey_set": "The hotkey «{hotkey}» now launches the set «{name}».",
        "hotkeys.preset_hotkey_removed": "The hotkey for the set «{name}» has been removed.",

        # ============== STATS DIALOG ==============
        "stats.window_title": "Usage statistics",
        "stats.chart_title": "📊 How many times each program was launched",
        "stats.hint": "Only counts real launches through the launcher — from the 'Programs' list, from sets, by schedule, or on autostart. Helps you see which software you actually need and which you can remove from the list.",
        "stats.reset_all_btn": "🗑 Reset all statistics",
        "stats.reset_confirm_title": "Reset statistics",
        "stats.reset_confirm_text": "Reset the launch counters for ALL programs?\nThis action cannot be undone.",

        # ============== SETTINGS: autostart / backup / theme import ==============
        "settings.autostart_error_title": "Autostart",
        "settings.autostart_error_text": "Failed to change the setting in the Windows registry: {error}",
        "settings.autostart_read_error": "Autostart: failed to read the path from the registry: {error}",
        "settings.autostart_path_updated": "Autostart: the registry path was outdated and has been updated to '{path}'.",
        "settings.autostart_update_error": "Autostart: failed to update the outdated path in the registry: {error}",
        "settings.backup_title": "Backup",
        "settings.backup_nothing_to_backup": "There are no saved settings or schedules to back up!",
        "settings.zip_filter_label": "ZIP Archive",
        "settings.backup_save_dialog_title": "Save backup as...",
        "settings.backup_created": "Backup of settings and schedule successfully created!",
        "settings.backup_create_failed": "Failed to create the backup file: {error}",
        "settings.backup_open_dialog_title": "Choose a backup file",
        "settings.restore_confirm_title": "Restore",
        "settings.restore_confirm_text": "Current settings, schedule, and sets will be completely replaced with data from the archive. Continue?",
        "settings.backup_extract_failed": "Failed to extract the data: {error}",
        "settings.backup_invalid": "The backup file is corrupted or has an invalid format.\n{details}\n\nRestore canceled, current data was not changed.",
        "settings.restore_success": "Configuration restored! Click the restart button to apply the changes.",
        "settings.backup_apply_failed": "Failed to apply the backup data: {error}",
        "settings.backup_file_not_json": "The file '{filename}' is not valid JSON ({error})",
        "settings.backup_file_read_failed": "Failed to read the file '{filename}' ({error})",
        "settings.backup_file_bad_structure": "The file '{filename}' has an unexpected data structure",
        "settings.theme_created": "Theme '{name}' created! Click the restart button.",
        "settings.theme_file_filter_label": "CustomTkinter Theme",
        "settings.import_success": "Imported themes: {count} ({names}).\nRestart the launcher to apply the selected one.",
        "settings.import_partial_title": "Partially imported",
        "settings.import_partial_text": "Successfully imported ({success_count}): {names}.\n\nFailed to import ({fail_count}):\n{errors}\n\nRestart the launcher to apply the selected theme.",
        "settings.import_all_failed": "No theme could be imported:\n{errors}",
        "settings.theme_file_not_json": "The file is not valid JSON ({error})",
        "settings.theme_file_read_failed": "Failed to read the file ({error})",
        "settings.theme_file_empty": "The file is empty or has an invalid structure (a JSON object is expected)",
        "settings.theme_file_not_theme": "The file doesn't look like a CustomTkinter theme (expected style keys are missing)",
        "settings.reset_themes_confirm_title": "Reset",
        "settings.reset_themes_confirm_text": "Are you sure you want to delete ALL custom and imported themes?",
        "settings.reset_themes_done_text": "Custom themes deleted! The default style has been applied.",
        "settings.reset_themes_error": "Error clearing themes: {error}",
        "settings.stats_unavailable_title": "Unavailable",
        "settings.stats_unavailable_text": "The program list is unavailable — try restarting the launcher.",
        "settings.save_error": "Error saving settings: {error}",
        "settings.load_error": "Error loading settings: {error}",

        # ============== INFO TAB ==============
        "info.window_title": "ℹ️About & Instructions",
        "info.about_title": "🚀 What is this app?",
        "info.about_text": "This is your personal flexible launcher for automating routine tasks.\n\nIt lets you group programs, games, or scripts into presets, schedule automatic launches by day of week and time, run software with your own command-line arguments, and start everything you need with one click or on a schedule.",
        "info.guide_label": "📖 Step-by-step guide",

        "info.step1_title": "1. Managing programs (Drag & Drop)",
        "info.step1_text": "On the 'Programs' tab you can manage individual shortcuts.\n\n• Just drag files (.exe, .lnk, .bat) with your mouse into the launcher window — they'll be added automatically.\n• You can also use the 'Add' button.\n• Right-clicking any program opens a context menu for renaming, deleting, configuring '⚙ Launch options' — your own command-line arguments (e.g. -windowed for a game, or a URL for a browser) — or assigning a '🏷 Category...' to group similar programs. Programs with set arguments are marked with an ⚙ icon in the list.",

        "info.step2_title": "2. Creating sets (Presets)",
        "info.step2_text": "Go to the 'Presets' tab to combine software into groups.\n\nCheck the boxes for the programs you want on the main screen, enter a name for the new set, and click 'Save new set'. Now you can launch the whole group of programs at once with the 'Launch set' button, or forcibly close all their processes with the 'Close set' button.\n\nTo have one of the sets launch right away when the launcher opens — select it in the list and enable the '🚀 Startup set' checkbox. Only one set can autostart at a time: enabling it for a new set automatically disables it for the previous one.",

        "info.step3_title": "3. Program categories (grouping & filtering)",
        "info.step3_text": "So a long list of programs doesn't turn into endless scrolling, each program can be assigned a category — an arbitrary tag like 'Work', 'Games', or 'Design'.\n\nRight-click a program → '🏷 Category...' — type a new name or pick one already created from the list. An empty field removes the category, and the program goes back to 'No category'.\n\nAbove the program list there's a '🏷 Category' dropdown — picking a name there shows only programs in that category; the 'All' option shows the full list again.\n\nThe 🗑 button next to the filter opens the category management window, where you can delete a category you no longer need. Deleting a category doesn't delete the programs themselves — they simply go back to 'No category'.",

        "info.step4_title": "4. Automation & Task Schedule",
        "info.step4_text": "The 'Schedule' tab lets you automatically launch software at a set time.\n\nChoose a range of days (e.g. from Monday to Friday), specify the exact time (HH:MM), choose the target type (a single program or a whole preset), and click 'Add to schedule'. The program runs in the background and will launch the software at exactly the specified minute.",

        "info.step5_title": "5. Delay, Smart Close, and Smart Launch",
        "info.step5_text": "If your PC struggles with launching many programs at once, go to 'Settings' and set the launch delay slider (in seconds).\n\nThe 'Close the launcher after launching programs' option automatically shuts down the launcher once it has done its job.\n\nThe '🧠 Smart launch' option checks the list of running processes before starting and skips a program if it's already open — so repeated clicks or schedule triggers don't spawn extra windows. It's not 100% accurate for shortcuts (.lnk) if their name differs from the process name.",

        "info.step6_title": "6. Working in the system tray",
        "info.step6_text": "In 'Settings' there's a toggle 'Minimize to background (tray) instead of closing on ❌'.\n\nIf it's enabled, clicking the regular window 'X' doesn't close the app completely — it hides it in the tray (next to the clock), so the schedule keeps working in the background. If it's disabled, the 'X' immediately closes the launcher completely.\n\nTo exit completely regardless of this toggle, use the '❌ Exit the program completely' button at the bottom of the launcher, or right-click the tray icon.",

        "info.step7_title": "7. Global hotkeys",
        "info.step7_text": "The 'Settings' tab has a '🎹 Manage hotkeys...' button — the single place where all the launcher's key combinations are gathered and edited.\n\n• One combination (e.g. Ctrl+Alt+L) instantly opens the launcher's main window from the tray, even if it's minimized or not focused.\n• Each set (preset) can be assigned its own combination to launch it directly, without opening the window at all.\n\nTo set a key — click 🎙 and immediately press the desired combination on your keyboard, or type it in manually (e.g. ctrl+alt+1), then save with 💾. This feature only works if the 'keyboard' library is installed (pip install keyboard) — if it's not, the launcher will warn you about it, and the rest of the functionality will keep working as usual.",

        "info.step8_title": "8. Usage statistics",
        "info.step8_text": "Next to each program in the 'Programs' list you'll now see a '▶ N' mark — how many times that program was actually launched through the launcher (manually, from a set, by schedule, or on autostart). This helps you see which software you really need at hand, and which hasn't been used in a while and can be removed from the list.\n\nA full chart for all programs is available on the 'Settings' tab — the '📊 View statistics...' button opens a separate window with a visual usage chart and a '🗑 Reset all statistics' button if you want to start counting over.\n\nYou can also reset an individual program's counter without this window — right-click the program → '🔄 Reset launch counter'.",

        "info.step9_title": "9. Interface customization & ready-made themes",
        "info.step9_part1": "Tired of the default colors? You can download ready-made styles from the community! Just search Google for \"CustomTkinter-Themes\" or go to the official theme pack on GitHub using the link below:",
        "info.step9_link_text": "🔗 Open CTkThemesPack on GitHub",
        "info.step9_part2": "Simply import the downloaded theme .json file using the '📁 Import .json' button on the Settings tab.",

        "info.version_label": "Version: {version}",
        "info.author_label": "Developer: {author}",
        "info.version_details_unavailable_title": "Unavailable",
        "info.version_details_unavailable_text": "File properties are only available in the built .exe.\nThis information can't be shown when running through Python.",

        # --- Corner "..." button (global menu) ---
        "info.corner_menu_about_item": "ℹ️ About the program",
        "info.about_window_title": "About the Program",
        "info.about_field_product": "Product Name",
        "info.about_field_description": "Description",
        "info.about_field_version": "Version",
        "info.about_field_internal_name": "Internal Name",
        "info.about_field_filename": "File Name",
        "info.about_field_developer": "Developer",
        "info.about_field_license": "License",
        "info.about_field_copyright": "Copyright",
        "info.about_license_link_text": "🔗 Full text of the PolyForm Noncommercial License",
        "info.about_contact_text": "Suggestions or questions? Contact:",
        "info.about_close_btn": "Close",
    },
}


_current_language = DEFAULT_LANGUAGE
_cache = {}  # {lang: {key: value}}


def _settings_file():
    return saves_path("settings.json")


def _ensure_locale_file(lang):
    """ Гарантує, що locales/<lang>.json існує і не порожній — якщо
    файлу немає чи він пошкоджений, (пере)створює його з вбудованих
    DEFAULT_STRINGS. Завдяки цьому файли перекладу можна редагувати
    вручну (додати мову, підправити фразу), а якщо їх випадково
    видалити — лаунчер сам відновить робочий варіант. """
    path = locales_path(f"{lang}.json")
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict) and data:
                return data
        except Exception:
            pass

    data = DEFAULT_STRINGS.get(lang, DEFAULT_STRINGS[DEFAULT_LANGUAGE])
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
    except Exception:
        # Не вдалося записати файл (немає прав тощо) — не критично,
        # користуємось вбудованим словником в оперативній пам'яті.
        pass
    return data


def _load(lang):
    if lang not in _cache:
        _cache[lang] = _ensure_locale_file(lang)
    return _cache[lang]


def available_languages():
    """ dict {код_мови: назва_мови для показу в списку}. """
    return dict(AVAILABLE_LANGUAGES)


def detect_saved_language():
    """ Читає обрану мову напряму з settings.json, в обхід SettingsManager
    (корисно для речей, що формуються ще до створення менеджерів —
    напр. заголовок вікна чи текст іконки трею). Якщо файл/ключ
    відсутні або мова невідома — повертає DEFAULT_LANGUAGE. """
    settings_file = _settings_file()
    if os.path.exists(settings_file):
        try:
            with open(settings_file, "r", encoding="utf-8") as f:
                st = json.load(f)
            lang = st.get("language", DEFAULT_LANGUAGE)
            if lang in AVAILABLE_LANGUAGES:
                return lang
        except Exception:
            pass
    return DEFAULT_LANGUAGE


def get_language():
    return _current_language


def set_language(lang):
    """ Перемикає поточну мову інтерфейсу (в оперативній пам'яті, на
    час роботи процесу). Сам вибір користувача зберігається окремо, у
    settings.json, через SettingsManager.save_settings() — так само,
    як тема чи затримка запуску. Щоб зміна мови реально відобразилась
    на вже побудованих віджетах, лаунчер потрібно перезапустити (як і
    при зміні кольорової теми). """
    global _current_language
    if lang in AVAILABLE_LANGUAGES:
        _current_language = lang


def t(key, **kwargs):
    """ Повертає переклад рядка інтерфейсу за ключем поточною мовою.
    Підстраховки, якщо ключа немає:
      1. пробуємо DEFAULT_LANGUAGE (англійську);
      2. якщо й там немає — повертаємо сам ключ, щоб інтерфейс не впав
         через відсутній чи забутий переклад.
    kwargs підставляються у рядок через str.format(), напр.:
        t("main.rename_prompt", name="Chrome") -> "Введіть нову назву для Chrome:"
    """
    strings = _load(_current_language)
    text = strings.get(key)
    if text is None and _current_language != DEFAULT_LANGUAGE:
        text = _load(DEFAULT_LANGUAGE).get(key)
    if text is None:
        text = key
    if kwargs:
        try:
            return text.format(**kwargs)
        except Exception:
            return text
    return text


# Мова визначається одразу при імпорті модуля, щоб усі частини
# лаунчера (навіть ті, що формують текст до створення SettingsManager,
# напр. заголовок вікна чи іконку трею) одразу бачили правильну мову.
set_language(detect_saved_language())
