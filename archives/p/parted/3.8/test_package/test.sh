#!/data/service/hnp/bin/bash
# test_package/test.sh — parted 3.8 功能 E2E（真实执行包内二进制，R34）
#
# 参数: $1 = 包的 bin 目录
# 全部操作在私有临时目录中的 64MiB sparse 镜像上完成，不需要 root/loop 设备。
#
# 断言（10 条）：
#   1  parted --version 报告 3.8
#   2  partprobe --version 报告 3.8
#   3  sparse 镜像创建成功
#   4  parted -s mklabel gpt 成功且 print 显示 gpt
#   5  print 报告 Disk 与镜像路径
#   6  mkpart primary ext4 成功且 print 列出分区
#   7  unit MiB print 正常（单位换算路径）
#   8  rm 1 成功且分区消失
#   9  --json 输出合法且含 "disk" 字段
#  10  mklabel msdos + mkpart fat32 成功（第二套 label 路径）
set -euo pipefail

BINDIR="${1:-}"
[ -n "$BINDIR" ] && [ -d "$BINDIR" ] || { echo "FAIL: usage: test.sh <bindir>" >&2; exit 1; }
PARTED="$BINDIR/parted"
PARTPROBE="$BINDIR/partprobe"
PASS=0
ok()   { echo "OK:   $1"; PASS=$((PASS + 1)); }
fail() { echo "FAIL: $1"; exit 1; }

WORK=""
for base in "${TMPDIR:-}" "${HOME:-}/tmp" "${HOME:-}"; do
  [ -n "$base" ] || continue
  mkdir -p "$base" 2>/dev/null || continue
  if WORK="$(mktemp -d "$base/parted-e2e.XXXXXX" 2>/dev/null)"; then break; fi
done
[ -n "$WORK" ] || fail "no writable temp directory"
trap 'rm -rf "$WORK"' EXIT HUP INT TERM
cd "$WORK"

# 1/2: --version
out="$("$PARTED" --version 2>&1)" || fail "1/10 parted --version rc=$?"
case "$out" in *"parted (GNU parted) 3.8"*) ok "1/10 parted --version = 3.8" ;;
  *) fail "1/10 unexpected version output: $out" ;;
esac
out="$("$PARTPROBE" --version 2>&1)" || fail "2/10 partprobe --version rc=$?"
case "$out" in *"partprobe (GNU parted) 3.8"*) ok "2/10 partprobe --version = 3.8" ;;
  *) fail "2/10 unexpected version output: $out" ;;
esac

# 3: disk image
truncate -s 64M disk.img 2>/dev/null || dd if=/dev/zero of=disk.img bs=1M count=64 2>/dev/null
[ -s disk.img ] || fail "3/10 disk.img not created"
ok "3/10 sparse 64MiB disk image created"

# 4/5: GPT label
"$PARTED" -s disk.img mklabel gpt >/dev/null 2>&1 || fail "4/10 mklabel gpt rc=$?"
out="$("$PARTED" -s disk.img print 2>&1)" || fail "4/10 print rc=$?"
case "$out" in *"Partition Table: gpt"*) ok "4/10 mklabel gpt + print shows gpt" ;;
  *) fail "4/10 gpt table not shown: $out" ;;
esac
case "$out" in *"Disk "*"disk.img"*) ok "5/10 print reports Disk and image path" ;;
  *) fail "5/10 Disk header missing: $out" ;;
esac

# 6: mkpart
"$PARTED" -s disk.img mkpart primary ext4 1MiB 32MiB >/dev/null 2>&1 || fail "6/10 mkpart rc=$?"
out="$("$PARTED" -s disk.img print 2>&1)" || fail "6/10 print rc=$?"
case "$out" in *"primary"*) ok "6/10 mkpart primary ext4 + listed in print" ;;
  *) fail "6/10 partition not listed: $out" ;;
esac

# 7: unit conversion
out="$("$PARTED" -s disk.img unit MiB print 2>&1)" || fail "7/10 unit MiB print rc=$?"
case "$out" in *"MiB"*) ok "7/10 unit MiB print" ;;
  *) fail "7/10 MiB unit missing: $out" ;;
esac

# 8: rm
"$PARTED" -s disk.img rm 1 >/dev/null 2>&1 || fail "8/10 rm 1 rc=$?"
out="$("$PARTED" -s disk.img print 2>&1)"
case "$out" in *"primary"*) fail "8/10 partition still present after rm" ;;
  *) ok "8/10 rm 1 removes the partition" ;;
esac

# 9: JSON output
out="$("$PARTED" --script --json disk.img unit s print 2>&1)" || fail "9/10 --json print rc=$?"
case "$out" in *'"disk"'*) ok "9/10 --json output contains disk object" ;;
  *) fail "9/10 unexpected json output: $out" ;;
esac

# 10: msdos label + fat32（第二套 label 路径）
# 注：libparted/labels/dos.c 读取分区表时用 ped_file_system_probe() 探测
# 真实文件系统；空白分区重读时 File system 列必然为空（parted 3.8 上游
# 行为，非缺陷，已用源码确认）。fat32 对应类型号 0x0c，落盘后表现为
# 「lba」flag。因此断言分两步：
#   - mkpart+print 同一会话：File system 列显示 fat32（内存 fs_type）
#   - 重新打开镜像 print：保留 lba flag（0x0c 已写盘）
"$PARTED" -s disk.img mklabel msdos >/dev/null 2>&1 || fail "10/10 mklabel msdos rc=$?"
out="$("$PARTED" -s disk.img mkpart primary fat32 1MiB 16MiB print 2>&1)" || fail "10/10 mkpart fat32 rc=$?"
case "$out" in *"Partition Table: msdos"*) ;; *) fail "10/10 msdos table missing: $out" ;; esac
case "$out" in *"fat32"*) ;; *) fail "10/10 fat32 not shown in creation print: $out" ;; esac
out="$("$PARTED" -s disk.img print 2>&1)" || fail "10/10 re-read print rc=$?"
case "$out" in *"lba"*) ok "10/10 msdos+fat32: creation print shows fat32, re-read keeps lba flag" ;;
  *) fail "10/10 lba flag missing on re-read: $out" ;;
esac

echo "[test.sh] all ${PASS} assertions passed"
