"""Close compilation archive — update status, patches, metadata.
"""
from __future__ import annotations
import os
import re
import subprocess
from datetime import datetime
from pathlib import Path

from .utils import find_project_dir, log_info, log_ok, log_warn, log_fail
from .refresh_patch import auto_mode as refresh_patch_auto


def close_archive(name: str, version: str, status: str,
                  skip_patch: bool = False, pdir: str | None = None) -> int:
    project = Path(pdir) if pdir else Path(find_project_dir())
    script_dir = project / "scripts"
    letter = name[0].lower()
    ver_dir = project / "archives" / letter / name / version

    if status not in ("published", "built", "failed", "archived"):
        log_fail(f"无效状态: {status}")
        return 1
    if not ver_dir.exists():
        log_fail(f"档案不存在: {ver_dir}")
        return 2

    manifest = ver_dir / "manifest.yaml"
    progress = ver_dir / "notes.md"
    if not manifest.exists() or not progress.exists():
        log_fail("manifest.yaml 或 notes.md 缺失")
        return 2

    log_info(f"关闭档案: {name} {version} → {status}")

    # Step 0: Patch pipeline (conditional)
    patches = list((ver_dir / "patches").glob("000*.patch"))
    if not patches and status != "failed" and not skip_patch:
        log_info("  触发补丁管线...")
        try:
            rc = refresh_patch_auto(name, version, pdir=str(project))
            if rc == 0:
                log_ok("  补丁生成成功")
            else:
                log_warn(f"  补丁管线失败 (RC={rc})")
        except Exception as e:
            log_warn(f"  补丁管线异常: {e}")

    # Step 1: Update manifest.yaml status
    content = manifest.read_text(encoding="utf-8")
    content = re.sub(r'status:\s*\w+', f'status: {status}', content)
    manifest.write_text(content, encoding="utf-8")
    log_ok(f"  manifest.yaml → {status}")

    # Step 2: Update notes.md (⭐ R25: 防止重复记录)
    ts = datetime.now().strftime("%Y-%m-%d %H:%M")
    
    # 先读取现有内容，检查是否有旧的编译结束记录
    pcontent = progress.read_text(encoding="utf-8")
    
    # 删除所有旧的编译结束块（---\n\n**编译结束**:...\n**最终状态**:...\n）
    # 使用正则表达式匹配并删除
    pattern = r'\n---\n\n\*\*编译结束\*\*:.*?\n\*\*最终状态\*\*:.*?\n'
    pcontent_new = re.sub(pattern, '', pcontent, flags=re.DOTALL)
    
    # 在末尾添加新的编译结束记录
    append_text = f"\n---\n\n**编译结束**: {ts}\n**最终状态**: {status}\n"
    pcontent_new = pcontent_new.rstrip() + append_text
    
    progress.write_text(pcontent_new, encoding="utf-8")
    log_ok("  notes.md 已更新（已清理旧记录）")

    # Step 5: Check pending items
    pcontent = progress.read_text(encoding="utf-8")
    pending = len(re.findall(r'(⏳|待评估|TODO|FIXME)', pcontent))
    if pending > 0:
        log_warn(f"  ⚠️ 存在 {pending} 个待评估知识条目")
        return 4

    log_ok(f"✅ 档案已关闭: {status}")
    return 0


def close_archive_cli(argv: list[str] | None = None) -> int:
    import argparse
    parser = argparse.ArgumentParser(prog="ohc close-archive")
    parser.add_argument("software")
    parser.add_argument("version")
    parser.add_argument("status", choices=["published", "built", "failed", "archived"])
    parser.add_argument("--skip-patch", action="store_true")
    parser.add_argument("--project-dir")
    args = parser.parse_args(argv)
    skip = args.skip_patch or os.environ.get("_SKIP_PATCH_GENERATION") == "true"
    return close_archive(args.software, args.version, args.status,
                          skip, getattr(args, "project_dir", None))
