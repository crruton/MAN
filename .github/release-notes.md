## MAN 1.0.0 — My Anti-Neuroslop

Скилл для русских текстов: находит нейрослоп и переписывает его. Работает в Claude Code, OpenCode, Codex и любом агенте, который читает `SKILL.md`.

### Что внутри

- 37 маркеров в пяти слоях: пустота, композиция, синтаксис, лексика, разметка.
- Карта плотности ИИ-лексики: красная, жёлтая и зелёная зоны.
- Протокол переписи от смысла к словам и чек-лист из 10 пунктов.
- Три режима: аудит, перепись, правка файла с сохранением кода и разметки.
- Разобранные примеры «до и после».

### Как установить

```bash
curl -fsSL https://raw.githubusercontent.com/crruton/MAN/main/scripts/install.sh | sh
```

```powershell
irm https://raw.githubusercontent.com/crruton/MAN/main/scripts/install.ps1 | iex
```

Другие способы: `MAN-Setup.exe`, архивы `man-skill.tar.gz` и `man-skill.zip`, `pipx`, `npx`, плагин Claude Code. Полная таблица — в [README](https://github.com/crruton/MAN#установка).

### Файлы релиза

| Файл | Что это |
|---|---|
| `MAN-Setup.exe` | установщик для Windows со встроенным скиллом, работает офлайн |
| `man-skill.tar.gz` | архив скилла для macOS и Linux |
| `man-skill.zip` | архив скилла для Windows |
| `install.sh`, `install.ps1` | те же установщики, что в репозитории |
| `SHA256SUMS.txt` | контрольные суммы всех файлов |

Проверка целостности:

```bash
sha256sum -c SHA256SUMS.txt
```
