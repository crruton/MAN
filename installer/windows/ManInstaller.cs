using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.IO.Compression;
using System.Linq;
using System.Reflection;
using System.Text;
using System.Text.RegularExpressions;

namespace ManSetup
{
    internal sealed class Agent
    {
        public string Key;
        public string Title;
        public string ConfigDir;
        public string SkillsDir;

        public bool Detected
        {
            get { return Directory.Exists(ConfigDir); }
        }
    }

    internal static class Program
    {
        private const string SkillName = "anti-neuroslop";
        private const string ManifestName = ".man.json";
        private const string ResourceName = "MAN.payload.zip";
        private static readonly List<Agent> Agents = new List<Agent>();
        private static bool _interactive;

        private static int Main(string[] args)
        {
            try { Console.OutputEncoding = new UTF8Encoding(false); } catch { }

            string home = Environment.GetFolderPath(Environment.SpecialFolder.UserProfile);
            string cwd = Directory.GetCurrentDirectory();
            Agents.Add(new Agent { Key = "claude", Title = "Claude Code", ConfigDir = Path.Combine(home, ".claude"), SkillsDir = Path.Combine(home, ".claude", "skills") });
            Agents.Add(new Agent { Key = "opencode", Title = "OpenCode", ConfigDir = Path.Combine(home, ".config", "opencode"), SkillsDir = Path.Combine(home, ".config", "opencode", "skills") });
            Agents.Add(new Agent { Key = "codex", Title = "Codex", ConfigDir = Path.Combine(home, ".codex"), SkillsDir = Path.Combine(home, ".codex", "skills") });

            string target = "auto";
            string scope = "user";
            string dir = null;
            bool force = false;
            bool uninstall = false;
            bool yes = false;

            for (int i = 0; i < args.Length; i++)
            {
                string arg = args[i];
                switch (arg)
                {
                    case "--target": target = Next(args, ref i, arg); break;
                    case "--scope": scope = Next(args, ref i, arg); break;
                    case "--dir": dir = Next(args, ref i, arg); break;
                    case "--force": force = true; break;
                    case "--uninstall": uninstall = true; break;
                    case "--yes": case "-y": yes = true; break;
                    case "--help": case "-h": case "/?": PrintHelp(); return 0;
                    default:
                        if (arg.StartsWith("--target=")) target = arg.Substring(9);
                        else if (arg.StartsWith("--scope=")) scope = arg.Substring(8);
                        else if (arg.StartsWith("--dir=")) dir = arg.Substring(6);
                        else { return Fail("неизвестный аргумент: " + arg); }
                        break;
                }
            }

            _interactive = args.Length == 0 && !Console.IsInputRedirected;

            if (string.IsNullOrEmpty(dir) && target != "all" && target != "auto" && !Agents.Any(a => a.Key == target))
            {
                return Fail("неизвестная цель: " + target);
            }

            List<string> destinations = ResolveDestinations(target, scope, dir);
            if (destinations.Count == 0)
            {
                return Fail("не найдено ни одного агента. Укажите папку: MAN-Setup.exe --dir <путь>");
            }

            if (_interactive)
            {
                PrintHeader();
                PrintDetected();
                if (!uninstall && !yes)
                {
                    Console.Write("Установить во все найденные? [Y/n] ");
                    string answer = Console.ReadLine();
                    if (answer != null && answer.Trim().Length > 0 && !answer.Trim().Equals("y", StringComparison.OrdinalIgnoreCase) && !answer.Trim().Equals("yes", StringComparison.OrdinalIgnoreCase) && !answer.Trim().Equals("да", StringComparison.OrdinalIgnoreCase))
                    {
                        Console.WriteLine("Отменено.");
                        Pause();
                        return 0;
                    }
                }
            }

            int code = uninstall ? Uninstall(destinations, force) : Install(destinations, force);
            if (_interactive) Pause();
            return code;
        }

        private static string Next(string[] args, ref int index, string name)
        {
            if (index + 1 >= args.Length)
            {
                Error("после " + name + " нужен аргумент");
                Environment.Exit(1);
            }
            index++;
            return args[index];
        }

        private static List<string> ResolveDestinations(string target, string scope, string dir)
        {
            if (!string.IsNullOrEmpty(dir)) return new List<string> { Path.GetFullPath(dir) };

            IEnumerable<Agent> chosen;
            if (target == "all") chosen = Agents;
            else if (target == "auto")
            {
                var found = Agents.Where(a => a.Detected).ToList();
                chosen = found.Count > 0 ? found : new List<Agent> { Agents[0] };
            }
            else chosen = Agents.Where(a => a.Key == target);

            return chosen.Select(a =>
            {
                if (scope != "project") return a.SkillsDir;
                string folder = a.Key == "opencode" ? ".opencode" : "." + a.Key;
                return Path.Combine(Directory.GetCurrentDirectory(), folder, "skills");
            }).ToList();
        }

        private static int Install(List<string> destinations, bool force)
        {
            string version = ReadVersion();
            foreach (string dest in destinations)
            {
                string skillDir = Path.Combine(dest, SkillName);
                Console.WriteLine("→ Цель: " + skillDir);
                if (Directory.Exists(skillDir))
                {
                    if (!force)
                    {
                        return Fail("скилл уже установлен. Обновите с --force или удалите с --uninstall");
                    }
                    if (!File.Exists(Path.Combine(skillDir, "SKILL.md")))
                    {
                        return Fail(skillDir + " не похож на скилл: нет SKILL.md");
                    }
                    Directory.Delete(skillDir, true);
                }
                Directory.CreateDirectory(dest);
                ExtractSkill(skillDir);
                WriteManifest(skillDir, version);
                Console.WriteLine("✓ установлено: " + skillDir + " (" + version + ")");
            }
            Console.WriteLine();
            Console.WriteLine("Что дальше:");
            Console.WriteLine("  • Claude Code: /anti-neuroslop или «проверь текст на нейрослоп»");
            Console.WriteLine("  • OpenCode, Codex: «перепиши, чтобы не пахло GPT»");
            Console.WriteLine("  • Проверить установку: antislop doctor");
            return 0;
        }

        private static int Uninstall(List<string> destinations, bool force)
        {
            bool removed = false;
            foreach (string dest in destinations)
            {
                string skillDir = Path.Combine(dest, SkillName);
                if (!Directory.Exists(skillDir))
                {
                    Console.WriteLine("! не найдено: " + skillDir);
                    continue;
                }
                if (!File.Exists(Path.Combine(skillDir, "SKILL.md")) && !force)
                {
                    return Fail(skillDir + " не похож на скилл: нет SKILL.md");
                }
                Directory.Delete(skillDir, true);
                Console.WriteLine("✓ удалено: " + skillDir);
                removed = true;
            }
            if (!removed) Console.WriteLine("! удалять нечего");
            return 0;
        }

        private static void ExtractSkill(string skillDir)
        {
            using (Stream stream = Assembly.GetExecutingAssembly().GetManifestResourceStream(ResourceName))
            {
                if (stream == null)
                {
                    Error("в установщик не встроен скилл. Скачайте релиз заново.");
                    Environment.Exit(1);
                }
                using (var archive = new ZipArchive(stream, ZipArchiveMode.Read))
                {
                    string root = Path.GetFullPath(skillDir) + Path.DirectorySeparatorChar;
                    foreach (ZipArchiveEntry entry in archive.Entries)
                    {
                        string full = entry.FullName.Replace('\\', '/');
                        int slash = full.IndexOf('/');
                        if (slash < 0) continue;
                        string relative = full.Substring(slash + 1);
                        if (relative.Length == 0) continue;
                        string target = Path.GetFullPath(Path.Combine(skillDir, relative.Replace('/', Path.DirectorySeparatorChar)));
                        if (!target.StartsWith(root, StringComparison.OrdinalIgnoreCase))
                        {
                            Error("архив содержит небезопасный путь: " + entry.FullName);
                            Environment.Exit(1);
                        }
                        Directory.CreateDirectory(Path.GetDirectoryName(target));
                        entry.ExtractToFile(target, true);
                    }
                }
            }
        }

        private static string ReadVersion()
        {
            try
            {
                using (Stream stream = Assembly.GetExecutingAssembly().GetManifestResourceStream(ResourceName))
                using (var archive = new ZipArchive(stream, ZipArchiveMode.Read))
                {
                    ZipArchiveEntry entry = archive.Entries.FirstOrDefault(e => e.FullName.Replace('\\', '/').EndsWith("/SKILL.md", StringComparison.OrdinalIgnoreCase));
                    if (entry == null) return "unknown";
                    using (var reader = new StreamReader(entry.Open(), Encoding.UTF8))
                    {
                        string text = reader.ReadToEnd();
                        Match match = Regex.Match(text, @"^\s{2}version:\s*(\S+)\s*$", RegexOptions.Multiline);
                        return match.Success ? match.Groups[1].Value : "unknown";
                    }
                }
            }
            catch
            {
                return "unknown";
            }
        }

        private static void WriteManifest(string skillDir, string version)
        {
            var files = new List<string>();
            foreach (string path in Directory.GetFiles(skillDir, "*", SearchOption.AllDirectories))
            {
                string rel = path.Substring(skillDir.Length).TrimStart(Path.DirectorySeparatorChar).Replace('\\', '/');
                if (rel != ManifestName) files.Add(rel);
            }
            files.Sort();
            var builder = new StringBuilder();
            builder.AppendLine("{");
            builder.AppendLine("  \"skill\": \"" + SkillName + "\",");
            builder.AppendLine("  \"version\": \"" + version + "\",");
            builder.AppendLine("  \"installed_at\": \"" + DateTime.UtcNow.ToString("yyyy-MM-ddTHH:mm:ssZ", CultureInfo.InvariantCulture) + "\",");
            builder.AppendLine("  \"source\": \"https://github.com/crruton/MAN\",");
            builder.AppendLine("  \"files\": [");
            for (int i = 0; i < files.Count; i++)
            {
                builder.Append("    \"" + files[i] + "\"");
                builder.AppendLine(i == files.Count - 1 ? "" : ",");
            }
            builder.AppendLine("  ]");
            builder.AppendLine("}");
            File.WriteAllText(Path.Combine(skillDir, ManifestName), builder.ToString(), new UTF8Encoding(false));
        }

        private static void PrintHeader()
        {
            Console.WriteLine("MAN — My Anti-Neuroslop");
            Console.WriteLine("Скилл, который находит и переписывает нейрослоп в русских текстах.");
            Console.WriteLine();
        }

        private static void PrintDetected()
        {
            Console.WriteLine("Найдены агенты:");
            foreach (Agent agent in Agents)
            {
                Console.WriteLine("  " + (agent.Detected ? "✓" : "·") + " " + agent.Title + " — " + agent.SkillsDir);
            }
            Console.WriteLine();
        }

        private static void PrintHelp()
        {
            Console.WriteLine("MAN — My Anti-Neuroslop");
            Console.WriteLine();
            Console.WriteLine("Использование:");
            Console.WriteLine("  MAN-Setup.exe [--target auto|all|claude|opencode|codex] [--scope user|project]");
            Console.WriteLine("                [--dir PATH] [--force] [--uninstall] [--yes]");
            Console.WriteLine();
            Console.WriteLine("Без аргументов запускается мастер установки.");
        }

        private static void Pause()
        {
            if (!_interactive) return;
            Console.WriteLine();
            Console.Write("Нажмите Enter, чтобы закрыть окно…");
            Console.ReadLine();
        }

        private static void Error(string message)
        {
            Console.WriteLine("× " + message);
        }

        private static int Fail(string message)
        {
            Error(message);
            if (_interactive) Pause();
            return 1;
        }
    }
}
