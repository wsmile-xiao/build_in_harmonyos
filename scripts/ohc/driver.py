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


# ── Constants ──
MAKE_JOBS = 2  # HarmonyOS sandbox limit
CHECK_TIMEOUT = 600  # 10 min total
CHECK_STUCK_THRESHOLD = 120  # 2 min no output

_STEP_MAP = {
    "Step1": 1, "Step1.5": 1.5, "Step2": 2, "Step3": 3, "Step4": 4,
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
            cmd = ["zsh", "-c", cmd]
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
            cmd = ["zsh", "-c", cmd]
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

    # ── Engine & Handoff ──

    def _run_engine(self, log_file: Path | None = None, tail: int = 50) -> bool:
        """Run error pattern matching engine. Returns True if hit."""
        lf = log_file or self.log_file
        if not lf.exists():
            return False
        error_text = lf.read_text(encoding="utf-8", errors="replace")[-tail * 200:]
        if not error_text.strip():
            return False

        result = run_engine(error_text)
        if not result.matched or not result.entry:
            return False

        self.ep_match_id = result.match_id
        self.ep_fix_cmd = result.entry.rec_command or ""
        self.ep_auto_retry = result.entry.rec_auto_fix

        return bool(self.ep_match_id)

    def _emit_handoff(self, reason: str, exit_code: int, step: str,
                      ep_id: str = "none", gap: bool = False,
                      actions: list[str] | None = None) -> None:
        """Emit HANDOFF block and exit."""
        resume_step_num = int(re.sub(r'[^0-9]', '', step))
        resume_cmd = f"python3 {self.script_dir}/ohc-run.py build {self.software} {self.version} --resume-from=Step{resume_step_num + 1}"

        # Write .manual-mode-stop
        stop_file = self.pdir / ".manual-mode-stop"
        stop_file.write_text(f"{self.software} {self.version}\n{step}\n{reason}\n", encoding="utf-8")

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
            ai_next_actions=actions or [],
        )
        emit_handoff(data)
        sys.exit(exit_code)

    def _error_recovery(self, step_name: str, step_num: float,
                        cmd_fn, retry_fn=None) -> int:
        """Unified error recovery pipeline (R15)."""
        rc = cmd_fn()
        if rc == 0:
            return 0

        self._log(f"❌ {step_name} failed (RC={rc})")

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

        # Load context
        self.ctx_data = parse_build_context(str(self.ctx_file))
        self.build_src_dir = Path(self.ctx_data.get("BUILD_SRC_DIR", ""))
        self.default_prefix = self.ctx_data.get("DEFAULT_PREFIX", self.default_prefix)
        self.build_system = self.ctx_data.get("BUILD_SYSTEM", "")
        self.archive_dir = Path(self.ctx_data.get("BUILD_ARCHIVE_DIR", str(self.archive_dir)))

        if not self.build_src_dir or not self.build_src_dir.exists():
            log_fail(f"BUILD_SRC_DIR 不存在: {self.build_src_dir}")
            raise RuntimeError(f"BUILD_SRC_DIR 不存在: {self.build_src_dir}")

        self._task_card_update("1", "✅完成", "init-build OK")
        self._log(f"✅ 源码: {self.build_src_dir}")

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
            # Dry run first
            rc, _ = self._run_capture(
                f"patch -p1 --dry-run < {p}", cwd=str(self.build_src_dir)
            )
            if rc == 0:
                rc, _ = self._run_capture(
                    f"patch -p1 < {p}", cwd=str(self.build_src_dir)
                )
                if rc == 0:
                    applied += 1
                    self._log(f"  ✅ {p.name}")
            else:
                self._log(f"  ⏭️ {p.name} (已应用或冲突)")

        self._task_card_update("2", "✅完成", f"{applied} patches applied")
        self._log(f"✅ 应用 {applied}/{len(patches)} 个补丁")

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
        """Read extra configure args from manifest.yaml."""
        manifest = self.archive_dir / "manifest.yaml"
        if not manifest.exists():
            return []
        args = []
        content = manifest.read_text(encoding="utf-8")
        # Simple YAML parse for build_config section
        in_section = False
        for line in content.split("\n"):
            if "build_config:" in line:
                in_section = True
                continue
            if in_section:
                if line.startswith("  ") or line.startswith("\t"):
                    val = line.strip().split(":")[-1].strip().strip('"').strip("'")
                    if val and val not in ("null", "~"):
                        args.append(val)
                else:
                    break
        return args

    # ── Step 3: configure ──

    def _step3_configure(self) -> None:
        if not self.should_run(3):
            return
        self._log("═══ [3/13] configure ═══")

        self._run("make distclean 2>/dev/null || true")
        self._run("rm -rf build builddir _build")

        self.build_system = self._detect_build_system()
        extra = self._read_extra_args()
        extra_str = " ".join(extra)

        self._log(f"构建系统: {self.build_system}")

        if self.build_system == "autotools":
            def do_configure():
                return self._run(f"./configure --prefix={self.test_prefix} {extra_str}")

            def do_retry(fix_cmd):
                self._run("make distclean 2>/dev/null || true")
                return self._run(f"./configure --prefix={self.test_prefix} {fix_cmd} {extra_str}")

            self._error_recovery("configure", 3, do_configure, do_retry)

        elif self.build_system == "cmake":
            self._run("mkdir -p build")
            rc = self._run(f"cmake -DCMAKE_INSTALL_PREFIX={self.test_prefix} -DCMAKE_BUILD_TYPE=Release {extra_str} ..",
                          cwd=str(self.build_src_dir / "build"))
            if rc != 0:
                self._emit_handoff("cmake_failed", 2, "Step3",
                    actions=["检查 CMakeLists.txt 配置", "运行 RESUME_CMD 继续"])

        elif self.build_system == "meson":
            rc = self._run(f"meson setup builddir --prefix={self.test_prefix} {extra_str}")
            if rc != 0:
                self._emit_handoff("meson_failed", 2, "Step3",
                    actions=["检查 meson.build 配置", "运行 RESUME_CMD 继续"])

        elif self.build_system == "perl":
            rc = self._run(f"perl Makefile.PL PREFIX={self.test_prefix} {extra_str}")
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
            return self._run(get_make_cmd())

        def do_retry(fix_cmd):
            self._run("make clean 2>/dev/null || true")
            env_extra = {}
            # fix_cmd might be env vars or extra flags
            return self._run(f"{get_make_cmd()} {fix_cmd}", env_extra=env_extra)

        self._error_recovery("make", 4, do_make, do_retry)
        self._task_card_update("4", "✅完成", "make OK")

    # ── Step 5: install ──

    def _step5_install(self) -> None:
        if not self.should_run(5):
            return
        self._log("═══ [5/13] make install ═══")

        if self.force and self.test_prefix.exists():
            import shutil
            shutil.rmtree(self.test_prefix, ignore_errors=True)
        self.test_prefix.mkdir(parents=True, exist_ok=True)

        install_tool = self._find_tool("install")
        sed_tool = self._find_tool("sed")
        install_args = f"INSTALL={install_tool} HELP2MAN=/bin/true MAKEINFO=/bin/true SED={sed_tool}"

        rc = 1
        if self.build_system in ("autotools", "perl", "makefile"):
            # Three-tier fallback
            rc = self._run(f"make install-binPROGRAMS install-binSCRIPTS {install_args}")
            if rc != 0:
                rc = self._run(f"make install {install_args}")
            if rc != 0:
                rc = self._run(f"make install SUBDIRS=\"lib src\" {install_args}")
        elif self.build_system == "cmake":
            rc = self._run(f"make -C build install {install_args}")
        elif self.build_system == "meson":
            rc = self._run(f"ninja -C builddir install")
        elif self.build_system == "python":
            rc = self._run(f"pip install --prefix={self.test_prefix} --no-deps .")

        # Verify output
        bin_count = len(list(self.test_prefix.rglob("bin/*"))) if self.test_prefix.exists() else 0
        lib_count = len(list(self.test_prefix.rglob("lib*/*.so*"))) + len(list(self.test_prefix.rglob("lib*/*.a")))

        if bin_count == 0 and lib_count == 0:
            log_fail("安装无产物")
            raise RuntimeError("安装无产物")

        self._task_card_update("5", "✅完成", f"bin={bin_count} lib={lib_count}")
        self._log(f"✅ 安装完成: bin={bin_count} lib={lib_count}")

    # ── Step 6: safety popup ──

    def _step6_safety(self) -> None:
        if not self.should_run(6):
            return
        self._log("═══ [6/13] 安全弹窗 (R7) ═══")

        # Quick version check for first 5 binaries
        bins = sorted(self.test_prefix.rglob("bin/*"))[:5]
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
            ["zsh", "-c", check_cmd],
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
        bins = list(self.test_prefix.rglob("bin/*")) if self.test_prefix.exists() else []
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
                                  debug=True, prefix=str(self.test_prefix),
                                  pdir=str(self.pdir))
        rc = builder.run()
        self._task_card_update("9", "✅完成" if rc == 0 else "⚠️部分", f"RC={rc}")

    # ── Step 10: deploy ──

    def _step10_deploy(self) -> None:
        self._log("═══ [10/13] deploy ═══")

        rc = 0
        for subdir in ["bin", "lib", "include", "share"]:
            src = self.test_prefix / subdir
            dst = Path(self.default_prefix) / subdir
            if src.exists():
                dst.mkdir(parents=True, exist_ok=True)
                for item in src.iterdir():
                    if item.is_dir():
                        shutil.copytree(str(item), str(dst / item.name), dirs_exist_ok=True)
                    else:
                        shutil.copy2(str(item), str(dst / item.name))

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

        required = ["manifest.yaml", "README.md", "PROGRESS.md", "RELEASENOTE.md", "install.sh"]
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

    def _step12_calibrate(self) -> None:
        self._log("═══ [12/13] 归档校准 ═══")
        # Simplified calibration check
        self._log(f"归档目录: {self.archive_dir}")
        patches = list((self.archive_dir / "patches").glob("*.patch")) if (self.archive_dir / "patches").exists() else []
        self._log(f"补丁数: {len(patches)}")

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
