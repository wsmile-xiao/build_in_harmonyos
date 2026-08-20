#!/usr/bin/env python3
"""Pre-compilation source code risk scanner.

Scans source tree against known OHOS/HMDFS/musl risk patterns
and produces a YAML report for AI-driven build planning.

Usage:
    python3 pre_scan.py <src_dir> [--rules <rules.yaml>] [--output <report.yaml>]
"""

import argparse
import os
import re
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    yaml = None

# ── Musl missing functions (high-frequency, from musl-glibc comparison) ──
# Key: function name, Value: severity
MUSL_MISSING = {
    "pthread_cancel": "critical",
    "mremap": "critical",
    "ppoll": "high",
    "secure_getenv": "medium",
    "pthread_kill": "medium",
    "backtrace": "medium",
    "backtrace_symbols": "medium",
    "memfrob": "low",
    "rawmemchr": "low",
    "getloadavg": "low",
    "malloc_trim": "low",
    "mallopt": "low",
    "mallinfo": "low",
    "error_at_line": "low",
    "obstack_": "medium",
    "register_printf": "low",
    "argp_": "medium",
}


_LOG_STDERR = False  # --json 模式下日志走 stderr，保持 stdout 纯 JSON


def _log(msg: str) -> None:
    print(f"  [pre-scan] {msg}", file=sys.stderr if _LOG_STDERR else sys.stdout, flush=True)


def _log_warn(msg: str) -> None:
    print(f"  [pre-scan] ⚠️ {msg}", file=sys.stderr if _LOG_STDERR else sys.stdout, flush=True)


# ═══════════════════════════════════════════════════════
# PreScanner
# ═══════════════════════════════════════════════════════

class PreScanner:
    """Scan source tree for OHOS build risks."""

    def __init__(self, src_dir: str, rules_path: str | None = None,
                 kb_dir: str | None = None, writeback: bool = True):
        self.src_dir = Path(src_dir)
        if not self.src_dir.is_dir():
            raise FileNotFoundError(f"源码目录不存在: {src_dir}")
        self.rules_path = Path(rules_path) if rules_path else None
        self.writeback = writeback
        self.yaml_rules = self._load_rules(rules_path)
        # KB 动态派生规则：知识库增长 → 扫描能力自动增长（v12.5）
        if kb_dir is None and self.rules_path is not None:
            kb_dir = str(self.rules_path.parent)  # 规则文件与 graph/*.kv 同目录
        self.kb_rules = self._load_kb_rules(kb_dir)
        self.rules = self.yaml_rules + self.kb_rules

    # ── Rules loading ──

    @staticmethod
    def _load_rules(rules_path: str | None) -> list[dict]:
        if not rules_path:
            return []
        p = Path(rules_path)
        if not p.exists():
            _log_warn(f"规则文件不存在: {rules_path}")
            return []
        if yaml:
            with open(p, encoding="utf-8") as f:
                data = yaml.safe_load(f)
            return data.get("rules", []) if data else []
        # Fallback: minimal YAML parsing (rules only)
        return PreScanner._parse_rules_fallback(p)

    @staticmethod
    def _parse_rules_fallback(path: Path) -> list[dict]:
        """Minimal YAML parser for rules when PyYAML unavailable."""
        rules = []
        current = None
        with open(path, encoding="utf-8") as f:
            for line in f:
                stripped = line.strip()
                if stripped.startswith("- id:"):
                    if current:
                        rules.append(current)
                    current = {"id": stripped.split(":", 1)[1].strip().strip("'\"")}
                elif current and ":" in stripped and not stripped.startswith("#"):
                    key, _, val = stripped.partition(":")
                    key = key.strip()
                    val = val.strip().strip("'\"")
                    if key in ("severity", "category", "description", "solution_hint",
                               "kb_ref", "check_type", "pattern"):
                        current[key] = val if val else None
                    elif key in ("auto_generated",):
                        current[key] = val.lower() == "true"
                    elif key in ("hit_count",):
                        current[key] = int(val) if val.isdigit() else 0
                    elif key in ("scope_globs", "check_targets"):
                        current[key] = [v.strip().strip("'\"") for v in val.strip("[]").split(",") if v.strip()]
        if current:
            rules.append(current)
        return rules

    # ── KB dynamic rule derivation (v12.5) ──

    _SEV_MAP = {"1": "low", "2": "medium", "3": "critical"}

    @staticmethod
    def _load_kb_rules(kb_dir: str | None) -> list[dict]:
        """从知识图谱 E*.kv 动态派生扫描规则（条目含 prescan_pattern 字段即生效）。

        新增知识条目无需改规则文件——在 .kv 中写 prescan_pattern 即可被扫描。
        不回写知识文件（保持知识库只读消费）。
        """
        if not kb_dir:
            return []
        gdir = Path(kb_dir)
        if not gdir.is_dir():
            return []
        rules = []
        for kvf in sorted(gdir.glob("E*.kv")):
            try:
                text = kvf.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue
            fields = {}
            for line in text.splitlines():
                if not line or line[:1] in (" ", "\t", "#"):
                    continue
                m = re.match(r"^(\w+):\s*(.*)$", line)
                if m and m.group(1) not in fields:
                    fields[m.group(1)] = m.group(2).strip()
            pat = fields.get("prescan_pattern", "").strip().strip("'\"")
            if not pat:
                continue
            sev_raw = fields.get("prescan_severity", "").strip()
            severity = sev_raw if sev_raw in ("critical", "high", "medium", "low", "info") \
                else PreScanner._SEV_MAP.get(fields.get("severity", "2").strip(), "medium")
            globs = [g.strip().strip("'\"") for g in
                     fields.get("prescan_globs", "*.c, *.h, *.cc, *.cpp, *.sh, Makefile*, *.mk").split(",")
                     if g.strip()]
            title = fields.get("title", "") or text.splitlines()[1] if len(text.splitlines()) > 1 else kvf.stem
            rules.append({
                "id": f"PSCAN-KB-{kvf.stem}",
                "category": "kb_derived",
                "severity": severity,
                "pattern": pat,
                "scope_globs": globs,
                "description": f"[KB] {str(title)[:70]}",
                "kb_ref": kvf.stem,
                "source": "knowledge_graph",
            })
        if rules:
            _log(f"知识库动态派生规则: {len(rules)} 条")
        return rules

    # ── Main scan ──

    def scan(self) -> dict:
        """Execute all rules and return report dict."""
        findings = []

        # Track patterns already covered by rules (avoid duplicates with musl scan)
        covered_patterns = set()

        # Rule-based scan
        for rule in self.rules:
            try:
                hits = self._apply_rule(rule)
            except Exception as e:
                _log_warn(f"规则 {rule.get('id', '?')} 执行失败: {e}")
                continue
            if hits:
                findings.append({
                    "rule_id": rule["id"],
                    "category": rule.get("category", ""),
                    "severity": rule.get("severity", "info"),
                    "description": rule.get("description", ""),
                    "hits": hits,
                    "kb_ref": rule.get("kb_ref"),
                    "solution_hint": rule.get("solution_hint"),
                    "auto_generated": rule.get("auto_generated", False),
                })
                # Track covered function names for dedup with musl scan
                if rule.get("category") == "musl_compat" and rule.get("pattern"):
                    # Extract word from pattern like '\bpthread_cancel\b'
                    m = re.search(r'\\b(\w+)\\b', rule["pattern"])
                    if m:
                        covered_patterns.add(m.group(1))

        # Musl function scan (always-on, from hardcoded list, deduplicated)
        musl_findings = self._scan_musl_functions(exclude=covered_patterns)
        findings.extend(musl_findings)

        metadata = self._collect_metadata()

        # v12.5: hit_count 闭环回填（只回写 yaml 手工规则；KB/auto 派生规则不写）
        if self.writeback and self.rules_path is not None:
            hit_rule_ids = {f["rule_id"] for f in findings if f.get("rule_id", "").startswith("PSCAN-")}
            try:
                self._writeback_hits(hit_rule_ids)
            except Exception as e:
                _log_warn(f"hit_count 回填失败（非阻塞）: {e}")

        return {
            "src_dir": str(self.src_dir),
            "findings": findings,
            "metadata": metadata,
            "summary": self._summarize(findings),
            "kb_rule_count": len(self.kb_rules),
        }

    def _writeback_hits(self, hit_rule_ids: set[str]) -> None:
        """命中规则的 hit_count +1，行级更新保留注释/格式（v12.5 闭环）。"""
        path = self.rules_path
        if not path or not path.exists():
            return
        lines = path.read_text(encoding="utf-8").split("\n")
        cur_id = None
        updated = 0
        for i, line in enumerate(lines):
            s = line.strip()
            if s.startswith("- id:"):
                cur_id = s.split(":", 1)[1].strip().strip("'\"")
            elif cur_id in hit_rule_ids and s.startswith("hit_count:"):
                m = re.match(r"hit_count:\s*(\d+)", s)
                if m:
                    n = int(m.group(1)) + 1
                    indent = line[:len(line) - len(line.lstrip())]
                    lines[i] = f"{indent}hit_count: {n}"
                    updated += 1
        if updated:
            path.write_text("\n".join(lines), encoding="utf-8")
            _log(f"hit_count 回填: {updated} 条规则")

    # ── Rule application ──

    def _apply_rule(self, rule: dict) -> list[str]:
        check_type = rule.get("check_type")
        if check_type == "file_exists":
            return self._check_file_exists(rule)
        if check_type == "dir_exists":
            return self._check_dir_exists(rule)
        pattern = rule.get("pattern")
        if pattern:
            return self._grep_pattern(rule)
        return []

    def _grep_pattern(self, rule: dict) -> list[str]:
        """Grep a regex pattern across files matching scope_globs."""
        pattern = rule["pattern"]
        scope_globs = rule.get("scope_globs", rule.get("scope", ["*"]))
        if isinstance(scope_globs, str):
            scope_globs = [scope_globs]

        try:
            compiled = re.compile(pattern)
        except re.error as e:
            _log_warn(f"规则 {rule.get('id')} 正则无效: {e}")
            return []

        hits = []
        for glob_pat in scope_globs:
            for filepath in self.src_dir.glob(f"**/{glob_pat}"):
                if not filepath.is_file():
                    continue
                if self._skip_file(filepath):
                    continue
                try:
                    text = filepath.read_text(errors="ignore")
                except OSError:
                    continue
                for lineno, line in enumerate(text.splitlines(), 1):
                    if self._is_comment_line(line, filepath):
                        continue
                    if compiled.search(line):
                        rel = filepath.relative_to(self.src_dir)
                        hits.append(f"{rel}:{lineno}: {line.strip()[:120]}")
                        if len(hits) >= 50:
                            return hits
        return hits

    def _check_file_exists(self, rule: dict) -> list[str]:
        targets = rule.get("check_targets", [])
        hits = []
        for t in targets:
            # Check top-level and nested (first match wins)
            for match in self.src_dir.glob(f"**/{t}"):
                if match.is_file():
                    rel = match.relative_to(self.src_dir)
                    hits.append(f"{rel}: EXISTS")
                    break
        return hits

    def _check_dir_exists(self, rule: dict) -> list[str]:
        targets = rule.get("check_targets", [])
        hits = []
        for t in targets:
            if (self.src_dir / t).is_dir():
                hits.append(f"{t}/: EXISTS")
        return hits

    # ── Musl function scan (always-on) ──

    def _scan_musl_functions(self, exclude: set[str] | None = None) -> list[dict]:
        """Scan for musl-missing functions in C/C++ source files."""
        findings = []
        code_globs = ["*.c", "*.h", "*.cc", "*.cpp"]
        exclude = exclude or set()

        # Build combined pattern, excluding functions covered by rules
        funcs = [f for f in MUSL_MISSING if f not in exclude]
        if not funcs:
            return findings

        pattern = r'\b(' + '|'.join(re.escape(f) for f in funcs) + r')'
        try:
            compiled = re.compile(pattern)
        except re.error:
            return findings

        hits_by_func: dict[str, list[str]] = {}
        for glob_pat in code_globs:
            for filepath in self.src_dir.glob(f"**/{glob_pat}"):
                if not filepath.is_file() or self._skip_file(filepath):
                    continue
                try:
                    text = filepath.read_text(errors="ignore")
                except OSError:
                    continue
                for lineno, line in enumerate(text.splitlines(), 1):
                    if self._is_comment_line(line, filepath):
                        continue
                    m = compiled.search(line)
                    if m:
                        func = m.group(1)
                        rel = filepath.relative_to(self.src_dir)
                        entry = f"{rel}:{lineno}: {line.strip()[:120]}"
                        hits_by_func.setdefault(func, []).append(entry)

        for func, hits in hits_by_func.items():
            severity = MUSL_MISSING.get(func, "medium")
            findings.append({
                "rule_id": f"PSCAN-MUSL-FUNC-{func}",
                "category": "musl_compat",
                "severity": severity,
                "description": f"源码中使用 {func}()，musl/OHOS 上可能不可用",
                "hits": hits[:30],
                "solution_hint": "检查 musl 是否提供该函数，必要时 #ifdef 替代",
                "auto_generated": False,
            })

        return findings

    # ── Metadata collection ──

    def _detect_build_system(self) -> list[str]:
        systems = []
        if (self.src_dir / "CMakeLists.txt").exists():
            systems.append("cmake")
        if (self.src_dir / "configure").exists() or (self.src_dir / "configure.ac").exists():
            systems.append("autotools")
        if (self.src_dir / "meson.build").exists():
            systems.append("meson")
        if (self.src_dir / "Makefile.am").exists():
            systems.append("autotools")
        if list(self.src_dir.glob("Makefile*")) and "autotools" not in systems:
            systems.append("make")
        return systems

    def _collect_metadata(self) -> dict:
        doc_names = []
        for f in self.src_dir.iterdir():
            if f.is_file() and f.name.startswith(("README", "INSTALL", "NEWS", "CHANGES", "ChangeLog")):
                doc_names.append(f.name)

        has_tests = bool(
            list(self.src_dir.glob("test*")) or
            list(self.src_dir.glob("tests*")) or
            list(self.src_dir.glob("t/*"))
        )

        return {
            "build_systems": self._detect_build_system(),
            "has_tests": has_tests,
            "doc_files": doc_names,
        }

    # ── Helpers ──

    @staticmethod
    def _skip_file(filepath: Path) -> bool:
        """Skip generated/build artifacts."""
        skip_dirs = {".git", "node_modules", "__pycache__", "autom4te.cache",
                     ".deps", ".libs", "build", "Build"}
        parts = filepath.parts
        for d in skip_dirs:
            if d in parts:
                return True

        name = filepath.name.lower()
        if name in ("config.h", "config.h.in", "config.status", "config.log",
                     "configure", "libtool", "stamp-h1"):
            return True

        # Check first few lines for "generated" markers
        try:
            with open(filepath, errors="ignore") as f:
                head = f.read(512).lower()
            if any(m in head for m in ("automatically generated", "do not edit")):
                return True
        except OSError:
            pass
        return False

    @staticmethod
    def _is_comment_line(line: str, filepath: Path) -> bool:
        stripped = line.lstrip()
        if not stripped:
            return True  # blank line
        name = filepath.name.lower()
        if name.endswith(('.c', '.h', '.cc', '.cpp', '.java', '.js')):
            return stripped.startswith(('//', '/*', '*'))
        if name.startswith('makefile') or name.endswith('.mk') or name.endswith('.py') or name.endswith('.sh'):
            return stripped.startswith('#') and not stripped.startswith('#!')  # shebang 不是注释
        return False

    def _summarize(self, findings: list[dict]) -> dict:
        levels: dict[str, int] = {}
        for f in findings:
            s = f.get("severity", "info")
            levels[s] = levels.get(s, 0) + 1
        return levels

    # ── Report output ──

    def save_report(self, output_path: str) -> dict:
        """Run scan and save report to YAML file."""
        report = self.scan()
        output = Path(output_path)
        output.parent.mkdir(parents=True, exist_ok=True)

        if yaml:
            content = yaml.dump(report, default_flow_style=False, allow_unicode=True, sort_keys=False)
        else:
            content = self._report_to_yaml(report)

        output.write_text(content, encoding="utf-8")
        _log(f"报告已保存: {output}")
        return report

    @staticmethod
    def _report_to_yaml(report: dict) -> str:
        """Fallback YAML serializer when PyYAML unavailable."""
        lines = [f'src_dir: "{report["src_dir"]}"', "findings:"]
        for f in report["findings"]:
            lines.append(f'  - rule_id: "{f["rule_id"]}"')
            lines.append(f'    category: "{f["category"]}"')
            lines.append(f'    severity: {f["severity"]}')
            lines.append(f'    description: "{f["description"]}"')
            lines.append("    hits:")
            for h in f["hits"][:10]:
                lines.append(f'      - "{h}"')
            if f.get("kb_ref"):
                lines.append(f'    kb_ref: "{f["kb_ref"]}"')
            if f.get("solution_hint"):
                lines.append(f'    solution_hint: "{f["solution_hint"]}"')
        lines.append("metadata:")
        m = report["metadata"]
        lines.append(f'  build_systems: {m["build_systems"]}')
        lines.append(f'  has_tests: {m["has_tests"]}')
        lines.append(f'  doc_files: {m["doc_files"]}')
        lines.append("summary:")
        for k, v in report["summary"].items():
            lines.append(f"  {k}: {v}")
        return "\n".join(lines)

    # ── Closed-loop: extract rules from patch ──

    @staticmethod
    def extract_rules_from_patch(patch_file: str, software: str, version: str) -> list[dict]:
        """Extract candidate scan rules from a unified diff patch file.

        Scans -lines (removed code) for function calls that were replaced.
        Returns a list of rule dicts suitable for appending to pre-scan-rules.yaml.
        """
        p = Path(patch_file)
        if not p.exists():
            return []

        # C function call pattern: word followed by (
        func_call_re = re.compile(r'^[-]\s+.*?\b(\w+)\s*\(')

        removed_funcs: dict[str, int] = {}
        with open(p, encoding="utf-8", errors="ignore") as f:
            for line in f:
                if not line.startswith('-'):
                    continue
                if line.startswith('---'):
                    continue
                m = func_call_re.search(line)
                if m:
                    func = m.group(1)
                    # Skip trivial names
                    if func in ("if", "for", "while", "switch", "return", "sizeof",
                                "else", "case", "break", "continue", "goto"):
                        continue
                    removed_funcs[func] = removed_funcs.get(func, 0) + 1

        rules = []
        for func, count in sorted(removed_funcs.items(), key=lambda x: -x[1]):
            rules.append({
                "id": f"PSCAN-AUTO-{func.upper()}",
                "category": "auto_extracted",
                "severity": "medium",
                "pattern": f'\\b{func}\\b',
                "scope_globs": ["*.c", "*.h", "*.cc", "*.cpp"],
                "description": f"从 {software} {version} 补丁自动提取: {func}()",
                "solution_hint": "检查该函数在 OHOS/musl 上是否可用",
                "source": f"{software} {version}",
                "auto_generated": True,
                "hit_count": 0,
            })
        return rules


# ═══════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════

def pre_scan_cli(argv: list[str] | None = None) -> int:
    """ohc-run.py prescan 入口（独立命令，v12.5）。"""
    return main(argv)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="ohc prescan",
        description="预编译源码风险扫描（规则集 + 知识库动态派生规则）",
    )
    parser.add_argument("src_dir", help="源码目录")
    parser.add_argument("--rules", help="规则集 yaml 文件路径 (默认: <项目>/knowledge/graph/pre-scan-rules.yaml)")
    parser.add_argument("--kb-dir", help="知识图谱目录（默认: 规则文件同目录，自动派生 PSCAN-KB-* 规则）")
    parser.add_argument("--no-writeback", action="store_true", help="不回填 hit_count（只读扫描）")
    parser.add_argument("--json", action="store_true", help="JSON 输出（供 AI 消费）")
    parser.add_argument("--output", help="输出报告路径 (默认: <src_dir>/.pre-scan-report.yaml)")
    args = parser.parse_args(argv)

    if args.json:
        global _LOG_STDERR
        _LOG_STDERR = True

    rules = args.rules
    if not rules:
        # 自动发现：cwd 或其上级含 knowledge/graph/pre-scan-rules.yaml
        for cand in [Path.cwd(), *Path.cwd().parents]:
            f = cand / "knowledge" / "graph" / "pre-scan-rules.yaml"
            if f.exists():
                rules = str(f)
                break

    scanner = PreScanner(args.src_dir, rules, kb_dir=args.kb_dir,
                         writeback=not args.no_writeback)
    output = args.output or str(Path(args.src_dir) / ".pre-scan-report.yaml")
    report = scanner.save_report(output)

    # Print summary
    summary = report.get("summary", {})
    emoji_map = {
        "critical": "🔴", "high": "🟠", "medium": "🟡",
        "low": "🟢", "info": "ℹ️", "auto": "🔧",
    }

    if args.json:
        import json as _json
        print(_json.dumps(report, ensure_ascii=False, indent=2))
        return 0

    print(f"\n━━━ 预编译风险扫描完成 ━━━")
    for level in ("critical", "high", "medium", "low", "info", "auto"):
        count = summary.get(level, 0)
        if count > 0:
            print(f"  {emoji_map.get(level, '❓')} {level}: {count} 项")

    meta = report.get("metadata", {})
    print(f"  构建系统: {meta.get('build_systems', [])}")
    print(f"  有测试: {meta.get('has_tests', False)}")
    if report.get("kb_rule_count"):
        print(f"  KB 动态规则: {report['kb_rule_count']} 条（知识库增长自动生效）")
    print(f"\n报告: {output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
