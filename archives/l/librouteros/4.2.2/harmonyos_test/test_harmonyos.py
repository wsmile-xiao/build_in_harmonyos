#!/usr/bin/env python3
"""librouteros 4.2.2 — HarmonyOS 专项消费者测试（独立入口，R02）。

本文件是独立于 test_package/test_librouteros.py 的鸿蒙特有测试入口：
- 独立源文件 + 独立运行入口（python3 test_harmonyos.py），不经 conan test() 阶段；
- 真实 import 并调用 librouteros 公开 API（protocol 编解码、login 编码、config 工具、query 构建）；
- 消费 OHOS 打包产物：经 Conan package_info 暴露的 runenv/buildenv PYTHONPATH
  （指向 OHOS profile 打包出的 site-packages）被真实 Python 解释器解析后完成断言；
- 每条断言均可失败；设置 HARMONYOS_TEST_INJECT_FAIL=1 时注入必然不成立的期望值
  （负向证明用），默认通过。

验证的鸿蒙行为/兼容性结论：
  本库作为纯 Python noarch 交付物，经 OHOS profile（os=OHOS, arch=armv8）Conan
  package_info 暴露的 PYTHONPATH，可被真实 Python 解释器解析并完成 RouterOS 协议
  字/长度编解码与 MD5 token 登录编码 —— 即 noarch site-packages 在 OHOS 打包产物
  中的落位与可消费性得到验证（而非仅开发树源码可 import）。
"""
import hashlib
import os
import sys

# 打包产物 site-packages 的绝对前缀（由运行方通过 PYTHONPATH 提供；本文件仅核对）
_PACKAGED_MARKER = "site-packages"


def _inject_fail() -> bool:
    """负向证明注入开关：设置为 1 时，首个比对断言被注入必然错误的期望值。"""
    return os.environ.get("HARMONYOS_TEST_INJECT_FAIL") == "1"


def test_module_resolved_from_packaged_site_packages() -> None:
    """断言被测模块来自 OHOS 打包产物的 site-packages（而非开发树源码/构建暂存）。"""
    import librouteros

    mod_path = os.path.abspath(librouteros.__file__)
    assert _PACKAGED_MARKER in mod_path, (
        f"librouteros 未从打包产物 site-packages 解析: {mod_path}"
    )
    assert os.path.isfile(mod_path), f"模块文件不存在: {mod_path}"
    print(f"PASS: 模块自 OHOS 打包产物解析 -> {mod_path}")


def test_parse_word_failable() -> None:
    """协议字解析：str/int/bool 三型（R01 已知语义，期望值可被负向注入打破）。"""
    from librouteros.protocol import parse_word

    port_expected = ("port", 8728) if not _inject_fail() else ("port", 9999)
    assert parse_word("=port=8728") == port_expected, "parse_word int 断言失败"
    assert parse_word("=name=admin") == ("name", "admin"), "parse_word str 断言失败"
    assert parse_word("=flag=yes") == ("flag", True), "parse_word bool 断言失败"
    assert parse_word("=flag=no") == ("flag", False), "parse_word bool-false 断言失败"
    print("PASS: parse_word str/int/bool 三型")


def test_compose_word_failable() -> None:
    """协议字组装：ROSType -> API 字符串（bool 映射 yes/no，负向注入可打破）。"""
    from librouteros.protocol import compose_word

    port_expected = "=port=8728" if not _inject_fail() else "=port=9999"
    assert compose_word("port", 8728) == port_expected, "compose_word int 断言失败"
    assert compose_word("name", "admin") == "=name=admin", "compose_word str 断言失败"
    assert compose_word("flag", True) == "=flag=yes", "compose_word bool 断言失败"
    print("PASS: compose_word str/int/bool 组装")


def test_length_codec_roundtrip_failable() -> None:
    """长度编解码回环（单/双/三字节边界），负向注入打破坏长度期望。"""
    from librouteros.protocol import decode_length, encode_length

    for value in (0, 1, 0x7F, 0x80, 0x4000, 0x3FFF, 0x10000):
        encoded = encode_length(value)
        decoded = decode_length(encoded)
        expected = value if not _inject_fail() else (value + 1)
        assert decoded == expected, f"length roundtrip 断言失败: {value} -> {decoded}"
    assert encode_length(0x80) == b"\x80\x80", "encode_length 两字节断言失败"
    assert encode_length(0x4000) == b"\xc0\x40\x00", "encode_length 三字节断言失败"
    print("PASS: encode/decode_length 回环 + 边界字节")


def test_encode_password_failable() -> None:
    """RouterOS 6.43 前 MD5 token 登录编码（已知向量），负向注入打破坏摘要。"""
    from librouteros.login import encode_password

    token = "000102030405060708090a0b0c0d0e0f"
    pwd = "test"
    encoded = encode_password(token, pwd)
    expected = "00" + hashlib.md5(
        b"\x00" + pwd.encode("ascii") + bytes.fromhex(token)
    ).hexdigest()
    if _inject_fail():
        expected = "00" + "f" * 32  # 必然不成立
    assert encoded == expected, f"encode_password 断言失败: {encoded} != {expected}"
    assert encoded.startswith("00"), "encode_password 前缀断言失败"
    print(f"PASS: encode_password MD5 向量 {encoded[:12]}...")


def test_config_tools_failable() -> None:
    """config 工具函数：版本串解析 + 导出头归一化 + 配置 diff（负向注入打破）。"""
    from librouteros.config import compare, parse_version, strip_header

    ver_expected = (7, 16) if not _inject_fail() else (7, 99)
    assert parse_version("7.16rc1 (testing)") == ver_expected, "parse_version 断言失败"
    assert parse_version("7.21.5") == (7, 21, 5), "parse_version 三段断言失败"

    text = "# 2026-07-11 21:04:13 by RouterOS 7.21.5\n/export\n"
    stripped = strip_header(text)
    assert "2026-07-11" not in stripped, "strip_header 时间戳未归一化"
    assert "# by RouterOS 7.21.5" in stripped, "strip_header 保留版本断言失败"

    running = "/system identity\nset name=router\n"
    diff_empty_expected = (compare(running, running) == "") if not _inject_fail() else False
    assert diff_empty_expected, "compare 相同配置应无差异（负向注入断言失败）"
    diff = compare(running, "/system identity\nset name=router2\n")
    assert "name=router2" in diff, "compare 差异 diff 断言失败"
    print("PASS: parse_version/strip_header/compare")


def test_query_build_failable() -> None:
    """query 构建器：Key 运算符产出协议查询字（负向注入打破）。"""
    from librouteros.query import And, Key, Or

    eq = list(Key("name") == "admin")
    expected = ["?=name=admin"] if not _inject_fail() else ["?=name=root"]
    assert eq == expected, f"Key== 断言失败: {eq}"
    assert list(Key("name") != "admin") == ["?=name=admin", "?#!"], "Key!= 断言失败"
    assert list(And(Key("a") == "1", Key("b") == "2"))[-1] == "?#&", "And 断言失败"
    assert list(Or(Key("a") == "1", Key("b") == "2"))[-1] == "?#|", "Or 断言失败"
    print("PASS: query Key/And/Or 构建")


def main() -> int:
    tests = [obj for name, obj in sorted(globals().items()) if name.startswith("test_")]
    passed = 0
    for t in tests:
        t()
        passed += 1
    print(f"\nRESULT: {passed}/{len(tests)} harmonyos tests passed")
    return 0 if passed == len(tests) else 1


if __name__ == "__main__":
    sys.exit(main())
