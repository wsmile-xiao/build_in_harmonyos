#!/usr/bin/env python3
"""debian-archive-keyring 数据包验证脚本。

用法: python3 test_keyring.py <data_dir> <package_folder>

验证的是**公钥本体**而不是"文件存在"：

  * 9 份 `.asc` 的文件名必须严格等于
    `debian-archive-{bookworm,bullseye,trixie}-{automatic,security-automatic,stable}.asc`
    的笛卡尔积（3 套发行版 × 3 种用途）；
  * 每一份都必须有正确的 ASCII armor 头尾，且**去掉 armor 头与 `=校验和` 行之后
    能 base64 解码**；
  * 解码结果必须是合法的 OpenPGP 公钥包：按老/新格式解析出 packet tag = 6
    （public key）且包内版本号 = 4 —— 这是"密钥没被截断、没被换成占位文本"的
    硬证据，不需要 gpg；
  * 9 份公钥两两不同（防止复制粘贴错文件）；每套发行版内部三把也两两不同；
  * `active-keys/`（jetring 密钥源 + sha256 index）随包发布，index 行数与密钥源
    文件数一致（9）；
  * 安装目录里不能混进构建系统（`Makefile`）或上游的 `debian/`、`removed-keys/`、
    空的 `keyrings/` 目录。

任一断言失败 → 退出码 1（Conan test_package 随之失败）。
"""

import base64
import os
import re
import sys

SUITES = ("bookworm", "bullseye", "trixie")
KINDS = ("automatic", "security-automatic", "stable")
EXPECTED_ASC = {f"debian-archive-{s}-{k}.asc" for s in SUITES for k in KINDS}
ACTIVE_KEY_SOURCES = 9

_ARMOR = re.compile(
    r"-----BEGIN PGP PUBLIC KEY BLOCK-----\r?\n(.*?)\r?\n"
    r"-----END PGP PUBLIC KEY BLOCK-----", re.S)

_results = []


def check(ok, label) -> bool:
    _results.append((bool(ok), label))
    print(f"        [{'ok' if ok else 'FAIL'}] {label}")
    return bool(ok)


def decode_armor(path):
    """解析 ASCII armor → 二进制。返回 (raw, 错误信息)。"""
    with open(path, encoding="ascii", errors="replace") as handle:
        text = handle.read()
    match = _ARMOR.search(text)
    if not match:
        return None, "缺完整的 BEGIN/END armor"
    body = "".join(
        line.strip() for line in match.group(1).splitlines()
        if line.strip() and ":" not in line and not line.strip().startswith("="))
    try:
        return base64.b64decode(body), ""
    except Exception as exc:  # noqa: BLE001
        return None, f"base64 解码失败: {exc}"


def public_key_packet(raw):
    """按 RFC 4880 解析首个 packet 头，返回 (tag, version)；解析不了返回 (None, None)。"""
    first = raw[0]
    if not first & 0x80:
        return None, None
    if first & 0x40:                       # 新格式头
        tag = first & 0x3F
        index = 1
        length0 = raw[index]
        index += 1
        if 192 <= length0 < 224:
            index += 1
        elif length0 == 255:
            index += 4
    else:                                  # 老格式头：长度类型在最低两位
        tag = (first >> 2) & 0x0F
        length_type = first & 0x03
        index = 1 + {0: 1, 1: 2, 2: 4}.get(length_type, 0)
    if index >= len(raw):
        return None, None
    return tag, raw[index]


def main() -> int:
    if len(sys.argv) != 3:
        print("usage: test_keyring.py <data_dir> <package_folder>")
        return 2

    data_dir, package_folder = sys.argv[1], sys.argv[2]
    print(f"[test] data_dir = {data_dir}")
    check(os.path.isdir(data_dir), f"share/keyrings 目录存在 ({data_dir})")

    # ── 1. 9 份公钥的文件名集合 ─────────────────────────────────────────
    asc_files = sorted(f for f in os.listdir(data_dir) if f.endswith(".asc"))
    check(set(asc_files) == EXPECTED_ASC,
          f"{len(EXPECTED_ASC)} 份公钥文件名与上游一致"
          f"（多 {sorted(set(asc_files) - EXPECTED_ASC)} / "
          f"少 {sorted(EXPECTED_ASC - set(asc_files))}）")

    # ── 2. 逐份解码 + OpenPGP 包头 ─────────────────────────────────────
    decoded = {}
    for name in sorted(EXPECTED_ASC):
        path = os.path.join(data_dir, name)
        if not os.path.isfile(path):
            continue
        raw, err = decode_armor(path)
        if raw is None:
            check(False, f"{name}: {err}")
            continue
        decoded[name] = raw

    check(len(decoded) == len(EXPECTED_ASC),
          f"全部 {len(EXPECTED_ASC)} 份公钥都能按 ASCII armor 解码（含跳过 `=校验和` 行）")
    heads = {n: public_key_packet(raw) for n, raw in decoded.items()}
    bad_tag = [n for n, (tag, _v) in heads.items() if tag != 6]
    check(not bad_tag,
          f"每份公钥的首个 packet 都是 tag=6（public key，异常 {bad_tag[:3]}）")
    bad_version = [n for n, (_t, v) in heads.items() if v != 4]
    check(not bad_version,
          f"每份公钥包内版本号均为 4（异常 {bad_version[:3]}）")
    tiny = [n for n, raw in decoded.items() if len(raw) < 200]
    check(not tiny,
          f"每份公钥解码后 ≥ 200 字节（过短 {[(n, len(decoded[n])) for n in tiny][:3]}）")

    # ── 3. 两两不同 ────────────────────────────────────────────────────
    check(len(set(decoded.values())) == len(decoded),
          f"{len(decoded)} 份公钥两两不同")
    per_suite_ok, detail = True, []
    for suite in SUITES:
        group = [decoded.get(f"debian-archive-{suite}-{k}.asc") for k in KINDS]
        if None in group or len(set(group)) != len(KINDS):
            per_suite_ok = False
            detail.append(f"{suite} 内部有重复")
        else:
            detail.append(f"{suite} 三把互不相同")
    check(per_suite_ok,
          "每套发行版的三把公钥（automatic / security-automatic / stable）互不相同"
          f"（{'；'.join(detail)}）")
    sizes = {f"{s}-{k}": len(decoded.get(f"debian-archive-{s}-{k}.asc", b""))
             for s in SUITES for k in KINDS}
    check(all(v > 0 for v in sizes.values()),
          f"9 份公钥尺寸分布：{sizes}")

    # ── 4. jetring 密钥源与 index ──────────────────────────────────────
    active = os.path.join(data_dir, "active-keys")
    if check(os.path.isdir(active), "active-keys/ 随包发布"):
        sources = [f for f in os.listdir(active) if f.startswith("add-")]
        check(len(sources) == ACTIVE_KEY_SOURCES,
              f"active-keys/ 含 {ACTIVE_KEY_SOURCES} 份密钥源（实际 {len(sources)}）")
        index_path = os.path.join(active, "index")
        if os.path.isfile(index_path):
            lines = [l for l in open(index_path, encoding="utf-8",
                                     errors="replace").read().splitlines() if l.strip()]
            check(len(lines) == ACTIVE_KEY_SOURCES
                  and all(re.match(r"^sha256-[0-9a-f]{64}\s+\S+", l) for l in lines),
                  f"active-keys/index 是 {ACTIVE_KEY_SOURCES} 行 sha256 清单")
        else:
            check(False, "active-keys/index 存在")

    # ── 5. 文档、许可与安装纯净性 ──────────────────────────────────────
    doc_dir = os.path.join(package_folder, "share", "doc", "debian-archive-keyring")
    docs = sorted(os.listdir(doc_dir)) if os.path.isdir(doc_dir) else []
    check(docs == ["README", "README.maintainer"],
          f"share/doc/debian-archive-keyring 随包发布（实际 {docs}）")

    lic = os.path.join(package_folder, "licenses", "copyright")
    check(os.path.isfile(lic)
          and "keys in the keyrings don't fall under any copyright"
          in open(lic, encoding="utf-8", errors="replace").read(),
          "licenses/copyright 已发布且写明公钥不受版权保护")

    leaked = [e for e in ("Makefile", "debian", "removed-keys", "trusted.pgp",
                          "keyrings") if os.path.exists(os.path.join(data_dir, e))]
    check(not leaked,
          f"安装目录未混入构建系统 / 历史密钥目录（发现 {leaked}）")
    unexpected = sorted(e for e in os.listdir(data_dir)
                        if not e.endswith(".asc") and e != "active-keys")
    check(not unexpected,
          f"share/keyrings 下只有 .asc 与 active-keys/（发现 {unexpected}）")

    passed = sum(1 for ok, _ in _results if ok)
    total = len(_results)
    print(f"\n        [test] {passed}/{total} assertions passed")
    if passed != total:
        print("FAILED assertions:")
        for ok, label in _results:
            if not ok:
                print(f"  - {label}")
        return 1
    print("All tests passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
