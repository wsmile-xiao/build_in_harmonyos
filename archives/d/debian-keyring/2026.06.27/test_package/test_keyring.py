#!/usr/bin/env python3
"""debian-keyring 2026.06.27 交付物自检（14 条断言）。

用法: python3 test_keyring.py <share/keyrings 目录> <package_folder>

为什么不用 gpg：OpenHarmony 上没有 `gpg`/`jetring`（上游 `t/*.t` 6 个用例正是靠它），
所以这里**自解析 OpenPGP 包结构**：按 RFC 4880 区分老格式头（长度类型在最低两位：
1/2/4 字节或到末尾）与新格式头（部分长度/2 字节/5 字节），逐个 packet 走完整个数据流。
解析走不通 ⇒ 拼接出来的密钥环是坏的，这比"文件非空"强得多。
"""

import hashlib
import os
import sys

RESULTS = []
# jetring 源目录里的 0x* 文件数（= 该密钥环应有的公钥包个数）
EXPECTED_KEYS = {
    "debian-keyring.pgp": 947,
    "debian-nonupload.pgp": 44,
    "debian-maintainers.pgp": 205,
    "debian-role-keys.pgp": 6,
}


def check(ok, label):
    RESULTS.append((bool(ok), label))
    print(f"        [{'ok' if ok else 'FAIL'}] {label}")
    return bool(ok)


def parse_packets(raw):
    """返回 (tags, error)；error 非空表示数据流损坏。"""
    tags = []
    i = 0
    while i < len(raw):
        first = raw[i]
        if not first & 0x80:
            return tags, f"offset {i}: 不是 packet 头（0x{first:02x}）"
        i += 1
        if first & 0x40:                       # 新格式
            tag = first & 0x3F
            if i >= len(raw):
                return tags, "新格式头后数据截断"
            length0 = raw[i]
            i += 1
            if length0 < 192:
                body = length0
            elif length0 < 224:
                if i >= len(raw):
                    return tags, "2 字节长度截断"
                body = ((length0 - 192) << 8) + raw[i] + 192
                i += 1
            elif length0 == 255:
                if i + 4 > len(raw):
                    return tags, "5 字节长度截断"
                body = int.from_bytes(raw[i:i + 4], "big")
                i += 4
            else:
                return tags, f"不支持的部分长度 0x{length0:02x}（应由后续 packet 续，本包不用）"
        else:                                  # 老格式
            tag = (first >> 2) & 0x0F
            length_type = first & 0x03
            if length_type == 3:
                body = len(raw) - i
            else:
                nbytes = {0: 1, 1: 2, 2: 4}[length_type]
                if i + nbytes > len(raw):
                    return tags, "老格式长度截断"
                body = int.from_bytes(raw[i:i + nbytes], "big")
                i += nbytes
        tags.append(tag)
        i += body
        if i > len(raw):
            return tags, f"offset {i} 越界（报文长度声明错误）"
    return tags, None


def main():
    if len(sys.argv) != 3:
        print("usage: test_keyring.py <share/keyrings> <package_folder>")
        return 2
    data_dir, package_folder = sys.argv[1], sys.argv[2]

    # 1) 文件齐备
    for name in EXPECTED_KEYS:
        check(os.path.isfile(os.path.join(data_dir, name)), f"{name} 存在")
    check(os.path.isfile(os.path.join(data_dir, "sha512sums.txt")), "sha512sums.txt 存在")

    # 2) 逐密钥环：包结构 + 公钥包个数 == jetring 源文件数
    actual = {}
    for name, want in EXPECTED_KEYS.items():
        path = os.path.join(data_dir, name)
        if not os.path.isfile(path):
            actual[name] = None
            continue
        raw = open(path, "rb").read()
        tags, err = parse_packets(raw)
        actual[name] = (len(raw), tags, err)
        check(err is None, f"{name} 全流 packet 解析无错（{len(raw)} 字节，{len(tags)} 个包）")
        pubs = tags.count(6)
        check(pubs == want, f"{name} 公钥包数 == jetring 源文件数（{pubs} vs 期望 {want}）")
        check(tags and tags[0] == 6 and any(t == 13 or t == 14 for t in tags),
              f"{name} 首个包是公钥包且含用户 ID/签名包")

    # 3) sha512sums.txt 与真实产物一致（消费者可直接复核）
    sums_path = os.path.join(data_dir, "sha512sums.txt")
    if os.path.isfile(sums_path):
        listed = {}
        for line in open(sums_path, encoding="utf-8"):
            parts = line.split()
            if len(parts) == 2:
                listed[parts[1]] = parts[0]
        check(set(listed) == set(EXPECTED_KEYS), "sha512sums.txt 恰好列出 4 个密钥环")
        bad = []
        for name in EXPECTED_KEYS:
            digest = hashlib.sha512(open(os.path.join(data_dir, name), "rb").read()).hexdigest()
            if listed.get(name) != digest:
                bad.append(name)
        check(not bad, f"sha512sums.txt 每条摘要与真实产物一致（不符 {bad}）")

    # 4) 文档 / 许可 / 纯净性
    check(os.path.isdir(os.path.join(package_folder, "share", "doc", "debian-keyring")),
          "share/doc/debian-keyring 随包发布")
    check(os.path.isfile(os.path.join(package_folder, "licenses", "copyright")),
          "licenses/copyright 已发布")
    leaked = [n for n in ("scripts", "cheatsheets", "t", "output", "Makefile", "runtests")
              if os.path.exists(os.path.join(package_folder, "share", n))
              or os.path.exists(os.path.join(data_dir, n))]
    check(not leaked, f"安装目录未混入上游维护脚本/测试（发现 {leaked}）")

    passed = sum(1 for ok, _ in RESULTS if ok)
    total = len(RESULTS)
    print(f"        [test] {passed}/{total} assertions passed")
    if passed != total:
        for ok, label in RESULTS:
            if not ok:
                print(f"  - {label}")
        return 1
    print("All tests passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
