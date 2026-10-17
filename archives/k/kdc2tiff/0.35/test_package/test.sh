#!/data/service/hnp/bin/bash
# test_package/test.sh — kdc2tiff 0.35 消费端功能测试（真跑安装后的两个二进制）
#
# 覆盖面（每条一个可数断言，末行 SUMMARY total=/passed=/failed=）：
#   T1  两个入口名都在 conanrun PATH 上（bin_PROGRAMS = kdc2tiff kdc2jpeg）
#   T2  ELF 取证：e_machine=EM_AARCH64(183)，DT_NEEDED 真含 libtiff/libjpeg
#   T3  usage 分支：无参数 ⇒ 退出码 1 + USAGE + Version: 0.35 + 按 argv[0] 分叉的选项集
#   T4  真实失败形态：输入文件不存在 ⇒ 非零 + "failed to open input file" + 无产物
#   T5  端到端 TIFF->TIFF（合成 4x4 无压缩 RGB，再从格式侧解析 IFD 校尺寸/通道）
#   T6  端到端 TIFF->JPEG（校 SOI/EOI）
#   T7  往返：kdc2tiff 读回自己写出的 TIFF 再写一次
#
# OHOS 约束：/tmp 只读（E002）⇒ 工作目录 $HOME/tmp；mksh 不能执行 ELF ⇒
#           由 conanfile 用 CONFIG_SHELL(bash) 调起本脚本；字节级校验一律走 python3
#           （toybox 的 od/head 选项子集不可靠）。
# 判据不放宽：failed>0 ⇒ 退出 1。
set -u

total=0
passed=0
failed=0
ok()  { total=$((total+1)); passed=$((passed+1)); echo "  [PASS] $1"; }
bad() { total=$((total+1)); failed=$((failed+1)); echo "  [FAIL] $1"; }
chk() { if [ "$1" -eq 0 ]; then ok "$2"; else bad "$2 (rc=$1)"; fi; }

SCRATCH="${TMPDIR:-$HOME/tmp}"
WORK="$SCRATCH/kdc2tiff-test-$$"
mkdir -p "$WORK" || { echo "cannot create $WORK"; exit 1; }
trap 'rm -rf "$WORK"' EXIT
cd "$WORK" || exit 1

echo "== T1 两个入口名在位 =="
command -v kdc2tiff > /dev/null 2>&1
chk $? "kdc2tiff 在 conanrun PATH 上可解析"
command -v kdc2jpeg > /dev/null 2>&1
chk $? "kdc2jpeg 在 conanrun PATH 上可解析（上游 ln -f 已改成 cp -f）"
KDCBIN="$(command -v kdc2tiff)"
JPGBIN="$(command -v kdc2jpeg)"

echo "== T2 ELF 机器码与依赖链 =="
cat > probe.py <<'PYEOF'
import struct, sys

def dynamic_needed(blob):
    """Return DT_NEEDED strings of an ELF64 little-endian binary."""
    shoff, = struct.unpack_from("<Q", blob, 0x28)
    shentsize, shnum = struct.unpack_from("<HH", blob, 0x3a)
    secs = []
    for i in range(shnum):
        base = shoff + i * shentsize
        sh_type, = struct.unpack_from("<I", blob, base + 4)
        sh_offset, sh_size = struct.unpack_from("<QQ", blob, base + 0x18)
        sh_link, = struct.unpack_from("<I", blob, base + 0x28)
        sh_entsize, = struct.unpack_from("<Q", blob, base + 0x38)
        secs.append((sh_type, sh_offset, sh_size, sh_link, sh_entsize))
    names = []
    for sh_type, off, size, link, entsize in secs:
        if sh_type != 6:                       # SHT_DYNAMIC
            continue
        strtab = secs[link][1]
        ent = entsize or 16
        pos = off
        while pos + ent <= off + size:
            d_tag, d_val = struct.unpack_from("<QQ", blob, pos)
            if d_tag == 0:
                break
            if d_tag == 1:                      # DT_NEEDED
                end = blob.index(b"\0", strtab + d_val)
                names.append(blob[strtab + d_val:end].decode())
            pos += ent
    return names


def tiff_tags(path):
    blob = open(path, "rb").read()
    if blob[:2] not in (b"II", b"MM"):
        return None
    endian = "<" if blob[:2] == b"II" else ">"
    magic, off = struct.unpack_from(endian + "HI", blob, 2)
    n, = struct.unpack_from(endian + "H", blob, off)
    tags = {}
    for i in range(n):
        base = off + 2 + i * 12
        tag, typ, cnt = struct.unpack_from(endian + "HHI", blob, base)
        val, = struct.unpack_from(endian + "I", blob, base + 8)
        tags[tag] = (typ, cnt, val)
    return tags


def scalar(tags, tag):
    typ, _cnt, val = tags[tag]
    return (val & 0xFFFF) if typ == 3 else val


cmd = sys.argv[1]
if cmd == "elf":
    for path in sys.argv[2:]:
        blob = open(path, "rb").read()
        if blob[:4] != b"\x7fELF":
            print(f"{path.rsplit('/', 1)[-1]}|NOTELF|")
            continue
        machine, = struct.unpack_from("<H", blob, 18)
        print(f"{path.rsplit('/', 1)[-1]}|{machine}|" + ",".join(dynamic_needed(blob)))

elif cmd == "mkinput":
    # 合成一张 4x4 无压缩 RGB baseline TIFF（1:1 像素宽高比，单 strip）
    out = sys.argv[2]
    W = H = 4
    pix = bytearray()
    for y in range(H):
        for x in range(W):
            pix += bytes(((x * 60 + 15) & 0xFF, (y * 60 + 15) & 0xFF, ((x + y) * 40) & 0xFF))
    entries = [
        (256, 3, 1, W),            # ImageWidth  SHORT
        (257, 3, 1, H),            # ImageLength SHORT
        (258, 3, 3, 146),          # BitsPerSample -> 三个 SHORT 存在 IFD 之后
        (259, 3, 1, 1),            # Compression = none
        (262, 3, 1, 2),            # PhotometricInterpretation = RGB
        (273, 4, 1, 168),          # StripOffsets
        (277, 3, 1, 3),            # SamplesPerPixel
        (278, 3, 1, H),            # RowsPerStrip
        (279, 4, 1, len(pix)),     # StripByteCounts
        (282, 10, 1, 152),         # XResolution  RATIONAL 72/1
        (283, 10, 1, 160),         # YResolution  RATIONAL 72/1
    ]
    ifd = struct.pack("<H", len(entries))
    for tag, typ, cnt, val in entries:
        payload = struct.pack("<HH", val, 0) if typ == 3 else struct.pack("<I", val)
        ifd += struct.pack("<HHI", tag, typ, cnt) + payload
    ifd += struct.pack("<I", 0)
    blob = b"II" + struct.pack("<HI", 42, 8) + ifd
    assert len(blob) == 146, len(blob)
    blob += struct.pack("<HHH", 8, 8, 8)      # BitsPerSample @146
    blob += struct.pack("<II", 72, 1)         # XResolution   @152
    blob += struct.pack("<II", 72, 1)         # YResolution   @160
    assert len(blob) == 168, len(blob)
    blob += bytes(pix)
    open(out, "wb").write(blob)
    print(f"synthesized {out} {len(blob)} bytes")

elif cmd == "tifftags":
    for path in sys.argv[2:]:
        tags = tiff_tags(path)
        if tags is None:
            print(f"{path}|NOTIFF|")
            continue
        w = scalar(tags, 256) if 256 in tags else -1
        h = scalar(tags, 257) if 257 in tags else -1
        spp = scalar(tags, 277) if 277 in tags else -1
        comp = scalar(tags, 259) if 259 in tags else -1
        print(f"{path}|TIFF|{w}x{h}|spp={spp}|compression={comp}|tags={len(tags)}")

elif cmd == "jpgmark":
    for path in sys.argv[2:]:
        blob = open(path, "rb").read()
        soi = blob[:2] == b"\xff\xd8"
        eoi = blob[-2:] == b"\xff\xd9"
        print(f"{path}|len={len(blob)}|soi={'1' if soi else '0'}|eoi={'1' if eoi else '0'}")

else:
    print("usage: probe.py elf|mkinput|tifftags|jpgmark ...")
    sys.exit(2)
PYEOF

python3 probe.py elf "$KDCBIN" "$JPGBIN" > elf.txt 2>&1
chk $? "ELF 取证脚本执行成功"
sed 's/^/  elf: /' elf.txt
grep -q '^kdc2tiff|183|' elf.txt
chk $? "kdc2tiff 的 e_machine=183（EM_AARCH64）"
grep -q '^kdc2jpeg|183|' elf.txt
chk $? "kdc2jpeg 的 e_machine=183（EM_AARCH64）"
grep '^kdc2tiff|' elf.txt | grep -q 'libtiff'
chk $? "kdc2tiff 的 DT_NEEDED 里有 libtiff（链到 conan 依赖而非系统同名库）"
grep '^kdc2tiff|' elf.txt | grep -q 'libjpeg'
chk $? "kdc2tiff 的 DT_NEEDED 里有 libjpeg（链到 conan 依赖而非系统同名库）"

echo "== T3 usage 分支 =="
"$KDCBIN" > usage.out 2> usage.err
usage_rc=$?
if [ "$usage_rc" -eq 1 ]; then ok "无参数退出码=1（上游 Usage(); return 1 分支）"; else bad "无参数退出码应为 1，实为 ${usage_rc}"; fi
grep -q "USAGE" usage.err
chk $? "usage 输出含 USAGE"
grep -q "Version: 0.35" usage.err
chk $? "usage 输出含 Version: 0.35（VERSION 由 config.h 注入 ⇒ 版本串走通）"
grep -q "TIFF compression scheme" usage.err
chk $? "argv[0]=kdc2tiff 时 usage 列出 TIFF 专属选项"
if grep -q "JPEG quality" usage.err; then bad "argv[0]=kdc2tiff 时 usage 不该列 JPEG 选项"; else ok "argv[0]=kdc2tiff 时 usage 不列 JPEG 选项"; fi
"$JPGBIN" > /dev/null 2> jpeg_usage.err
grep -q "JPEG quality setting" jpeg_usage.err
chk $? "argv[0]=kdc2jpeg 时 usage 列出 JPEG 专属选项（两个入口名真的分叉）"

echo "== T4 真实失败形态（输入不存在）=="
"$KDCBIN" no-such-file.tif -o out.tif > /dev/null 2> miss.err
miss_rc=$?
if [ "$miss_rc" -ne 0 ]; then ok "缺失输入退出码非零（rc=${miss_rc}）"; else bad "缺失输入却退出 0"; fi
grep -q "failed to open input file" miss.err
chk $? "报出可识别的真实失败：failed to open input file"
if [ -s out.tif ]; then bad "失败分支不该产出 out.tif"; else ok "失败分支未产出文件"; fi

echo "== T5 端到端 TIFF -> TIFF =="
python3 probe.py mkinput in.tif > mkinput.log 2>&1
chk $? "合成 4x4 无压缩 RGB baseline TIFF 输入"
if [ -s in.tif ]; then ok "in.tif 产出（$(wc -c < in.tif) 字节）"; else bad "in.tif 缺失"; fi
python3 probe.py tifftags in.tif > in_tags.txt 2>&1
grep -q 'in.tif|TIFF|4x4|spp=3' in_tags.txt
chk $? "合成件自身可被 IFD 解析（对照组）"
sed 's/^/  /' in_tags.txt

"$KDCBIN" in.tif -o conv.tif > conv.log 2>&1
chk $? "kdc2tiff in.tif -o conv.tif 退出码 0"
if [ -s conv.tif ]; then ok "conv.tif 产出且非空（$(wc -c < conv.tif) 字节）"; else bad "conv.tif 缺失或为空"; fi
python3 probe.py tifftags conv.tif > conv_tags.txt 2>&1
grep -q 'conv.tif|TIFF|' conv_tags.txt
chk $? "conv.tif 带 TIFF 魔数且 IFD 可解析"
grep -q 'conv.tif|TIFF|4x4|spp=3' conv_tags.txt
chk $? "conv.tif 尺寸保持 4x4 且 3 通道"
sed 's/^/  /' conv_tags.txt

echo "== T6 端到端 TIFF -> JPEG =="
"$JPGBIN" in.tif -o conv.jpg > convjpg.log 2>&1
chk $? "kdc2jpeg in.tif -o conv.jpg 退出码 0"
if [ -s conv.jpg ]; then ok "conv.jpg 产出且非空（$(wc -c < conv.jpg) 字节）"; else bad "conv.jpg 缺失或为空"; fi
python3 probe.py jpgmark conv.jpg > conv_mark.txt 2>&1
sed 's/^/  /' conv_mark.txt
grep '^conv.jpg|' conv_mark.txt | grep -q '|soi=1'
chk $? "conv.jpg 以 JPEG SOI（ffd8）开头"
grep '^conv.jpg|' conv_mark.txt | grep -q '|eoi=1'
chk $? "conv.jpg 以 JPEG EOI（ffd9）结尾"

echo "== T7 往返：读回自己写出的 TIFF =="
"$KDCBIN" conv.tif -o round.tif > round.log 2>&1
chk $? "kdc2tiff 读回 conv.tif 再写出（往返退出码 0）"
if [ -s round.tif ]; then ok "round.tif 产出且非空（$(wc -c < round.tif) 字节）"; else bad "round.tif 缺失"; fi

echo
echo "SUMMARY kdc2tiff consumer: total=$total passed=$passed failed=$failed"
[ "$failed" -eq 0 ] || exit 1
exit 0
