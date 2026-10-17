#!/usr/bin/env python3
"""Consumer test for librouteros 4.2.2 — import + protocol codec + login + config utils.

上游 sdist 无测试目录（纯 Python API 客户端包），由 test_package 补全消费者测试：
覆盖 import、协议字编解码（str/int/bool 三型）、长度编解码边界、
MD5 token 登录编码（已知向量）、版本串解析、导出头归一化、配置 diff、查询构建。
全部不需要真实 RouterOS 设备。
"""
import sys


def test_import_api():
    import librouteros

    for symbol in (
        "connect",
        "async_connect",
        "create_transport",
        "Api",
        "AsyncApi",
        "Config",
        "AsyncConfig",
        "SocketTransport",
        "AsyncSocketTransport",
        "plain",
        "token",
    ):
        assert hasattr(librouteros, symbol), f"missing symbol: {symbol}"
    print(f"PASS: librouteros {getattr(librouteros, '__version__', '4.2.2')} imported")


def test_connect_kwargs_defaults():
    from librouteros import connect

    # 不真正连接设备：仅验证默认参数对象可构建（connect 需要真实 socket，这里只测签名）
    import inspect

    sig = inspect.signature(connect)
    params = sig.parameters
    assert "host" in params and "port" in params
    assert params["port"].default == 8728, f"default port: {params['port'].default}"
    print(f"PASS: connect signature defaults port={params['port'].default}")


def test_parse_word():
    from librouteros.protocol import parse_word

    assert parse_word("=name=admin") == ("name", "admin")
    assert parse_word("=port=8728") == ("port", 8728)
    assert parse_word("=flag=yes") == ("flag", True)
    assert parse_word("=flag=no") == ("flag", False)
    assert parse_word("=empty=") == ("empty", "")
    print("PASS: parse_word str/int/bool/flag 解析")


def test_compose_word():
    from librouteros.protocol import compose_word

    assert compose_word("name", "admin") == "=name=admin"
    assert compose_word("port", 8728) == "=port=8728"
    assert compose_word("flag", True) == "=flag=yes"
    assert compose_word("flag", False) == "=flag=no"
    print("PASS: compose_word str/int/bool 组装")


def test_encode_length():
    from librouteros.protocol import encode_length

    assert encode_length(0) == b"\x00"
    assert encode_length(1) == b"\x01"
    assert encode_length(0x7F) == b"\x7f"
    assert encode_length(0x80) == b"\x80\x80"  # 两字节：0x80|0x8000=0x8080
    assert encode_length(0x4000) == b"\xc0\x40\x00"  # 三字节：0x4000|0xC00000=0xC04000
    print(f"PASS: encode_length 边界 {encode_length(0x80)!r} / {encode_length(0x4000)!r}")


def test_decode_length():
    from librouteros.protocol import encode_length, decode_length

    for value in (0, 1, 0x7F, 0x80, 0xFF, 0x4000, 0x3FFF, 0x10000):
        encoded = encode_length(value)
        decoded = decode_length(encoded)
        assert decoded == value, f"roundtrip {value} -> {encoded!r} -> {decoded}"
    print("PASS: encode/decode_length 回环")


def test_encode_password():
    from librouteros.login import encode_password

    # RouterOS 6.43 前认证：md5(0x00 + password + token)，前缀 "00"
    # 已知向量：token=000102030405060708090a0b0c0d0e0f, password=test
    token = "000102030405060708090a0b0c0d0e0f"
    pwd = "test"
    encoded = encode_password(token, pwd)
    import hashlib

    expected = "00" + hashlib.md5(b"\x00" + b"test" + bytes.fromhex(token)).hexdigest()
    assert encoded == expected, f"{encoded} != {expected}"
    assert encoded.startswith("00")
    print(f"PASS: encode_password MD5 向量 {encoded[:12]}...")


def test_parse_version():
    from librouteros.config import parse_version

    assert parse_version("7.16rc1 (testing)") == (7, 16)
    assert parse_version("7.21.5") == (7, 21, 5)
    assert parse_version("6.49.17") == (6, 49, 17)
    print("PASS: parse_version 版本串解析")


def test_strip_header():
    from librouteros.config import strip_header

    text = "# 2026-07-11 21:04:13 by RouterOS 7.21.5\n/export\n"
    stripped = strip_header(text)
    assert "# by RouterOS 7.21.5" in stripped
    assert "2026-07-11" not in stripped
    print("PASS: strip_header 导出头归一化")


def test_compare_empty():
    from librouteros.config import compare

    cfg = "/system identity\nset name=router\n"
    assert compare(cfg, cfg) == "", f"identical config diff: {compare(cfg, cfg)!r}"
    print("PASS: compare 相同配置无差异")


def test_compare_diff():
    from librouteros.config import compare

    running = "/system identity\nset name=router\n/ip address\n"
    candidate = "/system identity\nset name=router2\n/ip address\n"
    diff = compare(running, candidate)
    assert diff != ""
    assert "running" in diff and "candidate" in diff
    assert "name=router2" in diff
    print(f"PASS: compare 差异 diff 含标记 ({len(diff.splitlines())} lines)")


def test_query_key():
    from librouteros.query import Key, And, Or

    key = Key("name")
    eq = key == "admin"
    ne = key != "admin"
    lt = key < "zzz"
    gt = key > "aaa"
    combined = And(eq, ne)
    alt = Or(eq, lt)
    # QueryGen = Iterator[str]，此处仅验证生成器可枚举出操作符结构
    ops = []
    for item in eq:
        ops.append(item)
    assert any("name" in s for s in ops)
    assert any("==" in s or "=" in s for s in ops)
    assert combined is not None and alt is not None
    print(f"PASS: query Key 运算构建 ({ops})")


def main():
    tests = [obj for name, obj in sorted(globals().items()) if name.startswith("test_")]
    passed = 0
    for t in tests:
        t()
        passed += 1
    print(f"\nRESULT: {passed}/{len(tests)} consumer tests passed")
    return 0 if passed == len(tests) else 1


if __name__ == "__main__":
    sys.exit(main())
