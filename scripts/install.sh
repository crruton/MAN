#!/bin/sh
# MAN — My Anti-Neuroslop. Установщик скилла для macOS и Linux.
# Использование: curl -fsSL https://raw.githubusercontent.com/crruton/MAN/main/scripts/install.sh | sh
set -eu

REPO="crruton/MAN"
SKILL="anti-neuroslop"
TARGET="auto"
SCOPE="user"
CUSTOM_DIR=""
VERSION=""
FORCE=0
DRY=0
UNINSTALL=0

usage() {
  cat <<'EOF'
MAN — My Anti-Neuroslop

Использование:
  install.sh [параметры]

Параметры:
  --target auto|all|claude|opencode|codex   куда ставить (по умолчанию auto)
  --scope user|project                      личные скиллы или скиллы проекта
  --dir PATH                                своя папка скиллов
  --version vX.Y.Z                          конкретный релиз
  --force                                   перезаписать установленную версию
  --uninstall                               удалить скилл
  --dry-run                                 показать план без изменений
  -h, --help                                эта справка

Примеры:
  curl -fsSL https://raw.githubusercontent.com/crruton/MAN/main/scripts/install.sh | sh
  curl -fsSL https://raw.githubusercontent.com/crruton/MAN/main/scripts/install.sh | sh -s -- --target all
EOF
}

say() { printf '%s\n' "$*"; }
ok() { printf '✓ %s\n' "$*"; }
warn() { printf '! %s\n' "$*" >&2; }
die() { printf '× %s\n' "$*" >&2; exit 1; }

while [ $# -gt 0 ]; do
  case "$1" in
    --target) TARGET="${2:-}"; shift 2 ;;
    --target=*) TARGET="${1#*=}"; shift ;;
    --scope) SCOPE="${2:-}"; shift 2 ;;
    --scope=*) SCOPE="${1#*=}"; shift ;;
    --dir) CUSTOM_DIR="${2:-}"; shift 2 ;;
    --dir=*) CUSTOM_DIR="${1#*=}"; shift ;;
    --version) VERSION="${2:-}"; shift 2 ;;
    --version=*) VERSION="${1#*=}"; shift ;;
    --force) FORCE=1; shift ;;
    --uninstall) UNINSTALL=1; shift ;;
    --dry-run) DRY=1; shift ;;
    -h|--help) usage; exit 0 ;;
    *) die "неизвестный параметр: $1" ;;
  esac
done

case "$TARGET" in auto|all|claude|opencode|codex) ;; *) die "target должен быть auto, all, claude, opencode или codex" ;; esac
case "$SCOPE" in user|project) ;; *) die "scope должен быть user или project" ;; esac

HOME_DIR="${HOME:-${USERPROFILE:-}}"
[ -n "$HOME_DIR" ] || die "не удалось определить домашнюю папку"

fetch() {
  url="$1"; dest="$2"
  if command -v curl >/dev/null 2>&1; then
    curl -fsSL --retry 3 -o "$dest" "$url"
  elif command -v wget >/dev/null 2>&1; then
    wget -q -O "$dest" "$url"
  else
    die "нужен curl или wget"
  fi
}

dest_for() {
  agent="$1"
  if [ -n "$CUSTOM_DIR" ]; then
    printf '%s' "$CUSTOM_DIR"
    return
  fi
  if [ "$SCOPE" = "project" ]; then
    case "$agent" in
      claude) printf '%s/.claude/skills' "$PWD" ;;
      opencode) printf '%s/.opencode/skills' "$PWD" ;;
      codex) printf '%s/.codex/skills' "$PWD" ;;
    esac
    return
  fi
  case "$agent" in
    claude) printf '%s/.claude/skills' "$HOME_DIR" ;;
    opencode) printf '%s/.config/opencode/skills' "$HOME_DIR" ;;
    codex) printf '%s/.codex/skills' "$HOME_DIR" ;;
  esac
}

if [ -n "$CUSTOM_DIR" ]; then
  AGENTS="custom"
elif [ "$TARGET" = "all" ]; then
  AGENTS="claude opencode codex"
elif [ "$TARGET" = "auto" ]; then
  AGENTS=""
  [ -d "$HOME_DIR/.claude" ] && AGENTS="$AGENTS claude"
  [ -d "$HOME_DIR/.config/opencode" ] && AGENTS="$AGENTS opencode"
  [ -d "$HOME_DIR/.codex" ] && AGENTS="$AGENTS codex"
  [ -n "$AGENTS" ] || AGENTS="claude"
else
  AGENTS="$TARGET"
fi

if [ "$UNINSTALL" -eq 1 ]; then
  for agent in $AGENTS; do
    dest="$(dest_for "$agent")"
    skill_dir="$dest/$SKILL"
    if [ ! -d "$skill_dir" ]; then
      warn "не найдено: $skill_dir"
      continue
    fi
    if [ -f "$skill_dir/SKILL.md" ] || [ "$FORCE" -eq 1 ]; then
      if [ "$DRY" -eq 1 ]; then
        ok "будет удалено: $skill_dir"
      else
        rm -rf "$skill_dir"
        ok "удалено: $skill_dir"
      fi
    else
      die "$skill_dir не похож на скилл: нет SKILL.md"
    fi
  done
  exit 0
fi

# Источник: локальный клон рядом со скриптом или релиз на GitHub.
SCRIPT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
LOCAL_SKILL="$SCRIPT_DIR/../skills/$SKILL"
TMP_DIR=""
cleanup() { if [ -n "$TMP_DIR" ]; then rm -rf "$TMP_DIR"; fi; return 0; }
trap cleanup EXIT INT TERM

if [ -f "$LOCAL_SKILL/SKILL.md" ]; then
  SKILL_SRC="$LOCAL_SKILL"
  say "→ Источник: локальный клон"
else
  TMP_DIR="$(mktemp -d)"
  if [ -n "$VERSION" ]; then
    BASE="https://github.com/$REPO/releases/download/$VERSION"
  else
    BASE="https://github.com/$REPO/releases/latest/download"
  fi
  if fetch "$BASE/man-skill.tar.gz" "$TMP_DIR/skill.tar.gz" 2>/dev/null; then
    if fetch "$BASE/SHA256SUMS.txt" "$TMP_DIR/SHA256SUMS.txt" 2>/dev/null; then
      expected="$(awk -v n="man-skill.tar.gz" '$2==n || $2=="*"n {print $1; exit}' "$TMP_DIR/SHA256SUMS.txt")"
      if [ -n "$expected" ]; then
        if command -v sha256sum >/dev/null 2>&1; then
          actual="$(sha256sum "$TMP_DIR/skill.tar.gz" | awk '{print $1}')"
        elif command -v shasum >/dev/null 2>&1; then
          actual="$(shasum -a 256 "$TMP_DIR/skill.tar.gz" | awk '{print $1}')"
        else
          actual=""
          warn "нет sha256sum/shasum: контрольная сумма не проверена"
        fi
        if [ -n "$actual" ] && [ "$actual" != "$expected" ]; then
          die "контрольная сумма не совпала"
        fi
      fi
    fi
    say "→ Источник: релиз ${VERSION:-latest}"
  else
    warn "релиз не найден, беру ветку main"
    fetch "https://codeload.github.com/$REPO/tar.gz/refs/heads/main" "$TMP_DIR/skill.tar.gz"
    say "→ Источник: ветка main"
  fi
  mkdir -p "$TMP_DIR/unpacked"
  tar -xzf "$TMP_DIR/skill.tar.gz" -C "$TMP_DIR/unpacked"
  found="$(find "$TMP_DIR/unpacked" -type f -path "*/$SKILL/SKILL.md" | head -n 1)"
  [ -n "$found" ] || die "в архиве не найден скилл $SKILL"
  SKILL_SRC="$(dirname "$found")"
fi

SKILL_VERSION="$(awk '/^  version:/{print $2; exit}' "$SKILL_SRC/SKILL.md" 2>/dev/null || true)"
[ -n "$SKILL_VERSION" ] || SKILL_VERSION="unknown"

for agent in $AGENTS; do
  dest="$(dest_for "$agent")"
  skill_dir="$dest/$SKILL"
  say "→ Цель: $skill_dir"
  if [ -d "$skill_dir" ]; then
    if [ "$FORCE" -eq 0 ]; then
      die "скилл уже установлен в $skill_dir. Обновите с --force или удалите с --uninstall"
    fi
    [ -f "$skill_dir/SKILL.md" ] || die "$skill_dir не похож на скилл: нет SKILL.md"
    [ "$DRY" -eq 1 ] || rm -rf "$skill_dir"
  fi
  if [ "$DRY" -eq 1 ]; then
    ok "будет установлено: $skill_dir"
    continue
  fi
  mkdir -p "$dest"
  cp -R "$SKILL_SRC" "$skill_dir"
  cat > "$skill_dir/.man.json" <<EOF
{
  "skill": "$SKILL",
  "version": "$SKILL_VERSION",
  "installed_at": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "source": "https://github.com/$REPO",
  "files": []
}
EOF
  ok "установлено: $skill_dir"
done

if [ "$DRY" -eq 0 ]; then
  say ""
  say "Что дальше:"
  say "  • Claude Code: /anti-neuroslop или «проверь текст на нейрослоп»"
  say "  • OpenCode, Codex: «перепиши, чтобы не пахло GPT»"
  say "  • Проверить установку: antislop doctor"
fi
