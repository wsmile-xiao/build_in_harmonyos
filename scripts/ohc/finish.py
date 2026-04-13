"""Finish-build pipeline — 6-step post-compilation finishing.

After all 6 steps complete, emits a KNOWLEDGE CONSOLIDATION HANDOFF block
to hand over to AI for knowledge graph organization as contributor.
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
        packaged_marker = pkg_dir / ".packaged" if pkg_dir.exists() else None
        if not tars:
            self.gate_miss += 1
            self.gate_warnings.append("packaging:missing")
            log_warn("  预编译包缺失")
        elif packaged_marker and packaged_marker.exists():
            log_ok(f"  预编译包 ✅ ({len(tars)} 个，工具化打包)")
        else:
            # tar.gz exists but not via ohc-run.py package — manual packaging
            self.gate_miss += 1
            self.gate_warnings.append("packaging:manual")
            log_fail("  ❌ 预编译包存在但未经工具化打包（缺少 .packaged 标记）")
            log_fail("     必须使用 ohc-run.py package 完成打包（签名/RPATH/strip/权限）")
            log_fail("     手动 tar 打包的产物在鸿蒙上无法执行（ELF 未签名）")
            if self.status == "success":
                self.status = "partial"

        # Knowledge consolidation gate
        kd_marker = self.archive_dir / ".knowledge-done"
        if kd_marker.exists():
            log_ok("  知识整理 ✅")
        else:
            self.gate_miss += 1
            self.gate_warnings.append("knowledge:not-done")
            log_fail("  ❌ 知识整理未完成（缺少 .knowledge-done 标记）")
            log_fail("     必须先整理知识图谱（graph add --draft），再重新运行 finish")

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
            log_warn(f"  verify-build 异常: {e}"); self.steps["step3"] = False; return
        if rc == 0:
            self.steps["step3"] = True
            self._task_card("11c", "✅完成", "G1-G4 全通过"); log_ok("  G1-G4 全通过")
            if self.status == "failed": self.status = "partial"
        else:
            self.steps["step3"] = False
            self._task_card("11c", "❌失败", f"G1-G4 RC={rc}")
            log_fail(f"  质量门禁未通过 (RC={rc})，请修复后重新 verify")
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

    def _collect_knowledge_actions(self):
        """Collect AI next actions for knowledge consolidation."""
        actions = []

        # 1. Check knowledge gaps
        progress = self.archive_dir / "PROGRESS.md"
        pending_items = []
        if progress.exists():
            import re
            in_section = False
            for line in progress.read_text(encoding="utf-8").split("\n"):
                if re.search(r'(发现与知识|知识积累|discoveries|findings)', line, re.I):
                    in_section = True
                    continue
                if in_section and (line.startswith("## ") or line.strip() == "---"):
                    in_section = False
                    continue
                if in_section:
                    s = line.strip()
                    if s and re.search(r'(⏳|TODO|待评估|待提取|FIXME)', s, re.I):
                        pending_items.append(s)
                    elif s.startswith("- ") or s.startswith("* "):
                        pending_items.append(s)

        if pending_items:
            actions.append(
                f"PROGRESS.md 有 {len(pending_items)} 条待处理知识条目，逐条判断 L1/L2/L3 并写入对应位置"
            )

        # 2. Check manifest knowledge_gained
        manifest = self.archive_dir / "manifest.yaml"
        kg_count = 0
        if manifest.exists():
            content = manifest.read_text(encoding="utf-8")
            for line in content.split("\n"):
                if line.strip().startswith("- ") and "knowledge_gained" not in line:
                    # crude check: after knowledge_gained section
                    kg_count += 1
            if kg_count == 0:
                actions.append(
                    "manifest.yaml 的 knowledge_gained 为空，回顾编译过程提取经验写入"
                )

        # 3. Check draft knowledge
        draft_dir = self.pdir / "knowledge" / "graph" / "draft"
        draft_count = len(list(draft_dir.glob("E*-draft-*.kv"))) if draft_dir.is_dir() else 0
        if draft_count > 0:
            actions.append(
                f"已有 {draft_count} 条知识草稿（draft/），检查内容完整性后准备提交 PR"
            )
        else:
            # Check if new knowledge should be drafted
            actions.append(
                "检查编译中是否遇到新的通用问题（下一个不同软件也会遇到的），如有则用 "
                f"`python3 scripts/ohc-run.py graph add E{{NNN}} --draft` 写入草稿"
            )

        # 4. skill-feedback
        sf = self.archive_dir / "reports" / "skill-feedback.md"
        if sf.exists() and sf.stat().st_size > 50:
            actions.append(
                "reports/skill-feedback.md 有内容，回顾并确保所有发现已记录"
            )

        # 5. Check packaging method
        pkg_dir = self.archive_dir / "packaging"
        packaged_marker = pkg_dir / ".packaged" if pkg_dir.exists() else None
        if packaged_marker and packaged_marker.exists():
            pass  # Good, tool-packaged
        elif pkg_dir.exists() and list(pkg_dir.glob("*ohos-aarch64*.tar.gz")):
            actions.insert(0,
                "⚠️ 预编译包未经工具化打包！必须执行: "
                f"python3 scripts/ohc-run.py package {self.software} {self.version}"
            )

        # 6. Ensure edit tracker is up to date
        actions.append(
            f"确保编辑追踪器已记录所有修改: python3 scripts/ohc-run.py track-edit scan {self.software} {self.version}"
        )

        # 7. Always: self-check + git instructions
        actions.append(
            f"完成知识整理后执行自检: python3 scripts/ohc-run.py submit --check {self.software} {self.version}"
        )
        actions.append(
            f"自检通过后提交: git add archives/ knowledge/graph/draft/ && "
            f'git commit -m "feat: 编译 {self.software} {self.version}" && '
            f"git push origin feat/{self.software}-{self.version}"
        )

        return actions

    def print_summary(self):
        print()
        all_ok = all(self.steps.values())
        kd_marker = self.archive_dir / ".knowledge-done"

        if all_ok and kd_marker.exists():
            log_ok(f"✅ 编译收尾全部完成: {self.software} {self.version} → {self.status}")
        elif all_ok and not kd_marker.exists():
            log_fail(f"❌ 编译收尾未完成: {self.software} {self.version} → 知识整理未做")
            log_fail("   请按下方 HANDOFF 提示整理知识图谱，然后重新运行 finish")
        else:
            failed = [k for k, v in self.steps.items() if not v]
            log_warn(f"⚠️  编译收尾部分完成: {self.software} {self.version} → {self.status}")
            log_warn(f"   失败步骤: {', '.join(failed)}")

    def emit_knowledge_handoff(self):
        """Emit KNOWLEDGE CONSOLIDATION HANDOFF block after finish.

        This is a MANDATORY gate — finish returns exit code 1 until
        knowledge consolidation is done and .knowledge-done marker exists.
        """
        from .handoff import HandoffData, emit_handoff

        actions = self._collect_knowledge_actions()

        # Determine if this is a blocking handoff (knowledge not done)
        kd_marker = self.archive_dir / ".knowledge-done"
        is_blocking = not kd_marker.exists()

        data = HandoffData(
            exit_reason="finish_knowledge_required" if is_blocking else "finish_success",
            exit_code=1 if is_blocking else 0,
            step_failed="Step0" if is_blocking else "Step6",
            resume_cmd=f"python3 scripts/ohc-run.py finish {self.software} {self.version} {self.status}",
            knowledge_hit="none",
            knowledge_gap=is_blocking,
            log_file="",
            src_dir="",
            task_card="",
            software_name=self.software,
            software_version=self.version,
            archive_dir=str(self.archive_dir),
            ai_next_actions=actions,
        )
        emit_handoff(data, project_dir=str(self.pdir))

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
        self.emit_knowledge_handoff()

        kd_marker = self.archive_dir / ".knowledge-done"
        all_ok = all(self.steps.values()) and kd_marker.exists()
        return 0 if all_ok else 1


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
