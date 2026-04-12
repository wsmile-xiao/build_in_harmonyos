"""Finish-build pipeline — 6-step post-compilation finishing.
"""
from __future__ import annotations
import os
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from .utils import find_project_dir, log_info, log_ok, log_warn, log_fail
from .close_archive import close_archive
from .check_knowledge_gap import check_knowledge_gap
from .refresh_patch import auto_mode as refresh_patch_auto
from .verify_build import VerifyBuild
from .finalize_archive import finalize_archive
from .summary import generate_summary

class FinishPipeline:
    """6-step finishing pipeline for completed compilations."""

    def __init__(self, software, version, status="success", pdir=None):
        self.software = software
        self.version = version
        self.status = status
        self.timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        self.pdir = Path(pdir) if pdir else Path(find_project_dir())
        self.script_dir = self.pdir / "scripts"
        first_letter = software[0].lower()
        self.archive_dir = self.pdir / "archives" / first_letter / software / version
        self.gate_miss = 0
        self.gate_warnings = []
        self.steps = {}

    def _run_sub(self, cmd, env_extra=None, cwd=None):
        """Run a subprocess, return exit code."""
        env = os.environ.copy()
        if env_extra: env.update(env_extra)
        try:
            result = subprocess.run(cmd, env=env, cwd=cwd,
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            if result.stdout: print(result.stdout, end="")
            if result.returncode != 0 and result.stderr:
                print(result.stderr, end="", file=sys.stderr)
            return result.returncode
        except FileNotFoundError:
            log_warn(f"Script not found: {cmd[0]}")
            return -1

    def _task_card(self, task_id, status, detail):
        tc = self.archive_dir / "TASK_CARD.md"
        if not tc.exists(): return
        content = tc.read_text(encoding="utf-8")
        lines = content.split("\n")
        line = f"- [{task_id}] {status} — {detail} — {datetime.now().strftime('%H:%M:%S')}"
        for i, l in enumerate(lines):
            if task_id in l and ("⏳" in l or "🔄" in l):
                lines[i] = line; break
        tc.write_text("\n".join(lines), encoding="utf-8")

    # Step 0: Prerequisites
    def check_prerequisites(self):
        log_info("Step 0: 前置关卡检查...")
        tr = self.archive_dir / "reports" / "test-report.md"
        if not tr.exists():
            self.gate_miss += 1
            self.gate_warnings.append("test-report:missing")
            if self.status == "success":
                self.status = "partial"
                log_warn("  test-report.md 缺失 → 降级为 partial")
        else:
            log_ok("  test-report.md ✅")
        sv = self.archive_dir / ".staging-verified"
        if not sv.exists():
            self.gate_miss += 1
            self.gate_warnings.append("staging:missing")
            log_warn("  .staging-verified 缺失")
        else:
            log_ok(f"  .staging-verified ✅")
        pkg_dir = self.archive_dir / "packaging"
        tars = list(pkg_dir.glob("*ohos-aarch64*.tar.gz")) if pkg_dir.exists() else []
        if not tars:
            self.gate_miss += 1
            self.gate_warnings.append("packaging:missing")
            log_warn("  预编译包缺失")
        else:
            log_ok(f"  预编译包 ✅ ({len(tars)} 个)")

    # Step 1: refresh-patch
    def step1_refresh_patch(self):
        log_info("Step 1/6: 补丁生成...")
        try:
            rc = refresh_patch_auto(self.software, self.version, pdir=str(self.pdir))
        except Exception as e:
            log_warn(f"  refresh-patch 异常: {e}"); self.steps["step1"] = True; return
        self.steps["step1"] = True
        if rc == 0:
            self._task_card("11a", "✅完成", "refresh-patch OK"); log_ok("  refresh-patch 完成")
        else:
            self._task_card("11a", "⚠️部分", f"refresh-patch RC={rc}"); log_warn(f"  refresh-patch 失败 (RC={rc})")

    # Step 2: close-archive
    def step2_close_archive(self):
        log_info("Step 2/6: 归档收尾...")
        try:
            skip = os.environ.get("_SKIP_PATCH_GENERATION") == "true"
            rc = close_archive(self.software, self.version, self.status, skip_patch=skip, pdir=str(self.pdir))
        except Exception as e:
            rc = 1; log_fail(f"  close_archive 异常: {e}")
        if rc in (0, 4):
            self.steps["step2"] = True
            self._task_card("11b", "✅完成", "close-archive OK"); log_ok("  close-archive 完成")
        else:
            self.steps["step2"] = False
            self._task_card("11b", "❌失败", f"exit {rc}"); log_fail(f"  close-archive 失败 (RC={rc})")

    # Step 3: verify-build
    def step3_verify_build(self):
        log_info("Step 3/6: 质量门禁 G1-G4...")
        install_prefix = os.environ.get("TEST_PREFIX", "")
        v = VerifyBuild(self.software, self.version,
                        archive_dir=str(self.archive_dir),
                        project_dir=str(self.pdir),
                        install_prefix=install_prefix)
        try:
            rc = v.run()
        except Exception as e:
            log_warn(f"  verify-build 异常: {e}"); self.steps["step3"] = True; return
        self.steps["step3"] = True
        if rc == 0:
            self._task_card("11c", "✅完成", "G1-G4 全通过"); log_ok("  G1-G4 全通过")
            if self.status == "failed": self.status = "partial"
        else:
            self._task_card("11c", "⚠️部分", f"G1-G4 RC={rc}")
            if self.status == "success": self.status = "partial"
            elif self.status == "partial": self.status = "failed"

    # Step 4: finalize-archive
    def step4_finalize_archive(self):
        log_info("Step 4/6: 归档校验 + RELEASENOTE...")
        try:
            rc = finalize_archive(self.software, self.version, pdir=str(self.pdir))
        except Exception as e:
            log_warn(f"  finalize-archive 异常: {e}"); self.steps["step4"] = True; return
        self.steps["step4"] = True
        if rc == 0:
            self._task_card("11d", "✅完成", "finalize OK"); log_ok("  finalize-archive 完成")
        else:
            self._task_card("11d", "⚠️部分", "有警告"); log_warn(f"  finalize-archive 有警告 (RC={rc})")

    # Step 5: check-knowledge-gap
    def step5_check_knowledge_gap(self):
        log_info("Step 5/6: 知识完整性检查...")
        try:
            rc = check_knowledge_gap(self.software, self.version, pdir=str(self.pdir))
        except Exception as e:
            rc = 1; log_warn(f"  check_knowledge_gap 异常: {e}")
        if rc == 0:
            self.steps["step5b"] = True
            self._task_card("11e", "✅完成", "knowledge-gap OK"); log_ok("  知识完整性通过")
        elif rc == 3:
            self.steps["step5b"] = False
            self._task_card("11e", "⚠️部分", "有知识遗漏"); log_warn("  知识库存在遗漏")
        else:
            self.steps["step5b"] = True
            self._task_card("11e", "⚠️部分", f"检查异常 RC={rc}")

    # Step 6: gen_summary
    def step6_gen_summary(self):
        log_info("Step 6/6: 生成 SUMMARY.md...")
        try:
            generate_summary(pdir=str(self.pdir))
            self.steps["step6"] = True
            self._task_card("11f", "✅完成", "gen_summary OK"); log_ok("  SUMMARY.md 生成完成")
        except Exception as e:
            self.steps["step6"] = True
            self._task_card("11f", "⚠️部分", str(e)); log_warn(f"  gen_summary 失败: {e}")

    def print_summary(self):
        print()
        all_ok = all(self.steps.values())
        if all_ok:
            log_ok(f"✅ 编译收尾全部完成: {self.software} {self.version} → {self.status}")
        else:
            failed = [k for k, v in self.steps.items() if not v]
            log_warn(f"⚠️  编译收尾部分完成: {self.software} {self.version} → {self.status}")
            log_warn(f"   失败步骤: {', '.join(failed)}")

    def run(self):
        if not self.archive_dir.exists():
            log_fail(f"归档目录不存在: {self.archive_dir}"); return 1
        self.check_prerequisites()
        self.step1_refresh_patch()
        self.step2_close_archive()
        self.step3_verify_build()
        self.step4_finalize_archive()
        self.step5_check_knowledge_gap()
        self.step6_gen_summary()
        self.print_summary()
        return 0 if all(self.steps.values()) else 1


def finish_cli(argv=None):
    import argparse
    parser = argparse.ArgumentParser(prog="ohc finish",
        description="编译收尾 6 步管线")
    parser.add_argument("software", help="软件名称")
    parser.add_argument("version", help="版本号")
    parser.add_argument("status", nargs="?", default="success",
        choices=["success", "partial", "failed"], help="编译状态")
    parser.add_argument("--project-dir")
    args = parser.parse_args(argv)
    pipeline = FinishPipeline(args.software, args.version, args.status,
                               pdir=getattr(args, "project_dir", None))
    return pipeline.run()
