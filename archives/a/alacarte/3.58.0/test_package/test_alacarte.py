#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""test_alacarte.py — alacarte 3.58.0 test_package 真实测试源文件。

上游无任何测试框架/用例（CI 仅跑 make distcheck），本文件为适配补全
（L0c + R34 合规：真实调用被测包 API）。alacarte 是纯 Python GTK 应用，
OHOS CI 无 GTK/pygobject/图形环境，因此核心纯逻辑以 mock gi 后直接
加载被测包 Alacarte.util 验证（鸿蒙特有测试：去 GUI 依赖的单元测试）。

覆盖:
  T1 语法编译: 交付包内全部 .py 可被 py_compile 编译（无语法错误）
  T2 唯一文件名: util.getUniqueRedoFile / getUniqueFileId / getUniqueUndoFile
  T3 KeyFile 填充: util.fillKeyFile 类型分发
  T4 包结构: bin/alacarte 可执行 + site-packages/Alacarte 模块齐全 + config.py 版本
  T5 R34 负向防护: 被测 Alacarte.util.__file__ 必须位于被测包目录内
"""
import os
import sys
import types
import tempfile
import py_compile


# ── T0: 注入 gi/gi.repository mock（OHOS CI 无 GTK/pygobject）─────────
class _KeyFileFlags:
    KEEP_COMMENTS = 1
    KEEP_TRANSLATIONS = 2


class _MockGLib:
    KEY_FILE_DESKTOP_GROUP = "Desktop Entry"
    KeyFileFlags = _KeyFileFlags

    def __init__(self, data_dir, config_dir):
        self._data_dir = data_dir
        self._config_dir = config_dir

    def get_user_data_dir(self):
        return self._data_dir

    def get_system_data_dirs(self):
        return [self._data_dir]

    def get_user_config_dir(self):
        return self._config_dir

    def get_system_config_dirs(self):
        return [self._config_dir]


def _install_gi_mock(tmp):
    data_dir = os.path.join(tmp, "data")
    config_dir = os.path.join(tmp, "config")
    os.makedirs(data_dir, exist_ok=True)
    os.makedirs(config_dir, exist_ok=True)

    gi = types.ModuleType("gi")
    gi.require_version = lambda *a, **k: None
    repo = types.ModuleType("gi.repository")
    glib = _MockGLib(data_dir, config_dir)
    for name in ("Gtk", "GdkPixbuf", "GMenu"):
        m = types.ModuleType("gi.repository." + name)
        setattr(repo, name, m)
        sys.modules["gi.repository." + name] = m
    setattr(repo, "GLib", glib)
    gi.repository = repo
    sys.modules["gi"] = gi
    sys.modules["gi.repository"] = repo
    sys.modules["gi.repository.GLib"] = glib
    return data_dir, config_dir


def main():
    args = sys.argv[1:]
    pkg_root = args[0] if args else os.getcwd()  # conan package_folder
    site = os.path.join(pkg_root, "lib", "python3.12", "site-packages")
    alacarte_dir = os.path.join(site, "Alacarte")

    passed = 0
    failed = 0
    failures = []

    def check(name, cond, detail=""):
        nonlocal passed, failed
        if cond:
            passed += 1
            print(f"  [PASS] {name}")
        else:
            failed += 1
            failures.append(f"{name}: {detail}")
            print(f"  [FAIL] {name}: {detail}")

    # ── 前置: 包必须存在（R34: test 真实依赖被测包）──────────────────
    check("package Alacarte exists", os.path.isdir(alacarte_dir),
          f"missing {alacarte_dir}")

    # ── T1: 语法编译所有交付 .py ─────────────────────────────────────
    py_files = []
    for root, _dirs, files in os.walk(alacarte_dir):
        for fn in files:
            if fn.endswith(".py"):
                py_files.append(os.path.join(root, fn))
    check("T1 .py files found", len(py_files) >= 5,
          f"only {len(py_files)} .py under Alacarte/")
    syntax_ok = True
    for pf in sorted(py_files):
        try:
            py_compile.compile(pf, doraise=True)
        except py_compile.PyCompileError as e:
            syntax_ok = False
            print(f"    syntax error in {pf}: {e}")
    check("T1 py_compile all modules", syntax_ok)

    # ── T5: R34 负向防护（被测模块必须来自被测包）────────────────────
    tmp = tempfile.mkdtemp(prefix="alacarte-test-")
    _install_gi_mock(tmp)
    sys.path.insert(0, site)
    import Alacarte.util as util
    check("T5 util from package", util.__file__.startswith(alacarte_dir),
          f"{util.__file__}")

    # ── T2: 唯一文件名生成逻辑 ───────────────────────────────────────
    fpath = os.path.join(tmp, "foo.desktop")
    open(fpath, "w").close()
    r0 = util.getUniqueRedoFile(fpath)  # 无 .redo 冲突 → .redo-0
    check("T2 redo-0 first", r0 == fpath + ".redo-0", r0)
    open(r0, "w").close()
    r1 = util.getUniqueRedoFile(fpath)  # .redo-0 已存在 → .redo-1
    check("T2 redo-1 second", r1 == fpath + ".redo-1", r1)

    uid = util.getUniqueFileId("app", ".desktop")
    check("T2 file-id base", uid == "app.desktop", uid)
    user_items = util.getUserItemPath()
    os.makedirs(user_items, exist_ok=True)
    open(os.path.join(user_items, "app.desktop"), "w").close()
    uid2 = util.getUniqueFileId("app", ".desktop")
    check("T2 file-id unique", uid2 == "app-1.desktop", uid2)

    u0 = util.getUniqueUndoFile("app.desktop")
    check("T2 undo base", u0.endswith("app.desktop.undo-0"), u0)
    open(u0, "w").close()
    u1 = util.getUniqueUndoFile("app.desktop")
    check("T2 undo unique", u1.endswith("app.desktop.undo-1"), u1)

    # ── T3: fillKeyFile 类型分发 ─────────────────────────────────────
    class _Recorder:
        def __init__(self):
            self.calls = []

        def set_boolean(self, g, k, v):
            self.calls.append(("bool", k, v))

        def set_string(self, g, k, v):
            self.calls.append(("str", k, v))

        def set_string_list(self, g, k, v):
            self.calls.append(("list", k, v))

    rec = _Recorder()
    util.fillKeyFile(rec, {
        "Name": "Test App",
        "Hidden": True,
        "OnlyShowIn": ["a", "b"],
        "SkipMe": None,  # None → 跳过
    })
    check("T3 fillKeyFile count", len(rec.calls) == 3, f"calls={rec.calls}")
    check("T3 fillKeyFile types",
          [c[0] for c in rec.calls] == ["str", "bool", "list"],
          f"calls={rec.calls}")

    # ── T4: 包结构（launcher + 模块 + config.py 版本）─────────────────
    launcher = os.path.join(pkg_root, "bin", "alacarte")
    check("T4 bin/alacarte exists", os.path.isfile(launcher))
    if os.path.isfile(launcher):
        check("T4 bin/alacarte executable", os.access(launcher, os.X_OK))
        with open(launcher, encoding="utf-8") as f:
            head = f.read(60)
        check("T4 launcher shebang env-python", "env python3" in head, head)
    cfg = os.path.join(alacarte_dir, "config.py")
    check("T4 config.py exists", os.path.isfile(cfg))
    if os.path.isfile(cfg):
        cfg_txt = open(cfg, encoding="utf-8").read()
        check("T4 config version",
              'VERSION="3.58.0"' in cfg_txt or 'VERSION = "3.58.0"' in cfg_txt,
              cfg_txt[:80])
    for mod in ("__init__", "MainWindow", "MenuEditor",
                "ItemEditor", "util", "config"):
        check(f"T4 module {mod}", os.path.isfile(
            os.path.join(alacarte_dir, mod + ".py")),
            os.path.join(alacarte_dir, mod + ".py"))

    # ── 汇总 ────────────────────────────────────────────────────────
    print(f"\nRESULT: {passed} passed, {failed} failed")
    if failed:
        print("FAILURES:")
        for f_ in failures:
            print("  - " + f_)
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()
