#!/usr/bin/env python3
"""cramfsswap 1.4.5 test_package — 上游 autopkgtest 语义 + 鸿蒙适配断言。

上游测试 = debian autopkgtest test-cmd（mkfs.cramfs 生成镜像 → cramfsswap 交换
两次 → diff 断言「首换不同、再换复原」）。OHOS CI 环境无 util-linux 的
mkfs.cramfs，本脚本以确定性字节构造等价镜像运行同一语义断言（不落任何二进制
夹具入库）。

夹具布局（root 目录 + 1 个普通文件），word = 4 字节：
  word  0-15 : superblock（magic/size/flags/future/signature/crc/edition/blocks/files/name）
  word 16-18 : root inode（mode=S_IFDIR|0755, namelen=0, offset=19）
  word 19-21 : file inode（mode=S_IFREG|0644, size=4096, namelen=2, offset=24）
  word 22-23 : name "a.txt" 补零到 8 字节
  word 24    : 块指针 = 4192（数据块结束的字节偏移）
  byte 100..4192 : 4092 字节文件数据
总长 4192 字节。flags = 0x3（FSID_VERSION_2 | SORTED_DIRS）；cramfsswap 拒绝
flags & 0xFFFFFFFC 且要求 bit0。fsid.crc = crc32(crc 字段清零的镜像)，与
cramfsswap 输出侧重算口径一致（LE 位域、LSB 先排，与设备 aarch64 LE 一致）。
"""
import os
import struct
import subprocess
import sys
import zlib

CRAMFS_MAGIC = 0x28CD3D45
SIGNATURE = b"Compressed ROMFS"


def le32(x):
    return struct.pack("<I", x)


def be32(x):
    return struct.pack(">I", x)


def build_cramfs():
    name = b"a.txt\x00\x00\x00"
    data = bytes((i * 7 + 3) % 256 for i in range(4092))
    end = 100 + len(data)  # 4192
    img = bytearray(end)

    # superblock
    img[0:4] = le32(CRAMFS_MAGIC)
    img[4:8] = le32(end)
    img[8:12] = le32(0x3)
    img[12:16] = le32(0)
    img[16:32] = SIGNATURE
    img[32:36] = le32(0)  # fsid.crc, filled below
    img[36:40] = le32(0)  # edition
    img[40:44] = le32(1)  # blocks
    img[44:48] = le32(2)  # files: root + 1 regular file
    img[48:64] = b"cramfs-test".ljust(16, b"\x00")
    # root inode: mode:16|uid:16 ; size:24|gid:8 ; namelen:6|offset:26 (LE bitfields)
    img[64:76] = le32(0x41ED) + le32(0) + le32(0 | (19 << 6))
    # file inode
    img[76:88] = le32(0x81A4) + le32(4096) + le32(2 | (24 << 6))
    # name
    img[88:96] = name
    # block pointer (byte offset of end of the single data block)
    img[96:100] = le32(end)
    # data
    img[100:end] = data

    # store the crc cramfsswap expects: crc32 over image with crc word zeroed
    crc = zlib.crc32(bytes(img)) & 0xFFFFFFFF
    img[32:36] = le32(crc)
    return bytes(img)


def run(binpath, *args, clean_env=False):
    env = None
    if clean_env:
        env = {"PATH": os.environ.get("PATH", "/usr/bin:/bin")}
        env.pop("LD_LIBRARY_PATH", None)
    return subprocess.run([binpath, *args], capture_output=True, text=True,
                          env=env, timeout=60)


def main():
    binpath, work = sys.argv[1], sys.argv[2]
    os.makedirs(work, exist_ok=True)
    orig = os.path.join(work, "sample.cramfs")
    out1 = os.path.join(work, "sample_swp_1.cramfs")
    out2 = os.path.join(work, "sample_swp_2.cramfs")
    bad = os.path.join(work, "notacramfs.bin")

    checks = []

    def check(desc, ok):
        checks.append(ok)
        print(("ok - " if ok else "FAIL - ") + desc)

    with open(orig, "wb") as f:
        f.write(build_cramfs())
    with open(bad, "wb") as f:
        f.write(b"this is not a cramfs image, just plain text\n" * 10)

    # 1) swap: rc=0, output differs (upstream: diff ORG SWP_1 must differ)
    r1 = run(binpath, orig, out1)
    ok1 = r1.returncode == 0 and os.path.exists(out1)
    check("swap rc=0 且产出文件存在", ok1)
    d1 = open(orig, "rb").read()
    s1 = open(out1, "rb").read()
    check("交换后的镜像与原镜像不同（上游 diff ORG SWP_1 非零语义）", ok1 and d1 != s1)
    check("stdout 报告 little endian → big endian",
          "little endian, will be converted to big endian" in (r1.stdout or ""))
    check("stdout 报告重算 CRC（CRC: 0x…）", "CRC: 0x" in (r1.stdout or ""))
    check("magic 字段字节序已交换（28cd3d45 → 453dcd28）",
          s1[0:4] == be32(CRAMFS_MAGIC) and d1[0:4] == le32(CRAMFS_MAGIC))

    # 2) swap back: rc=0, byte-identical to original (upstream: diff ORG SWP_2 == 0)
    r2 = run(binpath, out1, out2)
    ok2 = r2.returncode == 0 and os.path.exists(out2)
    check("二次交换（换回）rc=0", ok2)
    s2 = open(out2, "rb").read()
    check("二次交换结果与原镜像逐字节一致（上游 diff ORG SWP_2 零差异语义）",
          ok2 and s2 == d1)

    # 3) version/help probes（OHOS 适配新增,上游无此入口）
    okv = True
    for flag in ("--version", "-V"):
        rv = run(binpath, flag, clean_env=True)
        okv = okv and rv.returncode == 0 and "1.4.5" in (rv.stdout or "")
    check("OHOS 适配：--version/-V 返回 rc=0 且自报 1.4.5", okv)
    okh = True
    for flag in ("--help", "-h"):
        rh = run(binpath, flag, clean_env=True)
        okh = okh and rh.returncode == 0 and "Usage" in (rh.stdout or "")
    check("OHOS 适配：--help/-h 返回 rc=0 并输出用法", okh)

    # 4) 错误路径（上游行为）：非 cramfs 输入 → rc=1 + cramfs magic not detected
    re_ = run(binpath, bad, os.path.join(work, "bad.out"))
    check("非 cramfs 输入 rc=1 且报 cramfs magic not detected（上游错误路径）",
          re_.returncode == 1 and "cramfs magic not detected" in (re_.stderr or ""))

    # 5) OHOS 适配：干净环境（不注入 LD_LIBRARY_PATH/conanrun 变量）直接执行成功
    rc3 = run(binpath, orig, os.path.join(work, "clean.out"), clean_env=True)
    check("OHOS 适配：无 LD 注入的干净环境可直接执行（zlib 静态链接进产物）",
          rc3.returncode == 0)

    npass = sum(1 for c in checks if c)
    nfail = len(checks) - npass
    print("cramfsswap test_package: PASS=%d FAIL=%d" % (npass, nfail))
    return 1 if nfail else 0


if __name__ == "__main__":
    sys.exit(main())
