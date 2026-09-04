"""recipe_search — 配方首稿检索（成长型语料，v12.6 L1）

语料三层（成长即生效）:
  1. 主仓 archives/*/*/*/conanfile.py（历史配方智慧，~2280 包）
  2. knowledge/recipes/catalog.tsv —— 特征索引（git 同步，社区每人成功配方
     经 finish 后 upsert，pull/merge 即汇聚）
  3. 新增配方无需注册：--rebuild 全量重建索引，或 finish 自动 upsert

设计原则（社区模式）: 本地可跑、零外部服务；索引是缓存不是事实源
（事实源永远是 conanfile.py 本身，索引可随时重建）。

用法:
  ohc-run.py recipe-search <name> [--build-system X] [--deps a,b] [--top N]
  ohc-run.py recipe-search --rebuild          # 全量重建 catalog.tsv
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

from .utils import find_project_dir, log_info, log_ok, log_warn, log_fail

# catalog 列: name  version  build_system  deps  options  patches  path
_HEADER = "# catalog.tsv — 配方特征索引（缓存，可 --rebuild 重建；finish 成功自动 upsert）"


def _catalog_path(pdir: str | None) -> Path:
    return Path(find_project_dir()) / "knowledge" / "recipes" / "catalog.tsv"


def _features_from_conanfile(text: str) -> dict:
    """从 conanfile.py 文本抽取特征（纯正则，不 import）。"""
    bs = "unknown"
    if re.search(r"from conan\.tools\.cmake import", text):
        bs = "cmake"
    elif re.search(r"from conan\.tools\.gnu import|AutotoolsToolchain", text):
        bs = "autotools"
    elif re.search(r"from conan\.tools\.meson import|MesonToolchain", text):
        bs = "meson"
    elif re.search(r"from conan\.tools\.make import|MakeToolchain", text):
        bs = "make"
    elif re.search(r"from conan\.tools\.scm|MSBuild", text):
        bs = "msbuild"
    elif "self.info.clear()" in text:
        bs = "headeronly"          # v12.21: 无构建族 A（header-only 库）
    elif "def build" not in text or not re.search(
            r"self\.run\(|Toolchain|Autotools|CMake\(|Meson\(", text):
        bs = "copy"                # v12.21: 无构建族 B/C（数据/脚本工具打包）

    deps = re.findall(r'self\.requires\(\s*["\']([^/"\']+)', text)
    if not deps:
        m = re.search(r"^\s*requires\s*=\s*[\(\[](.*?)[\)\]]", text, re.S | re.M)
        if m:
            deps = re.findall(r'["\']([^/"\']+)', m.group(1))

    n_options = len(re.findall(r'^\s{4}"\w+(?:/\w+)?":\s*["ANY]', text, re.M)) or \
        len(re.findall(r'^\s{4}"\w+":\s*\[', text, re.M))
    has_settings = bool(re.search(r"^\s*settings\s*=", text, re.M))
    has_tests = "test_package" in text or True  # 归档结构里基本都有，意义不大，忽略

    return {
        "build_system": bs,
        "deps": sorted({d.strip().split("/")[0].split("@")[0].lower() for d in deps}),
        "n_deps": len(deps),
        "n_options": n_options,
        "has_settings": has_settings,
    }


def build_catalog(pdir: str | None = None) -> int:
    """全量扫描 archives 重建 catalog.tsv。"""
    project = Path(find_project_dir())
    rows = []
    for cf in sorted(project.glob("archives/*/*/*/conanfile.py")):
        if cf.parent.name == "test_package":
            continue
        parts = cf.relative_to(project).parts  # archives/x/name/ver/conanfile.py
        if len(parts) < 4:
            continue
        name, version = parts[-3], parts[-2]
        try:
            text = cf.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        f = _features_from_conanfile(text)
        conandata = cf.parent / "conandata.yml"
        has_patches = "patches:" in conandata.read_text(encoding="utf-8", errors="ignore") if conandata.exists() else False
        rows.append("\t".join([
            name, version, f["build_system"],
            ",".join(f["deps"]), str(f["n_options"]),
            "1" if has_patches else "0",
            str(cf.relative_to(project)),
        ]))
    out = _catalog_path(pdir)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(_HEADER + "\n" + "\n".join(rows) + "\n", encoding="utf-8")
    log_ok(f"catalog 重建: {len(rows)} 配方 → {out}")
    return len(rows)


def load_catalog(pdir: str | None = None) -> list[dict]:
    path = _catalog_path(pdir)
    if not path.exists():
        log_warn("catalog.tsv 不存在，自动全量重建...")
        build_catalog(pdir)
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("#") or not line.strip():
            continue
        parts = line.split("\t")
        if len(parts) != 7:
            continue
        rows.append({
            "name": parts[0], "version": parts[1], "build_system": parts[2],
            "deps": [d for d in parts[3].split(",") if d],
            "n_options": parts[4], "patches": parts[5] == "1", "path": parts[6],
        })
    return rows


def _jaccard(a: set, b: set) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def _name_tokens(name: str) -> set:
    return {t for t in re.split(r"[-_+]+", name.lower()) if len(t) > 1}


def search(query: str, build_system: str = "", deps: list[str] | None = None,
           top_n: int = 3, pdir: str | None = None) -> list[tuple[float, dict]]:
    catalog = load_catalog(pdir)
    deps = [d.strip().lower() for d in (deps or []) if d.strip()]
    q_tokens = _name_tokens(query)
    results = []
    for row in catalog:
        score = _jaccard(q_tokens, _name_tokens(row["name"])) * 0.45
        if build_system and row["build_system"] == build_system:
            score += 0.30
        if deps:
            score += _jaccard(set(deps), set(row["deps"])) * 0.25
        # 微调：带补丁的配方参考价值更高（包含真实适配智慧）
        if row["patches"]:
            score += 0.05
        if score > 0.10:
            results.append((round(score, 3), row))
    results.sort(key=lambda x: -x[0])
    return results[:top_n]


def upsert_catalog(name: str, version: str, pdir: str | None = None) -> None:
    """finish 成功后调用：把新成功配方并入语料（社区 pull/merge 即共享）。"""
    project = Path(find_project_dir())
    cf = project / "archives" / name[0] / name / version / "conanfile.py"
    if not cf.exists():
        return
    text = cf.read_text(encoding="utf-8", errors="ignore")
    f = _features_from_conanfile(text)
    conandata = cf.parent / "conandata.yml"
    has_patches = "patches:" in conandata.read_text(encoding="utf-8", errors="ignore") if conandata.exists() else False
    new_row = "\t".join([
        name, version, f["build_system"], ",".join(f["deps"]),
        str(f["n_options"]), "1" if has_patches else "0",
        str(cf.relative_to(project)),
    ])
    path = _catalog_path(pdir)
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = []
    replaced = False
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            parts = line.split("\t")
            if len(parts) == 7 and parts[0] == name and parts[1] == version:
                lines.append(new_row)
                replaced = True
            else:
                lines.append(line)
    if not replaced:
        lines.append(new_row)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def recipe_search_cli(argv: list[str] | None = None) -> int:
    import argparse
    parser = argparse.ArgumentParser(
        prog="ohc recipe-search",
        description="配方首稿检索：从历史成功配方中找最相似骨架（语料随社区成长）",
    )
    parser.add_argument("name", nargs="?", help="目标软件名")
    parser.add_argument("--build-system", "-b", help="构建系统（cmake/autotools/meson/make/headeronly/copy）")
    parser.add_argument("--deps", "-d", help="已知依赖，逗号分隔")
    parser.add_argument("--top", type=int, default=3)
    parser.add_argument("--rebuild", action="store_true", help="全量重建 catalog.tsv")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--project-dir", "-p")
    args = parser.parse_args(argv)

    if args.rebuild:
        build_catalog(args.project_dir)
        return 0
    if not args.name:
        parser.error("需要软件名（或 --rebuild）")

    results = search(args.name, args.build_system or "",
                     args.deps.split(",") if args.deps else [], args.top, args.project_dir)
    if not results:
        log_warn(f"无相似配方（语料 {len(load_catalog(args.project_dir))} 条）——首稿走 conan-init 模板")
        return 0

    if args.json:
        import json
        print(json.dumps([{"score": s, **r} for s, r in results], ensure_ascii=False, indent=2))
        return 0

    log_info(f"配方检索: {args.name}（构建系统={args.build_system or '自动'}, 依赖={args.deps or '未知'}）")
    for i, (score, r) in enumerate(results, 1):
        patch_mark = " +补丁" if r["patches"] else ""
        print(f"  {i}. {r['name']}/{r['version']}  [{r['build_system']}]  score={score}{patch_mark}")
        if r["deps"]:
            print(f"     依赖: {', '.join(r['deps'][:8])}{' ...' if len(r['deps']) > 8 else ''}")
        print(f"     骨架: {r['path']}")
    print()
    print("  💡 用法: conan-init 前先阅读 top1 骨架的 options/patches/deps 处理方式，")
    print("     以其为底稿生成首稿（而非从空白模板起步）")
    return 0
