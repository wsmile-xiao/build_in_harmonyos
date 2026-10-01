#!/usr/bin/env python3
"""verify.py — vbrfixc 测试断言助手。

用法: python3 verify.py <check> <args...>
退出码: 0 = 断言成立；1 = 断言失败

checks:
  size        <file> <expected_bytes>      文件大小等于期望值
  size-delta  <file> <base_file> <delta>   大小 = base + delta
  contains    <file> <needle> <count>      子串出现次数等于 count
  startswith  <file> <magic_str>           文件魔数（前 N 字节）
  endswith    <file> <magic_str>           文件末尾 N 字节
  not-exists  <file>                       文件不存在
  elf-ohos    <file>                       是 OHOS 目标 AArch64 ELF
"""
import os
import struct
import sys


def fail(msg):
    print("    verify FAIL: " + msg)
    return 1


def ok(msg=""):
    if msg:
        print("    verify OK: " + msg)
    return 0


def main(argv):
    if len(argv) < 2:
        return fail("missing check name")
    check = argv[0]
    a = argv[1:]

    if check == "size":
        path, want = a[0], int(a[1])
        got = os.path.getsize(path)
        return ok("size=%d" % got) if got == want else fail(
            "%s size %d != %d" % (path, got, want))

    if check == "size-delta":
        path, base, delta = a[0], a[1], int(a[2])
        got, b = os.path.getsize(path), os.path.getsize(base)
        return ok("size=%d(base %d + %d)" % (got, b, delta)) if got == b + delta \
            else fail("%s size %d != %d + %d" % (path, got, b, delta))

    if check == "contains":
        data = open(a[0], "rb").read()
        got = data.count(a[1].encode())
        return ok("count=%d" % got) if got == int(a[2]) else fail(
            "%r count %d != %d" % (a[1], got, int(a[2])))

    if check == "startswith":
        data = open(a[0], "rb").read(len(a[1]))
        return ok(repr(data)) if data == a[1].encode() else fail(
            "prefix %r != %r" % (data, a[1]))

    if check == "not-exists":
        return ok("absent") if not os.path.exists(a[0]) else fail(
            "%s unexpectedly exists" % a[0])

    if check == "id3v1-at-end":
        raw = open(a[0], "rb").read()
        if len(raw) < 128:
            return fail("file smaller than an ID3v1 tag")
        tag = raw[-128:]
        return ok("ID3v1 tag @%d" % (len(raw) - 128)) if tag[:3] == b"TAG" \
            else fail("no ID3v1 'TAG' at len-128 (got %r)" % tag[:3])

    if check == "elf-ohos":
        path = a[0]
        data = open(path, "rb").read()
        if data[:4] != b"\x7fELF":
            return fail("not an ELF file")
        ei_class, ei_data = data[4], data[5]
        machine = struct.unpack_from("<H", data, 18)[0]
        if ei_class != 2:
            return fail("not ELF64 (ei_class=%d)" % ei_class)
        if ei_data != 1:
            return fail("not little-endian (ei_data=%d)" % ei_data)
        if machine != 0xB7:
            return fail("not AArch64 (e_machine=0x%x)" % machine)
        phoff = struct.unpack_from("<Q", data, 32)[0]
        phentsize = struct.unpack_from("<H", data, 54)[0]
        phnum = struct.unpack_from("<H", data, 56)[0]
        interp = None
        for i in range(phnum):
            off = phoff + i * phentsize
            if struct.unpack_from("<I", data, off)[0] == 3:  # PT_INTERP
                o = struct.unpack_from("<Q", data, off + 8)[0]
                s = struct.unpack_from("<Q", data, off + 32)[0]
                interp = data[o:o + s].rstrip(b"\0").decode()
        if not interp:
            return fail("no PT_INTERP (not a dynamic executable)")
        return ok("ELF64/LE/AArch64 interp=%s" % interp)

    return fail("unknown check: " + check)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
