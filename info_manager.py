import os
import sys
import customtkinter as ctk
import webbrowser
from tkinter import Menu

from locale_manager import t

APP_VERSION = "2.0 (Localization Update)"
APP_AUTHOR = "YumekoDeVil(Inna Varchenko)"

# --- Дані, що відповідають version_info.txt (StringFileInfo) ---
# Дублюються тут вручну, бо version_info.txt читається лише PyInstaller
# під час збірки .exe і не доступний як файл під час роботи програми
# (ані в dev-режимі, ані у зібраному .exe). Якщо version_info.txt
# змінюється перед новою збіркою — не забудьте оновити ці значення теж,
# щоб вікно "Про програму" не розійшлось з реальними метаданими .exe.
VERSION_INFO = {
    "product_name": "Program Launcher",
    "file_description": "Program Launcher",
    "file_version": "2.0.0.0",
    "internal_name": "ProgramLauncher",
    "original_filename": "ProgramLauncher.exe",
    "developer": "YumekoDeVil (Inna Varchenko)",
    "copyright": "© 2026 YumekoDeVil (Inna Varchenko)",
}

# Ліцензія та контакти — так само як GitHub-посилання у кроці 9
# інструкції (info.step9_link_text), не залежать від мови інтерфейсу,
# тому зберігаються як константи, а не ключі локалізації.
# Продубльовано в поле 'Comments' у version_info.txt, щоб та сама
# інформація була видна і у властивостях зібраного .exe у Провіднику
# Windows — якщо міняєте одне, оновіть і друге.
LICENSE_NAME = "PolyForm Noncommercial License 1.0.0"
LICENSE_URL = "https://polyformproject.org/licenses/noncommercial/1.0.0"
CONTACT_EMAIL = "devilyumeko42@gmail.com"


def _launcher_icon_path():
    """ Шлях до того самого assets/launcher.ico, що й іконка головного
    вікна/трею (див. resource_path() у ProgramLauncherStart.py) —
    продубльовано тут окремо, бо info_manager.py має власний __file__ і
    не імпортує resource_path() з головного скрипта. Логіка ідентична:
    у зібраному .exe PyInstaller розпаковує --add-data ресурси в
    sys._MEIPASS, у dev-режимі беремо теку поруч із файлами лаунчера. """
    base_path = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base_path, "assets", "launcher.ico")


def show_about_window(master):
    """ Невелике акуратно оформлене вікно "Про програму" з даними, що
    відповідають version_info.txt (VERSION_INFO вище) — назва продукту,
    опис, версія, внутрішня назва, ім'я файлу, розробник, копірайт. """
    win = ctk.CTkToplevel(master)
    win.title(t("info.about_window_title"))
    win.resizable(False, False)
    win.transient(master)

    def _apply_icon():
        try:
            win.iconbitmap(_launcher_icon_path())
        except Exception:
            # Немає файлу іконки, або .ico некоректний — тихо лишаємо
            # іконку за замовчуванням, це не критично
            pass

    # CTkToplevel на Windows скидає іконку на дефолтну одразу після
    # створення вікна (відомий нюанс customtkinter) — тому застосовуємо
    # її одразу І ще раз з невеликою затримкою, щоб перекрити цей скид.
    _apply_icon()
    win.after(200, _apply_icon)

    container = ctk.CTkFrame(win, fg_color="transparent")
    container.pack(fill="both", expand=True, padx=22, pady=20)

    title_lbl = ctk.CTkLabel(
        container, text=f"🚀 {VERSION_INFO['product_name']}", font=(None, 17, "bold")
    )
    title_lbl.pack(anchor="w", pady=(0, 2))

    version_sub = ctk.CTkLabel(
        container, text=f"v{VERSION_INFO['file_version']}", font=(None, 12), text_color="gray"
    )
    version_sub.pack(anchor="w", pady=(0, 14))

    card = ctk.CTkFrame(container)
    card.pack(fill="x")

    fields = [
        (t("info.about_field_product"), VERSION_INFO["product_name"]),
        (t("info.about_field_description"), VERSION_INFO["file_description"]),
        (t("info.about_field_version"), VERSION_INFO["file_version"]),
        (t("info.about_field_internal_name"), VERSION_INFO["internal_name"]),
        (t("info.about_field_filename"), VERSION_INFO["original_filename"]),
        (t("info.about_field_developer"), VERSION_INFO["developer"]),
        (t("info.about_field_license"), LICENSE_NAME),
    ]

    for i, (label_text, value_text) in enumerate(fields):
        row = ctk.CTkFrame(card, fg_color="transparent")
        row.pack(
            fill="x", padx=14,
            pady=(12 if i == 0 else 5, 12 if i == len(fields) - 1 else 0),
        )

        name_lbl = ctk.CTkLabel(
            row, text=label_text, font=(None, 11), text_color="gray",
            anchor="w", width=130,
        )
        name_lbl.pack(side="left")

        val_lbl = ctk.CTkLabel(
            row, text=value_text, font=(None, 12, "bold"),
            anchor="w", justify="left", wraplength=190,
            text_color=["#003F6C", "#E5E9F0"],
        )
        val_lbl.pack(side="left", fill="x", expand=True)

    # --- Ліцензія (клікабельне посилання на повний текст) ---
    license_link_lbl = ctk.CTkLabel(
        container,
        text=t("info.about_license_link_text"),
        font=(None, 11, "underline"),
        text_color=["#0066cc", "#4da6ff"],
        cursor="hand2",
    )
    license_link_lbl.pack(anchor="w", pady=(14, 0))
    license_link_lbl.bind("<Button-1>", lambda e: webbrowser.open(LICENSE_URL))
    license_link_lbl.bind(
        "<Enter>", lambda e: license_link_lbl.configure(text_color=["#004499", "#99ccff"])
    )
    license_link_lbl.bind(
        "<Leave>", lambda e: license_link_lbl.configure(text_color=["#0066cc", "#4da6ff"])
    )

    # --- Контакт для пропозицій / питань (клікабельний mailto) ---
    contact_row = ctk.CTkFrame(container, fg_color="transparent")
    contact_row.pack(anchor="w", pady=(6, 0), fill="x")

    contact_text_lbl = ctk.CTkLabel(
        contact_row, text=t("info.about_contact_text"), font=(None, 11), text_color="gray"
    )
    contact_text_lbl.pack(side="left")

    contact_email_lbl = ctk.CTkLabel(
        contact_row,
        text=CONTACT_EMAIL,
        font=(None, 11, "underline"),
        text_color=["#0066cc", "#4da6ff"],
        cursor="hand2",
    )
    contact_email_lbl.pack(side="left", padx=(4, 0))
    contact_email_lbl.bind("<Button-1>", lambda e: webbrowser.open(f"mailto:{CONTACT_EMAIL}"))
    contact_email_lbl.bind(
        "<Enter>", lambda e: contact_email_lbl.configure(text_color=["#004499", "#99ccff"])
    )
    contact_email_lbl.bind(
        "<Leave>", lambda e: contact_email_lbl.configure(text_color=["#0066cc", "#4da6ff"])
    )

    copyright_lbl = ctk.CTkLabel(
        container, text=VERSION_INFO["copyright"], font=(None, 10), text_color="gray"
    )
    copyright_lbl.pack(pady=(14, 0))

    close_btn = ctk.CTkButton(
        container, text=t("info.about_close_btn"), command=win.destroy, width=130
    )
    close_btn.pack(pady=(16, 0))

    # Центруємо відносно головного вікна лаунчера, а не в довільному
    # місці екрану
    win.update_idletasks()
    try:
        mx, my = master.winfo_rootx(), master.winfo_rooty()
        mw, mh = master.winfo_width(), master.winfo_height()
        ww, wh = win.winfo_width(), win.winfo_height()
        x = mx + (mw - ww) // 2
        y = my + (mh - wh) // 2
        win.geometry(f"+{max(x, 0)}+{max(y, 0)}")
    except Exception:
        pass

    win.lift()
    win.focus_force()


def create_corner_menu_button(row_parent, root=None):
    """ Створює маленьку іконку-кнопку "⋮" (три вертикальні крапки —
    класичний "kebab menu" з браузерів чи інших нативних застосунків)
    і пакує її ЗЛІВА у вже наявний рядок (row_parent) — той самий
    рядок, де стоїть перемикач вкладок (CTkSegmentedButton). Викликач
    (ProgramLauncherStart.py) відповідає за те, щоб row_parent був
    контейнером з layout `pack(side="left", ...)` для дітей, і щоб сам
    перемикач вкладок пакувався в нього ПІСЛЯ цього виклику з
    `side="left", fill="x", expand=True`, щоб зайняти залишок ширини.

    Це навмисно НЕ окремий рядок і НЕ .place() з жорсткими пікселями —
    обидва попередні варіанти або накладались на вкладки, або
    "з'їдали" зайвий рядок висоти й опускали весь інтерфейс. Тут кнопка
    просто перший елемент у тому ж рядку, що й вкладки — нічого нижче
    не зсувається, і на будь-якій ширині вікна вона лишається точно
    зліва від "Програми".

    root: вікно/віджет для контекстного меню та вікна "Про програму"
    (Menu і CTkToplevel потребують посилання на toplevel). Якщо не
    передано — визначається автоматично через row_parent.winfo_toplevel().

    Клік по кнопці відкриває невелике контекстне меню (як правою
    кнопкою миші). Наразі в ньому лише один пункт — "Про програму" з
    даними з version_info.txt, — але сюди легко додати ще пункти
    пізніше через menu.add_command(...). """
    root = root or row_parent.winfo_toplevel()

    btn = ctk.CTkButton(
        row_parent,
        text="⋮",
        width=22,
        height=22,
        font=(None, 17, "bold"),
        fg_color="transparent",
        hover_color=("gray80", "gray30"),
        border_width=0,
        corner_radius=11,
        text_color=("gray15", "gray92"),
        anchor="center",
    )
    btn.pack(side="left", padx=(0, 4))

    menu = Menu(root, tearoff=0)
    menu.add_command(
        label=t("info.corner_menu_about_item"),
        command=lambda: show_about_window(root),
    )

    def _open_menu():
        x = btn.winfo_rootx()
        y = btn.winfo_rooty() + btn.winfo_height() + 2
        try:
            menu.tk_popup(x, y)
        finally:
            menu.grab_release()

    btn.configure(command=_open_menu)
    return btn


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
        version_label.pack(side="left", padx=(10, 4))

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
