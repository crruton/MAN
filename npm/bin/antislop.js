#!/usr/bin/env node
"use strict";

const fs = require("fs");
const os = require("os");
const path = require("path");

const SKILL = "anti-neuroslop";
const MANIFEST = ".man.json";
const PKG_ROOT = path.resolve(__dirname, "..", "..");
const SKILL_SRC = path.join(PKG_ROOT, "skills", SKILL);

const ok = "\u2713";
const arrow = "\u2192";
const warn = "!";
const err = "\u00d7";

function main(argv) {
  const [command, ...rest] = argv;
  const opts = parse(rest);

  if (!command || opts.help || command === "help") {
    printHelp();
    return 0;
  }
  try {
    switch (command) {
      case "install":
        return install(opts);
      case "uninstall":
        return uninstall(opts);
      case "doctor":
        return doctor();
      case "version":
        return version();
      default:
        console.error(`${err} неизвестная команда «${command}»`);
        printHelp();
        return 1;
    }
  } catch (e) {
    console.error(`${err} ${e.message}`);
    return 1;
  }
}

function parse(args) {
  const opts = { target: "auto", scope: "user", dir: null, force: false, dryRun: false };
  for (let i = 0; i < args.length; i++) {
    const arg = args[i];
    if (arg === "--force") opts.force = true;
    else if (arg === "--dry-run") opts.dryRun = true;
    else if (arg === "--help" || arg === "-h") opts.help = true;
    else if (arg === "--target") opts.target = args[++i];
    else if (arg === "--scope") opts.scope = args[++i];
    else if (arg === "--dir") opts.dir = args[++i];
    else if (arg.startsWith("--target=")) opts.target = arg.split("=")[1];
    else if (arg.startsWith("--scope=")) opts.scope = arg.split("=")[1];
    else if (arg.startsWith("--dir=")) opts.dir = arg.split("=")[1];
    else throw new Error(`неизвестный аргумент «${arg}»`);
  }
  return opts;
}

function agents() {
  const home = os.homedir();
  const cwd = process.cwd();
  return [
    { key: "claude", title: "Claude Code", user: path.join(home, ".claude", "skills"), project: path.join(cwd, ".claude", "skills"), config: path.join(home, ".claude") },
    { key: "opencode", title: "OpenCode", user: path.join(home, ".config", "opencode", "skills"), project: path.join(cwd, ".opencode", "skills"), config: path.join(home, ".config", "opencode") },
    { key: "codex", title: "Codex", user: path.join(home, ".codex", "skills"), project: path.join(cwd, ".codex", "skills"), config: path.join(home, ".codex") },
  ];
}

function resolveTargets(opts) {
  if (opts.dir) return [path.resolve(opts.dir)];
  let chosen;
  if (opts.target === "all") chosen = agents();
  else if (opts.target === "auto") {
    const found = agents().filter((a) => fs.existsSync(a.config));
    chosen = found.length ? found : [agents()[0]];
  } else {
    chosen = agents().filter((a) => a.key === opts.target);
    if (!chosen.length) throw new Error(`неизвестная цель «${opts.target}»`);
  }
  if (opts.scope === "project") return chosen.map((a) => a.project);
  if (opts.scope === "user") return chosen.map((a) => a.user);
  throw new Error("scope должен быть user или project");
}

function install(opts) {
  if (!fs.existsSync(path.join(SKILL_SRC, "SKILL.md"))) {
    throw new Error(`в пакете нет папки skills/${SKILL}. Установите через скрипт: https://github.com/crruton/MAN#установка`);
  }
  const version = readVersion(SKILL_SRC);
  const targets = resolveTargets(opts);
  for (const dest of targets) {
    const target = path.join(dest, SKILL);
    console.log(`${arrow} Цель: ${target}`);
    if (fs.existsSync(target)) {
      if (!opts.force) {
        throw new Error(`скилл уже установлен в ${target}. Обновите с --force или удалите: uninstall`);
      }
      if (!fs.existsSync(path.join(target, "SKILL.md"))) {
        throw new Error(`${target} не похож на скилл: нет SKILL.md`);
      }
      if (!opts.dryRun) fs.rmSync(target, { recursive: true, force: true });
    }
    if (opts.dryRun) {
      console.log(`${ok} будет установлено: ${target} (${version})`);
      continue;
    }
    fs.mkdirSync(dest, { recursive: true });
    fs.cpSync(SKILL_SRC, target, { recursive: true });
    writeManifest(target, version);
    console.log(`${ok} установлено: ${target} (${version})`);
  }
  if (!opts.dryRun) {
    console.log("\nЧто дальше:");
    console.log("  • Claude Code: /anti-neuroslop или «проверь текст на нейрослоп»");
    console.log("  • OpenCode, Codex: «перепиши, чтобы не пахло GPT»");
    console.log("  • Проверить установку: antislop doctor");
  }
  return 0;
}

function uninstall(opts) {
  const targets = resolveTargets(opts);
  let removed = 0;
  for (const dest of targets) {
    const target = path.join(dest, SKILL);
    if (!fs.existsSync(target)) continue;
    const manifestPath = path.join(target, MANIFEST);
    if (fs.existsSync(manifestPath)) {
      if (!opts.dryRun) {
        const manifest = JSON.parse(fs.readFileSync(manifestPath, "utf8"));
        for (const rel of manifest.files || []) {
          const file = path.resolve(target, rel);
          if (file.startsWith(path.resolve(target) + path.sep) && fs.existsSync(file)) {
            fs.unlinkSync(file);
          }
        }
        fs.rmSync(target, { recursive: true, force: true });
      }
      console.log(`${ok} ${opts.dryRun ? "будет удалено" : "удалено"}: ${target}`);
      removed++;
    } else if (opts.force) {
      if (!opts.dryRun) fs.rmSync(target, { recursive: true, force: true });
      console.log(`${ok} ${opts.dryRun ? "будет удалено" : "удалено"}: ${target}`);
      removed++;
    } else {
      throw new Error(`в ${target} нет манифеста установки. Повторите с --force`);
    }
  }
  if (!removed) console.log(`${warn} скилл не найден — удалять нечего`);
  return 0;
}

function doctor() {
  const rows = agents().map((a) => {
    const target = path.join(a.user, SKILL);
    return {
      agent: a.title,
      detected: fs.existsSync(a.config),
      version: fs.existsSync(target) ? installedVersion(target) : null,
      path: target,
    };
  });
  const width = Math.max(...rows.map((r) => r.agent.length), 5);
  console.log(`${"Агент".padEnd(width)}  Найден  Версия   Путь`);
  console.log("-".repeat(width + 8 + 9 + 8 + 40));
  for (const r of rows) {
    console.log(`${r.agent.padEnd(width)}  ${(r.detected ? "да" : "нет").padEnd(7)}  ${(r.version || "—").padEnd(8)} ${r.path}`);
  }
  console.log(`\nantislop ${readPkgVersion()} · Node ${process.version} · ${os.type()} ${os.release()} · ${os.arch()}`);
  if (!rows.some((r) => r.detected)) {
    console.log(`${warn} ни один агент не найден. Установите вручную: antislop install --dir <папка>`);
  }
  return 0;
}

function version() {
  console.log(`antislop ${readPkgVersion()}`);
  console.log(`Node ${process.version} · ${os.type()} ${os.release()} · ${os.arch()}`);
  console.log("Репозиторий: https://github.com/crruton/MAN");
  return 0;
}

function readPkgVersion() {
  try {
    return JSON.parse(fs.readFileSync(path.join(PKG_ROOT, "package.json"), "utf8")).version;
  } catch {
    return "unknown";
  }
}

function readVersion(dir) {
  try {
    const text = fs.readFileSync(path.join(dir, "SKILL.md"), "utf8");
    const match = text.match(/^\s{2}version:\s*(\S+)\s*$/m);
    return match ? match[1] : "unknown";
  } catch {
    return "unknown";
  }
}

function installedVersion(dir) {
  const manifest = path.join(dir, MANIFEST);
  if (fs.existsSync(manifest)) {
    try {
      return JSON.parse(fs.readFileSync(manifest, "utf8")).version || "unknown";
    } catch {
      return "unknown";
    }
  }
  return readVersion(dir);
}

function writeManifest(target, version) {
  const files = [];
  const walk = (dir) => {
    for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
      const full = path.join(dir, entry.name);
      if (entry.isDirectory()) walk(full);
      else if (entry.name !== MANIFEST) files.push(path.relative(target, full).split(path.sep).join("/"));
    }
  };
  walk(target);
  files.sort();
  const data = {
    skill: SKILL,
    version,
    installed_at: new Date().toISOString().replace(/\.\d{3}Z$/, "Z"),
    source: "https://github.com/crruton/MAN",
    files,
  };
  fs.writeFileSync(path.join(target, MANIFEST), JSON.stringify(data, null, 2) + "\n", "utf8");
}

function printHelp() {
  console.log(`antislop — установщик скилла MAN (My Anti-Neuroslop)

Использование:
  antislop install [--target auto|all|claude|opencode|codex] [--scope user|project] [--dir PATH] [--force] [--dry-run]
  antislop uninstall [--target ...] [--scope ...] [--dir PATH] [--force]
  antislop doctor
  antislop version

Примеры:
  npx github:crruton/MAN install
  npx github:crruton/MAN install --target all
  npx github:crruton/MAN doctor`);
}

process.exitCode = main(process.argv.slice(2));
