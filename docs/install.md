# Установка

Скилл — это папка `anti-neuroslop` с файлом `SKILL.md`. Установка сводится к тому, чтобы положить её в папку, которую читает ваш агент. Способы ниже делают это по-разному, результат одинаковый.

## Что выбрать

| Условие | Способ |
|---|---|
| macOS или Linux, есть curl | скрипт `install.sh` |
| Windows, есть PowerShell | скрипт `install.ps1` |
| Windows, не хочется терминала | `MAN-Setup.exe` |
| Нет сети на машине | `tar.gz` или `zip` из Releases |
| Есть Python и нужен `doctor` | `pipx` или `uv` |
| Есть Node | `npx` |
| Claude Code | плагин или скрипт |
| Нестандартная папка скиллов | `--dir` или копирование вручную |

## Перед установкой

Проверьте, какие агенты есть на машине:

```bash
ls -d ~/.claude ~/.config/opencode ~/.codex 2>/dev/null
```

```powershell
Test-Path "$HOME\.claude", "$HOME\.config\opencode", "$HOME\.codex"
```

Скрипты ставят скилл во все найденные папки. Если не хотите ставить в какой-то агент, используйте `--target claude` (или `opencode`, `codex`).

## Скрипт для macOS и Linux

```bash
curl -fsSL https://raw.githubusercontent.com/crruton/MAN/main/scripts/install.sh | sh
```

Скрипт делает четыре шага:

1. Определяет домашнюю папку и установленных агентов.
2. Скачивает `man-skill.tar.gz` из последнего релиза.
3. Сверяет SHA256 с `SHA256SUMS.txt`.
4. Копирует скилл в папки скиллов.

Если релиза ещё нет, скрипт возьмёт ветку `main` и предупредит об этом.

Параметры передаются после `sh -s --`:

```bash
curl -fsSL https://raw.githubusercontent.com/crruton/MAN/main/scripts/install.sh \
  | sh -s -- --target all --force
```

| Параметр | Значение |
|---|---|
| `--target` | `auto`, `all`, `claude`, `opencode`, `codex` |
| `--scope` | `user` (по умолчанию) или `project` |
| `--dir` | своя папка, перекрывает target и scope |
| `--version` | тег релиза, например `v1.0.0` |
| `--force` | перезаписать установленную версию |
| `--uninstall` | удалить скилл |
| `--dry-run` | показать план без изменений |

Скачать скрипт и запустить локально тоже можно:

```bash
curl -fsSL -O https://raw.githubusercontent.com/crruton/MAN/main/scripts/install.sh
sh install.sh --target claude
```

## Скрипт для Windows

```powershell
irm https://raw.githubusercontent.com/crruton/MAN/main/scripts/install.ps1 -OutFile "$env:TEMP\man-install.ps1"
& "$env:TEMP\man-install.ps1"
```

Скрипт скачивается в файл и запускается оттуда. Так Windows PowerShell 5.1 читает кириллицу в сообщениях без искажений; при выполнении через `iex` метка порядка байтов в начале файла ломает разбор. PowerShell 7 читает UTF-8 и так, но команда одинаково работает в обеих версиях.

Если PowerShell блокирует выполнение, разрешите его для текущего процесса:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
& "$env:TEMP\man-install.ps1"
```

Параметры:

```powershell
& "$env:TEMP\man-install.ps1" -Target all
& "$env:TEMP\man-install.ps1" -Scope project
& "$env:TEMP\man-install.ps1" -Dir C:\skills
& "$env:TEMP\man-install.ps1" -Force
& "$env:TEMP\man-install.ps1" -Uninstall
```

Скрипт скачивает архив, проверяет SHA256 через `Get-FileHash`, распаковывает через `tar` (входит в Windows 10 и 11) и копирует папку.

## MAN-Setup.exe

Скачайте `MAN-Setup.exe` со страницы [Releases](https://github.com/crruton/MAN/releases) и запустите.

Что происходит:

1. Установщик показывает список найденных агентов.
2. Спрашивает подтверждение, по умолчанию «да».
3. Распаковывает встроенный скилл и пишет `.man.json`.
4. Показывает, что делать дальше, и ждёт Enter.

Скилл встроен в `.exe`, поэтому интернет не нужен. Размер около 35 КБ, зависимость — .NET Framework 4.x.

Тихий режим для скриптов и развёртывания:

```powershell
.\MAN-Setup.exe --yes
.\MAN-Setup.exe --target all --yes
.\MAN-Setup.exe --dir C:\skills --yes
.\MAN-Setup.exe --uninstall --yes
```

Windows SmartScreen может предупредить о неизвестном издателе: файл не подписан сертификатом. Проверьте SHA256 по `SHA256SUMS.txt` из релиза.

## Архивы tar.gz и zip

```bash
curl -L -O https://github.com/crruton/MAN/releases/latest/download/man-skill.tar.gz
curl -L -O https://github.com/crruton/MAN/releases/latest/download/SHA256SUMS.txt
sha256sum -c SHA256SUMS.txt
mkdir -p ~/.claude/skills
tar -xz -C ~/.claude/skills -f man-skill.tar.gz
```

```powershell
Invoke-WebRequest -Uri https://github.com/crruton/MAN/releases/latest/download/man-skill.zip -OutFile man-skill.zip
Get-FileHash man-skill.zip -Algorithm SHA256
Expand-Archive .\man-skill.zip -DestinationPath "$HOME\.claude\skills" -Force
```

Внутри архива одна папка `anti-neuroslop`. Распаковывать нужно в папку скиллов, а не в её подпапку.

## pipx и uv

Нужен Python 3.9 или новее.

```bash
pipx install "git+https://github.com/crruton/MAN.git#subdirectory=cli"
antislop install
```

```bash
uv tool install "git+https://github.com/crruton/MAN.git#subdirectory=cli"
antislop install
```

Команды `antislop`:

| Команда | Что делает |
|---|---|
| `antislop install` | ставит в найденные агенты |
| `antislop install --target all` | ставит во все три |
| `antislop install --dir PATH` | ставит в свою папку |
| `antislop install --source PATH` | берёт файлы из локальной папки |
| `antislop install --force` | обновляет |
| `antislop uninstall` | удаляет по манифесту |
| `antislop doctor` | показывает агентов и версии |
| `antislop version` | версия CLI и окружение |

`antislop install` скачивает последний релиз и проверяет SHA256. Запуск из клона репозитория использует локальные файлы.

## npx

Нужен Node 18 или новее.

```bash
npx github:crruton/MAN install
npx github:crruton/MAN install --target all
npx github:crruton/MAN doctor
npx github:crruton/MAN uninstall
```

Пакет не опубликован в реестр npm: `npx` собирает его из GitHub и берёт скилл из репозитория.

## Плагин Claude Code

```text
/plugin marketplace add crruton/MAN
/plugin install man@man
```

Плагин ставит скилл в управляемую Claude Code папку. Обновление — через `/plugin update man@man`.

## Вручную

```bash
git clone https://github.com/crruton/MAN.git
mkdir -p ~/.claude/skills
cp -R MAN/skills/anti-neuroslop ~/.claude/skills/
```

Для проекта:

```bash
mkdir -p .claude/skills
cp -R MAN/skills/anti-neuroslop .claude/skills/
```

## Корпоративные окружения

**Прокси.** Скрипты используют `curl`, `Invoke-WebRequest` и `urllib` — они уважают стандартные переменные `HTTPS_PROXY` и `HTTP_PROXY`. Для `pipx` и `npx` настройте прокси их обычными средствами.

**Офлайн.** Скачайте `man-skill.zip` на машине с сетью, перенесите файл и распакуйте вручную. `.exe` тоже работает без сети.

**Общая папка.** Если скиллы лежат в корпоративной папке, укажите её: `--dir /opt/company/skills`.

**Только проект.** `--scope project` не трогает домашнюю папку: скилл будет виден только в текущем репозитории.

## Обновление

```bash
antislop install --force
```

или тот же скрипт с `--force`. Обновление заменяет папку целиком, версия видна в `.man.json`.

## Удаление

```bash
antislop uninstall
```

```bash
curl -fsSL https://raw.githubusercontent.com/crruton/MAN/main/scripts/install.sh | sh -s -- --uninstall
```

```powershell
irm https://raw.githubusercontent.com/crruton/MAN/main/scripts/install.ps1 -OutFile "$env:TEMP\man-install.ps1"
& "$env:TEMP\man-install.ps1" -Uninstall
```

Вручную:

```bash
rm -rf ~/.claude/skills/anti-neuroslop
```

## Если что-то пошло не так

**`curl: command not found`.** Поставьте curl или скачайте архив вручную.

**`контрольная сумма не совпала`.** Файл скачался не полностью или подменён. Скачайте заново и сверьте SHA256 глазами.

**`Permission denied`.** Папка скиллов принадлежит другому пользователю. Используйте `--dir` с доступной папкой или `sudo` осознанно.

**PowerShell не запускает скрипт.** `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass` перед запуском.

**Скилл не появился в агенте.** Проверьте путь: `antislop doctor`. Перезапустите агент: список скиллов читается при старте.

**`скилл уже установлен`.** Добавьте `--force`.

**Антивирус удалил .exe.** Соберите установщик сами: `./installer/windows/build.ps1`, либо используйте скрипт или архив.
