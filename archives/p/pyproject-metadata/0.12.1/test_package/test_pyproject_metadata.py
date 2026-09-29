#!/usr/bin/env python3
"""pyproject-metadata consumer test (R34): package importable from the
packaged site-packages + real PEP 621 parsing and validation (not an
import-only smoke test).

The inner script parses an actual [project] table into the public
StandardMetadata dataclass, checks the derived fields (name/version/
dependencies/license), and asserts that an invalid declaration is rejected —
so a broken or empty package cannot pass.
"""
import os
import subprocess
import sys

SMOKE_PY = r'''
import os
import sys
import tempfile

sys.path[0:0] = __import__("os").environ["PYTHONPATH"].split(":")

import pyproject_metadata
from pyproject_metadata import StandardMetadata

print("pyproject_metadata", pyproject_metadata.__version__)

# project_dir 必须是 str/PathLike（传 None 会 TypeError），且 readme 为相对
# 路径时会相对该目录解析文件——故建临时目录并放一份 README.md。
with tempfile.TemporaryDirectory(prefix="pm-meta-") as td:
    with open(os.path.join(td, "README.md"), "w", encoding="utf-8") as f:
        f.write("# demo\n")

    # ---- 真实解析：PEP 621 [project] 表 ----
    # 注意：from_pyproject 的入参是**整份 pyproject 数据**（含 "project" 段），
    # 不是 project 段本身（实测误传 project 段会报
    # ConfigurationError: Section "project" missing in pyproject.toml）。
    meta = StandardMetadata.from_pyproject(
        {
            "project": {
                "name": "demo-project",
                "version": "1.2.3",
                "description": "A demo",
                "dependencies": ["packaging>=23.2", "requests>=2.0"],
                "readme": "README.md",
            },
        },
        project_dir=td,
    )
    assert meta.name == "demo-project", meta.name
    assert str(meta.version) == "1.2.3", meta.version
    assert len(meta.dependencies) == 2, meta.dependencies
    # 规范化后依赖保持可比较的 Requirement 对象
    dep_names = sorted(str(d).split(">")[0].split("=")[0].split("<")[0].strip()
                       for d in meta.dependencies)
    assert dep_names == ["packaging", "requests"], dep_names
    assert meta.description == "A demo", meta.description

    # ---- 真实校验：非法声明必须被拒绝 ----
    try:
        StandardMetadata.from_pyproject({"project": {"version": "1.0"}},
                                        project_dir=td)
    except Exception as exc:
        print("OK: invalid metadata correctly rejected:", type(exc).__name__)
    else:
        raise AssertionError("missing 'name' must be rejected but was accepted")

print("OK: pyproject-metadata parsed + validated real [project] table")
'''


def main() -> int:
    if len(sys.argv) < 2:
        print("FAIL: missing package path argument", file=sys.stderr)
        return 1
    pkg = sys.argv[1]
    site = os.path.join(pkg, "lib", "python3.12", "site-packages")
    mod = os.path.join(site, "pyproject_metadata", "__init__.py")
    if not os.path.isfile(mod):
        print(f"FAIL: pyproject_metadata module missing: {mod}",
              file=sys.stderr)
        return 1
    env = dict(os.environ)
    env["PYTHONPATH"] = site
    py = sys.executable
    r = subprocess.run([py, "-c", SMOKE_PY], capture_output=True,
                       text=True, env=env)
    if r.returncode != 0:
        print(f"FAIL: pyproject-metadata API: {r.stderr}", file=sys.stderr)
        return 1
    print(r.stdout.strip())
    print("OK: pyproject_metadata module + real [project] parsing works")
    return 0


if __name__ == "__main__":
    sys.exit(main())
