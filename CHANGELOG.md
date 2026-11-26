# Changelog

Формат — [Keep a Changelog](https://keepachangelog.com/ru/1.1.0/), версии — [SemVer](https://semver.org/lang/ru/).

## [1.0.0] — 2026-11-26

### Добавлено

- Скилл `anti-neuroslop`: контроль и перепись нейрослопа в русских текстах.
- Каталог из 37 маркеров в пяти слоях с примерами «до и после».
- Карта плотности ИИ-лексики: красная, жёлтая и зелёная зоны.
- Чек-лист из 10 пунктов, три теста и разбор типичных ошибок переписи.
- Протокол правки файлов: код, frontmatter, ссылки и цитаты не трогаются.
- Установка семью способами: скрипты `install.sh` и `install.ps1`, `MAN-Setup.exe`, архивы `tar.gz` и `zip`, `pipx`/`uv`, `npx`, плагин Claude Code.
- CLI `antislop`: `install`, `uninstall`, `doctor`, `version`; проверка SHA256.
- Сборка релизов в GitHub Actions: архивы, `.exe`, контрольные суммы.
- Проверка репозитория `scripts/validate.py`: структура, ссылки, версии, нумерация каталога.

[1.0.0]: https://github.com/crruton/MAN/releases/tag/v1.0.0
