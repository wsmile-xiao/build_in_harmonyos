#!/usr/bin/env python3
"""sbagen_consumer_e2e.py — sbagen 1.4.5 命令行消费者 e2e

直接使用打包产物 <pkg>/bin/sbagen 完成"用户真实会做"的操作，并逐项断言：

  [1] 产物契约：二进制可执行、文档与上游示例序列齐全
  [2] 产物架构：ELF 64-bit + machine = aarch64（0xB7）——证明装的是本平台自建产物，
      而非上游 tarball 内附带的 32 位 x86 预编译 sbagen（契约回归）
  [3] -h 帮助：退出码 0、含 SBaGen 与版本号 1.4.5
  [4] 合成确定性：同一命令两次运行输出 sha256 完全一致
  [5] 尺寸口径：raw = 秒数 × 44100 × 2ch × 2B；WAV = raw + 44 字节头
  [6] WAV 头字段：RIFF/WAVE、2ch、44100Hz、16bit、data 长度
  [7] 混音：-m <wav> 混入后样本与非混音不同（长度不变）→ 证明混音路径真的执行
  [8] 管道输出：-O 把 raw 写到 stdout，长度符合 -L 口径
  [9] 上游示例序列：-S -q 1 合成 share/sbagen/examples 下的 .sbg
  [10] 平台适配路径：不传 -o 时明确提示无音频设备（T_POSIX / NO_AUDIO 分支）
  [11] 解码器缺口：.ogg 输入报 "Ogg support wasn't compiled into this executable"
       而非崩溃（tremor 未发布 → 未启用可选解码器）
  [12] 错误路径：未知选项给出提示而非崩溃

用法: python3 sbagen_consumer_e2e.py <package-folder> <workdir>
"""
import glob
import hashlib
import os
import struct
import subprocess
import sys

RATE = 44100
FRAME_BYTES = 4              # stereo 16-bit
CHECKS = []
FAILED = []


def ck(cond, what, detail=""):
    CHECKS.append(what)
    if cond:
        print(f"  [ok]   {what}")
    else:
        FAILED.append(what)
        print(f"  [FAIL] {what}" + (f"  → {detail}" if detail else ""))


def run(binary, args, cwd=None):
    """以列表方式调用（不经过 shell：OHOS 无 /bin/sh）。"""
    return subprocess.run([binary] + args, cwd=cwd, stdout=subprocess.PIPE,
                          stderr=subprocess.PIPE)


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    pkg, work = sys.argv[1], sys.argv[2]
    binary = os.path.join(pkg, "bin", "sbagen")
    os.makedirs(work, exist_ok=True)

    # ---- [1] 产物契约 ----
    ck(os.path.isfile(binary), "bin/sbagen 存在")
    ck(os.access(binary, os.X_OK), "bin/sbagen 可执行")
    doc = os.path.join(pkg, "share", "doc", "sbagen", "SBAGEN.txt")
    ck(os.path.isfile(doc) and os.path.getsize(doc) > 50000,
       "share/doc/sbagen/SBAGEN.txt 手册存在且 >50KB")
    examples = sorted(glob.glob(os.path.join(pkg, "share", "sbagen", "examples",
                                             "**", "*.sbg"), recursive=True))
    ck(len(examples) >= 10, f"上游示例序列 >= 10 个（实际 {len(examples)}）")
    ck(os.path.isfile(os.path.join(pkg, "share", "sbagen", "scripts", "p-drop")),
       "预编程序列脚本 share/sbagen/scripts/p-drop 存在")

    # ---- [2] 产物架构（aarch64 自建产物，非上游 x86 预编译） ----
    with open(binary, "rb") as f:
        head = f.read(20)
    ck(head[:4] == b"\x7fELF", "产物为 ELF 文件")
    ck(len(head) >= 20 and head[4] == 2, "ELF class = 64-bit")
    machine = struct.unpack("<H", head[18:20])[0] if len(head) >= 20 else 0
    ck(machine == 0xB7, f"ELF machine = aarch64（实际 0x{machine:02x}）")

    # ---- [3] -h 帮助 ----
    p = run(binary, ["-h"])
    out = p.stdout.decode("utf-8", "replace")
    ck(p.returncode == 0, "-h 退出码 0", f"rc={p.returncode}")
    ck("SBaGen" in out, "-h 输出含 SBaGen")
    ck("1.4.5" in out, "-h 输出含版本号 1.4.5")

    # ---- [4][5] 合成确定性 + 尺寸口径 ----
    raw2 = os.path.join(work, "e2e_2s.raw")
    raw2b = os.path.join(work, "e2e_2s_b.raw")
    args2s = ["-Q", "-i", "-o", raw2, "-L", "00:00:02", "200+10/20"]
    p = run(binary, args2s)
    ck(p.returncode == 0, "2 秒 raw 合成退出码 0")
    size2 = os.path.getsize(raw2) if os.path.isfile(raw2) else -1
    ck(size2 == 2 * RATE * FRAME_BYTES,
       f"2 秒 raw 尺寸 = {2 * RATE * FRAME_BYTES}（实际 {size2}）")
    run(binary, ["-Q", "-i", "-o", raw2b, "-L", "00:00:02", "200+10/20"])
    ck(os.path.isfile(raw2b) and sha256(raw2) == sha256(raw2b),
       "两次相同参数合成结果 sha256 一致（确定性）")

    raw1 = os.path.join(work, "e2e_1s.raw")
    run(binary, ["-Q", "-i", "-o", raw1, "-L", "00:00:01", "200+10/20"])
    size1 = os.path.getsize(raw1) if os.path.isfile(raw1) else -1
    ck(size1 == RATE * FRAME_BYTES,
       f"1 秒 raw 尺寸 = {RATE * FRAME_BYTES}（实际 {size1}）")

    # ---- [6] WAV 头字段 ----
    wav2 = os.path.join(work, "e2e_2s.wav")
    run(binary, ["-Q", "-W", "-i", "-o", wav2, "-L", "00:00:02", "200+10/20"])
    wsize = os.path.getsize(wav2) if os.path.isfile(wav2) else -1
    ck(wsize == size2 + 44, f"WAV 尺寸 = raw + 44 头（实际 {wsize}）")
    with open(wav2, "rb") as f:
        blob = f.read()
    ck(blob[:4] == b"RIFF" and blob[8:12] == b"WAVE", "WAV 魔数 RIFF/WAVE")
    off, ch, rate, bits, dlen = 12, 0, 0, 0, 0
    while off + 8 <= len(blob):
        clen = struct.unpack("<I", blob[off + 4:off + 8])[0]
        if blob[off:off + 4] == b"fmt ":
            ch = struct.unpack("<H", blob[off + 10:off + 12])[0]
            rate = struct.unpack("<I", blob[off + 12:off + 16])[0]
            bits = struct.unpack("<H", blob[off + 22:off + 24])[0]
        elif blob[off:off + 4] == b"data":
            dlen = clen
            break
        off += 8 + clen + (clen & 1)
    ck((ch, rate, bits) == (2, RATE, 16),
       f"WAV fmt: 2ch/44100Hz/16bit（实际 {ch}ch/{rate}Hz/{bits}bit）")
    ck(dlen == 2 * RATE * FRAME_BYTES, f"WAV data 长度 = {2 * RATE * FRAME_BYTES}（实际 {dlen}）")

    # ---- [7] 混音路径 ----
    mix = os.path.join(work, "e2e_mix.raw")
    p = run(binary, ["-Q", "-i", "-m", wav2, "-o", mix, "-L", "00:00:01", "200+10/20"])
    ck(p.returncode == 0, "混音（-m wav）退出码 0", p.stderr.decode("utf-8", "replace")[:200])
    msize = os.path.getsize(mix) if os.path.isfile(mix) else -1
    ck(msize == size1, f"混音输出长度与非混音一致（实际 {msize}）")
    ck(os.path.isfile(mix) and sha256(mix) != sha256(raw1),
       "混入音频后样本与非混音不同（混音路径确实生效）")

    # ---- [8] stdout 管道输出 ----
    p = run(binary, ["-Q", "-i", "-O", "-L", "00:00:01", "200+10/20"])
    ck(p.returncode == 0, "-O 输出到 stdout 退出码 0")
    ck(len(p.stdout) == RATE * FRAME_BYTES,
       f"-O stdout 长度 = {RATE * FRAME_BYTES}（实际 {len(p.stdout)}）")

    # ---- [9] 上游示例序列合成 ----
    if examples:
        seq_out = os.path.join(work, "e2e_seq.raw")
        p = run(binary, ["-Q", "-S", "-q", "1", "-o", seq_out,
                         "-L", "00:00:03", examples[0]])
        ck(p.returncode == 0, f"上游示例序列合成退出码 0（{os.path.basename(examples[0])}）",
           p.stderr.decode("utf-8", "replace")[:200])
        ssize = os.path.getsize(seq_out) if os.path.isfile(seq_out) else -1
        ck(ssize == 3 * RATE * FRAME_BYTES,
           f"示例序列 3 秒输出尺寸 = {3 * RATE * FRAME_BYTES}（实际 {ssize}）")

    # ---- [10] 无音频设备（T_POSIX / NO_AUDIO 平台路径） ----
    p = run(binary, ["-Q", "-i", "-L", "00:00:01", "200+10/20"])
    err = p.stderr.decode("utf-8", "replace")
    ck(p.returncode != 0, "不指定 -o 时不以 0 退出（无音频设备）", f"rc={p.returncode}")
    ck("Direct output to soundcard not supported" in err,
       "提示 'Direct output to soundcard not supported'（T_POSIX/NO_AUDIO 路径）", err[:200])
    ck("Use -o or -O" in err, "给出 -o/-O/-Wo/-WO 的使用指引")

    # ---- [11] 未编译的解码器（tremor 未发布 → 可选解码器关闭） ----
    fake_ogg = os.path.join(work, "e2e_fake.ogg")
    with open(fake_ogg, "wb") as f:
        f.write(b"OggS" + b"\x00" * 60)
    ogg_out = os.path.join(work, "e2e_ogg.raw")
    p = run(binary, ["-Q", "-i", "-m", fake_ogg, "-o", ogg_out,
                     "-L", "00:00:01", "200+10/20"])
    oerr = p.stderr.decode("utf-8", "replace")
    ck(p.returncode != 0, ".ogg 混音失败退出（未编译 Ogg 支持）", f"rc={p.returncode}")
    ck("Ogg support wasn't compiled" in oerr,
       "报错明确：Ogg support wasn't compiled into this executable", oerr[:200])

    # ---- [12] 错误路径 ----
    p = run(binary, ["-Q", "-Z"])
    ck("not known" in p.stderr.decode("utf-8", "replace"),
       "未知选项给出 'not known' 提示而非崩溃")

    print(f"[sbagen_consumer_e2e] {len(CHECKS) - len(FAILED)}/{len(CHECKS)} checks passed")
    return 0 if not FAILED else 1


if __name__ == "__main__":
    sys.exit(main())
