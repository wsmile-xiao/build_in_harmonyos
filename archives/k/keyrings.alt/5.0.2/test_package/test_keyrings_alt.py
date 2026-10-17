#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""keyrings.alt 5.0.2 test_package 测试源文件。

由 test_package/conanfile.py 的 test() 方法通过
``python test_keyrings_alt.py`` 调用，在 Conan 消费者视角下验证：

1. 包结构完整：keyrings/ + keyrings/alt/ 均在包内（find spec 定位到
   conan 包目录而非环境 site-packages）
2. ``import keyrings.alt`` 成功（__init__.py 为空，零上游运行时依赖）
3. 后端模块可寻址断言：file/file_base/escape/multi/Gnome/Google/
   Windows/keyczar 八个后端模块经 ``importlib.util.find_spec`` 在包内
   可寻址（不执行模块体——Gnome/Google/keyczar 模块体 import 未发布的
   keyring/jaraco 依赖，寻址≠加载，属诚实降级而非空壳跳过）
4. escape/unescape 真实功能往返（无任何外部依赖，纯 stdlib 正则）
5. 桩替 keyring/jaraco.classes/jaraco.context 后的 PlaintextKeyring
   真实读写往返（set_password → get_password → delete_password，
   真实落盘 configparser 文件）——keyring/jaraco 系在制品仓无配方
   （R36），消费者侧注入最小桩模块（keyring.backend.KeyringBackend /
   keyring.errors / keyring.util.platform_ / jaraco.classes.properties）
   验证 keyrings.alt 自身代码路径的完整功能，同上游 tests/ 以 keyring
   testing 框架驱动的思路，桩面仅覆盖被测代码实际触碰的属性
6. 消费者可发现入口点声明（keyring.backends entry-points 元数据存在）

本文件存在的另一个目的：满足 CI 门禁 L0c
(build_and_test.sh) —— test_package/ 下必须存在
``.c/.cpp/.cc/.cxx/.sh/.py`` 测试源文件 (排除 conanfile.py)。
"""

import configparser
import importlib.util
import os
import sys
import tempfile
import types

EXPECTED_VERSION = "5.0.2"

# keyrings.alt 后端模块清单（pyproject entry-points 全量 + file_base/escape）
BACKEND_MODULES = [
    "file", "file_base", "escape", "multi",
    "Gnome", "Google", "Windows", "keyczar",
]

# 桩替的第三方模块（制品仓无配方，见配方 docstring——R36）
STUB_MODULES = [
    "keyring", "keyring.backend", "keyring.errors", "keyring.util",
    "keyring.util.platform_", "keyring.testing", "keyring.testing.backend",
    "jaraco", "jaraco.classes", "jaraco.context",
]


def _install_stubs() -> dict:
    """安装 keyring/jaraco 最小桩模块（消费者侧诚实降级）。

    桩面覆盖 keyrings.alt 源码（file_base/file/multi/keyczar）在
    PlaintextKeyring/MultipartKeyringWrapper 读写路径上实际触碰的属性：
      - keyring.backend.KeyringBackend（基类，仅 mro 占位）
      - keyring.errors.PasswordDeleteError（delete_password 抛出）
      - keyring.util.platform_.data_root()（file_path 默认根目录）
      - jaraco.classes.properties.NonDataProperty/classproperty
        （file_path/file_version/priority 装饰器）
    """
    stubs = {}

    keyring_top = types.ModuleType("keyring")
    keyring_top.__path__ = []

    keyring_backend = types.ModuleType("keyring.backend")

    class KeyringBackend:
        priority = 1

        @classmethod
        def get_priority(cls):
            return cls.priority

        @classmethod
        def viable(cls):
            return True

    class Crypter:
        """Mirrors keyring.backend.Crypter (abstract encrypt/decrypt)."""

        @staticmethod
        def encrypt(value):
            raise NotImplementedError

        @staticmethod
        def decrypt(value):
            raise NotImplementedError

    keyring_backend.KeyringBackend = KeyringBackend
    keyring_backend.Crypter = Crypter

    keyring_errors = types.ModuleType("keyring.errors")

    class PasswordSetError(Exception):
        pass

    class PasswordDeleteError(Exception):
        pass

    keyring_errors.PasswordSetError = PasswordSetError
    keyring_errors.PasswordDeleteError = PasswordDeleteError
    keyring_top.errors = keyring_errors

    keyring_util = types.ModuleType("keyring.util")
    keyring_util.__path__ = []
    keyring_platform = types.ModuleType("keyring.util.platform_")

    def data_root():
        return tempfile.gettempdir()

    keyring_platform.data_root = data_root
    keyring_util.platform_ = keyring_platform

    keyring_testing = types.ModuleType("keyring.testing")
    keyring_testing.__path__ = []
    keyring_testing_backend = types.ModuleType("keyring.testing.backend")

    class BackendBasicTests:
        pass

    keyring_testing_backend.BackendBasicTests = BackendBasicTests
    keyring_testing.backend = keyring_testing_backend
    keyring_top.testing = keyring_testing
    keyring_top.backend = keyring_backend

    jaraco_top = types.ModuleType("jaraco")
    jaraco_top.__path__ = []
    jaraco_classes = types.ModuleType("jaraco.classes")

    class _PropertyBase:
        def __init__(self, fget):
            self.fget = fget
            self.__doc__ = fget.__doc__

        def __get__(self, obj, objtype=None):
            if obj is None:
                return self
            return self.fget(obj)

        def __set__(self, obj, value):
            # NonDataProperty：实例字典优先，可被覆盖（file_path 覆盖场景）
            obj.__dict__[self.attr_name(obj)] = value

        def attr_name(self, obj):
            return self.fget.__name__

    class NonDataProperty(_PropertyBase):
        # non-data descriptor: no __set__ — instance __dict__ takes
        # precedence (that is exactly how keyrings.alt overrides file_path
        # per-instance in upstream tests)
        pass

    class classproperty:
        def __init__(self, fget):
            self.fget = fget

        def __get__(self, obj, objtype=None):
            return self.fget(objtype if objtype is not None else type(obj))

    jaraco_classes.properties = types.SimpleNamespace(
        NonDataProperty=NonDataProperty, classproperty=classproperty,
    )
    jaraco_top.classes = jaraco_classes

    jaraco_context = types.ModuleType("jaraco.context")

    class ExceptionTrap:
        """Mirrors jaraco.context.ExceptionTrap — probe decorator.

        keyrings.alt/alt/keyczar.py 在模块体执行
        ``passes = ExceptionTrap().passes``，随后 ``@passes def has_keyczar()``
        用捕获的 ImportError 探测 keyczar 库存在性——桩版陷阱一律放行
        （has_keyczar 成功），keyczar 命名空间由测试内 MockKeyczar 注入
        （上游 tests/mocks.py 同款手法）。
        """

        def passes(self, func):
            def inner(*args, **kwargs):
                return func(*args, **kwargs)
            return inner

    jaraco_context.ExceptionTrap = ExceptionTrap

    stubs["keyring"] = keyring_top
    stubs["keyring.backend"] = keyring_backend
    stubs["keyring.errors"] = keyring_errors
    stubs["keyring.util"] = keyring_util
    stubs["keyring.util.platform_"] = keyring_platform
    stubs["keyring.testing"] = keyring_testing
    stubs["keyring.testing.backend"] = keyring_testing_backend
    stubs["jaraco"] = jaraco_top
    stubs["jaraco.classes"] = jaraco_classes
    stubs["jaraco.context"] = jaraco_context

    for name, mod in stubs.items():
        sys.modules[name] = mod
    return stubs


def main() -> int:
    failures = []
    pkg_dir = None

    # ── 0. 定位 conan 包目录（须来自包内，不是环境 site-packages）──
    spec = importlib.util.find_spec("keyrings")
    if spec is None or not spec.submodule_search_locations:
        print("[FAIL] keyrings package not found on PYTHONPATH")
        return 1
    pkg_dir = list(spec.submodule_search_locations)[0]
    # 消费者视角：PYTHONPATH 由 conanrun 注入 conan 包目录，包内即真身
    if "keyrings" not in os.path.basename(pkg_dir.rstrip("/")):
        failures.append(f"unexpected package dir basename: {pkg_dir}")
    print(f"[ok] keyrings package located: {pkg_dir}")

    alt_dir = os.path.join(pkg_dir, "alt")
    if not os.path.isdir(alt_dir):
        failures.append(f"keyrings/alt missing in package: {alt_dir}")
    else:
        print(f"[ok] keyrings/alt subdir present: {alt_dir}")

    # __init__.py 存在性（pkgutil.extend_path 命名空间包机制）
    for init in (os.path.join(pkg_dir, "__init__.py"),
                 os.path.join(alt_dir, "__init__.py")):
        if not os.path.isfile(init):
            failures.append(f"missing __init__.py: {init}")
    if not failures:
        print("[ok] namespace __init__.py files present")

    # dist-info 元数据存在（pip install --target 布局：包根或其上一级，
    # dist-info 目录名为归一化后的 keyrings.alt-<ver>.dist-info 带点号）
    meta_roots = [pkg_dir, os.path.dirname(pkg_dir)]
    dist_infos = [d for root in meta_roots for d in os.listdir(root)
                  if (d.startswith("keyrings.alt-")
                      or d.startswith("keyrings_alt-"))
                  and d.endswith(".dist-info")]
    if not dist_infos:
        failures.append("no keyrings.alt-*.dist-info near package root")
    else:
        print(f"[ok] dist metadata present: {dist_infos[0]}")

    # ── 1. import 冒烟（零依赖入口）──
    try:
        import keyrings.alt  # noqa: F401
        print("[ok] import keyrings.alt")
    except Exception as exc:
        print(f"[FAIL] import keyrings.alt: {exc}")
        return 1

    # 版本核对（dist metadata 口径，keyrings.alt 无 __version__ 属性）
    from importlib.metadata import version as _pkg_version
    try:
        actual_version = _pkg_version("keyrings.alt")
        if actual_version != EXPECTED_VERSION:
            failures.append(
                f"version mismatch: expected {EXPECTED_VERSION!r}, "
                f"got {actual_version!r}")
        else:
            print(f"[ok] keyrings.alt version == {actual_version}")
    except Exception as exc:
        failures.append(f"metadata version lookup failed: {exc}")

    # ── 2. 后端模块可寻址断言（寻址≠加载，不触发未发布依赖的 import）──
    missing = []
    for mod_name in BACKEND_MODULES:
        mod_spec = importlib.util.find_spec(f"keyrings.alt.{mod_name}")
        if mod_spec is None or mod_spec.origin is None:
            missing.append(mod_name)
    if missing:
        failures.append(f"backend modules not addressable: {missing}")
    else:
        print(f"[ok] backend modules addressable: "
              f"{', '.join(BACKEND_MODULES)}")

    # ── 3. escape/unescape 真实功能往返（纯 stdlib，无外部依赖）──
    try:
        from keyrings.alt.escape import escape, unescape
        samples = ["user@example.com", "服务/用户", "plain", "with space"]
        for s in samples:
            e = escape(s)
            if not all(c.isalnum() or c == "_" for c in e):
                failures.append(f"escape output not alnum: {s!r} -> {e!r}")
            back = unescape(e)
            if back != s:
                failures.append(f"escape/unescape roundtrip failed: {s!r}")
        print("[ok] escape/unescape roundtrip verified")
    except Exception as exc:
        failures.append(f"escape roundtrip raised: {exc}")

    # ── 4. 桩替后端模块真实功能往返 ──
    #    file 模块体只依赖 jaraco.classes（file_base 的 keyring/jaraco 桩已装）
    try:
        _install_stubs()
        from keyrings.alt import file as alt_file
        from keyrings.alt import multi as alt_multi

        kr = alt_file.PlaintextKeyring()
        # file_path 默认为 data_root()/filename，显式指到临时目录避免污染
        kr.file_path = os.path.join(tempfile.mkdtemp(prefix="kalt-"),
                                    "keyring_pass.cfg")
        kr.set_password("service1", "user1", "s3cret-pass")
        got = kr.get_password("service1", "user1")
        if got != "s3cret-pass":
            failures.append(f"PlaintextKeyring get_password mismatch: {got!r}")
        else:
            print("[ok] PlaintextKeyring set/get roundtrip (real file I/O)")

        # 落盘文件确认为 configparser 可读（真实文件写入发生）
        cfg = configparser.RawConfigParser()
        cfg.read(kr.file_path, encoding="utf-8")
        if not cfg.has_section("service1"):
            failures.append("keyring file missing service1 section")
        else:
            print("[ok] keyring file persisted as configparser format")

        kr.delete_password("service1", "user1")
        if kr.get_password("service1", "user1") is not None:
            failures.append("PlaintextKeyring delete_password ineffective")
        else:
            print("[ok] PlaintextKeyring delete_password")

        # MultipartKeyringWrapper 分片写入往返（上游 test_multi 同款）
        wrapped = alt_file.PlaintextKeyring()
        wrapped.file_path = os.path.join(
            tempfile.mkdtemp(prefix="kalt-w-"), "keyring_pass.cfg")
        mkr = alt_multi.MultipartKeyringWrapper(wrapped, max_password_size=2)
        mkr.set_password("s2", "u2", "0123456")
        got2 = mkr.get_password("s2", "u2")
        if got2 != "0123456":
            failures.append(f"Multipart wrapper roundtrip mismatch: {got2!r}")
        else:
            print("[ok] MultipartKeyringWrapper split-set/get roundtrip")

        # keyczar 桩替冒烟（上游 mocks 同款 MockKeyczar 注入）
        from keyrings.alt import keyczar as alt_keyczar
        import base64 as _b64

        class _MockKeyczarCrypter:
            def __init__(self, reader):
                self.reader = reader

            @staticmethod
            def Read(location):
                return _MockKeyczarCrypter(_MockKeyczarReader(location))

        class _MockKeyczarReader:
            def __init__(self, location):
                self.location = location

        class _MockKeyczarReaders:
            @staticmethod
            def CreateReader(location):
                return _MockKeyczarReader(location)

            @staticmethod
            def EncryptedReader(reader, crypter):
                return reader

        class _MockKeyczar:
            @property
            def readers(self):
                return _MockKeyczarReaders

            @property
            def Crypter(self):
                return _MockKeyczarCrypter

        alt_keyczar.keyczar = _MockKeyczar()
        kz = alt_keyczar.Crypter("bar://baz")
        if kz.keyset_location != "bar://baz":
            failures.append("keyczar Crypter keyset_location mismatch")
        elif kz.encrypt("") != "" or kz.decrypt("") != "":
            failures.append("keyczar Crypter empty-payload mismatch")
        else:
            print("[ok] keyczar Crypter stubbed smoke (environ reader intact)")
    except Exception as exc:
        import traceback
        traceback.print_exc()
        failures.append(f"stubbed functional roundtrip raised: {exc}")

    # ── 5. entry-points 元数据可发现 ──
    try:
        from importlib.metadata import distribution
        dist = distribution("keyrings.alt")
        eps = [e for e in dist.entry_points
               if e.group == "keyring.backends"]
        names = sorted(e.name for e in eps)
        expected = sorted(["file", "Gnome", "Google", "keyczar",
                           "multi", "Windows (alt)"])
        if names != expected:
            failures.append(f"keyring.backends entry-points mismatch: {names}")
        else:
            print(f"[ok] keyring.backends entry-points declared: {names}")
    except Exception as exc:
        failures.append(f"entry-points discovery failed: {exc}")

    if failures:
        for f in failures:
            print(f"[FAIL] {f}")
        return 1

    print("[PASS] all keyrings.alt test_package assertions passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
