# build.ps1
# Збирає ProgramLauncher.exe і одразу створює README.txt поруч з ним
# у dist\ProgramLauncher, з поясненням, які файли/папки не можна
# видаляти чи переносити окремо від .exe.

$ErrorActionPreference = "Stop"

pyinstaller --onedir --windowed --name ProgramLauncher `
  --collect-all customtkinter `
  --icon=assets\launcher.ico `
  --version-file=assets\version_info.txt `
  --add-data "assets\launcher.ico;assets" `
  ProgramLauncherStart.py

if ($LASTEXITCODE -ne 0) {
    Write-Host "PyInstaller завершився з помилкою — README не створюю." -ForegroundColor Red
    exit $LASTEXITCODE
}

$distDir = Join-Path $PSScriptRoot "dist\ProgramLauncher"
$readmePath = Join-Path $distDir "README.txt"

$readmeContent = @"
=======================================================
  Program Launcher — важлива інформація перед запуском
=======================================================

Не видаляйте і не переносьте окремо від ProgramLauncher.exe:

  - Папку "_internal"
      Тут лежать усі бібліотеки, потрібні програмі для роботи
      (Python, customtkinter, psutil тощо). Без неї .exe просто
      не запуститься.

Ці папки програма створює сама поруч із .exe при першому запуску —
вони НЕ входять до збірки, зʼявляться автоматично, і видаляти
їх також не варто (у них зберігаються ваші дані):

  - "jsons_saves"  — налаштування, список програм, набори (пресети),
                     розклад запуску та статистика запусків.
  - "themes"       — кольорові теми оформлення (вбудовані та імпортовані/
                     створені вами вручну).
  - "locales"      — файли перекладу інтерфейсу (uk.json, en.json тощо).

Якщо видалити будь-яку з цих трьох папок — вона буде створена
заново з порожніми/стандартними даними, а все, що в ній зберігалося
(ваші програми, набори, розклад, статистика, власні теми чи мову),
буде втрачено.

-------------------------------------------------------
Перенесення програми на інший диск чи в іншу теку:
-------------------------------------------------------
Можна вільно переносити ВЕСЬ вміст цієї теки (ProgramLauncher.exe,
"_internal", і три папки вище, якщо вони вже створені) — програма
сама знаходить свої дані відносно розташування .exe, тому нічого
додатково налаштовувати не потрібно.

-------------------------------------------------------
Ярлики:
-------------------------------------------------------
Якщо створюєте ярлик на ProgramLauncher.exe, переконайтесь, що поле
"Робоча папка" (Start in) вказує на цю ж саму теку — інакше програма
все одно знайде свої дані правильно (вона орієнтується на шлях .exe,
а не на робочу папку), але про всяк випадок краще лишати їх однаковими.


=======================================================
  Program Launcher — important information before use
=======================================================

Do not delete or move separately from ProgramLauncher.exe:

  - The "_internal" folder
      This holds all the libraries the program needs to run
      (Python, customtkinter, psutil, etc.). Without it the .exe
      simply won't start.

These folders are created automatically by the program next to the
.exe on first run — they are NOT part of the build itself, and
should not be deleted either (they store your data):

  - "jsons_saves"  — settings, program list, presets, launch
                     schedule, and launch statistics.
  - "themes"       — color/appearance themes (built-in and any you
                     imported or created yourself).
  - "locales"      — interface translation files (uk.json, en.json, etc.).

Deleting any of these three folders will cause it to be recreated
with empty/default data, and anything that was stored in it (your
programs, presets, schedule, stats, custom themes, or language)
will be lost.

-------------------------------------------------------
Moving the program to another drive or folder:
-------------------------------------------------------
You can freely move the ENTIRE contents of this folder
(ProgramLauncher.exe, "_internal", and the three folders above, if
already created) — the program locates its data relative to the
.exe's own path, so nothing else needs to be configured.

-------------------------------------------------------
Shortcuts:
-------------------------------------------------------
If you create a shortcut to ProgramLauncher.exe, make sure the
"Start in" field points to this same folder — the program will
still find its data correctly either way (it's based on the .exe's
path, not the working directory), but it's safer to keep them
matching just in case.
"@

Set-Content -Path $readmePath -Value $readmeContent -Encoding UTF8

Write-Host "README створено: $readmePath" -ForegroundColor Green
