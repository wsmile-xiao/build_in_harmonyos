#!/usr/bin/env python3
"""Consumer-side check for the packaged typedload 2.41 (R34: real API).

驱动 conan 包内实际发布的 `typedload` 模块（不是源码树），覆盖：
  * 打包契约（OHOS python3.12 purelib 布局、py.typed/__init__.pyi、零运行时依赖）
  * 上游核心能力端到端：dataclass / NamedTuple / Enum / 容器 / Optional / Union /
    Literal / TypedDict / datetime / UUID / IP 地址 / re.Pattern / Path /
    moretypes.HexRGB，以及**负例**（类型不匹配、缺字段、裸泛型必须抛异常）
  * **鸿蒙（OHOS）专有断言 3 项**：平台身份、purelib 布局、OHOS 路径往返

Usage: test_typedload.py <site-packages-dir>
"""
import os
import sys

if len(sys.argv) > 1:
    sys.path.insert(0, os.path.abspath(sys.argv[1]))

FAILED = []
PASSED = []


def check(name, fn):
    try:
        fn()
    except Exception as exc:  # noqa: BLE001 — consumer test reports any failure
        FAILED.append(f"{name}: {type(exc).__name__}: {exc}")
    else:
        PASSED.append(name)


import dataclasses  # noqa: E402
import datetime  # noqa: E402
import enum  # noqa: E402
import ipaddress  # noqa: E402
import pathlib  # noqa: E402
import platform  # noqa: E402
import re  # noqa: E402
import subprocess  # noqa: E402
import sysconfig  # noqa: E402
import uuid  # noqa: E402
from typing import Literal, NamedTuple, Optional, TypedDict  # noqa: E402

import typedload  # noqa: E402
from typedload.exceptions import TypedloadException  # noqa: E402

PKG_ROOT = os.path.abspath(os.path.dirname(typedload.__file__))
SITE_DIR = os.path.abspath(sys.argv[1]) if len(sys.argv) > 1 else os.path.dirname(PKG_ROOT)


# ───────────────── 鸿蒙（OHOS）专有断言 ─────────────────

def t_ohos_platform_identity():
    """本包的目标平台就是 OHOS：解释器平台标签必须是 ohos-*。"""
    assert sys.platform == "ohos", sys.platform
    assert sysconfig.get_platform().startswith("ohos"), sysconfig.get_platform()
    assert platform.machine() == "aarch64", platform.machine()
    uname = platform.uname()
    assert "HarmonyOS" in uname.system or "HongMeng" in uname.version, uname


def t_ohos_purelib_layout():
    """OHOS python3.12 的 purelib 布局：<prefix>/lib/python3.12/site-packages。

    产物必须落在该布局下（与 ci/conan/profiles/ohos-aarch64 的
    lib/python3.12/site-packages 约定一致），否则 OHOS 解释器不会命中。
    """
    tail = os.path.join("lib", "python3.12", "site-packages")
    assert SITE_DIR.endswith(tail), SITE_DIR
    assert PKG_ROOT == os.path.join(SITE_DIR, "typedload"), PKG_ROOT
    assert sysconfig.get_paths()["purelib"].endswith(tail), \
        sysconfig.get_paths()["purelib"]


def t_ohos_path_roundtrip():
    """OHOS 真实路径（用户区 / 应用沙箱）经 typedload 的 Path 处理器往返。"""
    for raw in ("/storage/Users/currentUser/tmp/typedload-2.41.log",
                "/data/storage/el2/base/cache/typedload.json"):
        loaded = typedload.load(raw, pathlib.Path)
        assert loaded == pathlib.Path(raw), (loaded, raw)
        assert str(typedload.dump(loaded)) == raw, typedload.dump(loaded)


# ───────────────── 打包契约 ─────────────────

def t_payload_is_packaged_pure_python():
    assert os.path.basename(PKG_ROOT) == "typedload", PKG_ROOT
    assert os.path.isfile(os.path.join(PKG_ROOT, "__init__.py")), PKG_ROOT
    # 纯 Python：payload 里不得出现任何编译产物
    bad = [f for _r, _d, fs in os.walk(PKG_ROOT) for f in fs
           if f.endswith((".so", ".pyd", ".pyc"))]
    assert not bad, bad


def t_type_markers_shipped():
    """上游 setup.py package_data 声明 py.typed / __init__.pyi，必须随包发布。"""
    for marker in ("py.typed", "__init__.pyi"):
        assert os.path.isfile(os.path.join(PKG_ROOT, marker)), marker


def t_zero_runtime_dependencies():
    """运行时零第三方依赖：import typedload 不得拉起非 stdlib 顶层模块。"""
    code = (
        "import sys, json;"
        "before=set(sys.modules);"
        "import typedload;"
        "new=[m for m in set(sys.modules)-before if '.' not in m];"
        "extra=[m for m in new if m not in sys.stdlib_module_names "
        "and m != 'typedload'];"
        "print(json.dumps(extra))"
    )
    res = subprocess.run([sys.executable, "-c", code], capture_output=True,
                         text=True, timeout=180,
                         env={**os.environ, "PYTHONPATH": SITE_DIR,
                              "PYTHONDONTWRITEBYTECODE": "1"})
    assert res.returncode == 0, res.stderr
    assert res.stdout.strip() == "[]", res.stdout


def t_version_marker_moretypes():
    """2.41 的版本标记：typedload.moretypes 必须存在（上游 2026 新增模块）。"""
    import typedload.moretypes as mt
    assert hasattr(mt, "HexRGB"), dir(mt)


# ───────────────── 上游能力（真实 API）─────────────────

@dataclasses.dataclass
class User:
    username: str
    shell: str = "bash"
    sessions: list[str] = dataclasses.field(default_factory=list)


class Logins(NamedTuple):
    users: list[User]


class Color(enum.Enum):
    RED = "red"
    BLUE = "blue"


class Todo(TypedDict):
    title: str
    done: bool


def t_dataclass_roundtrip():
    data = {"username": "salvo", "shell": "bash", "sessions": ["pts/4", "tty7"]}
    u = typedload.load(data, User)
    assert isinstance(u, User) and u.username == "salvo", u
    assert u.sessions == ["pts/4", "tty7"], u
    # 默认 dump 会省略「等于默认值」的字段（上游 hidedefault=True 语义）
    assert typedload.dump(u) == {"username": "salvo", "sessions": ["pts/4", "tty7"]}, \
        typedload.dump(u)
    # hidedefault=False 时完整往返
    assert typedload.dump(u, hidedefault=False) == data, typedload.dump(u, hidedefault=False)
    # 默认值路径
    u2 = typedload.load({"username": "lop"}, User)
    assert u2.shell == "bash" and u2.sessions == [], u2


def t_namedtuple_and_enum():
    logins = typedload.load({"users": [{"username": "salvo"}]}, Logins)
    assert isinstance(logins, Logins) and isinstance(logins.users[0], User), logins
    assert typedload.load("red", Color) is Color.RED
    assert typedload.dump(Color.BLUE) == "blue", typedload.dump(Color.BLUE)


def t_containers_roundtrip():
    assert typedload.load([1, 2, 3], list[int]) == [1, 2, 3]
    assert typedload.load({"a": 1}, dict[str, int]) == {"a": 1}
    assert typedload.load([1, 2, 2], set[int]) == {1, 2}
    assert isinstance(typedload.load([1, 2], set[int]), set)
    assert typedload.load([1, "a"], tuple[int, str]) == (1, "a")


def t_optional_union_literal():
    assert typedload.load(None, Optional[int]) is None
    assert typedload.load(5, Optional[int]) == 5
    assert typedload.load("x", int | str) == "x"
    assert typedload.load(7, int | str) == 7
    assert typedload.load("a", Literal["a", "b"]) == "a"


def t_typeddict_load():
    t = typedload.load({"title": "x", "done": True}, Todo)
    assert t["title"] == "x" and t["done"] is True, t


def t_scalars_datetime_uuid_ip_pattern():
    assert typedload.load("2020-01-02", datetime.date) == datetime.date(2020, 1, 2)
    assert typedload.load("03:04:05", datetime.time) == datetime.time(3, 4, 5)
    u = uuid.UUID("12345678-1234-5678-1234-567812345678")
    assert typedload.load(str(u), uuid.UUID) == u
    assert typedload.load("10.0.0.1", ipaddress.IPv4Address) == \
        ipaddress.IPv4Address("10.0.0.1")
    assert typedload.load("::1", ipaddress.IPv6Address) == \
        ipaddress.IPv6Address("::1")
    pat = typedload.load("ab+c", re.Pattern)
    assert isinstance(pat, re.Pattern) and pat.pattern == "ab+c", pat
    assert typedload.dump(u) == str(u)


def t_moretypes_hexrgb():
    from typedload.moretypes import HexRGB
    assert HexRGB("#00ff00").value == 0x00FF00
    assert HexRGB(1234).value == 1234
    assert typedload.load("#00ff00", HexRGB).value == 0x00FF00


def t_negative_wrong_type_raises():
    for value, tname in (("abc", int), (None, int),
                         ("c", Literal["a", "b"]), ({"a": "b"}, dict[str, int])):
        try:
            typedload.load(value, tname)
        except TypedloadException:
            continue
        raise AssertionError(f"load({value!r}, {tname}) did not raise")


def t_negative_missing_field_raises():
    try:
        typedload.load({}, User)
    except TypedloadException:
        return
    raise AssertionError("load({}, User) did not raise")


def t_negative_bare_generic_raises():
    """上游语义：裸泛型（list/dict/set/tuple 不带参数）无法处理，必须显式报错。

    这是 typedload 的既定行为（见其文档 Supported types：list[SomeType]），
    也是本包「不做过度适配」的证据——不为其悄悄加兜底。
    """
    for value, tname in (([1, 2], list), ({"a": 1}, dict), ([1], set),
                         ([1, "a"], tuple)):
        try:
            typedload.load(value, tname)
        except TypedloadException:
            continue
        raise AssertionError(f"load({value!r}, {tname}) did not raise")


CHECKS = [
    # 鸿蒙专有（3）
    ("ohos_platform_identity", t_ohos_platform_identity),
    ("ohos_purelib_layout_site_packages", t_ohos_purelib_layout),
    ("ohos_path_roundtrip", t_ohos_path_roundtrip),
    # 打包契约（4）
    ("payload_is_packaged_pure_python", t_payload_is_packaged_pure_python),
    ("type_markers_shipped", t_type_markers_shipped),
    ("zero_runtime_dependencies", t_zero_runtime_dependencies),
    ("version_marker_moretypes", t_version_marker_moretypes),
    # 上游能力（7）
    ("dataclass_roundtrip", t_dataclass_roundtrip),
    ("namedtuple_and_enum", t_namedtuple_and_enum),
    ("containers_roundtrip", t_containers_roundtrip),
    ("optional_union_literal", t_optional_union_literal),
    ("typeddict_load", t_typeddict_load),
    ("scalars_datetime_uuid_ip_pattern", t_scalars_datetime_uuid_ip_pattern),
    ("moretypes_hexrgb", t_moretypes_hexrgb),
    # 负例（3）
    ("negative_wrong_type_raises", t_negative_wrong_type_raises),
    ("negative_missing_field_raises", t_negative_missing_field_raises),
    ("negative_bare_generic_raises", t_negative_bare_generic_raises),
]

for _name, _fn in CHECKS:
    check(_name, _fn)

print(f"typedload consumer API: {len(PASSED)}/{len(PASSED) + len(FAILED)} passed "
      f"(OHOS-specific: ohos_platform_identity, ohos_purelib_layout_site_packages, "
      f"ohos_path_roundtrip)")
for _name in PASSED:
    print(f"  [ok]   {_name}")
for _msg in FAILED:
    print(f"  [FAIL] {_msg}")
sys.exit(1 if FAILED else 0)
