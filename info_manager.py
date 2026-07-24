import customtkinter as ctk
import webbrowser

from locale_manager import t

APP_VERSION = "2.0 (Localization Update)"
APP_AUTHOR = "YumekoDeVil(Inna Varchenko)"


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
        title_label = ctk.CTkLabel(self, text=t("info.window_title"), font=(None, 18, "bold"))
        title_label.pack(pady=(15, 15), anchor="w", padx=10)

        # Картка "Що це за додаток"
        about_box = ctk.CTkFrame(self)
        about_box.pack(pady=(0, 15), fill="x", padx=5)

        about_title = ctk.CTkLabel(about_box, text=t("info.about_title"), font=(None, 13, "bold"))
        about_title.pack(pady=(8, 4), padx=12, anchor="w")

        about_desc = ctk.CTkLabel(about_box, text=t("info.about_text"), wraplength=420, justify="left", anchor="w", font=(None, 12))
        about_desc.pack(pady=(0, 12), padx=12, anchor="w", fill="x")
        self._make_responsive(about_box, about_desc)

        # Скрол-панель для кроків інструкції
        scroll_frame = ctk.CTkScrollableFrame(self, label_text=t("info.guide_label"))
        scroll_frame.pack(pady=5, fill="both", expand=True)

        # Кроки 1-8: звичайні текстові блоки
        for i in range(1, 9):
            self.add_step(
                scroll_frame,
                t(f"info.step{i}_title"),
                t(f"info.step{i}_text"),
            )

        # Крок 9 (З клікабельним посиланням на кастомізацію)
        self.add_customization_step(scroll_frame)

        # Підвал програми (Footer)
        footer_frame = ctk.CTkFrame(self, fg_color="transparent")
        footer_frame.pack(pady=(15, 0), fill="x")

        version_label = ctk.CTkLabel(footer_frame, text=t("info.version_label", version=APP_VERSION), font=(None, 11),
                                     text_color="gray")
        version_label.pack(side="left", padx=10)

        # Ім'я розробника залишено оригінальним за вашим запитом
        author_label = ctk.CTkLabel(footer_frame, text=t("info.author_label", author=APP_AUTHOR), font=(None, 11),
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

        t_lbl = ctk.CTkLabel(box, text=t("info.step9_title"), font=(None, 13, "bold"),
                             text_color=["#003F6C", "#E5E9F0"])
        t_lbl.pack(pady=(8, 6), padx=12, anchor="w")

        d_lbl1 = ctk.CTkLabel(box, text=t("info.step9_part1"), wraplength=380, justify="left", anchor="w", font=(None, 12))
        d_lbl1.pack(pady=(0, 6), padx=12, anchor="w", fill="x")
        self._make_responsive(box, d_lbl1)

        # КЛІКАБЕЛЬНЕ ПОСИЛАННЯ
        link_url = "https://github.com/a13xe/CTkThemesPack"
        link_label = ctk.CTkLabel(
            box,
            text=t("info.step9_link_text"),
            font=(None, 12, "underline"),
            text_color=["#0066cc", "#4da6ff"],
            cursor="hand2"
        )
        link_label.pack(pady=(2, 8), padx=12, anchor="w")

        # Бінди кліку та ховерів
        link_label.bind("<Button-1>", lambda e: webbrowser.open(link_url))
        link_label.bind("<Enter>", lambda e: link_label.configure(text_color=["#004499", "#99ccff"]))
        link_label.bind("<Leave>", lambda e: link_label.configure(text_color=["#0066cc", "#4da6ff"]))

        d_lbl2 = ctk.CTkLabel(box, text=t("info.step9_part2"), wraplength=380, justify="left", anchor="w", font=(None, 12))
        d_lbl2.pack(pady=(0, 12), padx=12, anchor="w", fill="x")
        self._make_responsive(box, d_lbl2)
