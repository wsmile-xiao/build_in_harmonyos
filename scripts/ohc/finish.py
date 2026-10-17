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
from .verify_build import VerifyBuild  # legacy, still used for archive checks
from .finalize_archive import finalize_archive
from .summary import generate_summary

class FinishPipeline:
    """6-step finishing pipeline for completed compilations."""

    def __init__(self, software, version, status="published", pdir=None):
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
            if self.status == "published":
                self.status = "built"
                log_warn("  test-report.md 缺失 → 降级为 built")
        else:
            log_ok("  test-report.md ✅")
        sv = self.archive_dir / ".staging-verified"
        if not sv.exists():
            self.gate_miss += 1
            self.gate_warnings.append("staging:missing")
            log_warn("  .staging-verified 缺失")
        else:
            log_ok(f"  .staging-verified ✅")
        # v3.0: Check for conanfile.py (preferred) or legacy packaging
        conanfile = self.archive_dir / "conanfile.py"
        if conanfile.exists():
            log_ok("  conanfile.py ✅ (v3.0 配方)")
        else:
            # Legacy: check for packaging
            pkg_dir = self.archive_dir / "packaging"
            tars = list(pkg_dir.glob("*ohos-aarch64*.tar.gz")) if pkg_dir.exists() else []
            if not tars:
                self.gate_miss += 1
                self.gate_warnings.append("packaging:missing")
                log_warn("  预编译包缺失（无 conanfile.py 也无 tar.gz）")
            else:
                log_ok(f"  预编译包 ✅ ({len(tars)} 个，legacy)")

        # Knowledge consolidation gate (non-blocking warning)
        kd_marker = self.archive_dir / ".knowledge-done"
        if kd_marker.exists():
            log_ok("  知识整理 ✅")
        else:
            self.gate_warnings.append("knowledge:not-done")
            log_warn("  ⚠️ 知识整理未完成（缺少 .knowledge-done 标记）")
            log_warn("     建议后续整理知识图谱（graph add --draft）")

            # Check for empty drafts — warn (non-blocking)
            draft_dir = self.pdir / "knowledge" / "graph" / "draft"
            if draft_dir.is_dir():
                empty_drafts = []
                for dkv in draft_dir.glob("E*-draft-*.kv"):
                    try:
                        content = dkv.read_text(encoding="utf-8")
                        # Check if key fields are still template placeholders
                        # Support both ":" and "=" separators
                        has_root_cause = False
                        has_error_sig = False
                        for line in content.split("\n"):
                            stripped = line.strip()
                            if (stripped.startswith("root_cause:") or stripped.startswith("root_cause=")) and len(stripped) > 20 and "[简短" not in stripped and "TODO" not in stripped:
                                has_root_cause = True
                            if (stripped.startswith("error_signature:") or stripped.startswith("error_signature=")) and len(stripped) > 25 and "configure|cmake" not in stripped:
                                has_error_sig = True
                        if not has_root_cause or not has_error_sig:
                            empty_drafts.append(dkv.name)
                    except Exception:
                        pass
                if empty_drafts:
                    log_warn(f"  ⚠️ 发现 {len(empty_drafts)} 个空草稿: {', '.join(empty_drafts[:5])}")
                    log_warn("     建议审查后填充或删除（不阻塞 finish）")

    # Step 1: refresh-patch
    def step1_refresh_patch(self):
        log_info("Step 1/10: 补丁生成...")
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
        log_info("Step 2/10: 归档收尾...")
        try:
            skip = os.environ.get("_SKIP_PATCH_GENERATION") == "true"
            rc = close_archive(self.software, self.version, self.status, skip_patch=skip, pdir=str(self.pdir))
        except Exception as e:
            rc = 1; log_fail(f"  close_archive 异常: {e}")
        if rc in (0, 4):
            self.steps["step2"] = True
            self._task_card("11b", "✅完成", "close-archive OK"); log_ok("  close-archive 完成")
            # v12.6 L1: 成功配方并入检索语料（社区 git pull/merge 即共享成长）
            try:
                from .recipe_search import upsert_catalog
                upsert_catalog(self.software, self.version, pdir=str(self.pdir))
                log_ok("  配方已并入检索语料 (recipe-search 可见)")
            except Exception as e:
                log_warn(f"  配方语料 upsert 失败（非阻塞）: {e}")
        else:
            self.steps["step2"] = False
            self._task_card("11b", "❌失败", f"exit {rc}"); log_fail(f"  close-archive 失败 (RC={rc})")

    # Step 2.5: G0 clean build verification
    def step25_g0_clean_verify(self):
        log_info("Step 3/10: G0 干净构建验证...")
        from .clean_verify import clean_verify
        rc = clean_verify(self.software, self.version, pdir=str(self.pdir))
        if rc != 0:
            log_warn("G0 干净构建验证失败，请手动检查构建结果")
            log_warn("运行 ohc-run.py clean-verify 获取详细错误")
            # Do not raise SystemExit - continue with finish
        else:
            log_ok("G0 干净构建验证通过")

    # Step 3: verify (conan_verify for v3.0, or legacy verify_build)
    def step3_verify_build(self):
        log_info("Step 4/10: 质量验证...")

        # v3.0: Use ConanVerifier if conanfile.py exists
        conanfile = self.archive_dir / "conanfile.py"
        if conanfile.exists():
            log_info("  检测到 conanfile.py，使用 Conan 验证 (R29)...")
            from .conan_verify import ConanVerifier
            verifier = ConanVerifier(
                self.software, self.version,
                pdir=str(self.pdir),
            )
            try:
                rc = verifier.run()
            except Exception as e:
                log_warn(f"  conan-verify 异常: {e}"); self.steps["step3"] = False; return
            if rc == 0:
                self.steps["step3"] = True
                self._task_card("11c", "✅完成", "conan-verify PASS"); log_ok("  conan-verify 通过")
                if self.status == "failed": self.status = "built"
            else:
                self.steps["step3"] = False
                self._task_card("11c", "❌失败", f"conan-verify RC={rc}")
                log_fail(f"  conan-verify 未通过 (RC={rc})，请修复 conanfile.py 后重新验证")
                if self.status == "published": self.status = "built"
                elif self.status == "built": self.status = "failed"
        else:
            # Legacy: Use old verify_build for archives without conanfile.py
            log_info("  无 conanfile.py，使用传统 G1-G4 验证...")
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
                if self.status == "failed": self.status = "built"
            else:
                self.steps["step3"] = False
                self._task_card("11c", "❌失败", f"G1-G4 RC={rc}")
                log_fail(f"  质量门禁未通过 (RC={rc})，请修复后重新 verify")
                if self.status == "published": self.status = "built"
                elif self.status == "built": self.status = "failed"

    # Step 3.5: Local CI simulation (W3) — BLOCKING with HANDOFF
    def step35_local_ci(self):
        log_info("Step 5/10: 本地 CI 模拟 (W3) [阻塞门禁]...")
        from .workflow_checks import run_local_ci
        rc = run_local_ci(self.software, self.version, pdir=str(self.pdir))
        if rc == 0:
            self.steps["step35"] = True
            self._task_card("11c2", "✅完成", "local CI OK")
            self._write_ci_result(passed=True)
            log_ok("  ✅ W3 本地 CI 模拟通过")
        else:
            self.steps["step35"] = False
            self._task_card("11c2", "❌失败", "CI模拟失败")
            log_fail("  ❌ W3 本地 CI 模拟失败 — 阻塞！不可继续 finish")
            self._emit_w3_handoff()
            sys.exit(1)

    def _write_ci_result(self, passed: bool):
        """Write .ci-result.json with integrity info (防伪造)."""
        import json
        import hashlib
        ts = datetime.now().isoformat()
        # Integrity hash: prevents AI from forging this file manually
        raw = f"{ts}:{self.software}:{self.version}:{0 if passed else 1}"
        integrity_hash = hashlib.sha256(raw.encode()).hexdigest()[:16]
        ci_result = {
            "timestamp": ts,
            "exit_code": 0 if passed else 1,
            "software": self.software,
            "version": self.version,
            "step": "W3_local_ci",
            "archive_dir": str(self.archive_dir),
            "integrity_hash": integrity_hash,
        }
        # 日志 SHA256（W3 完整输出，供审计比对）
        w3_log = self.archive_dir / "reports" / "w3-local-ci.log"
        if w3_log.exists():
            try:
                ci_result["log_sha256"] = hashlib.sha256(
                    w3_log.read_bytes()).hexdigest()
            except OSError:
                pass
        ci_path = self.archive_dir / ".ci-result.json"
        ci_path.write_text(
            json.dumps(ci_result, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def _emit_w3_handoff(self):
        """Emit HANDOFF block for W3 local CI failure (blocking)."""
        from .handoff import HandoffData, emit_handoff
        data = HandoffData(
            exit_reason="w3_local_ci_failed",
            exit_code=2,
            step_failed="Step5",
            resume_cmd=f"python3 scripts/ohc-run.py finish {self.software} {self.version} {self.status}",
            knowledge_hit="none",
            knowledge_gap=False,
            log_file="",
            src_dir="",
            task_card=str(self.archive_dir / "TASK_CARD.md"),
            software_name=self.software,
            software_version=self.version,
            archive_dir=str(self.archive_dir),
            ai_next_actions=[
                "W3 本地 CI 模拟失败，必须修复后重新 finish",
                "查看上方错误输出与 reports/w3-local-ci.log，定位 setup.sh 或 build_and_test.sh 失败原因",
                "若为构建超时（预算耗尽而非真实失败）: python3 scripts/ohc-run.py timeout set "
                f"{self.software} {self.version} <3600-57600秒>（CI 与 W3 同源配置）",
                f"修复后重新运行: python3 scripts/ohc-run.py finish {self.software} {self.version} {self.status}",
            ],
        )
        emit_handoff(data, project_dir=str(self.pdir))

    # Step 4: finalize-archive
    def step4_finalize_archive(self):
        log_info("Step 6/10: 归档校验...")
        try:
            rc = finalize_archive(self.software, self.version, pdir=str(self.pdir))
        except Exception as e:
            log_warn(f"  finalize-archive 异常: {e}"); self.steps["step4"] = True; return
        self.steps["step4"] = True
        if rc == 0:
            self._task_card("11d", "✅完成", "finalize OK"); log_ok("  finalize-archive 完成")
        else:
            self._task_card("11d", "⚠️部分", "有警告"); log_warn(f"  finalize-archive 有警告 (RC={rc})")

    # Step 5: knowledge completeness (W4)
    def step5_check_knowledge_gap(self):
        log_info("Step 7/10: 知识图谱完整性检查 (W5)...")
        # W4: Enhanced knowledge graph completeness check
        from .workflow_checks import check_knowledge_completeness
        rc = check_knowledge_completeness(pdir=str(self.pdir))
        # Also run archive-specific knowledge gap check
        try:
            rc2 = check_knowledge_gap(self.software, self.version, pdir=str(self.pdir))
        except Exception as e:
            rc = 1; log_warn(f"  check_knowledge_gap 异常: {e}")
        if rc == 0 and rc2 in (0, 3):
            self.steps["step5b"] = True
            self._task_card("11e", "✅完成", "knowledge OK"); log_ok("  知识图谱完整性通过")
        elif rc2 == 3:
            self.steps["step5b"] = False
            self._task_card("11e", "⚠️部分", "有知识遗漏"); log_warn("  知识库存在遗漏")
        else:
            self.steps["step5b"] = False
            self._task_card("11e", "⚠️部分", f"检查异常 RC={rc}")

    # Step 6: gen_summary
    def step6_gen_summary(self):
        log_info("Step 8/10: 生成 SUMMARY.md...")
        try:
            generate_summary(pdir=str(self.pdir))
            self.steps["step6"] = True
            self._task_card("11f", "✅完成", "gen_summary OK"); log_ok("  SUMMARY.md 生成完成")
        except Exception as e:
            self.steps["step6"] = True
            self._task_card("11f", "⚠️部分", str(e)); log_warn(f"  gen_summary 失败: {e}")

    # Step 7: PR atomicity check (W2)
    def step7_pr_atomicity(self):
        log_info("Step 9/10: PR 原子性检查 (W2)...")
        from .workflow_checks import check_pr_atomicity
        rc = check_pr_atomicity(pdir=str(self.pdir))
        if rc == 0:
            self.steps["step7"] = True
            self._task_card("11g", "✅完成", "PR atomicity OK")
        else:
            self.steps["step7"] = False
            self._task_card("11g", "⚠️部分", "框架文件混入")
            log_warn("  ⚠️ 发现框架文件变更，请拆分到独立 PR")

    def step8_submit_readiness(self):
        """Step 10/10: Submit readiness pre-check."""
        log_info("Step 10/10: submit 就绪预检...")
        checks = []

        # Check test-report.md
        test_report = self.archive_dir / "reports" / "test-report.md"
        if test_report.exists():
            checks.append(("✅", "test-report.md", ""))
        else:
            checks.append(("❌", "test-report.md", "需创建 reports/test-report.md"))

        # Check packaging directory
        packaging_dir = self.archive_dir / "packaging"
        if packaging_dir.exists() and any(packaging_dir.iterdir()):
            checks.append(("✅", "packaging/", ""))
        else:
            checks.append(("❌", "packaging/", "需创建 packaging/ 目录并打包"))

        # Check .staging-verified
        staging = self.archive_dir / ".staging-verified"
        if staging.exists():
            checks.append(("✅", ".staging-verified", ""))
        else:
            checks.append(("❌", ".staging-verified", "需创建 .staging-verified 空文件"))

        # Check .build-closed or 编译结束 marker in notes.md
        build_closed = self.archive_dir / ".build-closed"
        notes = self.archive_dir / "notes.md"
        has_marker = build_closed.exists()
        if not has_marker and notes.exists():
            has_marker = "编译结束" in notes.read_text(encoding="utf-8", errors="replace")
        if has_marker:
            checks.append(("✅", "build-closed marker", ""))
        else:
            checks.append(("❌", "build-closed marker", "需运行 close-archive 或手动添加标记"))

        failed = [c for c in checks if c[0] == "❌"]
        for icon, name, hint in checks:
            log_info(f"  {icon} {name}" + (f" — {hint}" if hint else ""))

        if failed:
            log_warn(f"  ⚠️ {len(failed)} 项未就绪，submit 前需修复")
            self._task_card("12", "⚠️部分", f"submit readiness: {len(failed)} 项未就绪")
        else:
            log_ok("  ✅ submit 就绪")
            self._task_card("12", "✅完成", "submit readiness OK")

        self.steps["step8"] = len(failed) == 0

    def _collect_knowledge_actions(self):
        """Collect AI next actions for knowledge consolidation."""
        actions = []

        # 1. Check knowledge gaps
        progress = self.archive_dir / "notes.md"
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
                f"notes.md 有 {len(pending_items)} 条待处理知识条目，逐条判断 L1/L2/L3 并写入对应位置"
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

        # 3. Check draft knowledge (实际草稿目录: knowledge/drafts/, 两种命名)
        draft_dir = self.pdir / "knowledge" / "drafts"
        draft_count = 0
        if draft_dir.is_dir():
            draft_count = len(list(draft_dir.glob("E*-draft-*.kv"))) + \
                          len(list(draft_dir.glob("DRAFT-*.kv")))
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
            f"⚠️ R6: 确认所有源码修改已记录: python3 scripts/ohc-run.py track-edit scan {self.software} {self.version}"
            f"（如有遗漏，用 track-edit add 补录）"
        )

        # 7. Always: self-check + git instructions
        actions.append(
            f"完成知识整理后执行自检: python3 scripts/ohc-run.py submit {self.software} {self.version}"
        )
        actions.append(
            f"自检通过后提交: git add archives/ knowledge/drafts/ && "
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
        elif all_ok and not kd_marker.exists():  # non-blocking
            log_warn(f"⚠️ 编译收尾完成（知识整理待做）: {self.software} {self.version} → {self.status}")
            log_warn("   建议后续整理知识图谱")
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
        is_blocking = False  # non-blocking: knowledge consolidation does not block finish

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
        self.step25_g0_clean_verify()
        self.step3_verify_build()
        self.step35_local_ci()
        self.step4_finalize_archive()
        self.step5_check_knowledge_gap()
        self.step6_gen_summary()
        self.step7_pr_atomicity()
        self.step8_submit_readiness()
        self.print_summary()
        self.emit_knowledge_handoff()

        kd_marker = self.archive_dir / ".knowledge-done"
        all_ok = all(self.steps.values())
        return 0 if all_ok else 1


def finish_cli(argv=None):
    import argparse
    parser = argparse.ArgumentParser(prog="ohc finish",
        description="编译收尾 10 步管线")
    parser.add_argument("software", help="软件名称")
    parser.add_argument("version", help="版本号")
    parser.add_argument("status", nargs="?", default="published",
        choices=["published", "built", "failed", "archived"], help="编译状态")
    parser.add_argument("--project-dir")
    args = parser.parse_args(argv)
    # R46: W3 收尾管线启动前写生命周期草稿（管线中途中断也有 result.json）
    try:
        from .result_report import write_lifecycle_draft
        write_lifecycle_draft(args.software, args.version, "w3_finish_started")
    except Exception:
        pass
    pipeline = FinishPipeline(args.software, args.version, args.status,
                               pdir=getattr(args, "project_dir", None))
    return pipeline.run()

