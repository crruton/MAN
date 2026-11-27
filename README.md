# MAN — My Anti-Neuroslop

[![validate](https://github.com/crruton/MAN/actions/workflows/validate.yml/badge.svg)](https://github.com/crruton/MAN/actions/workflows/validate.yml)
[![release](https://github.com/crruton/MAN/actions/workflows/release.yml/badge.svg)](https://github.com/crruton/MAN/actions/workflows/release.yml)
[![license: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

Скилл для русских текстов: находит нейрослоп и переписывает его. Работает в Claude Code, OpenCode, Codex и любом агенте, который читает `SKILL.md`.

Нейрослоп — текст, в котором форма изображает смысл. Грамотный, гладкий, вежливый и пустой: читатель доходит до конца и не может сказать, что узнал. MAN показывает, где именно текст пустой, и возвращает в него содержание.

> **До:** Музей, расположенный в самом сердце города, играет ключевую роль в культурной жизни и представляет собой уникальное пространство, объединяющее прошлое и настоящее.
>
> **После:** Музей открылся в 1974 году в бывшем трамвайном депо. В зале 14 вагонов, включая вагон 1936 года: по субботам он выходит на кольцо вокруг парка.

## Что умеет

- **Контроль.** Разбор с таблицей маркеров, тестом подстановки и вердиктом: живой текст, зона внимания или слоп.
- **Замена.** Перепись от смысла к словам: тезис, разгон, обобщения, синтаксис, лексика, ритм, проверка фактов.
- **Файлы.** Правка прозы в репозитории: код, frontmatter, ссылки и цитаты остаются на месте.
- **Честность.** Скилл не выдумывает цифры: на месте недостающего факта появляется `[нужна цифра]` и вопрос автору.

Внутри 37 маркеров в пяти слоях, карта плотности ИИ-лексики, чек-лист из 10 пунктов и три разобранных примера. Подробнее — [docs/how-it-works.md](docs/how-it-works.md).

## Установка

Выберите любой способ. Все они ставят один и тот же скилл `anti-neuroslop`.

| Способ | Команда | Когда подходит |
|---|---|---|
| Скрипт, macOS и Linux | `curl -fsSL https://raw.githubusercontent.com/crruton/MAN/main/scripts/install.sh \| sh` | быстрее всего, ничего не нужно кроме curl |
| PowerShell, Windows | `irm https://raw.githubusercontent.com/crruton/MAN/main/scripts/install.ps1 -OutFile "$env:TEMP\man-install.ps1"; & "$env:TEMP\man-install.ps1"` | то же для Windows |
| Установщик `.exe` | скачать `MAN-Setup.exe` из [Releases](https://github.com/crruton/MAN/releases) и запустить | без терминала, работает офлайн |
| `tar.gz` | `curl -L .../man-skill.tar.gz \| tar -xz -C ~/.claude/skills` | офлайн, CI, свой путь |
| `zip` | распаковать `man-skill.zip` в папку скиллов | офлайн, Windows |
| pipx / uv | `pipx install "git+https://github.com/crruton/MAN.git#subdirectory=cli"` | есть Python, нужен `antislop doctor` |
| npx | `npx github:crruton/MAN install` | есть Node |
| Claude Code plugin | `/plugin marketplace add crruton/MAN` | Claude Code |
| Вручную | скопировать `skills/anti-neuroslop` | любой агент |

### Одна команда

macOS и Linux:

```bash
curl -fsSL https://raw.githubusercontent.com/crruton/MAN/main/scripts/install.sh | sh
```

Windows PowerShell:

```powershell
irm https://raw.githubusercontent.com/crruton/MAN/main/scripts/install.ps1 -OutFile "$env:TEMP\man-install.ps1"; & "$env:TEMP\man-install.ps1"
```

Скрипт сам находит установленных агентов и ставит скилл в личную папку. Если агентов несколько, ставит во все найденные. Если ни одного — в `~/.claude/skills`.

Параметры:

```bash
# во все агенты, даже если они не запускались
... | sh -s -- --target all

# только в проект, рядом с репозиторием
... | sh -s -- --scope project

# своя папка
... | sh -s -- --dir ./my-skills

# конкретный релиз
... | sh -s -- --version v1.0.0

# удалить
... | sh -s -- --uninstall
```

В PowerShell скрипт скачивается в файл и запускается оттуда: так Windows PowerShell 5.1 правильно читает кириллицу в сообщениях.

```powershell
irm https://raw.githubusercontent.com/crruton/MAN/main/scripts/install.ps1 -OutFile "$env:TEMP\man-install.ps1"
& "$env:TEMP\man-install.ps1" -Target all
& "$env:TEMP\man-install.ps1" -Scope project
& "$env:TEMP\man-install.ps1" -Dir C:\skills
& "$env:TEMP\man-install.ps1" -Force
& "$env:TEMP\man-install.ps1" -Uninstall
```

### MAN-Setup.exe

Скачайте `MAN-Setup.exe` со страницы [Releases](https://github.com/crruton/MAN/releases) и запустите двойным щелчком. Установщик покажет найденных агентов, спросит подтверждение и поставит скилл. Скилл встроен внутрь, интернет не нужен.

Тихая установка:

```powershell
.\MAN-Setup.exe --yes
.\MAN-Setup.exe --target all --yes
.\MAN-Setup.exe --dir C:\skills --yes
.\MAN-Setup.exe --uninstall
```

Файл весит около 35 КБ и использует .NET Framework 4.x, который стоит в Windows 10 и 11 по умолчанию.

### tar.gz и zip

Архивы лежат в [Releases](https://github.com/crruton/MAN/releases). Внутри папка `anti-neuroslop/` с готовым скиллом.

```bash
# macOS и Linux, личные скиллы Claude Code
mkdir -p ~/.claude/skills
curl -L https://github.com/crruton/MAN/releases/latest/download/man-skill.tar.gz \
  | tar -xz -C ~/.claude/skills

# проверить контрольную сумму
curl -L -O https://github.com/crruton/MAN/releases/latest/download/SHA256SUMS.txt
sha256sum -c SHA256SUMS.txt
```

```powershell
# Windows
Expand-Archive .\man-skill.zip -DestinationPath "$HOME\.claude\skills" -Force
```

### pipx и uv

```bash
pipx install "git+https://github.com/crruton/MAN.git#subdirectory=cli"
antislop install
antislop doctor
```

То же через uv:

```bash
uv tool install "git+https://github.com/crruton/MAN.git#subdirectory=cli"
antislop install --target all
```

`antislop` скачивает последний релиз, проверяет SHA256 и ставит скилл. Если запустить из клона репозитория, возьмёт файлы оттуда.

### npx

```bash
npx github:crruton/MAN install
npx github:crruton/MAN install --target all
npx github:crruton/MAN doctor
npx github:crruton/MAN uninstall
```

Пакет не опубликован в npm: `npx` ставит прямо из GitHub и берёт скилл из репозитория, без сети после скачивания.

### Claude Code plugin

```text
/plugin marketplace add crruton/MAN
/plugin install man@man
```

После установки скилл вызывается как `/anti-neuroslop` или срабатывает на фразы вроде «проверь текст на нейрослоп».

### Вручную

Скопируйте папку `skills/anti-neuroslop` в папку скиллов вашего агента:

```bash
git clone https://github.com/crruton/MAN.git
cp -R MAN/skills/anti-neuroslop ~/.claude/skills/
```

## Куда ставится

| Агент | Личные скиллы | Скиллы проекта |
|---|---|---|
| Claude Code | `~/.claude/skills/` | `.claude/skills/` |
| OpenCode | `~/.config/opencode/skills/` | `.opencode/skills/` |
| Codex | `~/.codex/skills/` | `.codex/skills/` |

Скилл — это папка `anti-neuroslop` с `SKILL.md` внутри. Другие агенты читают её так же: укажите свою папку через `--dir` или скопируйте вручную.

## Проверка и удаление

```bash
antislop doctor      # что найдено и какая версия стоит
antislop uninstall   # удалить отовсюду, где стоит
```

Без CLI:

```bash
curl -fsSL https://raw.githubusercontent.com/crruton/MAN/main/scripts/install.sh | sh -s -- --uninstall
```

```powershell
irm https://raw.githubusercontent.com/crruton/MAN/main/scripts/install.ps1 -OutFile "$env:TEMP\man-install.ps1"; & "$env:TEMP\man-install.ps1" -Uninstall
```

## Как пользоваться

Скилл включается сам, когда разговор заходит о качестве русского текста. Можно и явно:

```text
проверь этот текст на нейрослоп
перепиши, чтобы не пахло GPT
убери ИИ-штампы, оставь смысл
это писал ИИ? что здесь не так
```

Три режима:

- **Аудит** — «что не так с текстом». Диагноз, маркеры, вердикт.
- **Перепись** — «сделай нормально». Готовый текст и объяснение правок.
- **Файл** — «почисти README». Правка прозы с сохранением кода и разметки.

Пример запроса и ответа — [docs/usage.md](docs/usage.md), большой разбор — [examples/before-after.md](examples/before-after.md).

## Что внутри

```text
skills/anti-neuroslop/
├── SKILL.md              протокол: контекст, режимы, пять признаков, порядок переписи
├── agents/openai.yaml    описание для Codex
└── references/
    ├── katalog.md        37 маркеров в пяти слоях, с примерами до и после
    ├── leksika.md        карта плотности ИИ-лексики: красная, жёлтая, зелёная зоны
    ├── proverka.md       чек-лист, три теста, типичные ошибки правки
    └── primery.md        полный цикл на тексте музея и два коротких случая
```

## Документация

| Файл | О чём |
|---|---|
| [docs/install.md](docs/install.md) | все способы установки, прокси, офлайн, развёртывание, типичные ошибки |
| [docs/usage.md](docs/usage.md) | режимы работы, примеры запросов и ответов |
| [docs/how-it-works.md](docs/how-it-works.md) | маркеры, тесты, порядок переписи, границы метода |
| [docs/faq.md](docs/faq.md) | частые вопросы: детекторы, стиль, обновление, CI |
| [examples/before-after.md](examples/before-after.md) | полный разбор текста о приложении для учёта расходов |

## Разработка

```bash
python scripts/validate.py          # структура, ссылки, версии
python scripts/package.py           # dist/man-skill.tar.gz, zip, SHA256SUMS
./installer/windows/build.ps1       # dist/MAN-Setup.exe
```

Релиз собирается тегом:

```bash
git tag v1.0.0
git push origin v1.0.0
```

GitHub Actions проверит репозиторий, соберёт архивы и `.exe`, посчитает контрольные суммы и опубликует релиз.

Как добавить маркер или изменить протокол — [CONTRIBUTING.md](CONTRIBUTING.md).

## Лицензия

Код и тексты — [MIT](LICENSE) © 2026 Andrei Nosov.

Каталог маркеров опирается на описания признаков ИИ-текста в Википедии ([AI slop](https://en.wikipedia.org/wiki/AI_slop), [Signs of AI writing](https://en.wikipedia.org/wiki/Wikipedia:Signs_of_AI_writing), [Признаки сгенерированности текста](https://ru.wikipedia.org/wiki/Википедия:Признаки_сгенерированности_текста), CC BY-SA 4.0) (MIT). Формулировки и русские примеры написаны заново.
