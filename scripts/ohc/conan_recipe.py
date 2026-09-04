"""Conan recipe generator — creates conanfile.py + conandata.yml + test_package/.

Reads manifest.yaml + notes.md + patches/ from the archive directory,
generates standard Conan 2.x recipe files.

Usage:
    python3 ohc-run.py conan-init <software> <version> [--force]
"""
from __future__ import annotations

import os
import re
import shutil
from pathlib import Path
from typing import Optional

from .utils import find_project_dir, log_info, log_ok, log_warn, log_fail


# ── Template paths ──
_TEMPLATES = {
    "cmake": "conanfile-cmake.py.tmpl",
    "autotools": "conanfile-autotools.py.tmpl",
    "makefile": "conanfile-makefile.py.tmpl",
    "meson": "conanfile-meson.py.tmpl",
    "headeronly": "conanfile-headeronly.py.tmpl",   # v12.21: 无构建/打包族（26% 配方）
}


def _parse_manifest(manifest_path: Path) -> dict:
    """Parse manifest.yaml (simple line-based parser, no PyYAML dependency).

    Handles 2-space indentation for nested keys:
      top_key:
        sub_key: value
        list_key:
          - item
    """
    data: dict[str, object] = {}
    if not manifest_path.exists():
        return data
    content = manifest_path.read_text(encoding="utf-8", errors="replace")
    current_section: str | None = None

    for line in content.split("\n"):
        if not line.strip() or line.strip().startswith("#"):
            continue

        stripped = line.strip()
        indent = len(line) - len(line.lstrip())

        if indent == 0:
            # Top-level key
            m = re.match(r'^(\w+):\s*(.*)$', stripped)
            if m:
                key, val = m.group(1), m.group(2).strip()
                if val and val != "[]":
                    data[key] = val.strip('"').strip("'")
                elif val == "[]":
                    data[key] = []
                else:
                    # Empty value → start a sub-section
                    current_section = key
                    data[key] = {}
            continue

        elif indent == 2 and current_section:
            # Sub-key under current_section
            m2 = re.match(r'^(\w+):\s*(.*)$', stripped)
            if m2:
                key, val = m2.group(1), m2.group(2).strip()
                if val and val != "[]":
                    if isinstance(data.get(current_section), dict):
                        data[current_section][key] = val.strip('"').strip("'")
                    else:
                        data[current_section] = {key: val.strip('"').strip("'")}
                elif val == "[]":
                    if isinstance(data.get(current_section), dict):
                        data[current_section][key] = []
                else:
                    # Nested sub-key with no value → could be a list
                    if isinstance(data.get(current_section), dict):
                        data[current_section][key] = []
            continue

        elif indent >= 4 and stripped.startswith("- "):
            # List item (4+ space indent)
            val = stripped[2:].strip().strip('"').strip("'")
            # Find which list this belongs to
            if current_section and isinstance(data.get(current_section), dict):
                # Find the last list in the section
                for k, v in reversed(list(data[current_section].items())):
                    if isinstance(v, list):
                        data[current_section][k].append(val)
                        break
            continue

    return data


def _parse_configure_options(manifest_path: Path) -> list[str]:
    """Extract configure_options list from manifest.yaml."""
    if not manifest_path.exists():
        return []
    content = manifest_path.read_text(encoding="utf-8", errors="replace")
    options = []
    in_options = False
    for line in content.split("\n"):
        stripped = line.strip()
        if stripped.startswith("configure_options:"):
            in_options = True
            continue
        if in_options:
            if stripped.startswith("- "):
                val = stripped[2:].strip().strip('"').strip("'")
                if val and not val.lower() in ("null", "~", "[]"):
                    options.append(val)
            elif stripped and not stripped.startswith("#") and not line.startswith(" "):
                break
    return options


def _parse_dependencies(manifest_path: Path) -> list[str]:
    """Extract dependencies list from manifest.yaml."""
    if not manifest_path.exists():
        return []
    content = manifest_path.read_text(encoding="utf-8", errors="replace")
    deps = []
    in_deps = False
    for line in content.split("\n"):
        stripped = line.strip()
        if stripped.startswith("dependencies:"):
            in_deps = True
            continue
        if in_deps:
            if stripped.startswith("- "):
                val = stripped[2:].strip().strip('"').strip("'")
                if val:
                    deps.append(val)
            elif stripped and not stripped.startswith("#") and not line.startswith(" "):
                break
    return deps


def _detect_build_system(manifest: dict, source_dir: Path | None = None) -> str:
    """Detect build system from manifest or source directory scan."""
    # Check BUILD_SYSTEM env var (set by init-build)
    env_bs = os.environ.get("BUILD_SYSTEM", "").strip()
    if env_bs:
        return env_bs
    # Check manifest build.system
    build = manifest.get("build", {})
    if isinstance(build, dict):
        sys_name = build.get("system", "")
        if sys_name:
            return sys_name
    # Check top-level build_system (software-level manifest)
    bs = manifest.get("build_system", "")
    if bs:
        return bs

    # Fallback: scan source directory for build system markers
    if source_dir and source_dir.is_dir():
        if (source_dir / "CMakeLists.txt").exists():
            return "cmake"
        if (source_dir / "meson.build").exists():
            return "meson"
        if (source_dir / "configure").exists() or (source_dir / "configure.ac").exists():
            return "autotools"
        if (source_dir / "Makefile").exists() or (source_dir / "makefile").exists():
            return "makefile"

    return "autotools"  # default


def _get_source_info(manifest: dict) -> tuple[str, str]:
    """Extract source URL and SHA256 from manifest."""
    source = manifest.get("source", {})
    if isinstance(source, dict):
        url = source.get("url", "")
        sha = source.get("sha256", "")
        return url, sha
    return "", ""


def _find_patches(archive_dir: Path) -> list[Path]:
    """Find all .patch files in patches/ directory."""
    patch_dir = archive_dir / "patches"
    if not patch_dir.exists():
        return []
    return sorted(patch_dir.glob("*.patch"))


def _load_template(project_dir: Path, template_name: str) -> str:
    """Load a template file from templates/ directory."""
    tmpl_path = project_dir / "templates" / template_name
    if not tmpl_path.exists():
        log_fail(f"Template not found: {tmpl_path}")
        return ""
    return tmpl_path.read_text(encoding="utf-8")


def _generate_conanfile(
    project_dir: Path,
    software: str,
    version: str,
    build_system: str,
    source_url: str,
    source_sha: str,
    dependencies: list[str],
    configure_options: list[str],
    patches: list[Path],
    manifest: dict,
) -> str:
    """Generate conanfile.py content from template + manifest data."""
    tmpl_name = _TEMPLATES.get(build_system, _TEMPLATES["autotools"])
    tmpl = _load_template(project_dir, tmpl_name)

    # Replace placeholders — ensure valid Python class name (can't start with digit)
    name_upper = software.replace("-", "").replace("_", "").title()
    if name_upper and name_upper[0].isdigit():
        name_upper = "P" + name_upper  # Prefix P for Package (e.g. 7zip → P7Zip)
    license_val = manifest.get("license", "MIT")
    homepage = manifest.get("homepage", "")
    description = manifest.get("description", f"{software} {version}")

    content = tmpl.replace("{NAME}", name_upper)
    content = content.replace("{name}", software)
    content = content.replace("{version}", version)
    content = content.replace("{description}", description)
    content = content.replace("{license}", license_val)
    content = content.replace("{homepage}", homepage)

    # Generate requirements() body
    req_lines = []
    for dep in dependencies:
        dep = dep.split('@')[0]  # 兼容性: 去掉可能的 @user/channel 后缀
        req_lines.append(f'        self.requires("{dep}")')

    if req_lines:
        req_body = "\n".join(req_lines)
    else:
        req_body = "        pass"

    # Replace the "pass" in requirements() with actual deps
    # Find the requirements method and replace its body
    content = re.sub(
        r'(def requirements\(self\):)\n.*?(?=    def |\nclass |\Z)',
        lambda m: m.group(1) + "\n" + req_body + "\n\n",
        content,
        flags=re.DOTALL,
        count=1,
    )

    # Add configure options to generate() method
    if configure_options and build_system == "cmake":
        opts_lines = []
        for opt in configure_options:
            if opt.startswith("-D"):
                # Convert -DFOO=BAR to tc.variables["FOO"] = "BAR"
                m = re.match(r'-D(\w+)=(.+)', opt)
                if m:
                    opts_lines.append(f'        tc.variables["{m.group(1)}"] = "{m.group(2)}"')
        if opts_lines:
            opts_block = "\n".join(opts_lines) + "\n"
            content = content.replace(
                '        tc.generate()',
                opts_block + '        tc.generate()',
                1,
            )
    elif configure_options and build_system == "autotools":
        opts_lines = []
        for opt in configure_options:
            if opt.startswith("--"):
                opts_lines.append(f'        tc.configure_args.append("{opt}")')
        if opts_lines:
            opts_block = "\n".join(opts_lines) + "\n"
            content = content.replace(
                '        tc.generate()',
                opts_block + '        tc.generate()',
                1,
            )

    return content


def _generate_conandata(
    software: str,
    version: str,
    source_url: str,
    source_sha: str,
    patches: list[Path],
) -> str:
    """Generate conandata.yml content."""
    lines = [
        f"# conandata.yml — {software} {version}",
        f"# Auto-generated by ohc-run.py conan-init",
        "",
        "sources:",
        f'  url: "{source_url}"',
        f'  sha256: "{source_sha}"' if source_sha else '  sha256: "REPLACE_WITH_ACTUAL_SHA256"',
    ]

    if patches:
        lines.append("")
        lines.append("patches:")
        for p in patches:
            patch_type = "portability"
            # Heuristic: if "fix" in name → bugfix, if "backport" → backport
            if "fix" in p.name.lower():
                patch_type = "bugfix"
            elif "backport" in p.name.lower():
                patch_type = "backport"
            lines.append(f'  - patch_file: "patches/{p.name}"')
            lines.append(f'    patch_description: "{p.stem.replace("-", " ")}"')
            lines.append(f'    patch_type: "{patch_type}"')
    else:
        lines.append("")
        lines.append("patches: {}")

    return "\n".join(lines) + "\n"


def _generate_test_package(
    project_dir: Path,
    software: str,
    version: str,
    archive_dir: Path,
) -> int:
    """Generate test_package/ directory from templates.

    Detects whether the package is a library or executable by checking
    the generated conanfile.py for cpp_info.libs / cpp_info.includedirs.
    """
    tp_dir = archive_dir / "test_package"
    tp_dir.mkdir(parents=True, exist_ok=True)

    name_upper = software.replace("-", "").replace("_", "").title()
    if name_upper and name_upper[0].isdigit():
        name_upper = "P" + name_upper

    # Detect package type from generated conanfile.py
    conanfile_path = archive_dir / "conanfile.py"
    is_library = False
    if conanfile_path.exists():
        content = conanfile_path.read_text(encoding="utf-8")
        is_library = "cpp_info.libs" in content or "cpp_info.includedirs" in content

    if is_library:
        # Library package: use CMake-based test_package
        tmpl = _load_template(project_dir, "test_package/conanfile.py.tmpl")
        content = tmpl.replace("{NAME}", name_upper).replace("{name}", software)
        (tp_dir / "conanfile.py").write_text(content, encoding="utf-8")

        tmpl = _load_template(project_dir, "test_package/CMakeLists.txt.tmpl")
        content = tmpl.replace("{name}", software).replace("{NAME}", name_upper)
        (tp_dir / "CMakeLists.txt").write_text(content, encoding="utf-8")

        # Minimal test.c for CMake-based test
        test_c = f'''#include <stdio.h>
#include <stdlib.h>

int main(void) {{
    printf("test {software} {version}: OK\\n");
    return 0;
}}
'''
        (tp_dir / "test.c").write_text(test_c, encoding="utf-8")
    else:
        # Executable package: use test.sh-based test_package
        tmpl = _load_template(project_dir, "test_package-executable/conanfile.py.tmpl")
        content = tmpl.replace("{ClassName}", name_upper).replace("{name}", software)
        (tp_dir / "conanfile.py").write_text(content, encoding="utf-8")

        # Generate test.sh (smoke test: --version / --help)
        tmpl = _load_template(project_dir, "test_package-executable/test.sh.tmpl")
        content = tmpl.replace("{name}", software)
        (tp_dir / "test.sh").write_text(content, encoding="utf-8")

    # ── Generate MANIFEST.yml (required by CI L0e gate) ──
    manifest_path = archive_dir / "manifest.yaml"
    sw_manifest_path = archive_dir.parent / "manifest.yaml"
    sw_manifest = _parse_manifest(sw_manifest_path)
    homepage = sw_manifest.get("homepage", "")

    # Determine check command based on build system
    conanfile_content = conanfile_path.read_text(encoding="utf-8") if conanfile_path.exists() else ""
    if "cmake.test()" in conanfile_content:
        check_cmd = "ctest"
        test_cmd = "cmake.test()"
    elif "meson.test()" in conanfile_content:
        check_cmd = "meson test"
        test_cmd = "meson.test()"
    elif "make(target=\"check\")" in conanfile_content or "autotools.make(target=" in conanfile_content:
        check_cmd = "make check"
        test_cmd = "make check"
    elif 'self.run("make check"' in conanfile_content:
        check_cmd = "make check"
        test_cmd = "make check"
    else:
        check_cmd = "make check"
        test_cmd = ""

    has_upstream_test = bool(test_cmd)

    manifest_tmpl = _load_template(project_dir, "test_package/MANIFEST.yml.tmpl")
    manifest_content = (
        manifest_tmpl
        .replace("{name}", software)
        .replace("{version}", version)
        .replace("{homepage}", homepage)
        .replace("{check_command}", check_cmd)
        .replace("{test_in_build}", str(has_upstream_test).lower())
        .replace("{test_command}", test_cmd)
        .replace("{test_file}", "<TODO: 测试源文件>")
        .replace("{source_archive}", f"{software}-{version}")
        .replace("{test_description}", "<TODO: 测试描述>")
        .replace("{test_binary}", "<TODO: 测试程序>")
        .replace("{test_package_file}", "test.c")
        .replace("{test_package_description}", "消费者测试")
        .replace("{test_package_binary}", f"test_{software}")
        .replace("{assertion_count}", "<TODO: 断言数>")
    )
    (tp_dir / "MANIFEST.yml").write_text(manifest_content, encoding="utf-8")

    return 0


def conan_init(
    software: str,
    version: str,
    force: bool = False,
    pdir: str | None = None,
) -> int:
    """Generate conanfile.py + conandata.yml + test_package/ from archive data."""
    project = Path(pdir) if pdir else Path(find_project_dir())
    letter = software[0].lower()
    archive_dir = project / "archives" / letter / software / version

    if not archive_dir.exists():
        log_fail(f"归档目录不存在: {archive_dir}")
        log_fail("请先运行 ohc-run.py init-build 创建归档骨架")
        return 1

    # Check if conanfile.py already exists
    conanfile = archive_dir / "conanfile.py"
    if conanfile.exists() and not force:
        log_warn(f"conanfile.py 已存在: {conanfile}")
        log_warn("使用 --force 覆盖生成")
        return 0

    log_info(f"🚀 生成 Conan 配方: {software} {version}")

    # ── 1. Read manifest.yaml ──
    manifest_path = archive_dir / "manifest.yaml"
    manifest = _parse_manifest(manifest_path)

    if not manifest:
        log_fail("manifest.yaml 不存在或为空")
        return 1

    # Extract info
    # Try to get source dir from build context for build system auto-detection
    source_dir = None
    ctx_file = project / f".build-context-{software}-{version}"
    if ctx_file.exists():
        try:
            ctx_content = ctx_file.read_text(encoding="utf-8")
            for line in ctx_content.split("\n"):
                if line.startswith("export BUILD_SRC_DIR="):
                    source_dir = Path(line.split("=", 1)[1].strip().strip('"'))
                    break
        except Exception:
            pass
    build_system = _detect_build_system(manifest, source_dir)
    source_url, source_sha = _get_source_info(manifest)
    dependencies = _parse_dependencies(manifest_path)
    configure_options = _parse_configure_options(manifest_path)
    patches = _find_patches(archive_dir)

    # Also check software-level manifest for license/homepage
    sw_manifest_path = archive_dir.parent / "manifest.yaml"
    sw_manifest = _parse_manifest(sw_manifest_path)
    license_val = manifest.get("license", sw_manifest.get("license", "MIT"))
    homepage = manifest.get("homepage", sw_manifest.get("homepage", ""))
    description = manifest.get("description", sw_manifest.get("description", f"{software} {version}"))

    # Merge into manifest dict for template generation
    manifest["license"] = license_val
    manifest["homepage"] = homepage
    manifest["description"] = description

    log_info(f"  构建系统: {build_system}")
    log_info(f"  源码 URL: {source_url or '(missing)'}")
    log_info(f"  依赖: {len(dependencies)} 个")
    log_info(f"  配置选项: {len(configure_options)} 个")
    log_info(f"  补丁: {len(patches)} 个")

    # ── 2. Generate conanfile.py ──
    log_info("生成 conanfile.py...")
    conanfile_content = _generate_conanfile(
        project, software, version, build_system,
        source_url, source_sha, dependencies,
        configure_options, patches, manifest,
    )
    conanfile.write_text(conanfile_content, encoding="utf-8")
    log_ok(f"  ✅ {conanfile.relative_to(project)}")

    # ── 3. Generate conandata.yml ──
    log_info("生成 conandata.yml...")
    conandata_content = _generate_conandata(
        software, version, source_url, source_sha, patches,
    )
    conandata = archive_dir / "conandata.yml"
    conandata.write_text(conandata_content, encoding="utf-8")
    log_ok(f"  ✅ {conandata.relative_to(project)}")

    # ── 4. Generate test_package/ ──
    log_info("生成 test_package/...")
    _generate_test_package(project, software, version, archive_dir)
    log_ok(f"  ✅ test_package/")

    # ── 5. Summary ──
    print()
    print("╔═══ CONAN RECIPE GENERATED ═══════════════════════╗")
    print(f"║ Software:  {software} {version}")
    print(f"║ Archive:   {archive_dir.relative_to(project)}")
    print(f"║ Files:     conanfile.py + conandata.yml + test_package/ + MANIFEST.yml")
    print("║")
    print("║ ⭐ 下一步:")
    print("║   1. 检查 conanfile.py 的 requirements() 和 package_info()")
    print("║   2. 检查 conandata.yml 的 sha256 是否正确")
    print("║   3. 填写 test_package/MANIFEST.yml 的上游测试声明")
    print("║   4. 运行验证: ohc-run.py conan-verify " + f"{software} {version}")
    print("╚══════════════════════════════════════════════════╝")

    return 0


def conan_init_cli(argv: list[str] | None = None) -> int:
    import argparse
    parser = argparse.ArgumentParser(
        prog="ohc conan-init",
        description="从 manifest.yaml + notes.md + patches/ 生成 Conan 配方",
    )
    parser.add_argument("software", help="软件名称")
    parser.add_argument("version", help="版本号")
    parser.add_argument("--force", action="store_true", help="覆盖已有的 conanfile.py")
    parser.add_argument("--project-dir")
    args = parser.parse_args(argv)
    rc = conan_init(
        args.software, args.version, force=args.force,
        pdir=getattr(args, "project_dir", None),
    )
    if rc == 0:
        # R46: 配方生成成功 → 里程碑草稿
        try:
            from .result_report import write_lifecycle_draft
            write_lifecycle_draft(args.software, args.version,
                                  "recipe_generated")
        except Exception:
            pass
    return rc
