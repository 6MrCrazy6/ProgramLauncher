import customtkinter as ctk
import webbrowser


class InfoManager(ctk.CTkFrame):
    def __init__(self, master, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self.create_widgets()

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
            "і запускати все необхідне в один клік або за розкладом."
        )
        about_desc = ctk.CTkLabel(about_box, text=about_text, wraplength=420, justify="left", font=(None, 12))
        about_desc.pack(pady=(0, 12), padx=12, anchor="w")

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
            "• Правий клік по будь-якій програмі відкриває контекстне меню для перейменування або видалення."
        )

        # Крок 2: Набори (Пресет-менеджер)
        self.add_step(
            scroll_frame,
            "2. Створення наборів (Пресетів)",
            "Перейдіть у вкладку 'Набори', щоб об'єднати софт у групи.\n\n"
            "Виберіть галочками потрібні програми на головному екрані, введіть назву для нового набору та натисніть 'Створити пресет'. Тепер ви зможете запустити всю групу програм одночасно. Один із пресетів можна призначити на автозапуск при старті лаунчера."
        )

        # Крок 3: Планувальник та Розклад
        self.add_step(
            scroll_frame,
            "3. Автоматизація та Розклад завдання",
            "Вкладка 'Розклад' дозволяє автоматично запускати софт у визначений час.\n\n"
            "Виберіть діапазон днів (наприклад, з Понеділка по П'ятницю), вкажіть точний час (ГГ:ХХ), оберіть тип цілі (одиночна програма чи цілий пресет) та натисніть 'Додати до розкладу'. Програма працює у фоні та запустить софт точно у вказану хвилину."
        )

        # Крок 4: Налаштування та затримка
        self.add_step(
            scroll_frame,
            "4. Налаштування затримки та Розумне закриття",
            "Якщо ваш ПК важко переносить одночасний старт багатьох програм, зайдіть в 'Налаштування' та виставте повзунок затримки запуску (у секундах).\n\n"
            "Тут також можна увімкнути опцію 'Закривати після запуску', щоб лаунчер автоматично вимикався після того, як виконає свою роботу."
        )

        # Крок 5: Трей
        self.add_step(
            scroll_frame,
            "5. Робота в системному треї",
            "При натисканні на звичайний 'хрестик' вікна додаток не закривається повністю, а ховається в трей (біля годинника), щоб успішно виконувати завдання за розкладом.\n\n"
            "Для повного виходу використовуйте кнопку 'Повний вихід з програми' внизу лаунчера або правий клік по іконці в треї."
        )

        # Крок 6 (З клікабельним посиланням на кастомізацію)
        self.add_customization_step(scroll_frame)

        # Підвал програми (Footer)
        footer_frame = ctk.CTkFrame(self, fg_color="transparent")
        footer_frame.pack(pady=(15, 0), fill="x")

        version_label = ctk.CTkLabel(footer_frame, text="Версія: 1.5.0 (Schedule & DND Update)", font=(None, 11),
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

        d_lbl = ctk.CTkLabel(box, text=text, wraplength=380, justify="left", font=(None, 12))
        d_lbl.pack(pady=(0, 12), padx=12, anchor="w")

    def add_customization_step(self, master):
        """ Спеціальний крок для кастомізації з клікабельним лінком """
        box = ctk.CTkFrame(master)
        box.pack(pady=6, fill="x", padx=5)

        t_lbl = ctk.CTkLabel(box, text="6. Кастомізація інтерфейсу та готові теми", font=(None, 13, "bold"),
                             text_color=["#003F6C", "#E5E9F0"])
        t_lbl.pack(pady=(8, 6), padx=12, anchor="w")

        part1_text = (
            "Набрид стандартний колір? Ви можете завантажити готові стилі від спільноти! "
            "Для цього введіть в Google запит \"CustomTkinter-Themes\" або перейдіть за офіційним паком тем на GitHub за посиланням нижче:"
        )
        d_lbl1 = ctk.CTkLabel(box, text=part1_text, wraplength=380, justify="left", font=(None, 12))
        d_lbl1.pack(pady=(0, 6), padx=12, anchor="w")

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
        d_lbl2 = ctk.CTkLabel(box, text=part2_text, wraplength=380, justify="left", font=(None, 12))
        d_lbl2.pack(pady=(0, 12), padx=12, anchor="w")