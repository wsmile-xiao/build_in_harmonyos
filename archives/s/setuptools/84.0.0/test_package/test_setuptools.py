#!/usr/bin/env python3
"""Consumer-side API test for setuptools 84.0.0 (R34 真实执行).

以消费者视角使用**已打包**的 setuptools。全部为硬断言（任一条失败即
print + sys.exit(1)）。关键点不是"能 import"，而是真的把 setuptools 当作
PEP 517 构建后端跑一次 wheel 构建 —— 这才是下游（以及本仓 lxml/pillow/
greenlet 等编译型 Python 包）实际需要的用法。
"""
import os
import sys
import tempfile

site = sys.argv[1]
sys.path.insert(0, site)

checks = []


def check(name, cond, detail=""):
    checks.append((name, bool(cond), detail))


# ── 1. 导入与版本 ────────────────────────────────────────────
import setuptools  # noqa: E402

check("自 site-packages 导入", setuptools.__file__.startswith(site),
      setuptools.__file__)
# version.py 经 importlib.metadata 取版本 → 必须有 dist-info
check("__version__ == 84.0.0", setuptools.__version__ == "84.0.0",
      setuptools.__version__)

# ── 2. distutils 劫持（distutils-precedence.pth + _distutils_hack）──
import _distutils_hack  # noqa: E402

check("_distutils_hack 来自包内",
      _distutils_hack.__file__.startswith(site), _distutils_hack.__file__)
import distutils.core  # noqa: E402

check("distutils 被劫持到 setuptools._distutils",
      "setuptools/_distutils" in distutils.core.__file__.replace("\\", "/"),
      distutils.core.__file__)

# ── 3. PEP 517 后端可用 ──────────────────────────────────────
import setuptools.build_meta as bm  # noqa: E402

for fn in ("build_wheel", "build_sdist", "get_requires_for_build_wheel",
           "prepare_metadata_for_build_wheel"):
    check(f"build_meta.{fn} 可调用", callable(getattr(bm, fn, None)))
check("build_meta 来自包内", bm.__file__.startswith(site), bm.__file__)

# ── 4. 真实构建一个最小 wheel（端到端）──────────────────────
with tempfile.TemporaryDirectory() as td:
    proj = os.path.join(td, "proj")
    out = os.path.join(td, "out")
    os.makedirs(proj)
    os.makedirs(out)
    with open(os.path.join(proj, "pyproject.toml"), "w") as f:
        f.write(
            "[build-system]\n"
            'requires = ["setuptools"]\n'
            'build-backend = "setuptools.build_meta"\n\n'
            "[project]\n"
            'name = "conancheck"\n'
            'version = "1.2.3"\n'
        )
    with open(os.path.join(proj, "conancheck.py"), "w") as f:
        f.write("VALUE = 42\n")

    prev = os.getcwd()
    os.chdir(proj)
    try:
        wheel = bm.build_wheel(out)
        # sdist 同样走一次（另一条上游代码路径）。
        # 必须在**同一个 os.chdir(proj) 作用域内**调用：build_sdist 是 PEP 517
        # 后端，按约定从 **cwd** 读取 pyproject.toml/setup.py。而 setuptools 在
        # cwd 找不到配置时会用合成的 `setup()` 兜底，产出退化的
        # `UNKNOWN-0.0.0.tar.gz` —— 断言会**空壳通过**；若 cwd 恰好有别的配置，
        # 构建的则是**别的项目**。故此处与 wheel 共用同一 cwd。
        sdist = bm.build_sdist(out)
    finally:
        os.chdir(prev)

    wheel_path = os.path.join(out, wheel)
    check("PEP517 build_wheel 产出 wheel", os.path.isfile(wheel_path), wheel)
    check("wheel 文件名符合规范",
          wheel.startswith("conancheck-1.2.3-") and wheel.endswith(".whl"),
          wheel)
    check("wheel 非空", os.path.getsize(wheel_path) > 0
          if os.path.isfile(wheel_path) else False,
          f"{os.path.getsize(wheel_path)}B"
          if os.path.isfile(wheel_path) else "MISSING")

    # 断言收紧为**带包名版本前缀**，防止 UNKNOWN-0.0.0.tar.gz 之类的退化产物
    # 让该断言空壳通过（管理员 P2）。
    sdist_path = os.path.join(out, sdist)
    check("PEP517 build_sdist 产出 tar.gz",
          os.path.isfile(sdist_path) and sdist.endswith(".tar.gz"), sdist)
    check("sdist 文件名带包名-版本（非退化产物）",
          sdist.startswith("conancheck-1.2.3"), sdist)
    check("sdist 非空", os.path.getsize(sdist_path) > 0
          if os.path.isfile(sdist_path) else False,
          f"{os.path.getsize(sdist_path)}B"
          if os.path.isfile(sdist_path) else "MISSING")

# ── 5. 元数据能力 ────────────────────────────────────────────
with tempfile.TemporaryDirectory() as td:
    proj = os.path.join(td, "p2")
    os.makedirs(proj)
    with open(os.path.join(proj, "pyproject.toml"), "w") as f:
        f.write(
            "[build-system]\n"
            'requires = ["setuptools"]\n'
            'build-backend = "setuptools.build_meta"\n\n'
            "[project]\n"
            'name = "conancheck2"\n'
            'version = "0.9"\n'
        )
    prev = os.getcwd()
    os.chdir(proj)
    try:
        dist_info = bm.prepare_metadata_for_build_wheel(td)
    finally:
        os.chdir(prev)
    meta = os.path.join(td, dist_info, "METADATA")
    check("prepare_metadata 生成 METADATA", os.path.isfile(meta), dist_info)
    if os.path.isfile(meta):
        with open(meta, encoding="utf8") as f:
            text = f.read()
        check("METADATA 含 Name/Version",
              "Name: conancheck2" in text and "Version: 0.9" in text,
              text.splitlines()[:3].__repr__())

# ── 6. vendored 依赖自足性（无外部 runtime 依赖）─────────────
import setuptools._vendor.packaging as _vp  # noqa: E402

check("vendored packaging 可用",
      _vp.__file__.startswith(site), _vp.__file__)
check("setuptools 无外部 runtime 依赖（MAINTAINED: requires 为空）",
      not (os.path.exists(os.path.join(site, "wheel")) or
           os.path.exists(os.path.join(site, "packaging"))),
      "wheel/packaging 不应独立出现在 site-packages（应为 vendored）")

# ── 汇总 ─────────────────────────────────────────────────────
failed = [c for c in checks if not c[1]]
print(f"\nsetuptools {setuptools.__version__} consumer API: "
      f"{len(checks) - len(failed)}/{len(checks)} passed")
for name, ok, detail in failed:
    print(f"  FAIL: {name}  {detail}")
if failed:
    sys.exit(1)
print("consumer API: PASS")
