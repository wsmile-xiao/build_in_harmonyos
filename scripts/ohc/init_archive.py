"""Create/restore compilation archive skeleton.

⭐ D4 规则：必须使用 templates/ 目录的模板文件，禁止硬编码模板。
"""
from __future__ import annotations
import re
import shutil
from datetime import datetime
from pathlib import Path

from .utils import find_project_dir, log_info, log_ok, log_warn, log_fail

# 模板目录路径（相对于 scripts/ohc/）
TEMPLATES_DIR = Path(__file__).parent.parent.parent / "templates"


def _sanitize(s: str) -> str:
    return re.sub(r'[^a-zA-Z0-9._+\-]', '', s)


def _load_template(template_name: str, name: str, version: str,
                   date: str = None, build_system: str = "unknown",
                   source_url: str = "") -> str:
    """从 templates/ 目录加载模板并填充变量（⭐ D4 规则）

    Args:
        template_name: 模板文件名（如 notes.md, README.md）
        name: 软件名
        version: 版本号
        date: 日期（可选）
        build_system: 构建系统（可选）
        source_url: 源码 URL（可选）

    Returns:
        填充后的模板内容
    """
    template_path = TEMPLATES_DIR / template_name
    if not template_path.exists():
        log_warn(f"模板文件不存在: {template_path}，使用默认骨架")
        return _fallback_template(template_name, name, version, date, build_system)

    content = template_path.read_text(encoding="utf-8")

    # 替换所有占位符格式
    replacements = {
        "{软件名}": name,
        "{{SOFTWARE_NAME}}": name,
        "{版本号}": version,
        "{{VERSION}}": version,
        "{版本}": version,
        "{构建系统}": build_system,
        "{autotools/cmake/etc}": build_system,
        "{下载链接}": source_url,
        "{源码下载链接}": source_url,
        "{日期}": date or datetime.now().strftime("%Y-%m-%d"),
        "{{DATE}}": date or datetime.now().strftime("%Y-%m-%d"),
        "YYYY-MM-DD": date or datetime.now().strftime("%Y-%m-%d"),
    }

    for old, new in replacements.items():
        content = content.replace(old, new)

    # 处理时间戳格式
    content = re.sub(r'YYYY-MM-DD HH:MM:SS',
                     datetime.now().strftime("%Y-%m-%d %H:%M:%S"), content)
    content = re.sub(r'YYYY-MM-DD HH:MM',
                     datetime.now().strftime("%Y-%m-%d %H:%M"), content)

    return content


def _fallback_template(template_name: str, name: str, version: str,
                       date: str, build_system: str) -> str:
    """模板文件不存在时的降级骨架（仅作为后备）"""
    if template_name == "notes.md":
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
    elif template_name == "README.md":
        return (f"# {name} {version} — OpenHarmony 编译记录\n\n"
                f"## 基本信息\n- 软件: {name}\n- 版本: {version}\n"
                f"- 构建系统: {build_system}\n- 目标: ohos-aarch64\n\n"
                f"## 编译指导\n<!-- 编译注意事项 -->\n\n"
                f"## 补丁清单\n<!-- patches/ 目录中的补丁说明 -->\n\n"
                f"## 已知限制\n<!-- 平台相关限制 -->\n\n"
                f"## 功能验证\n<!-- 验证命令和结果 -->\n")
    return ""


def _detect_language(source_url: str, build_system: str) -> str | None:
    """P1: 检测 Go/Rust 项目，给出平台限制提示。

    Returns:
        "go" | "rust" | None
    """
    url_lower = source_url.lower()
    bs_lower = build_system.lower()
    if any(k in url_lower for k in ["/go-", "-go/", "golang"]) or bs_lower == "go":
        return "go"
    if any(k in url_lower for k in ["/rust", "cargo"]) or bs_lower in ("rust", "cargo"):
        return "rust"
    return None


def _check_github_mirror(source_url: str) -> str | None:
    """P1: 检测 GitHub URL，返回镜像建议。

    Returns:
        镜像 URL 或 None（非 GitHub URL）
    """
    if "github.com" not in source_url:
        return None
    # Suggest gitcode.com mirror
    return source_url.replace("https://github.com/", "https://gitcode.com/")


def _generate_conanfile(name: str, version: str, build_system: str,
                        source_url: str) -> str | None:
    """从 templates/ 加载 conanfile.py 模板（⭐ D4 规则）。

    Returns:
        conanfile.py 内容，或 None（模板不可用时）
    """
    template_map = {
        "cmake": "conanfile-cmake.py",
        "autotools": "conanfile-autotools.py",
        "makefile": "conanfile-makefile.py",
        "make": "conanfile-makefile.py",
        "headeronly": "conanfile-headeronly.py",
    }
    template_name = template_map.get(build_system.lower(), "conanfile-cmake.py")
    template_path = TEMPLATES_DIR / template_name
    if not template_path.exists():
        return None

    content = template_path.read_text(encoding="utf-8")
    # Generate class name (CamelCase)
    class_name = "".join(w.capitalize() for w in re.split(r'[-_]', name))
    content = content.replace("{Name}", class_name)
    content = content.replace("{name}", name)
    content = content.replace("{version}", version)
    content = content.replace("{description}", f"{name} {version}")
    return content


def _generate_conandata(source_url: str) -> str | None:
    """从 templates/conandata.yml 加载模板（⭐ D4 规则）。"""
    template_path = TEMPLATES_DIR / "conandata.yml"
    if not template_path.exists():
        return None
    content = template_path.read_text(encoding="utf-8")
    if source_url:
        content = content.replace('url: "https://..."', f'url: "{source_url}"')
    return content


def _generate_test_package(name: str, version: str, build_system: str) -> None:
    """生成 test_package/ 脚手架（⭐ D4 规则）。

    生成:
      test_package/conanfile.py
      test_package/test.c (CMake 项目)
      test_package/CMakeLists.txt (CMake 项目)
      test_package/MANIFEST.yml
    """
    tp_dir = None  # Will be set by caller
    # This function is called from init_archive which has ver_dir
    # Implementation is inline in init_archive for directory access


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
    for d in ["patches", "reports", "packaging", "test_package"]:
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

    # P1: 语言检测
    lang = _detect_language(source_url, build_system)
    if lang == "go":
        log_warn("  ⚠️ Go 项目: 鸿蒙 PC 原生环境可能未预装 Go 工具链")
        log_warn("    Go 链接器在 OHOS 上因 mmap 限制可能失败")
    elif lang == "rust":
        log_warn("  ⚠️ Rust 项目: 鸿蒙 PC 原生环境无 Rust/Cargo 工具链")
        log_warn("    建议跳过此包，等待 Rust 工具链可用后再迁移")

    # P1: GitHub 镜像检测
    mirror = _check_github_mirror(source_url)
    if mirror:
        log_warn(f"  ⚠️ 源码 URL 使用 github.com，建议使用镜像: {mirror}")

    # manifest.yaml
    mf = ver_dir / "manifest.yaml"
    if not mf.exists() or mf.stat().st_size < 200:
        mf.write_text(_manifest_template(name, version, build_system, source_url),
                       encoding="utf-8")
        log_ok("  manifest.yaml 已生成")
    else:
        log_ok("  manifest.yaml 已存在，保留")

    # conandata.yml（⭐ D4: 使用 templates/conandata.yml）
    cd = ver_dir / "conandata.yml"
    if not cd.exists():
        conandata_content = _generate_conandata(source_url)
        if conandata_content:
            cd.write_text(conandata_content, encoding="utf-8")
            log_ok("  conandata.yml 已生成（使用 templates/conandata.yml）")
            log_warn("  ⚠️ sha256 为占位符，必须运行 sha256sum 替换！")
        else:
            log_warn("  conandata.yml 模板不可用，跳过")
    else:
        log_ok("  conandata.yml 已存在，保留")

    # conanfile.py（⭐ D4: 使用 templates/ 模板）
    cf = ver_dir / "conanfile.py"
    if not cf.exists():
        conanfile_content = _generate_conanfile(name, version, build_system, source_url)
        if conanfile_content:
            cf.write_text(conanfile_content, encoding="utf-8")
            log_ok(f"  conanfile.py 已生成（{build_system} 模板）")
        else:
            log_warn(f"  conanfile.py 模板不可用（{build_system}），跳过")
    else:
        log_ok("  conanfile.py 已存在，保留")

    # test_package/ 脚手架（⭐ D4: 使用 templates/ 模板）
    tp_dir = ver_dir / "test_package"
    # test_package/conanfile.py
    tp_cf = tp_dir / "conanfile.py"
    if not tp_cf.exists():
        tp_template = "test_package-conanfile.py" if build_system.lower() == "cmake" else "test_package-conanfile-autotools.py"
        tp_template_path = TEMPLATES_DIR / tp_template
        if tp_template_path.exists():
            content = tp_template_path.read_text(encoding="utf-8")
            class_name = "".join(w.capitalize() for w in re.split(r'[-_]', name))
            content = content.replace("{Name}", class_name)
            content = content.replace("{name}", name)
            content = content.replace("{version}", version)
            tp_cf.write_text(content, encoding="utf-8")
            log_ok("  test_package/conanfile.py 已生成")
        else:
            log_warn(f"  test_package 模板不可用（{tp_template}），跳过")
    else:
        log_ok("  test_package/conanfile.py 已存在，保留")

    # test_package/test.c (for CMake projects)
    if build_system.lower() == "cmake":
        tp_test = tp_dir / "test.c"
        if not tp_test.exists():
            test_template = TEMPLATES_DIR / "test_package-test.c"
            if test_template.exists():
                content = test_template.read_text(encoding="utf-8")
                content = content.replace("{name}", name).replace("{version}", version)
                tp_test.write_text(content, encoding="utf-8")
                log_ok("  test_package/test.c 已生成")
        tp_cmake = tp_dir / "CMakeLists.txt"
        if not tp_cmake.exists():
            cmake_template = TEMPLATES_DIR / "test_package-CMakeLists.txt"
            if cmake_template.exists():
                content = cmake_template.read_text(encoding="utf-8")
                content = content.replace("{name}", name)
                tp_cmake.write_text(content, encoding="utf-8")
                log_ok("  test_package/CMakeLists.txt 已生成")

    # test_package/MANIFEST.yml
    tp_manifest = tp_dir / "MANIFEST.yml"
    if not tp_manifest.exists():
        manifest_template = TEMPLATES_DIR / "test_package-MANIFEST.yml"
        if manifest_template.exists():
            content = manifest_template.read_text(encoding="utf-8")
            content = content.replace("{name}", name).replace("{version}", version)
            tp_manifest.write_text(content, encoding="utf-8")
            log_ok("  test_package/MANIFEST.yml 已生成")
        else:
            log_warn("  test_package/MANIFEST.yml 模板不可用，跳过")
    else:
        log_ok("  test_package/MANIFEST.yml 已存在，保留")

    # notes.md（⭐ D4: 使用 templates/notes.md）
    pf = ver_dir / "notes.md"
    if not pf.exists() or len(pf.read_text(encoding="utf-8").split("\n")) < 15:
        today = datetime.now().strftime("%Y-%m-%d")
        content = _load_template("notes.md", name, version, today, build_system, source_url)
        pf.write_text(content, encoding="utf-8")
        log_ok("  notes.md 已生成（使用 templates/notes.md）")
    else:
        log_ok("  notes.md 已存在，保留")

    # 软件级 meta 同步（仅 README.md）
    fname = "README.md"
    src = ver_dir / fname
    dst = sw_dir / fname
    if src.exists() and not dst.exists():
        shutil.copy2(src, dst)

    # Verify
    missing = []
    for req in ["manifest.yaml", "notes.md", "patches", "reports", "packaging",
                "test_package", "conanfile.py", "conandata.yml"]:
        if not (ver_dir / req).exists():
            missing.append(req)
    if missing:
        log_warn(f"  验证缺失: {missing}")
        # Don't fail if only conanfile/conandata/test_package missing (non-fatal)
        critical = [m for m in missing if m in ("manifest.yaml", "notes.md", "patches", "reports")]
        if critical:
            return 3

    pcnt = len(list((ver_dir / "patches").glob("*")))
    rcnt = len(list((ver_dir / "reports").glob("*")))
    tpcnt = len(list((ver_dir / "test_package").glob("*"))) if (ver_dir / "test_package").exists() else 0
    log_ok(f"  ✅ 档案就绪: patches={pcnt} reports={rcnt} test_package={tpcnt}")
    return 0


def _manifest_template(name: str, version: str, bs: str, url: str) -> str:
    """从 templates/manifest-version.yaml 加载 manifest 模板（⭐ D4 规则）"""
    template_path = TEMPLATES_DIR / "manifest-version.yaml"
    if not template_path.exists():
        log_warn(f"模板文件不存在: {template_path}，使用内联骨架")
        t = (f"software: {name}\nversion: {version}\nstatus: archived\n"
             f"build_system: {bs}\ncreated_at: {datetime.now().strftime('%Y-%m-%d')}\n"
             f"knowledge_gained: []\npatches_applied: []\nbuild_log: logs/build.log\n")
        if url:
            t += f"source_url: {url}\n"
        return t

    content = template_path.read_text(encoding="utf-8")
    today = datetime.now().strftime("%Y-%m-%d")

    # 替换占位符
    content = content.replace("{version}", version)
    content = content.replace("{YYYY-MM-DD}", today)
    content = content.replace("system: cmake", f"system: {bs}")

    if url:
        content = content.replace('url: "https://..."', f'url: "{url}"')

    # 插入 software 字段（模板中无此字段，但 manifest 规范要求）
    if "software:" not in content:
        content = f"software: {name}\n" + content

    return content


# ⭐ D4 规则：_progress_template 和 _readme_template 已废弃
# 现在使用 _load_template() 从 templates/ 目录加载模板
# 保留 _fallback_template() 作为后备（模板文件不存在时）


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
    # R46: 任务起点即写生命周期草稿（防中断丢 result.json；best-effort 不阻塞）
    try:
        from .result_report import write_lifecycle_draft
        write_lifecycle_draft(args.software, args.version, "task_started")
    except Exception:
        pass
    return init_archive(args.software, args.version, args.source_url,
                        args.build_system, args.clean,
                        getattr(args, "project_dir", None))
