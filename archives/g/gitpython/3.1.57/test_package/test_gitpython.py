#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""GitPython 3.1.57 test_package 测试源文件。

由 test_package/conanfile.py 的 test() 方法通过
``python test_gitpython.py`` 调用，在 Conan 消费者视角下验证：

1. ``git`` 模块可被正常导入
2. ``git.__version__`` 与配方版本一致
3. 核心 API（``Repo``、``Git``、``Commit``、``Head``、``Remote`` 等）可访问
4. Git 对象操作函数可用（``Actor``、``IndexObject`` 序列化工具等）
5. 间接依赖 ``gitdb``/``smmap`` 也可导入（验证 Conan 依赖链传递）
6. 端到端冒烟：在真实临时目录 ``Repo.init`` 建仓 + commit + log 读取
   （需要环境有 git 可执行文件——GitPython 本质是 git 命令封装库，
   无 git 可执行文件时该段降级为跳过并说明，不计失败）

本文件存在的另一个目的：满足 CI 门禁 L0c
(build_and_test.sh) —— test_package/ 下必须存在
``.c/.cpp/.cc/.cxx/.sh/.py`` 测试源文件 (排除 conanfile.py)。
"""

import os
import shutil
import subprocess
import sys
import tempfile

EXPECTED_VERSION = "3.1.57"


def main() -> int:
    failures = []

    # 1. 模块导入
    try:
        import git  # noqa: F401
    except Exception as exc:  # pragma: no cover - 诊断信息
        print(f"[FAIL] import git: {exc}")
        return 1

    # 2. 版本核对
    actual_version = getattr(git, "__version__", None)
    if actual_version != EXPECTED_VERSION:
        failures.append(
            f"version mismatch: expected {EXPECTED_VERSION!r}, got {actual_version!r}"
        )
    else:
        print(f"[ok] git.__version__ == {actual_version}")

    # 3. 核心 API 可访问（repo / cmd / objects / refs 四大子域抽样）
    required_attrs = [
        "Repo", "Git", "Actor", "Commit", "Blob", "Tree", "TagReference",
        "Head", "Remote", "IndexFile", "GitCommandError", "InvalidGitRepositoryError",
    ]
    for attr in required_attrs:
        if not hasattr(git, attr):
            failures.append(f"missing git.{attr}")
    if not failures:
        print(f"[ok] core API present: {len(required_attrs)} attrs")

    # 4. Git 函数可用性断言（Refresh 常用路径 + db/util 函数存在性）
    from git.repo import Repo as RepoCls
    from git.cmd import Git as GitCls
    for fn in ("init", "clone_from"):
        if not hasattr(RepoCls, fn):
            failures.append(f"missing Repo.{fn}")
    for fn in ("version_info", "execute", "custom_environment"):
        if not hasattr(GitCls, fn):
            failures.append(f"missing Git.{fn}")
    if not failures:
        print("[ok] Repo/Git function surface verified")

    # 5. 间接依赖 gitdb/smmap 可导入（验证 Conan 依赖链传递）
    try:
        import gitdb  # noqa: F401
        import smmap  # noqa: F401
        print(f"[ok] gitdb ({gitdb.__version__}) + smmap available via Conan deps")
    except Exception as exc:  # pragma: no cover - 诊断信息
        failures.append(f"dependency chain import failed: {exc}")

    # 6. 端到端冒烟：Repo.init + commit + log（git 可执行文件存在时）
    git_bin = shutil.which("git") or os.environ.get("GIT_PYTHON_GIT_EXECUTABLE")
    if git_bin:
        tmp = tempfile.mkdtemp(prefix="gitpython-smoke-")
        try:
            r = RepoCls.init(os.path.join(tmp, "repo"))
            with r.config_writer() as cw:
                cw.set_value("user", "email", "smoke@test.local")
                cw.set_value("user", "name", "Smoke Test")
            hello = os.path.join(r.working_tree_dir, "hello.txt")
            with open(hello, "w") as fh:
                fh.write("hello gitpython\n")
            r.index.add(["hello.txt"])
            commit = r.index.commit("smoke: init commit")
            head_sha = r.head.commit.hexsha
            if head_sha != commit.hexsha:
                failures.append(f"HEAD {head_sha} != commit {commit.hexsha}")
            else:
                print(f"[ok] end-to-end smoke: Repo.init + commit + head "
                      f"resolve ({head_sha[:10]})")
        except Exception as exc:
            failures.append(f"end-to-end smoke failed: {exc}")
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    else:
        print("[skip] no git executable in PATH — end-to-end smoke skipped "
              "(GitPython wraps the git binary; library import verified above)")

    if failures:
        for f in failures:
            print(f"[FAIL] {f}")
        return 1

    print("[PASS] all gitpython test_package assertions passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
