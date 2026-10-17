#!/usr/bin/env python3
"""libloc-database 消费侧校验脚本（由 test_package/conanfile.py 调用）。

用法: python3 test_database.py <package_folder>

对纯数据包而言，"真实消费"就是读取安装后的数据库并校验其身份与完整性，
等价于 libloc 库启动时打开 location.db 需要通过的检查：

  1. share/libloc-location/location.db 存在（Debian 官方包同路径）
  2. 字节数 == 48,930,795（上游发布物解压后大小）
  3. SHA256 == 819748dd33a18aecbbce624bc10b0b685cb292e95377bb2b434665b5afc69ffd
  4. 魔数 == b"LOCDBXX\\x01"（libloc DB format 1）
  5. 头部时间戳 == 1782621203（2026-06-28T04:33:23Z，与上游 2026-06-28 发布版本一致）
  6. 数据库尾部可读（文件完整未截断）

退出码: 0 = 全部用例通过; 1 = 存在失败用例。

注: 本文件是 test_package 内的独立消费侧脚本（无法导入 scripts/ohc/utils 的 log_* 输出层），
因此用例结果直接用 print() 输出。
"""
import hashlib
import os
import struct
import sys

DB_SIZE_BYTES = 48930795
DB_SHA256 = "819748dd33a18aecbbce624bc10b0b685cb292e95377bb2b434665b5afc69ffd"
DB_MAGIC = b"LOCDBXX\x01"
DB_TIMESTAMP = 1782621203          # 2026-06-28T04:33:23Z
DB_RELPATH = os.path.join("share", "libloc-location", "location.db")

results = []


def check(name, func):
    try:
        func()
    except Exception as exc:  # noqa: BLE001 - 用例失败统一汇总
        results.append((name, False, str(exc)))
        print(f"  [FAIL] {name}: {exc}")
    else:
        results.append((name, True, ""))
        print(f"  [ok]   {name}")


def sha256_of(path):
    digest = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main():
    if len(sys.argv) < 2:
        print("usage: test_database.py <package_folder>")
        return 1

    pkg = os.path.abspath(sys.argv[1])
    db_path = os.path.join(pkg, DB_RELPATH)
    print(f"libloc-database consumer check\n  package_folder: {pkg}\n  database: {db_path}\n")

    def case_exists():
        if not os.path.isfile(db_path):
            raise AssertionError(f"location.db not found at {db_path}")

    def case_size():
        size = os.path.getsize(db_path)
        if size != DB_SIZE_BYTES:
            raise AssertionError(f"size={size}, expected {DB_SIZE_BYTES}")

    def case_sha256():
        digest = sha256_of(db_path)
        if digest != DB_SHA256:
            raise AssertionError(f"sha256={digest}, expected {DB_SHA256}")

    def case_magic():
        with open(db_path, "rb") as fh:
            magic = fh.read(8)
        if magic != DB_MAGIC:
            raise AssertionError(f"magic={magic!r}, expected {DB_MAGIC!r}")

    def case_timestamp():
        with open(db_path, "rb") as fh:
            header = fh.read(16)
        stamp = struct.unpack(">I", header[12:16])[0]
        if stamp != DB_TIMESTAMP:
            raise AssertionError(f"header timestamp={stamp}, expected {DB_TIMESTAMP}")

    def case_tail_readable():
        size = os.path.getsize(db_path)
        with open(db_path, "rb") as fh:
            fh.seek(max(0, size - 4096))
            tail = fh.read()
        if len(tail) != min(4096, size):
            raise AssertionError("tail of database could not be read")

    check("1. database installed at share/libloc-location/location.db", case_exists)
    check("2. database size == 48930795 bytes", case_size)
    check("3. database sha256 matches upstream artifact", case_sha256)
    check("4. database magic is LOCDBXX\\x01 (format 1)", case_magic)
    check("5. header timestamp == 2026-06-28T04:33:23Z release", case_timestamp)
    check("6. database tail readable (not truncated)", case_tail_readable)

    passed = sum(1 for _, ok, _ in results if ok)
    failed = len(results) - passed
    print(f"\nlibloc-database test_package: total={len(results)} passed={passed} failed={failed} skipped=0")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
