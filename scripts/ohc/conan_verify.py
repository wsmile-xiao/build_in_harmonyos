"""Conan recipe verifier — validates conanfile.py via conan create + conan test.

Runs `conan create` from a clean source tree to verify the recipe is
self-contained and reproducible. When conan create fails, the error is
matched against the knowledge graph (engine.py) — if a match is found,
the recommended fix is displayed; if not, a draft knowledge entry is
created in knowledge/drafts/ for later review.

Gates:
  G0  Pre-build assessment (knowledge graph proactive query)
  G1  Recipe completeness (conanfile.py + conandata.yml + test_package/)
  G2  conan create (clean build) + knowledge graph integration
  G3  System-lib collision verification (R26)
  G4  Artifact integrity (bin/lib/include)
  L2  Platform smoke test (binary --version)
  L4  Static security scan (NX/PIE/RELRO)
  L5  Product baseline comparison

Usage:
    python3 ohc-run.py conan-verify <software> <version>
"""
from __future__ import annotations

import hashlib
import os
import re
import shlex
import shutil
import subprocess
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from .utils import find_project_dir, log_info, log_ok, log_warn, log_fail


# ── Gate results ──

@dataclass
class VerifyResult:
    gate: str
    passed: bool
    details: list[str] = field(default_factory=list)
    knowledge_hit: str = ""  # E-entry ID if knowledge graph matched

    def ok(self) -> bool:
        return self.passed


class ConanVerifier:
    """Verify a Conan recipe by running conan create + multi-level checks."""

    def __init__(self, software: str, version: str,
                 conan_profile: str = "ohos-aarch64",
                 conan_user: str = "ohpcd",
                 conan_channel: str = "stable",
                 pdir: str | None = None):
        self.software = software
        self.version = version
        self.profile = conan_profile
        self.user = conan_user
        self.channel = conan_channel
        self.pdir = Path(pdir) if pdir else Path(find_project_dir())
        self.script_dir = self.pdir / "scripts"
        letter = software[0].lower()
        self.archive_dir = self.pdir / "archives" / letter / software / version
        self.ref = f"{software}/{version}@{conan_user}/{conan_channel}"
        self.report_dir = self.archive_dir / "reports"
        self._draft_count = 0

    def _run(self, cmd: list[str] | str, **kw) -> tuple[int, str]:
        """Run command, return (exit_code, combined_output)."""
        if isinstance(cmd, str):
            cmd = ["/bin/sh", "-c", cmd]
        try:
            timeout = kw.pop("timeout", 1800)  # 30 min default
            r = subprocess.run(cmd, capture_output=True, text=True,
                               timeout=timeout, **kw)
            return r.returncode, (r.stdout or "") + (r.stderr or "")
        except subprocess.TimeoutExpired:
            return 1, "TIMEOUT"
        except FileNotFoundError as e:
            return 1, str(e)

    def _check_conan_available(self) -> bool:
        """Check if conan CLI is available."""
        import shutil
        conan_path = shutil.which("conan")
        if not conan_path:
            # Try common locations
            for candidate in [
                "/storage/Users/currentUser/usr/local/bin/conan",
                os.path.expanduser("~/usr/local/bin/conan"),
                "/usr/local/bin/conan",
            ]:
                if os.path.isfile(candidate) and os.access(candidate, os.X_OK):
                    conan_path = candidate
                    break

        if conan_path:
            self._conan_path = conan_path
            rc, out = self._run([conan_path, "--version"])
            if rc == 0:
                log_ok(f"  Conan: {out.strip()} (path: {conan_path})")
                return True

        log_fail("  Conan CLI 不可用")
        log_fail("  安装: pip3 install conan==2.12.0")
        return False

    def _conan(self, args: list[str], **kw) -> tuple[int, str]:
        """Run a conan subcommand using the discovered conan path."""
        conan = getattr(self, "_conan_path", shutil.which("conan") or "conan")
        return self._run([conan] + args, **kw)

    def _ensure_profile(self) -> bool:
        """Ensure ohos-aarch64 profile exists."""
        profile_file = self.pdir / "ci" / "conan" / "profiles" / self.profile
        if profile_file.exists():
            log_ok(f"  Profile file: {profile_file.relative_to(self.pdir)}")
            return True

        rc, out = self._conan(["profile", "list"])
        if rc == 0 and self.profile in out:
            log_ok(f"  Profile '{self.profile}' exists in conan config")
            return True

        log_warn(f"  Profile '{self.profile}' not found, creating from template...")
        if profile_file.exists():
            rc, _ = self._conan(["profile", "import", str(profile_file)])
            return rc == 0

        rc, _ = self._conan(["profile", "detect", "--name", self.profile])
        return rc == 0

    # ── Knowledge graph integration ──

    def _query_knowledge_graph(self, error_text: str) -> str:
        """Query the knowledge graph for a matching error pattern.

        Returns formatted knowledge entry string if matched, empty string if not.
        Also creates a draft entry if no match is found.
        """
        try:
            from .engine import run_engine, format_inline
        except ImportError:
            return ""

        if not error_text.strip():
            return ""

        result = run_engine(error_text, project_dir=str(self.pdir))
        if result.matched and result.entry:
            # Display the knowledge entry
            inline = format_inline(result)
            if inline:
                log_info(inline)

            e = result.entry
            lines = [
                f"  🧠 知识图谱命中: {e.id} (评分:{result.total_score})",
                f"     根因: {e.root_cause[:120]}",
                f"     方案: {e.rec_approach}",
            ]
            if e.rec_command:
                lines.append(f"     命令: {e.rec_command[:120]}")
            if e.doc_file:
                lines.append(f"     文档: {e.doc_file}")
            return "\n".join(lines)
        else:
            # No match — create draft entry
            draft_path = self._create_draft_entry(error_text)
            if draft_path:
                return (
                    f"  📝 知识图谱未命中，已生成草稿: {draft_path.relative_to(self.pdir)}\n"
                    f"     请审查后移动到 knowledge/graph/ 并更新 index.tsv"
                )
            return "  ⚠️ 知识图谱未命中，草稿生成失败"

    def _create_draft_entry(self, error_text: str) -> Path | None:
        """Create a draft knowledge entry for an unmatched error.

        Before creating, checks for similar existing drafts to avoid duplicates.
        """
        drafts_dir = self.pdir / "knowledge" / "drafts"
        drafts_dir.mkdir(parents=True, exist_ok=True)

        # Extract keywords for dedup check
        keywords = self._extract_keywords(error_text)
        keyword_set = set(keywords)

        # Check for similar existing drafts (share >50% keywords)
        existing_drafts = sorted(drafts_dir.glob("DRAFT-*.kv"))
        for existing in existing_drafts:
            try:
                content = existing.read_text(encoding="utf-8", errors="replace")
                # Extract keywords from existing draft
                existing_kws = set()
                for line in content.split("\n"):
                    if line.startswith("keywords:"):
                        kws = line.split(":", 1)[1].strip().strip(",")
                        existing_kws = {k.strip() for k in kws.split(",") if k.strip()}
                        break
                # Check overlap
                if existing_kws and keyword_set:
                    overlap = len(keyword_set & existing_kws) / max(len(keyword_set), 1)
                    if overlap > 0.5:
                        log_info(f"  📝 发现相似草稿: {existing.name} (关键词重合 {overlap:.0%})，跳过生成")
                        return existing
            except Exception:
                continue
        existing = existing_drafts
        next_num = 1
        if existing:
            nums = [int(re.search(r'DRAFT-(\d+)', f.name).group(1))
                    for f in existing if re.search(r'DRAFT-(\d+)', f.name)]
            next_num = max(nums) + 1 if nums else 1

        draft_id = f"DRAFT-{next_num:03d}"
        draft_path = drafts_dir / f"{draft_id}.kv"

        # Extract keywords from error text (simple heuristic)
        keywords = self._extract_keywords(error_text)

        # Extract error excerpt (first meaningful error lines)
        error_excerpt = "\n".join(
            l for l in error_text.split("\n")
            if any(w in l.lower() for w in ["error", "fail", "denied", "not found",
                   "cannot", "undefined", "missing", "fatal"])
        )[:1000]

        timestamp = datetime.now().isoformat()

        # Auto-fill author from git config (knowledge collaboration mode)
        git_author = self._get_git_author()

        content = f"""# ═══ Draft knowledge entry — auto-generated by conan-verify ═══
# Timestamp: {timestamp}
# Software: {self.software} {self.version}
# Gate: G2 (conan create)
# Status: UNMATCHED — needs human/AI review to promote to E-entry
#
# To promote:
#   1. Review the error excerpt below
#   2. Fill in root_cause, rec_approach, rec_command
#   3. Rename to E0XX.kv and move to knowledge/graph/
#   4. Add a row to knowledge/graph/index.tsv

id: {draft_id}
severity: 2
category: conan|build
trigger_tool: conan
phase: build|package
approach: TODO — describe the fix approach

keywords: {", ".join(keywords)}

error_signature: {"|".join(kw for kw in keywords[:5] if len(kw) > 3)}
match_keywords: {",".join(keywords[:6])}

root_cause: TODO — describe the root cause
affected_scope: TODO — describe the impact

rec_priority: 1
rec_approach: TODO — describe the recommended approach
rec_description: TODO — describe the fix in detail
rec_command: TODO — provide the fix command
rec_auto_fix: false
rec_impl: manual

doc_file:

principles:

# ── Error excerpt (first 1000 chars of relevant lines) ──
error_text_excerpt: |
  {error_excerpt}

# ── Full log path ──
full_log: {self.report_dir / "conan-create.log"}

# ── Knowledge collaboration (auto-filled from git config) ──
authors: {git_author}
"""
        draft_path.write_text(content, encoding="utf-8")
        self._draft_count += 1
        return draft_path

    def _get_git_author(self) -> str:
        """Get author info from git config for knowledge collaboration."""
        import subprocess
        try:
            name = subprocess.check_output(
                ["git", "config", "user.name"], text=True, stderr=subprocess.DEVNULL
            ).strip()
            email = subprocess.check_output(
                ["git", "config", "user.email"], text=True, stderr=subprocess.DEVNULL
            ).strip()
            if name and email:
                return f"{name} <{email}>"
        except Exception:
            pass
        return ""

    def _extract_keywords(self, text: str) -> list[str]:
        """Extract potential keywords from error text for draft entries."""
        # Common error-related terms
        stop_words = {"the", "a", "an", "is", "not", "and", "or", "but",
                      "in", "on", "at", "to", "for", "of", "with", "by",
                      "from", "this", "that", "it", "was", "were", "be",
                      "been", "has", "have", "had", "will", "would", "could",
                      "should", "may", "might", "can", "cannot", "no", "yes"}

        # Extract words from error lines
        words = set()
        for line in text.split("\n"):
            if not any(w in line.lower() for w in ["error", "fail", "denied",
                    "not found", "cannot", "undefined", "missing", "fatal"]):
                continue
            for w in re.findall(r'[a-zA-Z_][a-zA-Z0-9_./-]{2,}', line):
                w_lower = w.lower().strip("./-")
                if w_lower and w_lower not in stop_words and len(w_lower) >= 3:
                    words.add(w_lower)

        return sorted(words)[:12]

    # ── Gate 0: Pre-build assessment (knowledge graph proactive query) ──

    # Build system → known risk keywords mapping
    _BUILD_SYSTEM_RISKS = {
        "autotools": "autotools configure config.guess config.sub HarmonyOS cannot guess build type mktemp config.status umask permission denied",
        "cmake": "cmake CMAKE_SYSTEM_NAME HarmonyOS platform detection unknown system ohos",
        "meson": "meson host_system HarmonyOS platform detection undefined symbol",
        "makefile": "makefile Makefile HarmonyOS build system install",
    }

    def _detect_build_system_from_conanfile(self, content: str) -> str:
        """Detect build system from conanfile.py imports."""
        if "from conan.tools.cmake import" in content or "CMakeToolchain" in content:
            return "cmake"
        if "from conan.tools.gnu import" in content or "AutotoolsToolchain" in content:
            return "autotools"
        if "from conan.tools.meson import" in content or "MesonToolchain" in content:
            return "meson"
        if "from conan.tools.make import" in content or "MakeToolchain" in content:
            return "makefile"
        return "unknown"

    def _check_risk_addressed(self, content: str, eid: str) -> bool:
        """Check if conanfile.py already addresses a known risk."""
        if eid == "E007":  # config.guess — check for patches
            conandata = (self.archive_dir / "conandata.yml").read_text(encoding="utf-8", errors="replace")
            return "config.guess" in conandata or "config.sub" in conandata
        if eid == "E011":  # mktemp/umask — check for TMPDIR or umask fix
            return "TMPDIR" in content or "umask" in content or "CONFIG_SHELL" in content
        if eid == "E092":  # CMAKE_SYSTEM_NAME — check for toolchain setting
            return "CMAKE_SYSTEM_NAME" in content or "ohos" in content.lower()
        if eid == "E090":  # meson platform — check for meson.options
            return "meson.options" in content or "host_machine" in content
        return False

    def gate0_pre_build_assessment(self) -> VerifyResult:
        """G0: Pre-build assessment — proactively query knowledge graph for known risks.

        This gate runs BEFORE conan create to save time. It detects the build
        system from conanfile.py, queries the knowledge graph for known issues
        with that build system on HarmonyOS, and checks if the recipe already
        addresses them. Non-blocking — only warns.
        """
        log_info("G0: 预构建风险评估 (知识图谱预查询)...")
        g = VerifyResult(gate="G0", passed=True)

        conanfile = self.archive_dir / "conanfile.py"
        if not conanfile.exists():
            g.details.append("  ⏭️ 跳过（无 conanfile.py）")
            return g

        content = conanfile.read_text(encoding="utf-8")
        build_system = self._detect_build_system_from_conanfile(content)
        g.details.append(f"  📦 构建系统: {build_system}")

        if build_system == "unknown":
            g.details.append("  ℹ️ 无法识别构建系统，跳过预查询")
            return g

        # Query knowledge graph with build-system-specific risk keywords
        risk_query = self._BUILD_SYSTEM_RISKS.get(build_system, "")
        if not risk_query:
            return g

        try:
            from .engine import run_engine
        except ImportError:
            g.details.append("  ⚠️ 知识图谱引擎不可用")
            return g

        result = run_engine(risk_query, project_dir=str(self.pdir))
        if not result.matched or not result.entry:
            g.details.append("  ✅ 知识图谱未发现已知风险")
            return g

        e = result.entry
        addressed = self._check_risk_addressed(content, e.id)

        if addressed:
            g.details.append(f"  ✅ 已知风险 {e.id} 已在配方中处理")
            g.details.append(f"     {e.root_cause[:100]}")
        else:
            # Non-blocking warning — the risk exists but hasn't been addressed
            g.details.append(f"  ⚠️ 已知风险 {e.id} 未在配方中处理")
            g.details.append(f"     根因: {e.root_cause[:120]}")
            g.details.append(f"     方案: {e.rec_approach}")
            if e.rec_command:
                g.details.append(f"     修复: {e.rec_command[:120]}")
            g.details.append(f"     ⚡ G2 conan create 可能因此失败，建议先修复")
            g.knowledge_hit = e.id

        log_ok(f"  G0: {'PASS' if g.passed else 'WARN'}")
        return g

    # ── Gate 1: Recipe completeness ──

    def gate1_recipe_completeness(self) -> VerifyResult:
        """Check that conanfile.py + conandata.yml + test_package/ exist."""
        log_info("G1: 配方完整性检查...")
        g = VerifyResult(gate="G1", passed=True)

        conanfile = self.archive_dir / "conanfile.py"
        if not conanfile.exists():
            g.passed = False
            g.details.append("  ❌ conanfile.py 缺失")
        else:
            content = conanfile.read_text(encoding="utf-8")
            checks = [
                ("name = ", "name 声明"),
                ("version = ", "version 声明"),
                ("def source(", "source() 方法"),
                ("def build(", "build() 方法"),
                ("def package(", "package() 方法"),
                ("def package_info(", "package_info() 方法"),
                ("export_sources", "export_sources() 方法"),
                ("apply_conandata_patches", "补丁应用调用"),
            ]
            for pattern, desc in checks:
                if pattern not in content:
                    g.passed = False
                    g.details.append(f"  ❌ conanfile.py 缺少: {desc}")
                else:
                    g.details.append(f"  ✅ {desc}")
            if "BUILD_SHARED_LIBS" in content or "-static" in content or "default_library" in content:
                g.details.append("  ✅ R26: 系统同名库静态链接配置存在")
            else:
                g.details.append("  ℹ️ R26: 未检测到静态链接配置（非系统同名库无需静态）")

        conandata = self.archive_dir / "conandata.yml"
        if not conandata.exists():
            g.passed = False
            g.details.append("  ❌ conandata.yml 缺失")
        else:
            content = conandata.read_text(encoding="utf-8")
            if "sources:" not in content:
                g.passed = False
                g.details.append("  ❌ conandata.yml 缺少 sources 段")
            elif "url:" not in content:
                g.passed = False
                g.details.append("  ❌ conandata.yml 缺少 sources.url")
            elif "REPLACE_WITH" in content:
                g.passed = False
                g.details.append("  ❌ conandata.yml sha256 未填写")
            else:
                g.details.append("  ✅ conandata.yml 完整")

        tp = self.archive_dir / "test_package"
        if not tp.exists():
            g.passed = False
            g.details.append("  ❌ test_package/ 缺失 (R28)")
        elif not (tp / "conanfile.py").exists():
            g.passed = False
            g.details.append("  ❌ test_package/conanfile.py 缺失 (R28)")
        else:
            g.details.append("  ✅ test_package/ 存在 (R28)")

        # Check test_package/MANIFEST.yml (required by CI L0e)
        manifest_yml = self.archive_dir / "test_package" / "MANIFEST.yml"
        if not manifest_yml.exists():
            g.passed = False
            g.details.append("  ❌ test_package/MANIFEST.yml 缺失 (CI L0e 门禁要求)")
        else:
            g.details.append("  ✅ test_package/MANIFEST.yml 存在")

        log_ok(f"  G1: {'PASS' if g.passed else 'FAIL'}")
        return g

    # ── Gate 2: conan create (clean build) + knowledge graph ──

    def gate2_conan_create(self) -> VerifyResult:
        """Run conan create to verify recipe builds from clean source.

        On failure, queries the knowledge graph for matching error patterns.
        If no match is found, creates a draft knowledge entry.
        """
        log_info("G2: conan create (干净构建)...")
        g = VerifyResult(gate="G2", passed=True)

        profile_file = self.pdir / "ci" / "conan" / "profiles" / self.profile
        if profile_file.exists():
            pr_args = f"-pr:h={shlex.quote(str(profile_file))} -pr:b={shlex.quote(str(profile_file))}"
        else:
            pr_args = f"-pr:h={self.profile} -pr:b={self.profile}"

        # ── E017 prevention: inject ghfast.top mirror for GitHub URLs ──
        conandata_path = self.archive_dir / "conandata.yml"
        _url_injected = False
        _original_conandata = None
        if conandata_path.exists():
            _original_conandata = conandata_path.read_text(encoding="utf-8")
            if "github.com" in _original_conandata and "ghfast.top" not in _original_conandata:
                modified = _original_conandata.replace("https://github.com", "https://ghfast.top/https://github.com")
                conandata_path.write_text(modified, encoding="utf-8")
                _url_injected = True
                log_info("  🔧 E017 预防: GitHub URL 已临时注入 ghfast.top 镜像")

        try:
            cmd = (
                f"{self._conan_path} create {shlex.quote(str(self.archive_dir))} "
                f"{pr_args} "
                f"--build=missing "
                f"--user={self.user} --channel={self.channel}"
            )
            log_info(f"  Running: {cmd}")

            rc, output = self._run(cmd, timeout=3600, cwd=str(self.pdir))

            # Save full log
            self.report_dir.mkdir(parents=True, exist_ok=True)
            log_file = self.report_dir / "conan-create.log"
            log_file.write_text(output, encoding="utf-8")

            if rc == 0:
                g.details.append(f"  ✅ conan create 成功")
                g.details.append(f"  📄 日志: {log_file.relative_to(self.pdir)}")
                ref_match = re.search(r'Package.*?(\w+/\w+@\w+/\w+)', output)
                if ref_match:
                    g.details.append(f"  📦 包引用: {ref_match.group(1)}")
                # Extract package_id for G3/G4 cache path lookup
                pkg_id_match = re.search(r'(\w+/\w+@\w+/\w+):(\w+)', output)
                if pkg_id_match:
                    self._package_id = pkg_id_match.group(2)
                    g.details.append(f"  📦 包ID: {self._package_id}")
            else:
                g.passed = False
                error_lines = [l for l in output.split("\n")
                              if "ERROR" in l or "error:" in l.lower()]
                if error_lines:
                    g.details.append(f"  ❌ conan create 失败:")
                    for line in error_lines[:5]:
                        g.details.append(f"     {line.strip()}")
                else:
                    g.details.append(f"  ❌ conan create 失败 (RC={rc})")
                g.details.append(f"  📄 日志: {log_file.relative_to(self.pdir)}")

                # ── Knowledge graph integration ──
                log_info("  🧠 查询知识图谱...")
                kg_result = self._query_knowledge_graph(output)
                if kg_result:
                    g.details.append(f"  {kg_result}")
                    # Extract matched E-entry ID
                    match = re.search(r'(E\d+)', kg_result)
                    if match:
                        g.knowledge_hit = match.group(1)
                else:
                    g.details.append("  ⚠️ 知识图谱查询失败")
        finally:
            if _url_injected and _original_conandata is not None:
                conandata_path.write_text(_original_conandata, encoding="utf-8")
                log_info("  🔄 已恢复原始 conandata.yml")

        log_ok(f"  G2: {'PASS' if g.passed else 'FAIL'}")
        return g

    # ── Gate 3: System-lib collision verification (R26) ──

    def _get_cache_ref(self) -> str:
        """Get the full cache reference including package_id for binary package path."""
        pkg_id = getattr(self, '_package_id', None)
        if pkg_id:
            return f"{self.ref}:{pkg_id}"
        # Fallback: try to discover package_id via conan list
        rc, out = self._conan(["list", f"{self.ref}:*"], timeout=30)
        if rc == 0:
            match = re.search(r'(\w{40})', out)
            if match:
                self._package_id = match.group(1)
                return f"{self.ref}:{self._package_id}"
        return self.ref

    def gate3_static_linking(self) -> VerifyResult:
        """Verify system-name libraries don't output .so to system paths (R26)."""
        log_info("G3: 系统同名库隔离验证 (R26)...")
        g = VerifyResult(gate="G3", passed=True)

        cache_ref = self._get_cache_ref()
        rc, cache_path = self._conan(["cache", "path", cache_ref], timeout=30)
        if rc != 0:
            g.details.append("  ⚠️ 无法获取 conan cache 路径（可能 G2 未通过）")
            return g

        cache_path = cache_path.strip()
        if not cache_path or not Path(cache_path).exists():
            g.details.append(f"  ⚠️ cache 路径无效: {cache_path}")
            return g

        bin_dir = Path(cache_path) / "bin"

        if not bin_dir.exists() or not any(bin_dir.iterdir()):
            g.details.append("  ℹ️ 无 bin/ 目录（可能是纯库包）")

        # R26 新策略: 检查包是否输出了与系统同名的 .so
        # 如果 lib/ 目录下有 .so 且名字与系统 /lib /lib64 冲突 → 违规
        lib_dir = Path(cache_path) / "lib"
        if not lib_dir.exists():
            for p in Path(cache_path).rglob("lib"):
                if p.is_dir() and any(p.iterdir()):
                    lib_dir = p
                    break

        issues = []
        if lib_dir.exists():
            # 收集系统 /lib /lib64 下的 .so 基名（去掉版本后缀）
            # libz.so.1.2.3 -> libz.so
            system_so_base = set()
            for system_lib_dir in ["/lib", "/lib64"]:
                try:
                    rc, out = self._run(["ls", system_lib_dir], timeout=5)
                    if rc == 0:
                        for line in out.split("\n"):
                            line = line.strip()
                            if line.startswith("lib") and ".so" in line:
                                base = line.split(".so")[0] + ".so"
                                system_so_base.add(base)
                except Exception:
                    pass

            for lib_file in lib_dir.iterdir():
                if not lib_file.is_file() or ".so" not in lib_file.name:
                    continue
                pkg_base = lib_file.name.split(".so")[0] + ".so"
                if pkg_base in system_so_base:
                    issues.append(f"  {lib_file.name}: 与系统同名 .so 冲突")
        else:
            g.details.append("  ℹ️ 无 lib/ 目录（纯可执行包）")

        if issues:
            g.passed = False
            g.details.append(f"  ❌ R26 违规: 系统同名库输出了 .so")
            for issue in issues[:10]:
                g.details.append(f"     {issue}")
            g.details.append("  💡 在 conanfile.py generate() 中对系统同名库添加 BUILD_SHARED_LIBS=OFF / --disable-shared")
        else:
            g.details.append("  ✅ 无系统同名库冲突（R26 通过）")

        log_ok(f"  G3: {'PASS' if g.passed else 'FAIL'}")
        return g

    # ── Gate 4: Artifact integrity ──

    def gate4_artifact_integrity(self) -> VerifyResult:
        """Verify package artifacts (bin/lib/include) are present."""
        log_info("G4: 产物完整性检查...")
        g = VerifyResult(gate="G4", passed=True)

        # In Conan 2, `conan cache path <recipe_ref>` returns the recipe
        # exports path, not the package path.  Query the package ID first.
        rc, list_out = self._conan(["list", self.ref + ":*", "--format=json"], timeout=30)
        if rc != 0:
            g.details.append("  ⚠️ 无法查询包列表")
            return g

        try:
            import json
            listing = json.loads(list_out)
            pkgs = list(listing["Local Cache"][self.software][self.ref]
                        ["revisions"].values())[0]["packages"]
            pkg_id = next(iter(pkgs))
        except (KeyError, IndexError, StopIteration):
            g.details.append("  ⚠️ 无法找到程序包 ID")
            return g

        pkg_ref = f"{self.ref}:{pkg_id}"
        rc, cache_path = self._conan(["cache", "path", pkg_ref], timeout=30)
        if rc != 0:
            g.details.append("  ⚠️ 无法获取 conan cache 路径")
            return g

        cache_path = cache_path.strip()
        if not cache_path or not Path(cache_path).exists():
            g.details.append(f"  ⚠️ cache 路径无效: {cache_path}")
            return g

        cache = Path(cache_path)
        self._cache_path = cache  # save for L2/L4/L5

        bin_dir = cache / "bin"
        if bin_dir.exists():
            bin_count = len([f for f in bin_dir.iterdir() if f.is_file()])
            g.details.append(f"  ✅ bin/: {bin_count} 个文件")
        else:
            bins = list(cache.rglob("bin"))
            if bins:
                bin_count = sum(1 for b in bins[0].iterdir() if b.is_file())
                g.details.append(f"  ✅ bin/: {bin_count} 个文件 (in {bins[0].name})")

        lib_dir = cache / "lib"
        if lib_dir.exists():
            a_count = len(list(lib_dir.glob("*.a")))
            so_count = len(list(lib_dir.glob("*.so*")))
            g.details.append(f"  ✅ lib/: {a_count} .a + {so_count} .so")

        inc_dir = cache / "include"
        if inc_dir.exists():
            h_count = len(list(inc_dir.rglob("*.h"))) + len(list(inc_dir.rglob("*.hpp")))
            g.details.append(f"  ✅ include/: {h_count} 个头文件")

        has_artifact = any([
            bin_dir.exists() and any(bin_dir.iterdir()),
            lib_dir.exists() and any(lib_dir.iterdir()),
            inc_dir.exists() and any(inc_dir.rglob("*")),
        ])
        if not has_artifact:
            g.passed = False
            g.details.append("  ❌ 无任何产物（bin/lib/include 均为空）")

        log_ok(f"  G4: {'PASS' if g.passed else 'FAIL'}")
        return g

    # ── L2: Platform smoke test ──

    def gate_l2_smoke_test(self) -> VerifyResult:
        """L2: Platform functional smoke test — verify built binaries run."""
        log_info("L2: 平台功能矩阵 (smoke test)...")
        g = VerifyResult(gate="L2", passed=True)

        cache = getattr(self, "_cache_path", None)
        if not cache or not cache.exists():
            g.details.append("  ⏭️ 跳过（无 cache 路径）")
            return g

        bin_dir = cache / "bin"
        if not bin_dir.exists():
            g.details.append("  ℹ️ 无 bin/ 目录（纯库包，跳过 smoke test）")
            return g

        tested = 0
        failed = []
        for bin_file in sorted(bin_dir.iterdir()):
            if not bin_file.is_file():
                continue
            if not os.access(bin_file, os.X_OK):
                continue
            # Quick smoke test: run with --version
            rc, out = self._run([str(bin_file), "--version"], timeout=10)
            if rc == 0:
                tested += 1
                version_line = out.strip().split("\n")[0][:80]
                g.details.append(f"  ✅ {bin_file.name}: {version_line}")
            else:
                # Try --help as fallback
                rc2, out2 = self._run([str(bin_file), "--help"], timeout=10)
                if rc2 == 0:
                    tested += 1
                    g.details.append(f"  ✅ {bin_file.name}: --help OK")
                else:
                    failed.append(bin_file.name)
                    g.details.append(f"  ⚠️ {bin_file.name}: --version 和 --help 均失败")

        if failed and not tested:
            g.passed = False
            g.details.append(f"  ❌ 所有二进制文件均无法运行")
        elif failed:
            g.details.append(f"  ⚠️ {len(failed)} 个二进制文件无法运行: {', '.join(failed[:5])}")
        else:
            g.details.append(f"  ✅ {tested} 个二进制文件通过 smoke test")

        log_ok(f"  L2: {'PASS' if g.passed else 'FAIL'}")
        return g

    # ── L4: Static security scan ──

    def gate_l4_security_scan(self) -> VerifyResult:
        """L4: Static security scan — check NX, PIE, RELRO on ELF binaries."""
        log_info("L4: 静态安全扫描 (checksec)...")
        g = VerifyResult(gate="L4", passed=True)

        cache = getattr(self, "_cache_path", None)
        if not cache or not cache.exists():
            g.details.append("  ⏭️ 跳过（无 cache 路径）")
            return g

        bin_dir = cache / "bin"
        if not bin_dir.exists():
            g.details.append("  ℹ️ 无 bin/ 目录，检查 lib/ 中的 .so")
            targets = list((cache / "lib").glob("*.so*")) if (cache / "lib").exists() else []
        else:
            targets = [f for f in bin_dir.iterdir() if f.is_file()]

        if not targets:
            g.details.append("  ℹ️ 无可扫描的 ELF 文件")
            return g

        scanned = 0
        warnings = []
        for target in sorted(targets):
            try:
                if target.read_bytes()[:4] != b'\x7fELF':
                    continue
            except Exception:
                continue

            # Use readelf -l for program headers (NX, PIE)
            rc, out = self._run(["readelf", "-l", "-d", str(target)], timeout=10)
            if rc != 0:
                rc, out = self._run(["llvm-readelf", "-l", "-d", str(target)], timeout=10)
            if rc != 0:
                continue

            scanned += 1
            security = {
                "NX": "unknown",
                "PIE": "unknown",
                "RELRO": "unknown",
                "STACK_CANARY": "unknown",
            }

            # NX: check for GNU_STACK segment
            if "GNU_STACK" in out:
                if "RW" in out.split("GNU_STACK")[1][:200] and "E" not in out.split("GNU_STACK")[1][:200]:
                    security["NX"] = "enabled"
                else:
                    security["NX"] = "disabled"
                    warnings.append(f"{target.name}: NX disabled")

            # PIE: check for DYN type
            if "DYN" in out[:500]:
                security["PIE"] = "enabled"
            elif "EXEC" in out[:500]:
                security["PIE"] = "disabled"
                warnings.append(f"{target.name}: PIE disabled (non-PIE executable)")

            # RELRO: check for BIND_NOW
            if "BIND_NOW" in out or "FLAGS: BIND_NOW" in out:
                security["RELRO"] = "full"
            elif "GNU_RELRO" in out:
                security["RELRO"] = "partial"
            else:
                security["RELRO"] = "none"
                warnings.append(f"{target.name}: RELRO none")

            # Stack canary: check for __stack_chk_fail symbol
            rc2, syms = self._run(["readelf", "-s", str(target)], timeout=10)
            if rc2 == 0 and "__stack_chk_fail" in syms:
                security["STACK_CANARY"] = "enabled"
            else:
                security["STACK_CANARY"] = "not found"

            status_str = " ".join(f"{k}={v}" for k, v in security.items())
            g.details.append(f"  {'⚠️' if warnings and target.name in ' '.join(warnings) else '✅'} {target.name}: {status_str}")

        if warnings:
            g.details.append(f"  ⚠️ {len(warnings)} 个安全警告")
            for w in warnings[:10]:
                g.details.append(f"     {w}")
        else:
            g.details.append(f"  ✅ {scanned} 个 ELF 文件安全扫描通过")

        log_ok(f"  L4: {'PASS' if g.passed else 'FAIL'}")
        return g

    # ── L5: Product baseline ──

    def gate_l5_baseline(self) -> VerifyResult:
        """L5: Product baseline — compare against known-good baseline if exists."""
        log_info("L5: 产物基线对比...")
        g = VerifyResult(gate="L5", passed=True)

        cache = getattr(self, "_cache_path", None)
        if not cache or not cache.exists():
            g.details.append("  ⏭️ 跳过（无 cache 路径）")
            return g

        # Compute current baseline
        current_baseline = {}
        for f in sorted(cache.rglob("*")):
            if f.is_file():
                rel = f.relative_to(cache)
                sha = hashlib.sha256(f.read_bytes()).hexdigest()[:16]
                current_baseline[str(rel)] = {"size": f.stat().st_size, "sha256_16": sha}

        baseline_file = self.archive_dir / "reports" / "baseline.json"

        if not baseline_file.exists():
            # First run — save baseline
            import json
            baseline_file.write_text(
                json.dumps(current_baseline, indent=2, sort_keys=True),
                encoding="utf-8"
            )
            g.details.append(f"  ✅ 首次运行，基线已保存: {baseline_file.relative_to(self.pdir)}")
            g.details.append(f"  📦 {len(current_baseline)} 个文件")
            log_ok(f"  L5: PASS (baseline saved)")
            return g

        # Compare against existing baseline
        import json
        old_baseline = json.loads(baseline_file.read_text(encoding="utf-8"))

        added = set(current_baseline) - set(old_baseline)
        removed = set(old_baseline) - set(current_baseline)
        modified = []
        for f in set(current_baseline) & set(old_baseline):
            if current_baseline[f]["sha256_16"] != old_baseline[f]["sha256_16"]:
                modified.append(f)

        if added:
            g.details.append(f"  ➕ 新增文件: {len(added)}")
            for f in sorted(added)[:5]:
                g.details.append(f"     {f}")
        if removed:
            g.details.append(f"  ➖ 删除文件: {len(removed)}")
            for f in sorted(removed)[:5]:
                g.details.append(f"     {f}")
        if modified:
            g.details.append(f"  🔄 修改文件: {len(modified)}")
            for f in sorted(modified)[:5]:
                g.details.append(f"     {f}")

        if not added and not removed and not modified:
            g.details.append(f"  ✅ 产物与基线完全一致 ({len(current_baseline)} 个文件)")
        else:
            g.details.append(f"  ⚠️ 产物与基线有差异: +{len(added)} -{len(removed)} ~{len(modified)}")
            # Update baseline
            baseline_file.write_text(
                json.dumps(current_baseline, indent=2, sort_keys=True),
                encoding="utf-8"
            )
            g.details.append(f"  📝 基线已更新")

        log_ok(f"  L5: {'PASS' if g.passed else 'FAIL'}")
        return g

    # ── Main run ──

    def run(self) -> int:
        if not self.archive_dir.exists():
            log_fail(f"归档目录不存在: {self.archive_dir}")
            return 1

        log_info(f"🔍 Conan 配方验证: {self.software} {self.version}")
        log_info(f"   引用: {self.ref}")

        if not self._check_conan_available():
            return 1
        if not self._ensure_profile():
            return 1

        # Run gates in order
        g1 = self.gate1_recipe_completeness()
        if not g1.passed:
            log_fail("G1 失败，请先生成完整配方: ohc-run.py conan-init <软件> <版本>")
            self._write_report([g1])
            return 1

        g0 = self.gate0_pre_build_assessment()
        g2 = self.gate2_conan_create()
        skip = VerifyResult("", True, ["  ⏭️ 跳过（G2 未通过）"])

        g3 = self.gate3_static_linking() if g2.passed else skip
        g4 = self.gate4_artifact_integrity() if g2.passed else skip
        l2 = self.gate_l2_smoke_test() if g2.passed else skip
        l4 = self.gate_l4_security_scan() if g2.passed else skip
        l5 = self.gate_l5_baseline() if g2.passed else skip

        gates = [g0, g1, g2, g3, g4, l2, l4, l5]
        self._write_report(gates)

        all_pass = all(g.passed for g in gates)
        if all_pass:
            log_ok(f"\n✅ 配方验证通过: {self.software} {self.version}")
            log_ok("   可标记 status: published")
            marker = self.archive_dir / ".conan-verified"
            marker.write_text(
                f"verified_at={datetime.now().isoformat()}\n",
                encoding="utf-8",
            )
            return 0
        else:
            failed = [g.gate for g in gates if not g.passed]
            log_fail(f"\n❌ 配方验证失败: {', '.join(failed)}")
            if g2.knowledge_hit:
                log_info(f"   🧠 知识图谱建议: 参考 {g2.knowledge_hit}")
            if self._draft_count:
                log_info(f"   📝 已生成 {self._draft_count} 个草稿知识条目")
            log_fail("   请修复后重新验证: ohc-run.py conan-verify <软件> <版本>")
            return 1

    def _write_report(self, gates: list[VerifyResult]) -> None:
        """Write verification report."""
        self.report_dir.mkdir(parents=True, exist_ok=True)
        report = self.report_dir / "conan-verify-report.md"

        all_pass = all(g.passed for g in gates)
        verdict = "PASS" if all_pass else "FAIL"

        lines = [
            f"# Conan Verify Report — {self.software} {self.version}",
            f"",
            f"**Verdict**: {verdict}",
            f"**Reference**: `{self.ref}`",
            f"**Profile**: {self.profile}",
            f"**Date**: {datetime.now().isoformat()}",
            f"",
        ]

        for g in gates:
            if not g.gate:
                continue
            status = "✅ PASS" if g.passed else "❌ FAIL"
            lines.append(f"## {g.gate}: {status}")
            if g.knowledge_hit:
                lines.append(f"**Knowledge hit**: {g.knowledge_hit}")
            for detail in g.details:
                lines.append(detail)
            lines.append("")

        report.write_text("\n".join(lines), encoding="utf-8")
        log_info(f"  报告: {report.relative_to(self.pdir)}")


def conan_verify_cli(argv: list[str] | None = None) -> int:
    import argparse
    parser = argparse.ArgumentParser(
        prog="ohc conan-verify",
        description="验证 Conan 配方: conan create + 知识图谱 + 五级测试",
    )
    parser.add_argument("software", help="软件名称")
    parser.add_argument("version", help="版本号")
    parser.add_argument("--profile", default="ohos-aarch64", help="Conan profile 名称")
    parser.add_argument("--user", default="ohpcd", help="Conan user")
    parser.add_argument("--channel", default="stable", help="Conan channel")
    parser.add_argument("--project-dir")
    args = parser.parse_args(argv)

    verifier = ConanVerifier(
        args.software, args.version,
        conan_profile=args.profile,
        conan_user=args.user,
        conan_channel=args.channel,
        pdir=getattr(args, "project_dir", None),
    )
    return verifier.run()
