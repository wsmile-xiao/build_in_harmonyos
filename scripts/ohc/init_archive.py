"""Create/restore compilation archive skeleton.
"""
from __future__ import annotations
import re
import shutil
from datetime import datetime
from pathlib import Path

from .utils import find_project_dir, log_info, log_ok, log_warn, log_fail


def _sanitize(s: str) -> str:
    return re.sub(r'[^a-zA-Z0-9._+\-]', '', s)


def init_archive(name: str, version: str, source_url: str = "",
                 build_system: str = "unknown", clean: bool = False,
                 pdir: str | None = None) -> int:
    project = Path(pdir) if pdir else Path(find_project_dir())
    name = _sanitize(name)
    version = _sanitize(version)
    letter = name[0].lower() if name else "x"

    ver_dir = project / "archives" / letter / name / version
    sw_dir = ver_dir.parent

    log_info(f"初始化档案: {name} {version}")
    log_info(f"  路径: {ver_dir}")

    # Create directories
    for d in ["patches", "reports", "packaging"]:
        (ver_dir / d).mkdir(parents=True, exist_ok=True)
    log_ok(f"  目录已就绪")

    # --clean mode
    if clean:
        for pat in ["patches/*.patch", "packaging/*.tar.gz", "packaging/*.sh"]:
            for f in ver_dir.glob(pat):
                f.unlink()
        for d in ["packaging/bin", "packaging/debug", "packaging/share"]:
            dp = ver_dir / d
            if dp.exists():
                shutil.rmtree(dp, ignore_errors=True)
        log_info("  --clean: 已清空旧产物")

    # manifest.yaml
    mf = ver_dir / "manifest.yaml"
    if not mf.exists() or mf.stat().st_size < 200:
        mf.write_text(_manifest_template(name, version, build_system, source_url),
                       encoding="utf-8")
        log_ok("  manifest.yaml 已生成")
    else:
        log_ok("  manifest.yaml 已存在，保留")

    # PROGRESS.md
    pf = ver_dir / "PROGRESS.md"
    if not pf.exists() or len(pf.read_text(encoding="utf-8").split("\n")) < 15:
        today = datetime.now().strftime("%Y-%m-%d")
        content = _progress_template(name, version, today)
        pf.write_text(content, encoding="utf-8")
        log_ok("  PROGRESS.md 已生成")
    else:
        log_ok("  PROGRESS.md 已存在，保留")

    # README.md
    rm = ver_dir / "README.md"
    if not rm.exists() or len(rm.read_text(encoding="utf-8").split("\n")) < 10:
        rm.write_text(_readme_template(name, version, build_system), encoding="utf-8")
        log_ok("  README.md 已生成")
    else:
        log_ok("  README.md 已存在，保留")

    # Software-level meta sync
    for fname in ["README.md", "RELEASENOTE.md"]:
        src = ver_dir / fname
        dst = sw_dir / fname
        if src.exists() and not dst.exists():
            shutil.copy2(src, dst)

    # _meta.yaml — always regenerate
    meta = ver_dir / "_meta.yaml"
    patches_count = len(list((ver_dir / "patches").glob("*.patch")))
    meta.write_text(
        f"software: {name}\nversion: {version}\nletter: {letter}\n"
        f"status: compiling\nbuild_system: {build_system}\n"
        f"compatibility: unknown\npatches_count: {patches_count}\n"
        f"archive_path: {ver_dir}\ncompile_date: {datetime.now().strftime('%Y-%m-%d')}\n",
        encoding="utf-8")

    # Verify
    missing = []
    for req in ["manifest.yaml", "PROGRESS.md", "README.md", "patches", "reports", "packaging"]:
        if not (ver_dir / req).exists():
            missing.append(req)
    if missing:
        log_warn(f"  验证缺失: {missing}")
        return 3

    pcnt = len(list((ver_dir / "patches").glob("*")))
    rcnt = len(list((ver_dir / "reports").glob("*")))
    log_ok(f"  ✅ 档案就绪: patches={pcnt} reports={rcnt}")
    return 0


def _manifest_template(name: str, version: str, bs: str, url: str) -> str:
    t = (f"software: {name}\nversion: {version}\nstatus: compiling\n"
         f"build_system: {bs}\ncreated_at: {datetime.now().strftime('%Y-%m-%d')}\n"
         f"knowledge_gained: []\npatches_applied: []\nbuild_log: logs/build.log\n")
    if url:
        t += f"source_url: {url}\n"
    return t


def _progress_template(name: str, version: str, date: str) -> str:
    return (f"# {name} {version} 编译进度\n\n"
            f"**日期**: {date}\n**状态**: 🔄 编译中\n\n"
            f"## 步骤记录\n\n"
            f"| 步骤 | 状态 | 备注 |\n|------|------|------|\n"
            f"| Step 1 init | ⏳ | |\n| Step 2 patches | ⏳ | |\n"
            f"| Step 3 configure | ⏳ | |\n| Step 4 make | ⏳ | |\n"
            f"| Step 5 install | ⏳ | |\n| Step 6 safety | ⏳ | |\n"
            f"| Step 7 check | ⏳ | |\n| Step 8 staging | ⏳ | |\n"
            f"| Step 9 package | ⏳ | |\n| Step 10 deploy | ⏳ | |\n"
            f"| Step 11 finish | ⏳ | |\n\n"
            f"## 发现与知识\n\n<!-- 编译过程中发现的问题和解决方案 -->\n")


def _readme_template(name: str, version: str, bs: str) -> str:
    return (f"# {name} {version} — OpenHarmony 编译记录\n\n"
            f"## 基本信息\n- 软件: {name}\n- 版本: {version}\n"
            f"- 构建系统: {bs}\n- 目标: ohos-aarch64\n\n"
            f"## 编译指导\n<!-- 编译注意事项 -->\n\n"
            f"## 补丁清单\n<!-- patches/ 目录中的补丁说明 -->\n\n"
            f"## 已知限制\n<!-- 平台相关限制 -->\n\n"
            f"## 功能验证\n<!-- 验证命令和结果 -->\n")


def init_archive_cli(argv: list[str] | None = None) -> int:
    import argparse
    parser = argparse.ArgumentParser(prog="ohc init-archive")
    parser.add_argument("software")
    parser.add_argument("version")
    parser.add_argument("source_url", nargs="?", default="")
    parser.add_argument("build_system", nargs="?", default="unknown")
    parser.add_argument("--clean", action="store_true")
    parser.add_argument("--project-dir")
    args = parser.parse_args(argv)
    return init_archive(args.software, args.version, args.source_url,
                        args.build_system, args.clean,
                        getattr(args, "project_dir", None))
