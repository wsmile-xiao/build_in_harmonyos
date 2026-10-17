#!/usr/bin/env python3
"""pari-seadata 数据包内容级校验（test_package 消费，R34 真实依赖被测包）。

用法: python3 test_verify.py <seadata_dir>
其中 <seadata_dir> = <package_folder>/res/pari/seadata
上游 seadata 为 p<500 的模多项式文本表，共 51 个 sea<p> 数据文件 + README。
"""
import hashlib
import os
import sys

# 上游 2009-06-18 seadata 基线（由 orig.tar.gz / 官方 seadata.tgz 实测得到）
EXPECTED_SEA_COUNT = 51
SEA_CONCAT_SHA256 = ("c055c577d25f7f0e1a9cf90d699df846b4ecde5b7cb64debae1dc2f50f1aa738")


def main():
    if len(sys.argv) != 2:
        print("usage: test_verify.py <seadata_dir>", file=sys.stderr)
        return 2
    d = sys.argv[1]

    # 1) 目录存在
    if not os.path.isdir(d):
        print(f"FAIL: seadata dir not found: {d}", file=sys.stderr)
        return 1

    entries = sorted(os.listdir(d))
    readme = os.path.join(d, "README")
    if not os.path.isfile(readme):
        print(f"FAIL: README missing in {d}", file=sys.stderr)
        return 1

    sea_files = [f for f in entries if f.startswith("sea")]

    # 2) 数量正确
    if len(sea_files) != EXPECTED_SEA_COUNT:
        print(f"FAIL: expected {EXPECTED_SEA_COUNT} sea* files, got {len(sea_files)}",
              file=sys.stderr)
        return 1

    # 3) 每个文件为 GP 文本向量格式（首字符 '['）且非空，边校验边累计拼接哈希
    h = hashlib.sha256()
    for name in sea_files:
        p = os.path.join(d, name)
        size = os.path.getsize(p)
        if size == 0:
            print(f"FAIL: {name} is empty", file=sys.stderr)
            return 1
        with open(p, "rb") as f:
            first = f.read(1)
            f.seek(0)
            data = f.read()
        if first != b"[":
            print(f"FAIL: {name} not GP vector format (starts with {first!r})",
                  file=sys.stderr)
            return 1
        # 与上游一致：按文件名排序后拼接
        h.update(data)

    digest = h.hexdigest()
    if digest != SEA_CONCAT_SHA256:
        print(f"FAIL: seadata payload fingerprint mismatch\n"
              f"      expected {SEA_CONCAT_SHA256}\n      actual   {digest}",
              file=sys.stderr)
        return 1

    print(f"OK: pari-seadata payload verified — {len(sea_files)} sea* files, "
          f"all GP-format, payload sha256 == {digest[:16]}…  (README present)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
