import customtkinter as ctk
import webbrowser


class InfoManager(ctk.CTkFrame):
    def __init__(self, master, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self.create_widgets()

    def _make_responsive(self, container, label, label_padx=12):
        """ Прив'язує wraplength підпису (label) до РЕАЛЬНОЇ ширини його
        безпосереднього контейнера (container), а не до наближеної оцінки
        ширини всієї вкладки. Це набагато надійніше за один загальний
        розрахунок "ширина вкладки мінус приблизний відступ", бо тут ми
        отримуємо від Tkinter точну виділену ширину контейнера, яка вже
        враховує всі вкладені відступи, скролбар CTkScrollableFrame тощо.

        Додатково ділимо на поточний коефіцієнт масштабування CTk
        (widget_scaling, залежить від DPI-масштабу Windows — 100%, 125%,
        150% тощо), бо CTkLabel.configure(wraplength=...) сам множить
        передане значення на цей коефіцієнт. Якщо не скомпенсувати —
        на будь-якому масштабі, відмінному від 100%, wraplength вийде
        більшим за реально доступний простір, і текст перестане переноситись. """

        def _on_container_resize(event):
            scaling = ctk.ScalingTracker.get_widget_scaling(label) or 1
            usable = event.width - (label_padx * 2)
            new_width = max(int(usable / scaling), 150)
            label.configure(wraplength=new_width)

        container.bind("<Configure>", _on_container_resize)

    def create_widgets(self):
        # Головний заголовок вікна
        title_label = ctk.CTkLabel(self, text="ℹ️Про програму та інструкція", font=(None, 18, "bold"))
        title_label.pack(pady=(15, 15), anchor="w", padx=10)

        # Картка "Що це за додаток"
        about_box = ctk.CTkFrame(self)
        about_box.pack(pady=(0, 15), fill="x", padx=5)

        about_title = ctk.CTkLabel(about_box, text="🚀 Що це за додаток?", font=(None, 13, "bold"))
        about_title.pack(pady=(8, 4), padx=12, anchor="w")

        about_text = (
            "Це ваш персональний гнучкий лаунчер для автоматизації рутини.\n\n"
            "Він дозволяє групувати програми, ігри чи скрипти у пресети, "
            "налаштовувати автоматичний запуск за днями тижня та часом, "
            "запускати софт з власними аргументами командного рядка "
            "і запускати все необхідне в один клік або за розкладом."
        )
        about_desc = ctk.CTkLabel(about_box, text=about_text, wraplength=420, justify="left", anchor="w", font=(None, 12))
        about_desc.pack(pady=(0, 12), padx=12, anchor="w", fill="x")
        self._make_responsive(about_box, about_desc)

        # Скрол-панель для кроків інструкції
        scroll_frame = ctk.CTkScrollableFrame(self, label_text="📖 Покрокове керівництво")
        scroll_frame.pack(pady=5, fill="both", expand=True)

        # Крок 1: Головний екран та Drag & Drop
        self.add_step(
            scroll_frame,
            "1. Керування програмами (Drag & Drop)",
            "На вкладці 'Програми' ви можете керувати окремими ярликами.\n\n"
            "• Просто перетягніть файли (.exe, .lnk, .bat) мишкою у вікно лаунчера — вони додадуться автоматично.\n"
            "• Також можна скористатися кнопкою 'Додати'.\n"
            "• Правий клік по будь-якій програмі відкриває контекстне меню для перейменування, видалення, "
            "налаштування '⚙ Параметри запуску' — власних аргументів командного рядка "
            "(наприклад, -windowed для гри або посилання на сайт для браузера) — "
            "або призначення '🏷 Категорія...' для групування схожих програм. "
            "Програми з заданими аргументами позначаються значком ⚙ у списку."
        )

        # Крок 2: Набори (Пресет-менеджер)
        self.add_step(
            scroll_frame,
            "2. Створення наборів (Пресетів)",
            "Перейдіть у вкладку 'Набори', щоб об'єднати софт у групи.\n\n"
            "Виберіть галочками потрібні програми на головному екрані, введіть назву для нового набору та "
            "натисніть 'Зберегти новий набір'. Тепер ви зможете запустити всю групу програм одночасно "
            "кнопкою 'Запустити набір' або примусово завершити всі їх процеси кнопкою 'Закрити набір'.\n\n"
            "Щоб один із наборів запускався одразу при відкритті лаунчера — оберіть його у списку та "
            "увімкніть чекбокс '🚀 Стартовий набір'. Автозапуск завжди лише в одного набору: увімкнення "
            "для нового автоматично вимикає його в попереднього."
        )

        # Крок 3: Категорії програм
        self.add_step(
            scroll_frame,
            "3. Категорії програм (групування та фільтр)",
            "Щоб довгий список програм не перетворювався на нескінченний скрол, кожній програмі можна "
            "призначити категорію — довільну назву-тег на кшталт 'Робота', 'Ігри' чи 'Дизайн'.\n\n"
            "Правий клік по програмі → '🏷 Категорія...' — введіть нову назву або оберіть уже створену зі списку. "
            "Порожнє поле прибирає категорію, і програма повертається у стан 'Без категорії'.\n\n"
            "Над списком програм з'являється випадаючий список '🏷 Категорія' — обравши в ньому потрібну назву, "
            "ви побачите лише програми цієї категорії; пункт 'Всі' знову показує повний список.\n\n"
            "Кнопка 🗑 поруч із фільтром відкриває вікно керування категоріями, де можна видалити непотрібну "
            "категорію. Видалення категорії не видаляє самі програми — вони просто повертаються у 'Без категорії'."
        )

        # Крок 4: Планувальник та Розклад
        self.add_step(
            scroll_frame,
            "4. Автоматизація та Розклад завдання",
            "Вкладка 'Розклад' дозволяє автоматично запускати софт у визначений час.\n\n"
            "Виберіть діапазон днів (наприклад, з Понеділка по П'ятницю), вкажіть точний час (ГГ:ХХ), оберіть тип цілі (одиночна програма чи цілий пресет) та натисніть 'Додати до розкладу'. Програма працює у фоні та запустить софт точно у вказану хвилину."
        )

        # Крок 5: Налаштування, затримка та Розумний запуск
        self.add_step(
            scroll_frame,
            "5. Затримка, Розумне закриття та Розумний запуск",
            "Якщо ваш ПК важко переносить одночасний старт багатьох програм, зайдіть в 'Налаштування' та виставте повзунок затримки запуску (у секундах).\n\n"
            "Опція 'Закривати лаунчер після запуску програм' автоматично вимикає лаунчер, щойно він виконав свою роботу.\n\n"
            "Опція '🧠 Розумний запуск' перевіряє список запущених процесів перед стартом і пропускає програму, "
            "якщо вона вже відкрита — щоб не плодити зайві вікна при повторних кліках чи спрацюванні розкладу. "
            "Не працює зі 100% точністю для ярликів (.lnk), якщо їхня назва відрізняється від назви процесу."
        )

        # Крок 6: Трей
        self.add_step(
            scroll_frame,
            "6. Робота в системному треї",
            "У 'Налаштуваннях' є перемикач 'Не закривати, а згортати у фоновий режим (трей) при натисканні ❌'.\n\n"
            "Якщо він увімкнений — натискання на звичайний 'хрестик' вікна не закриває застосунок повністю, "
            "а ховає його в трей (біля годинника), щоб розклад продовжував працювати у фоні. "
            "Якщо вимкнений — хрестик одразу повністю закриває лаунчер.\n\n"
            "Для повного виходу незалежно від цього перемикача використовуйте кнопку "
            "'❌ Повний вихід з програми' внизу лаунчера або правий клік по іконці в треї."
        )

        # Крок 6 (З клікабельним посиланням на кастомізацію)
        self.add_customization_step(scroll_frame)

        # Підвал програми (Footer)
        footer_frame = ctk.CTkFrame(self, fg_color="transparent")
        footer_frame.pack(pady=(15, 0), fill="x")

        version_label = ctk.CTkLabel(footer_frame, text="Версія: 1.7.0 (Categories Update)", font=(None, 11),
                                     text_color="gray")
        version_label.pack(side="left", padx=10)

        # Ім'я розробника залишено оригінальним за вашим запитом
        author_label = ctk.CTkLabel(footer_frame, text="Розробник: YumekoDeVil(Inna Varchenko)", font=(None, 11),
                                    text_color="gray")
        author_label.pack(side="right", padx=10)

    def add_step(self, master, title, text):
        """ Шаблон для створення звичайного текстового кроку """
        box = ctk.CTkFrame(master)
        box.pack(pady=6, fill="x", padx=5)

        t_lbl = ctk.CTkLabel(box, text=title, font=(None, 13, "bold"), text_color=["#003F6C", "#E5E9F0"])
        t_lbl.pack(pady=(8, 6), padx=12, anchor="w")

        d_lbl = ctk.CTkLabel(box, text=text, wraplength=380, justify="left", anchor="w", font=(None, 12))
        d_lbl.pack(pady=(0, 12), padx=12, anchor="w", fill="x")
        self._make_responsive(box, d_lbl)

    def add_customization_step(self, master):
        """ Спеціальний крок для кастомізації з клікабельним лінком """
        box = ctk.CTkFrame(master)
        box.pack(pady=6, fill="x", padx=5)

        t_lbl = ctk.CTkLabel(box, text="7. Кастомізація інтерфейсу та готові теми", font=(None, 13, "bold"),
                             text_color=["#003F6C", "#E5E9F0"])
        t_lbl.pack(pady=(8, 6), padx=12, anchor="w")

        part1_text = (
            "Набрид стандартний колір? Ви можете завантажити готові стилі від спільноти! "
            "Для цього введіть в Google запит \"CustomTkinter-Themes\" або перейдіть за офіційним паком тем на GitHub за посиланням нижче:"
        )
        d_lbl1 = ctk.CTkLabel(box, text=part1_text, wraplength=380, justify="left", anchor="w", font=(None, 12))
        d_lbl1.pack(pady=(0, 6), padx=12, anchor="w", fill="x")
        self._make_responsive(box, d_lbl1)

        # КЛІКАБЕЛЬНЕ ПОСИЛАННЯ
        link_url = "https://github.com/a13xe/CTkThemesPack"
        link_label = ctk.CTkLabel(
            box,
            text="🔗 Відкрити CTkThemesPack на GitHub",
            font=(None, 12, "underline"),
            text_color=["#0066cc", "#4da6ff"],
            cursor="hand2"
        )
        link_label.pack(pady=(2, 8), padx=12, anchor="w")

        # Бінди кліку та ховерів
        link_label.bind("<Button-1>", lambda e: webbrowser.open(link_url))
        link_label.bind("<Enter>", lambda e: link_label.configure(text_color=["#004499", "#99ccff"]))
        link_label.bind("<Leave>", lambda e: link_label.configure(text_color=["#0066cc", "#4da6ff"]))

        part2_text = "Завантажений .json файл теми просто імпортуйте через кнопку '📁 Імпортувати .json' у вкладці Налаштувань."
        d_lbl2 = ctk.CTkLabel(box, text=part2_text, wraplength=380, justify="left", anchor="w", font=(None, 12))
        d_lbl2.pack(pady=(0, 12), padx=12, anchor="w", fill="x")
        self._make_responsive(box, d_lbl2)