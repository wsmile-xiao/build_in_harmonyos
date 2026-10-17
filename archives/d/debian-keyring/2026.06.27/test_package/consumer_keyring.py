#!/usr/bin/env python3
"""debian-keyring 2026.06.27 —— 完整消费者用例（端到端消费交付的密钥环）。

用法: python3 consumer_keyring.py <package_folder>

**消费方是谁**：OpenHarmony 上没有 `gpg`，但"把密钥环当可信密钥库读取"这件事本身
不需要 gpg —— apt / jetring 的消费链路是：

    /usr/share/keyrings/*.pgp   ← 可信密钥库（本包交付的 share/keyrings）
         │  ① 按清单核对交付完整性（sha512sums.txt，等同 apt 校 Release 校验和）
         │  ② 读取 OpenPGP 数据流 → 公钥包/UID 包/自签名包 → 建索引（fingerprint/keyid）
         │  ③ 按签名者 keyid 解析"这个签名人受不受信"（apt 的 Signed-By 查找）
         └─ ④ 读不出 / 对不上 / 查不到 ⇒ 消费失败（非 0 退出）

因此本用例**真的把密钥环当库用起来**：自己按 RFC 4880 解析报文体，算 v4 指纹
（SHA-1 over 0x99‖len‖body），从自签名包里取 issuer keyid 与公钥绑定，
然后回答查询（keyid / 指纹查找命中，以及不存在的 keyid 必须查不到）。

与 `test_keyring.py`（适配自检）的分工：那边断言"交付物齐备、包结构自洽、包数对得上"；
这里跑的是**消费流程**，产出的是"索引了多少把钥匙 / 解析了多少次查询"这类可核对结果。
"""

import hashlib
import os
import sys

# 公钥算法号（RFC 4880 §9.1）
ALGO = {
    1: "RSA", 2: "RSA-E", 3: "RSA-S", 16: "Elgamal", 17: "DSA",
    18: "ECDH", 19: "ECDSA", 22: "EdDSA",
}
# 只对这几种算法解析第一段 MPI（模数/素数）来量强度
BITS_ALGO = {1: "n", 2: "n", 3: "n", 17: "p"}

FAILURES = []


def fail(msg):
    FAILURES.append(msg)
    print(f"  [consumer][FAIL] {msg}")


# ────────────────────────── OpenPGP 解析 ──────────────────────────

def walk_packets(raw):
    """按 RFC 4880 §4.2 逐个报文体切分（支持新格式部分长度），产出 (tag, body, off)。"""
    i, n = 0, len(raw)
    while i < n:
        first = raw[i]
        if not first & 0x80:
            raise ValueError(f"offset {i}: 0x{first:02x} 不是报文头")
        i += 1
        if first & 0x40:                                     # 新格式头
            tag = first & 0x3F
            body = bytearray()
            while True:
                if i >= n:
                    raise ValueError("新格式长度域截断")
                l0 = raw[i]
                i += 1
                if l0 < 192:                                 # 1 字节定长
                    need, partial = l0, False
                elif l0 < 224:                               # 2 字节定长
                    if i >= n:
                        raise ValueError("2 字节长度域截断")
                    need, partial = ((l0 - 192) << 8) + raw[i] + 192, False
                    i += 1
                elif l0 < 255:                               # 部分长度（分块续）
                    need, partial = 1 << (l0 & 0x1F), True
                else:                                        # 255 → 4 字节定长
                    if i + 4 > n:
                        raise ValueError("5 字节长度域截断")
                    need, partial = int.from_bytes(raw[i:i + 4], "big"), False
                    i += 4
                if i + need > n:
                    raise ValueError(f"报文长度越界（offset {i}, 需 {need}）")
                body += raw[i:i + need]
                i += need
                if not partial:
                    break
            yield tag, bytes(body), i - len(body)
        else:                                                # 老格式头
            tag = (first >> 2) & 0x0F
            lt = first & 0x03
            if lt == 3:
                need = n - i
            else:
                nb = {0: 1, 1: 2, 2: 4}[lt]
                if i + nb > n:
                    raise ValueError("老格式长度域截断")
                need = int.from_bytes(raw[i:i + nb], "big")
                i += nb
            if i + need > n:
                raise ValueError("老格式报文长度越界")
            yield tag, raw[i:i + need], i
            i += need


def fingerprint_v4(body):
    return hashlib.sha1(b"\x99" + len(body).to_bytes(2, "big") + body).hexdigest().upper()


def parse_pubkey(body):
    """返回 dict(fp, keyid, version, created, algo, bits)；只解析指纹与强度所需字段。"""
    if len(body) < 6:
        raise ValueError("公钥报文过短")
    ver = body[0]
    created = int.from_bytes(body[1:5], "big")
    if ver == 4:
        algo = body[5]
        bits = int.from_bytes(body[6:8], "big") if (algo in BITS_ALGO and len(body) >= 8) else None
        fp = fingerprint_v4(body)
        keyid = fp[24:]
    elif ver == 3:                                           # v3 RSA：keyid = 模数低 64 位
        algo = body[7]
        if algo not in (1, 2, 3) or len(body) < 10:
            raise ValueError(f"v3 公钥包算法异常（algo={algo}）")
        mpi_bits = int.from_bytes(body[8:10], "big")
        nbytes = (mpi_bits + 7) // 8
        mod = body[10:10 + nbytes]
        if len(mod) != nbytes:
            raise ValueError("v3 公钥包模数截断")
        keyid, bits = mod[-8:].hex().upper(), mpi_bits
        fp = hashlib.md5(mod).hexdigest().upper()            # v3 指纹（RFC 4880 §12.2，近似标注）
    else:
        raise ValueError(f"未知公钥版本 version={ver}")
    return {"fp": fp, "keyid": keyid, "version": ver, "created": created, "algo": algo,
            "algo_name": ALGO.get(algo, f"algo-{algo}"), "bits": bits}


def _subpacket_len(body, q):
    """签名子包长度（RFC 4880 §5.2.3.1：1 / 2 / 5 字节，且**含**类型字节）。"""
    l0 = body[q]
    if l0 < 192:
        return l0, q + 1
    if l0 < 255:
        return ((l0 - 192) << 8) + body[q + 1] + 192, q + 2
    return int.from_bytes(body[q + 1:q + 5], "big"), q + 5


def sig_issuer(body):
    """签名包（tag 2）里的签发者 keyid：v4 取 issuer keyid(16)/issuer 指纹(33) 子包，v3 取定长域。"""
    if not body:
        return None
    if body[0] == 4 and len(body) >= 6:
        p = 4                                                # [4:6] = hashed 区长度
        for _ in range(2):                                   # 先 hashed，再 unhashed
            if p + 2 > len(body):
                break
            area_len = int.from_bytes(body[p:p + 2], "big")
            q, end = p + 2, min(p + 2 + area_len, len(body))
            while q + 2 <= end:
                slen, nxt = _subpacket_len(body, q)
                if slen <= 0:
                    break
                stype = body[nxt] & 0x7F                     # 最高位是 critical 标志
                if stype == 16 and slen == 9:                # issuer keyid：1 + 8
                    return body[nxt + 1:nxt + 9].hex().upper()
                if stype == 33 and slen == 21:               # issuer 指纹：1 + 20（v4）
                    return body[nxt + 13:nxt + 21].hex().upper()
                q = nxt + slen                               # 长度域自身不计入 slen
            p = end
        return None
    if body[0] == 3 and len(body) >= 10:
        return body[2:10].hex().upper()
    return None


def index_ring(raw):
    """把一条密钥环读成索引：每把主钥 → keyid/指纹/UID/自签名绑定。"""
    keys, cur = [], None
    for tag, body, off in walk_packets(raw):
        if tag == 6:                                         # 公钥
            cur = {"uids": [], "selfsigs": 0, "othersigs": 0, **parse_pubkey(body)}
            keys.append(cur)
        elif tag == 13 and cur is not None:                  # User ID
            cur["uids"].append(body.decode("utf-8", "replace"))
        elif tag == 2 and cur is not None:                   # 签名
            iss = sig_issuer(body)
            if iss == cur["keyid"]:
                cur["selfsigs"] += 1
            else:
                cur["othersigs"] += 1
    return keys


def keyid_lookup(store, keyid):
    keyid = keyid.upper()
    if keyid.startswith("0X"):
        keyid = keyid[2:]
    return [k for k in store if k["keyid"] == keyid]


def fp_lookup(store, fp):
    fp = fp.upper()
    return [k for k in store if k["fp"] == fp]


# ────────────────────────── 消费流程 ──────────────────────────

def main():
    if len(sys.argv) < 2:
        print("usage: consumer_keyring.py <package_folder> [keyring_dir]")
        return 2
    package_folder = os.path.abspath(sys.argv[1])
    store_dir = sys.argv[2] if len(sys.argv) > 2 else os.path.join(package_folder, "share", "keyrings")
    print(f"  [consumer] 可信密钥库: {store_dir}")

    # ① 发现交付的密钥环（apt 扫描 /usr/share/keyrings 的方式：目录里所有 *.pgp）
    if not os.path.isdir(store_dir):
        fail(f"可信密钥库目录不存在: {store_dir}")
        return 1
    rings = sorted(f for f in os.listdir(store_dir) if f.endswith(".pgp"))
    print(f"  [consumer] 发现 {len(rings)} 条密钥环: {', '.join(rings)}")

    # ② 按交付清单核对完整性（等同 apt 校 Release 的校验和）
    manifest = {}
    sums_path = os.path.join(store_dir, "sha512sums.txt")
    if not os.path.isfile(sums_path):
        fail("缺少 sha512sums.txt —— 消费者无法核对交付完整性")
    else:
        for line in open(sums_path, encoding="utf-8"):
            parts = line.split()
            if len(parts) == 2:
                manifest[parts[1]] = parts[0].lower()
        if sorted(manifest) != rings:
            fail(f"清单与实际交付不一致：清单 {sorted(manifest)} vs 实际 {rings}")
        for name in rings:
            digest = hashlib.sha512(open(os.path.join(store_dir, name), "rb").read()).hexdigest()
            if manifest.get(name) != digest:
                fail(f"{name} 的 sha512 与清单不符（清单 {manifest.get(name)} 实际 {digest}）")
        print(f"  [consumer] 清单核对 OK：{len(manifest)} 条密钥环 sha512 全部一致")

    # ③ 读取密钥环 → 建索引（消费真实报文体，不是看文件大小）
    store, per_ring = [], {}
    for name in rings:
        raw = open(os.path.join(store_dir, name), "rb").read()
        try:
            keys = index_ring(raw)
        except ValueError as exc:
            fail(f"{name} 读不出可消费的 OpenPGP 数据流: {exc}")
            continue
        per_ring[name] = keys
        store += keys
        uids = sum(len(k["uids"]) for k in keys)
        bound = sum(1 for k in keys if k["selfsigs"] > 0 and k["uids"])
        print(f"  [consumer] {name}: {len(keys)} 把公钥 / {uids} 个 UID / "
              f"{bound} 把有 UID 且被自身签名绑定 / 报文体 {len(raw)} 字节")
        nokey = [k["keyid"] for k in keys if not k["uids"]]
        if nokey:
            fail(f"{name}: {len(nokey)} 把公钥没有 UID（{nokey[:3]}）——消费方无法据此认人")
        nobind = [k["keyid"] for k in keys if k["uids"] and not k["selfsigs"]]
        if nobind:
            fail(f"{name}: {len(nobind)} 把公钥有 UID 却无自签名绑定（{nobind[:3]}）")
        weak = [(k["keyid"], k["bits"]) for k in keys
                if k["bits"] is not None and k["bits"] < 2048]
        if weak:
            fail(f"{name}: {len(weak)} 把公钥强度 < 2048 bit（{weak[:3]}）")

    # ④ 去重一致性：同一密钥库里 keyid/指纹唯一（上游 t/no-dupes 的语义）
    for name, keys in per_ring.items():
        ids = [k["keyid"] for k in keys]
        fps = [k["fp"] for k in keys]
        if len(set(ids)) != len(ids):
            dup = sorted({i for i in ids if ids.count(i) > 1})
            fail(f"{name}: 出现重复 keyid {dup[:3]}")
        if len(set(fps)) != len(fps):
            fail(f"{name}: 出现重复指纹")
    print(f"  [consumer] 索引共 {len(store)} 把公钥（去重后 {len(set(k['fp'] for k in store))}）")

    # ⑤ 按签名者查找：apt 的 Signed-By 语义 —— keyid / 指纹都能定位到同一把钥匙
    hits = 0
    for key in store:
        by_id = keyid_lookup(store, key["keyid"])
        by_fp = fp_lookup(store, key["fp"])
        if len(by_id) != 1 or len(by_fp) != 1 or by_id[0]["fp"] != key["fp"]:
            fail(f"查找失败: keyid {key['keyid']} 命中 {len(by_id)} 次 / "
                 f"指纹 {key['fp']} 命中 {len(by_fp)} 次")
            continue
        hits += 1
    print(f"  [consumer] Signed-By 查找：{hits}/{len(store)} 把公钥按 keyid 与指纹均可唯一定位")

    # ⑥ 反向控制：未受信的 keyid 必须查不到（否则这个库等于"什么都信"）
    for bogus in ("DEADBEEFDEADBEEF", "0000000000000000", "FFFFFFFFFFFFFFFF"):
        if keyid_lookup(store, bogus):
            fail(f"未受信 keyid {bogus} 竟然查得到 —— 可信库语义被破坏")
    print("  [consumer] 反向控制 OK：3 个未受信 keyid 均查不到")

    if FAILURES:
        print(f"  [consumer] 消费失败：{len(FAILURES)} 项")
        return 1
    print(f"  [consumer] 端到端消费完成：{len(rings)} 条密钥环 / {len(store)} 把公钥 / "
          f"清单与查找全部核对通过")
    return 0


if __name__ == "__main__":
    sys.exit(main())
