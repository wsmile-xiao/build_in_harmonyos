"""Build driver — 13-step compilation pipeline.

Usage:
    python3 ohc-run.py build <software> [<version>] [--skip-check] [--force] [--resume-from=StepN]
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

from .utils import find_project_dir, log_info, log_ok, log_warn, log_fail
from .models import parse_kv_file, parse_build_context
from .engine import engine_cli, run_engine
from .handoff import handoff_cli, emit_handoff, HandoffData
from .init_build import init_build
from .package_builder import PackageBuilder
from .finish import FinishPipeline
from .dependency_resolver import (
    is_prebuilt_available, get_available_version, get_install_url,
    check_tool_available, get_package_for_tool, auto_install_tool,
    auto_install_missing_tools_from_log, check_common_build_tools,
)


# ── Constants ──
MAKE_JOBS = 2  # HarmonyOS sandbox limit
CHECK_TIMEOUT = 600  # 10 min total
CHECK_STUCK_THRESHOLD = 120  # 2 min no output

# Shell for subprocess — HarmonyOS restricts fork+exec to signed binaries
_SHELL = shutil.which("zsh") or shutil.which("sh") or "/system/bin/sh"

_STEP_MAP = {
    "Step1": 1, "Step1.5": 1.5, "Step2": 2, "Step2.5": 2.5, "Step3": 3, "Step4": 4,
    "Step5": 5, "Step6": 6, "Step7": 7, "Step8": 8, "Step9": 9,
}


class BuildDriver:
    """13-step compilation driver."""

    def __init__(self, software: str, version: str = "",
                 skip_check: bool = False, force: bool = False,
                 resume_from: str | None = None, pdir: str | None = None):
        self.software = software
        self.version = version
        self.skip_check = skip_check
        self.force = force
        self.resume_from = _STEP_MAP.get(resume_from, 0) if resume_from else 0

        self.pdir = Path(pdir) if pdir else Path(find_project_dir())
        self.script_dir = self.pdir / "scripts"
        self.py = os.environ.get("OHC_PY", "python3")

        first_letter = software[0].lower()
        self.archive_dir = self.pdir / "archives" / first_letter / software / version
        self.tmpdir = os.environ.get("TMPDIR", os.path.expanduser("~/tmp"))
        self.test_prefix = Path(self.tmpdir) / f"test-install-{software}-{version or 'latest'}"
        self.log_file = Path(self.tmpdir) / f"build-driver-{software}-{version or 'latest'}.log"

        # Build context (loaded after Step 1)
        self.build_src_dir: Path | None = None
        self.default_prefix: str = os.path.expanduser("~/usr/local")
        self.build_system: str = ""
        self.ctx_data: dict[str, str] = {}
        self.ctx_file: Path | None = None

        # Engine results
        self.ep_match_id = ""
        self.ep_fix_cmd = ""
        self.ep_auto_retry = False

        # Actual configure command (for write-back to manifest.yaml)
        self._actual_configure_cmd: str = ""

    @property
    def staging_prefix(self) -> Path:
        """DESTDIR staging install path: $DESTDIR/$PREFIX/

        With DESTDIR mode:
          configure --prefix=$DEFAULT_PREFIX  (runtime path, hardcoded into binary)
          make install DESTDIR=$TEST_PREFIX   (files land at $TEST_PREFIX/$DEFAULT_PREFIX/)

        Binary hardcoded paths are $DEFAULT_PREFIX (correct runtime path).
        Package builder collects from this staging path.
        """
        return self.test_prefix / self.default_prefix.lstrip("/")

    def should_run(self, step: float) -> bool:
        return step >= self.resume_from

    # ── Helpers ──

    def _log(self, msg: str) -> None:
        ts = datetime.now().strftime("%H:%M:%S")
        line = f"[{ts}] {msg}"
        print(line)
        with open(self.log_file, "a", encoding="utf-8") as f:
            f.write(line + "\n")

    def _run(self, cmd: str | list[str], *, cwd: str | None = None,
             env_extra: dict | None = None, capture: bool = False) -> int:
        """Run command, return exit code."""
        if isinstance(cmd, str):
            cmd = [_SHELL, "-c", cmd]
        env = os.environ.copy()
        if env_extra:
            env.update(env_extra)
        try:
            result = subprocess.run(
                cmd, env=env, cwd=cwd or (str(self.build_src_dir) if self.build_src_dir else None),
                stdout=subprocess.PIPE if capture else None,
                stderr=subprocess.STDOUT if capture else None,
                text=True,
            )
            return result.returncode
        except FileNotFoundError:
            log_fail(f"Command not found: {cmd[0]}")
            return 1

    def _run_capture(self, cmd: str | list[str], **kw) -> tuple[int, str]:
        """Run command, return (exit_code, output)."""
        if isinstance(cmd, str):
            cmd = [_SHELL, "-c", cmd]
        env = os.environ.copy()
        if "env_extra" in kw:
            env.update(kw.pop("env_extra"))
        try:
            result = subprocess.run(cmd, env=env, capture_output=True, text=True, **kw)
            return result.returncode, (result.stdout or "") + (result.stderr or "")
        except FileNotFoundError:
            return 1, ""

    def _find_tool(self, name: str) -> str:
        """Find GNU version of tool, fallback to system."""
        candidates = [
            os.path.expanduser(f"~/usr/local/bin/{name}"),
            str(self.test_prefix / "bin" / name),
        ]
        for c in candidates:
            if os.path.isfile(c) and os.access(c, os.X_OK):
                rc, out = self._run_capture([c, "--version"])
                if rc == 0 and "GNU" in out:
                    return c
                return c
        # System
        rc, path = self._run_capture(["which", name])
        if rc == 0:
            return path.strip()
        return name

    def _task_card_update(self, step: str, status: str, detail: str = "") -> None:
        tc = self.archive_dir / "TASK_CARD.md"
        if not tc.exists():
            return
        lines = tc.read_text(encoding="utf-8").split("\n")
        for i, l in enumerate(lines):
            if step in l and ("⏳" in l or "🔄" in l):
                lines[i] = f"- [{step}] {status} — {detail} — {datetime.now().strftime('%H:%M:%S')}"
                break
        tc.write_text("\n".join(lines), encoding="utf-8")

    def _emit_checkpoint(self, step: str, step_name: str, doc_actions: list[str]) -> None:
        """⭐ D8 规则：成功阶段后提醒 AI 更新文档。
        
        输出 CHECKPOINT 块（类似 HANDOFF 但用于成功阶段），
        提醒 AI 在 PROGRESS.md 和 README.md 中记录此阶段的操作。
        """
        lines = [
            "",
            "╔═══ 📝 CHECKPOINT — 文档更新提醒 ═══════════════════╗",
            f"║ STEP: {step} ({step_name})",
            f"║ SOFTWARE: {self.software} {self.version}",
            f"║ ARCHIVE_DIR: {self.archive_dir}",
            "║",
            "║ ⭐ D8 规则要求：此阶段完成后必须更新文档",
            "║",
            "║ 文档更新要求:",
        ]
        for action in doc_actions:
            lines.append(f"║   - {action}")
        lines += [
            "║",
            "║ 提醒：这些记录是断点续传的关键，请勿跳过！",
            "╚══════════════════════════════════════════════════╝",
            "",
        ]
        print("\n".join(lines), file=sys.stdout)

    # ── Engine & Handoff & Dependency Detection ──

    # ⭐ 新增：GNU 工具必需列表（toybox 版本行为差异会导致编译失败）
    # 这些工具在 configure/make 中会被高频使用，行为差异会导致静默失败
    _GNU_TOOLS_REQUIRED = {
        "sed": {"cmd_pkgs_ver": "4.9", "reason": "正则匹配能力"},
        "gawk": {"cmd_pkgs_ver": "5.3.0", "reason": "复杂脚本处理"},
        "grep": {"cmd_pkgs_ver": "3.11", "reason": "-P 正则支持"},
        "find": {"cmd_pkgs_ver": "", "reason": "-newer 等选项"},
        "coreutils": {"cmd_pkgs_ver": "9.10", "reason": "install、cp 等命令"},
    }

    # ⭐ 新增：依赖缺失模式识别
    _DEPENDENCY_PATTERNS = [
        # pkg-config 模式
        (r"Package '([^']+)', required by '[^']+', not found", "library"),
        (r"Package '([^']+)' not found", "library"),
        (r"Could not find ([a-zA-Z0-9_-]+)\.pc", "library"),
        # autotools 模式
        (r"checking for ([a-zA-Z0-9_-]+)\.\.\. no", "library"),
        (r"configure: error: ([a-zA-Z0-9_-]+) not found", "library"),
        (r"configure: error: ([a-zA-Z0-9_-]+) development files not found", "library"),
        (r"([a-zA-Z0-9_-]+)-development files not found", "library"),
        # cmake 模式
        (r"Could NOT find ([A-Za-z0-9_]+)", "library"),
        (r"FIND_PACKAGE([^)]+) could not find ([A-Za-z0-9_]+)", "library"),
        # 构建工具缺失
        (r"([a-zA-Z0-9_-]+): command not found", "tool"),
        (r"which: no ([a-zA-Z0-9_-]+) in", "tool"),
        (r"([a-zA-Z0-9_-]+) is required to build", "tool"),
        # 命令差异
        (r"([a-zA-Z0-9_-]+): unsupported option", "command"),
    ]

    def _detect_dependency_missing(self) -> tuple[str, str, str, bool]:
        """解析 configure 输出和 config.log，检测依赖缺失。

        Returns:
            (missing_dep, missing_ver, dep_type, prebuilt_available)
            如 ("openssl", "1.1.1", "library", True)
            或未检测到时返回 ("", "", "", False)
        """
        # 读取 build log
        if not self.log_file.exists():
            return "", "", "", False
        log_text = self.log_file.read_text(encoding="utf-8", errors="replace")

        # 读取 config.log（configure 失败时更详细的错误信息）
        config_log = ""
        if self.build_src_dir:
            cl = self.build_src_dir / "config.log"
            if cl.exists():
                config_log = cl.read_text(encoding="utf-8", errors="replace")
            # VPATH build 时 config.log 在 build 目录
            if self.vpath_dir:
                cl2 = self.vpath_dir / "config.log"
                if cl2.exists():
                    config_log += "\n" + cl2.read_text(encoding="utf-8", errors="replace")

        combined = log_text + "\n" + config_log

        for pattern, dep_type in self._DEPENDENCY_PATTERNS:
            match = re.search(pattern, combined, re.IGNORECASE)
            if match:
                dep_name = match.group(1).lower()
                # 规范化依赖名（处理常见变体）
                dep_name = self._normalize_dep_name(dep_name)
                # 检查是否有预编译包
                prebuilt = is_prebuilt_available(dep_name)
                # 获取所需版本（如果有）
                ver_match = re.search(rf"{dep_name}[^\d]*(\d+\.\d+\.\d+|\d+\.\d+)", combined)
                missing_ver = ver_match.group(1) if ver_match else ""
                return dep_name, missing_ver, dep_type, prebuilt

        return "", "", "", False

    def _normalize_dep_name(self, name: str) -> str:
        """规范化依赖名称，处理常见变体。"""
        # 处理 lib 前缀
        name = name.lower()
        if name.startswith("lib"):
            name = name[3:]
        # 处理常见别名
        aliases = {
            "ssl": "openssl",
            "crypto": "openssl",
            "crypto.so": "openssl",
            "ffi": "libffi",
            "pcreposix": "pcre",
            "pcrecpp": "pcre",
            "pcre2-posix": "pcre2",
            "pcre2-8": "pcre2",
            "ncursesw": "ncurses",
            "curl": "libcurl",  # 注意：curl 在 cmd-pkgs 中是工具名，库是 libcurl
        }
        return aliases.get(name, name)

    def _run_engine(self, log_file: Path | None = None, tail: int = 50) -> bool:
        """Run error pattern matching engine. Returns True if hit.
        
        For configure failures, also reads config.log to get the real error
        (e.g. config.sub rejection) instead of only the driver's own log
        which may just say 'configure failed (RC=127)'.
        """
        lf = log_file or self.log_file
        if not lf.exists():
            return False
        error_text = lf.read_text(encoding="utf-8", errors="replace")[-tail * 200:]
        if not error_text.strip():
            return False

        # Supplement with config.log tail for configure failures
        if self.build_src_dir:
            config_log = self.build_src_dir / "config.log"
            if config_log.exists():
                config_tail = config_log.read_text(encoding="utf-8", errors="replace")[-tail * 200:]
                # Append config.log errors to engine input for accurate matching
                error_text = error_text + "\n--- config.log ---\n" + config_tail

        result = run_engine(error_text)
        if not result.matched or not result.entry:
            return False

        self.ep_match_id = result.match_id
        self.ep_fix_cmd = result.entry.rec_command or ""
        self.ep_auto_retry = result.entry.rec_auto_fix

        return bool(self.ep_match_id)

    def _emit_handoff(self, reason: str, exit_code: int, step: str,
                      ep_id: str = "none", gap: bool = False,
                      actions: list[str] | None = None,
                      missing_dep: str = "", missing_ver: str = "",
                      dep_type: str = "", prebuilt: bool = False) -> None:
        """Emit HANDOFF block and exit."""
        resume_step_num = int(re.sub(r'[^0-9]', '', step))
        resume_cmd = f"python3 {self.script_dir}/ohc-run.py build {self.software} {self.version} --resume-from=Step{resume_step_num + 1}"

        # Write .manual-mode-stop
        stop_file = self.pdir / ".manual-mode-stop"
        stop_file.write_text(f"{self.software} {self.version}\n{step}\n{reason}\n", encoding="utf-8")

        # Inject track-edit reminder into actions (R6 enforcement)
        final_actions = list(actions or [])
        track_reminder = (
            f"⚠️ R6: 每次修改源文件后必须运行: "
            f"python3 {self.script_dir}/ohc-run.py track-edit add {self.software} {self.version} <修改的文件路径>"
        )
        final_actions.insert(0, track_reminder)

        # ⭐ 新增：依赖缺失时的专用 actions
        if reason in ("dependency_missing", "build_tool_missing", "command_mismatch"):
            if prebuilt:
                # 有预编译包：生成安装命令
                install_url = get_install_url(missing_dep) or ""
                ver_to_install = missing_ver or get_available_version(missing_dep) or ""
                dep_actions = [
                    f"⭐ R18 铁律：依赖缺失，必须先安装预编译包",
                    f"安装命令: curl -fsSL {install_url} | sh -s -- {missing_dep} {ver_to_install}",
                    f"验证安装: pkg-config --modversion {missing_dep} 或 {missing_dep} --version",
                    "运行 RESUME_CMD 继续",
                ]
            else:
                # 无预编译包：需要手动编译
                dep_actions = [
                    f"⭐ 依赖 {missing_dep} 无预编译包，需手动编译",
                    f"查 dependencies.md 编译顺序，先编 {missing_dep}",
                    f"或创建子任务编译: createSubTask(objective='编译 {missing_dep}')",
                    "运行 RESUME_CMD 继续",
                ]
            final_actions = dep_actions

        # Build HandoffData and emit directly
        data = HandoffData(
            exit_reason=reason,
            exit_code=exit_code,
            step_failed=step,
            resume_cmd=resume_cmd,
            knowledge_hit=ep_id or "none",
            knowledge_gap=gap,
            log_file=str(self.log_file),
            src_dir=str(self.build_src_dir or ""),
            task_card=str(self.archive_dir / "TASK_CARD.md"),
            software_name=self.software,
            software_version=self.version,
            archive_dir=str(self.archive_dir),
            ai_next_actions=final_actions,
            # ⭐ 新增字段
            missing_dependency=missing_dep,
            missing_version=missing_ver,
            dependency_type=dep_type,
            precompiled_available=prebuilt,
        )
        emit_handoff(data)
        sys.exit(exit_code)

    def _error_recovery(self, step_name: str, step_num: float,
                        cmd_fn, retry_fn=None) -> int:
        """Unified error recovery pipeline (R15 + R18 依赖检测 + 工具自动安装)."""
        rc = cmd_fn()
        if rc == 0:
            return 0

        self._log(f"❌ {step_name} failed (RC={rc})")

        # 读取错误日志
        log_text = ""
        if self.log_file.exists():
            log_text = self.log_file.read_text(encoding="utf-8", errors="replace")
        
        # 补充 config.log（configure 失败时更详细）
        if step_name == "configure" and self.build_src_dir:
            for cl_path in [
                self.build_src_dir / "config.log",
                (self.vpath_dir or self.build_src_dir) / "config.log"
            ]:
                if cl_path.exists():
                    log_text += "\n--- config.log ---\n" + cl_path.read_text(encoding="utf-8", errors="replace")

        # ⭐ R18 扩展：先尝试自动安装缺失的工具
        installed = auto_install_missing_tools_from_log(log_text, self.default_prefix)
        if installed:
            self._log(f"🔄 已自动安装工具: {', '.join(installed)}，重试...")
            # 重试
            rc2 = cmd_fn()
            if rc2 == 0:
                self._log(f"✅ 重试成功")
                return 0
            self._log(f"❌ 重试仍然失败")

        # ⭐ R18 铁律：检测依赖缺失
        if step_name == "configure":
            dep_name, dep_ver, dep_type, prebuilt = self._detect_dependency_missing()
            if dep_name:
                self._log(f"⚠️ 检测到依赖缺失: {dep_name} {dep_ver} (类型={dep_type}, 预编译包={prebuilt})")
                # 根据依赖类型设置 EXIT_REASON
                exit_reason = "dependency_missing" if dep_type == "library" else \
                              "build_tool_missing" if dep_type == "tool" else "command_mismatch"
                self._emit_handoff(
                    exit_reason, 2, f"Step{int(step_num)}",
                    missing_dep=dep_name, missing_ver=dep_ver,
                    dep_type=dep_type, prebuilt=prebuilt,
                )
                return rc  # unreachable

        # Run engine
        hit = self._run_engine()
        if hit and self.ep_auto_retry and self.ep_fix_cmd and retry_fn:
            self._log(f"🔄 Auto-retry with: {self.ep_fix_cmd}")
            rc2 = retry_fn(self.ep_fix_cmd)
            if rc2 == 0:
                self._log(f"✅ Auto-retry succeeded")
                return 0
            self._log(f"❌ Auto-retry also failed")

        # Emit HANDOFF
        if hit:
            self._emit_handoff(
                f"{step_name}_failed", 2, f"Step{int(step_num)}",
                ep_id=self.ep_match_id, gap=False,
                actions=[f"参考 {self.ep_match_id} 方案修复源码", "运行 RESUME_CMD 继续"],
            )
        else:
            self._emit_handoff(
                f"{step_name}_failed", 2, f"Step{int(step_num)}",
                ep_id="none", gap=True,
                actions=["诊断错误原因并修复源码",
                         "修复成功后沉淀到知识图谱(graph add)",
                         "运行 RESUME_CMD 继续"],
            )
        return rc  # unreachable

    # ── Step 1: init-build ──

    def _step1_init(self) -> None:
        if not self.should_run(1):
            # Even when resuming past Step1, we must load the build context
            # because all subsequent steps depend on BUILD_SRC_DIR etc.
            if not self.ctx_data:
                self._load_context()
            return
        self._log("═══ [1/13] init-build ═══")

        # Find or create context file
        ctx_pattern = f".build-context-{self.software}-{self.version}*"
        ctx_files = list(self.pdir.glob(ctx_pattern))

        if ctx_files and not self.force:
            self.ctx_file = ctx_files[0]
            self._log(f"使用已有上下文: {self.ctx_file.name}")
        else:
            rc = init_build(self.software, self.version, mode="auto",
                            force=self.force, pdir=str(self.pdir))
            if rc != 0:
                log_fail("init-build 失败")
                raise RuntimeError("init-build 失败")

            ctx_files = list(self.pdir.glob(ctx_pattern))
            if not ctx_files:
                log_fail("init-build 未生成 .build-context 文件")
                raise RuntimeError("init-build 未生成 .build-context 文件")
            self.ctx_file = ctx_files[0]

        self._load_context()
        self._task_card_update("1", "✅完成", "init-build OK")
        self._log(f"✅ 源码: {self.build_src_dir}")

    def _load_context(self) -> None:
        """Load build context from .build-context file into instance vars."""
        if not self.ctx_file:
            ctx_pattern = f".build-context-{self.software}-{self.version}*"
            ctx_files = list(self.pdir.glob(ctx_pattern))
            if not ctx_files:
                log_fail("未找到 .build-context 文件")
                raise RuntimeError("未找到 .build-context 文件")
            self.ctx_file = ctx_files[0]

        self.ctx_data = parse_build_context(str(self.ctx_file))
        self.build_src_dir = Path(self.ctx_data.get("BUILD_SRC_DIR", ""))
        self.default_prefix = self.ctx_data.get("DEFAULT_PREFIX", self.default_prefix)
        self.build_system = self.ctx_data.get("BUILD_SYSTEM", "")
        self.archive_dir = Path(self.ctx_data.get("BUILD_ARCHIVE_DIR", str(self.archive_dir)))

        if not self.build_src_dir or not self.build_src_dir.exists():
            log_fail(f"BUILD_SRC_DIR 不存在: {self.build_src_dir}")
            raise RuntimeError(f"BUILD_SRC_DIR 不存在: {self.build_src_dir}")

    # ── Step 1.5: Archive history ──

    def _step15_history(self) -> None:
        if not self.should_run(1.5):
            return
        self._log("═══ [1.5/13] 归档历史查询 (R11) ═══")

        readme = self.archive_dir / "README.md"
        if readme.exists():
            lines = readme.read_text(encoding="utf-8").split("\n")
            if len(lines) > 10:
                self._log(f"已有归档记录 ({len(lines)} 行)")
                for line in lines[:20]:
                    self._log(f"  {line}")
        else:
            self._log("首次编译，无历史记录")

    # ── Step 2: apply patches ──

    def _step2_patches(self) -> None:
        if not self.should_run(2):
            return
        self._log("═══ [2/13] apply-patches ═══")

        patch_dir = self.archive_dir / "patches"
        if not patch_dir.exists():
            self._log("无补丁目录，跳过")
            return

        patches = sorted(patch_dir.glob("*.patch"))
        if not patches:
            self._log("无补丁文件，跳过")
            return

        applied = 0
        for p in patches:
            # Try multiple strip levels (-p1, -p0, -p2) to handle path mismatches
            applied_this = False
            for strip_level in [1, 0, 2]:
                rc, out = self._run_capture(
                    f"patch -p{strip_level} --dry-run < {p}", cwd=str(self.build_src_dir)
                )
                if rc == 0:
                    rc2, _ = self._run_capture(
                        f"patch -p{strip_level} < {p}", cwd=str(self.build_src_dir)
                    )
                    if rc2 == 0:
                        applied += 1
                        applied_this = True
                        self._log(f"  ✅ {p.name} (strip=-p{strip_level})")
                        break
                else:
                    # Distinguish: already applied vs path mismatch vs other
                    if "Reversed (or previously applied) patch detected" in out:
                        self._log(f"  ⏭️ {p.name} (已应用)")
                        applied_this = True
                        break
            if not applied_this:
                self._log(f"  ⚠️ {p.name} (所有 strip level 均失败，需手动应用)")

        self._task_card_update("2", "✅完成", f"{applied} patches applied")
        self._log(f"✅ 应用 {applied}/{len(patches)} 个补丁")

    # ── Step 2.5: pre-scan ──

    def _step2b_prescan(self) -> None:
        if not self.should_run(2.5):
            return
        if not self.build_src_dir or not self.build_src_dir.exists():
            return

        self._log("═══ [2.5/13] 预编译风险扫描 (pre-scan) ═══")

        rules_path = self.pdir / "knowledge" / "graph" / "pre-scan-rules.yaml"
        report_path = self.build_src_dir / ".pre-scan-report.yaml"

        try:
            from .pre_scan import PreScanner
            scanner = PreScanner(str(self.build_src_dir),
                                 rules_path=str(rules_path) if rules_path.exists() else None)
            report = scanner.save_report(str(report_path))
        except Exception as e:
            self._log(f"⚠️ pre-scan 异常（非阻塞）: {e}")
            self._task_card_update("2.5", "⚠️跳过", str(e)[:60])
            return

        # Log summary
        summary = report.get("summary", {})
        emoji_map = {"critical": "🔴", "high": "🟠", "medium": "🟡", "low": "🟢", "info": "ℹ️", "auto": "🔧"}
        total = sum(summary.values())
        for level in ("critical", "high", "medium", "low", "info", "auto"):
            count = summary.get(level, 0)
            if count > 0:
                self._log(f"  {emoji_map.get(level, '?')} {level}: {count} 项")

        # Highlight critical/high findings
        for finding in report.get("findings", []):
            if finding["severity"] in ("critical", "high"):
                self._log(f"  ⚡ {finding['rule_id']}: {finding['description']}")
                if finding.get("solution_hint"):
                    self._log(f"     → {finding['solution_hint']}")

        self._task_card_update("2.5", "✅完成", f"{total} findings")
        self._log(f"✅ 预扫描报告: {report_path}")

    # ── Build system detection ──

    def _detect_build_system(self) -> str:
        src = self.build_src_dir
        if (src / "CMakeLists.txt").exists() and not (src / "configure").exists():
            return "cmake"
        if (src / "meson.build").exists():
            return "meson"
        if (src / "Makefile.PL").exists() or (src / "Build.PL").exists():
            return "perl"
        if (src / "setup.py").exists() or (src / "pyproject.toml").exists():
            return "python"
        if any((src / f).exists() for f in ("configure", "configure.ac", "configure.in")):
            return "autotools"
        if any((src / f).exists() for f in ("Makefile", "GNUmakefile")):
            return "makefile"
        return "unknown"

    def _read_extra_args(self) -> list[str]:
        """Read extra configure args from manifest.yaml configure_options."""
        manifest = self.archive_dir / "manifest.yaml"
        if not manifest.exists():
            return []
        args = []
        content = manifest.read_text(encoding="utf-8")
        # Find configure_options: section and parse its list items
        in_opts = False
        for line in content.split("\n"):
            stripped = line.lstrip()
            if stripped.startswith("configure_options:"):
                in_opts = True
                continue
            if in_opts:
                if stripped.startswith("- "):
                    # Extract value from list item, strip quotes
                    val = stripped[2:].strip().strip('"').strip("'")
                    # Skip --prefix — driver always sets it via --prefix={default_prefix}
                    if val.startswith("--prefix="):
                        continue
                    if val and val not in ("null", "~"):
                        args.append(val)
                elif stripped == "" or stripped.startswith("#"):
                    continue
                else:
                    break
        return args

    # ── Step 3: configure ──

    @property
    def vpath_dir(self) -> Path | None:
        """VPATH build directory (separate from source)."""
        if self.build_src_dir:
            d = self.build_src_dir.parent / f"{self.software}-{self.version}-build"
            if d.exists():
                return d
        return None

    def _step3_configure(self) -> None:
        if not self.should_run(3):
            return
        self._log("═══ [3/13] configure ═══")

        # ⭐ R18 扩展：configure 前检查常见构建工具可用性（动态发现）
        self._log("  检查构建工具可用性...")
        tool_status = check_common_build_tools(self.default_prefix)
        missing_tools = []
        
        for tool, (available, info) in tool_status.items():
            if available and "GNU" in info:
                self._log(f"  ✅ {tool}: {info[:40]}")
            elif available:
                self._log(f"  ⚠️ {tool}: {info[:40]}")
                # 记录可能需要替换的工具（toybox 版本）
                pkg_name, _ = get_package_for_tool(tool)
                if pkg_name:
                    missing_tools.append(tool)
            else:
                self._log(f"  ❌ {tool}: {info}")
                pkg_name, _ = get_package_for_tool(tool)
                if pkg_name:
                    missing_tools.append(tool)
        
        # 自动安装缺失的工具（如果有预编译包）
        if missing_tools:
            self._log(f"  发现 {len(missing_tools)} 个工具需安装: {', '.join(missing_tools)}")
            for tool in missing_tools[:3]:  # 最多尝试安装 3 个，避免太慢
                rc = auto_install_tool(tool, self.default_prefix)
                if rc == 0:
                    self._log(f"  ✅ 已安装: {tool}")
                else:
                    self._log(f"  ⚠️ 安装失败: {tool}")

        self._run("make distclean 2>/dev/null || true")
        self._run("rm -rf build builddir _build")

        self.build_system = self._detect_build_system()
        extra = self._read_extra_args()
        extra_str = " ".join(extra)

        self._log(f"构建系统: {self.build_system}")

        if self.build_system == "autotools":
            # Use VPATH build: configure runs in a separate build directory
            # to avoid Permission denied errors when source tree is owned by
            # a different UID (HarmonyOS sandbox).
            vpath_dir = self.build_src_dir.parent / f"{self.software}-{self.version}-build"
            vpath_dir.mkdir(parents=True, exist_ok=True)

            _configure_cmd = f"sh {self.build_src_dir}/configure --prefix={self.default_prefix} {extra_str}".strip()
            self._actual_configure_cmd = _configure_cmd

            # TMPDIR: config.status uses "mktemp -d ./confXXXXXX" which fails
            # on HarmonyOS due to SGID + umask 077 conflict.  Point TMPDIR
            # to $HOME/tmp where the user has unrestricted write access.
            _env_extra = {
                "PKG_CONFIG_PATH": f"{self.default_prefix}/lib/pkgconfig",
                "TMPDIR": str(Path(self.tmpdir)),
            }

            def do_configure():
                return self._run(_configure_cmd, cwd=str(vpath_dir), env_extra=_env_extra)

            def do_retry(fix_cmd):
                self._run("make distclean 2>/dev/null || true", cwd=str(vpath_dir))
                retry_cmd = f"sh {self.build_src_dir}/configure --prefix={self.default_prefix} {fix_cmd} {extra_str}".strip()
                return self._run(retry_cmd, cwd=str(vpath_dir), env_extra=_env_extra)

            self._error_recovery("configure", 3, do_configure, do_retry)

        elif self.build_system == "cmake":
            _configure_cmd = f"cmake -DCMAKE_INSTALL_PREFIX={self.default_prefix} -DCMAKE_BUILD_TYPE=Release {extra_str} ..".strip()
            self._actual_configure_cmd = _configure_cmd
            self._run("mkdir -p build")
            rc = self._run(_configure_cmd,
                          cwd=str(self.build_src_dir / "build"))
            if rc != 0:
                self._emit_handoff("cmake_failed", 2, "Step3",
                    actions=["检查 CMakeLists.txt 配置", "运行 RESUME_CMD 继续"])

        elif self.build_system == "meson":
            _configure_cmd = f"meson setup builddir --prefix={self.default_prefix} {extra_str}".strip()
            self._actual_configure_cmd = _configure_cmd
            rc = self._run(_configure_cmd)
            if rc != 0:
                self._emit_handoff("meson_failed", 2, "Step3",
                    actions=["检查 meson.build 配置", "运行 RESUME_CMD 继续"])

        elif self.build_system == "perl":
            _configure_cmd = f"perl Makefile.PL PREFIX={self.default_prefix} {extra_str}".strip()
            self._actual_configure_cmd = _configure_cmd
            rc = self._run(_configure_cmd)
            if rc != 0:
                self._emit_handoff("perl_configure_failed", 2, "Step3")

        elif self.build_system == "python":
            self._log("Python 项目无需单独 configure")

        elif self.build_system == "makefile":
            self._log("Makefile 项目无需 configure")

        else:
            self._log("❌ 无法检测构建系统")
            self._emit_handoff("unknown_build_system", 2, "Step3",
                actions=["手动确认构建系统并配置", "运行 RESUME_CMD 继续"])

        self._task_card_update("3", "✅完成", f"{self.build_system} OK")
        
        # ⭐ D8 规则：configure 完成后提醒更新文档
        self._emit_checkpoint("Step3", "configure", [
            "PROGRESS.md: 在对话记录部分写入 configure 参数和耗时",
            "PROGRESS.md: 更新 Phase 2 checkbox 为完成",
            f"configure 参数: {self._actual_configure_cmd or '自动检测'}",
        ])

    # ── Step 4: make ──

    def _step4_make(self) -> None:
        if not self.should_run(4):
            return
        self._log("═══ [4/13] make ═══")

        if self.build_system == "python":
            self._log("Python 项目跳过 make")
            self._task_card_update("4", "⏭️跳过", "python")
            return

        def get_make_cmd():
            if self.build_system == "cmake":
                return f"make -C build -j{MAKE_JOBS}"
            elif self.build_system == "meson":
                return f"ninja -C builddir -j{MAKE_JOBS}"
            return f"make -j{MAKE_JOBS}"

        def do_make():
            cwd = str(self.vpath_dir) if self.vpath_dir else None
            return self._run(get_make_cmd(), cwd=cwd)

        def do_retry(fix_cmd):
            cwd = str(self.vpath_dir) if self.vpath_dir else None
            self._run("make clean 2>/dev/null || true", cwd=cwd)
            return self._run(f"{get_make_cmd()} {fix_cmd}", cwd=cwd)

        self._error_recovery("make", 4, do_make, do_retry)
        self._task_card_update("4", "✅完成", "make OK")
        
        # ⭐ D8 规则：make 完成后提醒更新文档
        self._emit_checkpoint("Step4", "make", [
            "PROGRESS.md: 在对话记录部分写入编译结果和遇到的问题",
            "README.md: 如有补丁应用，在补丁说明部分记录用途",
        ])

    # ── Step 5: install ──

    def _step5_install(self) -> None:
        if not self.should_run(5):
            return
        self._log("═══ [5/13] make install (DESTDIR mode) ═══")

        if self.force and self.test_prefix.exists():
            import shutil
            shutil.rmtree(self.test_prefix, ignore_errors=True)
        self.test_prefix.mkdir(parents=True, exist_ok=True)

        install_tool = self._find_tool("install")
        sed_tool = self._find_tool("sed")
        install_args = f"INSTALL={install_tool} HELP2MAN=/bin/true MAKEINFO=/bin/true SED={sed_tool}"
        destdir = f"DESTDIR={self.test_prefix}"

        rc = 1
        # VPATH: autotools build dir (make install must run where Makefile is)
        make_cwd = str(self.vpath_dir) if self.vpath_dir else None
        if self.build_system in ("autotools", "perl", "makefile"):
            # Three-tier fallback with DESTDIR
            rc = self._run(f"make install-binPROGRAMS install-binSCRIPTS {destdir} {install_args}", cwd=make_cwd)
            if rc != 0:
                rc = self._run(f"make install {destdir} {install_args}", cwd=make_cwd)
            if rc != 0:
                rc = self._run(f"make install SUBDIRS=\"lib src\" {destdir} {install_args}", cwd=make_cwd)
        elif self.build_system == "cmake":
            rc = self._run(f"make -C build install {destdir} {install_args}")
        elif self.build_system == "meson":
            rc = self._run(f"DESTDIR={self.test_prefix} ninja -C builddir install")
        elif self.build_system == "python":
            rc = self._run(f"pip install --root={self.test_prefix} --prefix={self.default_prefix} --no-deps .")

        # Verify output (use staging_prefix, not test_prefix)
        sp = self.staging_prefix
        bin_count = len(list(sp.rglob("bin/*"))) if sp.exists() else 0
        lib_count = len(list(sp.rglob("lib*/*.so*"))) + len(list(sp.rglob("lib*/*.a")))

        if bin_count == 0 and lib_count == 0:
            log_fail(f"安装无产物 (staging: {sp})")
            raise RuntimeError("安装无产物")

        self._task_card_update("5", "✅完成", f"bin={bin_count} lib={lib_count}")
        self._log(f"✅ 安装完成: bin={bin_count} lib={lib_count} (staging: {sp})")
        
        # ⭐ D8 规则：install 完成后提醒更新文档
        self._emit_checkpoint("Step5", "install", [
            "PROGRESS.md: 更新 Phase 2.5 checkbox 为完成",
            "PROGRESS.md: 在源码修改清单部分记录安装文件",
            "README.md: 如遇到问题已解决，在遇到的问题部分记录解决方案",
        ])

    # ── Step 6: safety popup ──

    def _step6_safety(self) -> None:
        if not self.should_run(6):
            return
        self._log("═══ [6/13] 安全弹窗 (R7) ═══")

        # Quick version check for first 5 binaries
        bins = sorted(self.staging_prefix.rglob("bin/*"))[:5]
        for b in bins:
            if b.is_file() and os.access(b, os.X_OK):
                self._run_capture([str(b), "--version"], timeout=5)

        self._task_card_update("6", "✅完成", "safety check OK")

    # ── Step 7: make check ──

    def _step7_check(self) -> None:
        if not self.should_run(7):
            return
        self._log("═══ [7/13] make check ═══")

        if self.skip_check:
            report = self.archive_dir / "reports" / "test-report.md"
            report.parent.mkdir(parents=True, exist_ok=True)
            report.write_text(f"# Test Report\n\nStatus: skipped (--skip-check)\n", encoding="utf-8")
            self._task_card_update("7", "⏭️跳过", "--skip-check")
            return

        check_log = Path(self.tmpdir) / f"make-check-{os.getpid()}.log"

        # Build check command
        if self.build_system == "cmake":
            check_cmd = f"make -C build check"
        elif self.build_system == "meson":
            check_cmd = f"ninja -C builddir test"
        else:
            check_cmd = f"make check"

        # Run with timeout (simplified from bash's complex monitoring)
        start_time = time.time()
        proc = subprocess.Popen(
            [_SHELL, "-c", check_cmd],
            cwd=str(self.build_src_dir),
            stdout=open(check_log, "w"),
            stderr=subprocess.STDOUT,
            env=os.environ.copy(),
        )

        while proc.poll() is None:
            elapsed = time.time() - start_time
            if elapsed > CHECK_TIMEOUT:
                proc.terminate()
                self._log(f"⚠️ make check 超时 ({CHECK_TIMEOUT}s)")
                break
            time.sleep(15)

        rc = proc.returncode or 0

        # Generate report
        report = self.archive_dir / "reports" / "test-report.md"
        report.parent.mkdir(parents=True, exist_ok=True)
        status = "PASS" if rc == 0 else "FAIL"
        report.write_text(
            f"# Test Report\n\nStatus: {status}\nRC: {rc}\n"
            f"Duration: {int(time.time() - start_time)}s\n"
            f"Log: {check_log}\n", encoding="utf-8")

        self._task_card_update("7", "✅完成" if rc == 0 else "⚠️部分", f"RC={rc}")

    # ── Step 8: staging verify ──

    def _step8_staging(self) -> None:
        if not self.should_run(8):
            return
        self._log("═══ [8/13] Staging 验证 ═══")

        mark = self.archive_dir / ".staging-verified"
        bins = list(self.staging_prefix.rglob("bin/*")) if self.staging_prefix.exists() else []
        exes = [b for b in bins if b.is_file() and os.access(b, os.X_OK)]

        verified = 0
        failed = []
        for exe in exes:
            rc, _ = self._run_capture([str(exe), "--version"], timeout=5)
            if rc == 0:
                verified += 1
            else:
                failed.append(exe.name)

        report = f"verified={verified} failed={len(failed)}"
        if failed:
            report += f" exclude={','.join(failed[:10])}"
            # Write EXCLUDE_LIST
            excl = self.archive_dir / "EXCLUDE_LIST"
            excl.write_text("\n".join(failed), encoding="utf-8")

        mark.write_text(report, encoding="utf-8")
        self._task_card_update("8", "✅完成", report)

    # ── Step 9: package ──

    def _step9_package(self) -> None:
        if not self.should_run(9):
            return
        self._log("═══ [9/13] package ═══")

        builder = PackageBuilder(self.software, self.version,
                                  debug=True, prefix=str(self.staging_prefix),
                                  pdir=str(self.pdir))
        rc = builder.run()
        self._task_card_update("9", "✅完成" if rc == 0 else "⚠️部分", f"RC={rc}")

    # ── Step 10: deploy ──

    def _step10_deploy(self) -> None:
        self._log("═══ [10/13] deploy ═══")

        rc = 0
        for item in self.staging_prefix.iterdir() if self.staging_prefix.exists() else []:
            dst = Path(self.default_prefix) / item.name
            if item.is_dir():
                dst.mkdir(parents=True, exist_ok=True)
                shutil.copytree(str(item), str(dst), dirs_exist_ok=True)
            else:
                shutil.copy2(str(item), str(dst))

        # Ensure executables
        dst_bin = Path(self.default_prefix) / "bin"
        if dst_bin.exists():
            for f in dst_bin.iterdir():
                if f.is_file():
                    try:
                        os.chmod(f, 0o755)
                    except OSError:
                        pass

        self._task_card_update("10", "✅完成" if rc == 0 else "⚠️部分", "deploy")

    # ── Step 11: finish ──

    def _step11_finish(self) -> None:
        self._log("═══ [11/13] finish-build ═══")

        pipeline = FinishPipeline(self.software, self.version, "success",
                                   pdir=str(self.pdir))
        try:
            rc = pipeline.run()
        except Exception as e:
            log_fail(f"finish-build 异常: {e}")
            rc = 1
        self._task_card_update("11", "✅完成" if rc == 0 else "⚠️部分", f"RC={rc}")

    # ── Step 11.5: required files ──

    def _step11b_required_files(self) -> None:
        self._log("═══ [11.5/13] 必填文件校验 ═══")

        required = ["manifest.yaml", "README.md", "PROGRESS.md", "RELEASENOTE.md"]
        missing = []
        for f in required:
            if not (self.archive_dir / f).exists():
                missing.append(f)

        # Auto-generate RELEASENOTE if missing
        if "RELEASENOTE.md" in missing and (self.archive_dir / "manifest.yaml").exists():
            rn = self.archive_dir / "RELEASENOTE.md"
            rn.write_text(
                f"# {self.software} {self.version} — Release Note\n\n"
                f"Auto-generated by build-driver.\n", encoding="utf-8")
            missing.remove("RELEASENOTE.md")

        if missing:
            log_warn(f"缺失必填文件: {missing}")

    # ── Step 12: calibrate ──

    def _write_back_configure_options(self) -> None:
        """Write actual configure args back to manifest.yaml (line-level, no PyYAML)."""
        if not self._actual_configure_cmd:
            return

        # Extract args from the actual command
        parts = self._actual_configure_cmd.split()
        args = []
        for p in parts[1:]:
            if p.startswith("-"):
                args.append(p)

        if not args:
            return

        manifest = self.archive_dir / "manifest.yaml"
        if not manifest.exists():
            return

        content = manifest.read_text(encoding="utf-8")
        lines = content.split("\n")

        # Build the new configure_options lines
        args_yaml = "configure_options:\n" + "\n".join(
            f"  - \"{a}\"" for a in args
        )

        # Find and replace the configure_options section
        new_lines = []
        i = 0
        replaced = False
        while i < len(lines):
            stripped = lines[i].lstrip()
            # Match the start of configure_options: under build_config
            if not replaced and stripped.startswith("configure_options:"):
                # Determine indent level (same as this line)
                indent = lines[i][:len(lines[i]) - len(lines[i].lstrip())]
                # Collect all following lines that are deeper-indented list items
                j = i + 1
                while j < len(lines):
                    next_stripped = lines[j].lstrip()
                    next_indent = lines[j][:len(lines[j]) - len(lines[j].lstrip())]
                    if next_stripped.startswith("- ") and len(next_indent) > len(indent):
                        j += 1
                    elif next_stripped == "":
                        j += 1
                    else:
                        break
                # Replace with new args (preserve original indent)
                for arg_line in args_yaml.split("\n"):
                    if arg_line.startswith("configure_options:"):
                        new_lines.append(indent + arg_line)
                    else:
                        new_lines.append(indent + arg_line)
                i = j
                replaced = True
            else:
                new_lines.append(lines[i])
                i += 1

        if replaced:
            manifest.write_text("\n".join(new_lines), encoding="utf-8")
            self._log(f"✅ 已回写 configure 参数到 manifest.yaml ({len(args)} 项)")
        else:
            # configure_options section not found; try to insert under build_config
            for idx, line in enumerate(lines):
                if "build_config:" in line:
                    indent = line[:len(line) - len(line.lstrip())] + "  "
                    insert_lines = [indent + l for l in args_yaml.split("\n")]
                    for offset, il in enumerate(insert_lines):
                        new_lines.insert(idx + 1 + offset, il)
                    manifest.write_text("\n".join(new_lines), encoding="utf-8")
                    self._log(f"✅ 已新增 configure_options 到 manifest.yaml ({len(args)} 项)")
                    return
            self._log("⚠️ manifest.yaml 中未找到 build_config 段，跳过回写")

    def _step12_calibrate(self) -> None:
        self._log("═══ [12/13] 归档校准 ═══")
        # Simplified calibration check
        self._log(f"归档目录: {self.archive_dir}")
        patches = list((self.archive_dir / "patches").glob("*.patch")) if (self.archive_dir / "patches").exists() else []
        self._log(f"补丁数: {len(patches)}")

        # ── Write back actual configure options to manifest.yaml ──
        self._write_back_configure_options()

    # ── Step 13: cleanup ──

    def _step13_cleanup(self) -> None:
        self._log("═══ [13/13] 清理 ═══")

        # Clean staging
        if self.test_prefix.exists():
            import shutil
            shutil.rmtree(self.test_prefix, ignore_errors=True)
            self._log(f"清理 staging: {self.test_prefix}")

    # ── Main run ──

    def run(self) -> int:
        self._log(f"🚀 开始编译: {self.software} {self.version}")
        self._log(f"   恢复模式: {self.resume_from or '从Step1开始'}")

        self._step1_init()
        self._step15_history()
        self._step2_patches()
        self._step2b_prescan()
        self._step3_configure()
        self._step4_make()
        self._step5_install()
        self._step6_safety()
        self._step7_check()
        self._step8_staging()
        self._step9_package()
        self._step10_deploy()
        self._step11_finish()
        self._step11b_required_files()
        self._step12_calibrate()
        self._step13_cleanup()

        self._log(f"🎉 编译完成: {self.software} {self.version}")
        return 0


# ═══════════════════════════════════════════════════════
# CLI entry
# ═══════════════════════════════════════════════════════

def build_cli(argv: list[str] | None = None) -> int:
    import argparse
    parser = argparse.ArgumentParser(
        prog="ohc build",
        description="13步编译驱动管线",
    )
    parser.add_argument("software", help="软件名称")
    parser.add_argument("version", nargs="?", default="", help="版本号")
    parser.add_argument("--skip-check", action="store_true", help="跳过 make check")
    parser.add_argument("--force", action="store_true", help="强制重新初始化")
    parser.add_argument("--resume-from", dest="resume_from", help="从指定步骤恢复 (Step3-Step9)")
    parser.add_argument("--project-dir")

    args = parser.parse_args(argv)
    driver = BuildDriver(
        args.software, args.version,
        skip_check=args.skip_check,
        force=args.force,
        resume_from=args.resume_from,
        pdir=getattr(args, "project_dir", None),
    )
    try:
        return driver.run()
    except RuntimeError as e:
        log_fail(str(e))
        return 1

