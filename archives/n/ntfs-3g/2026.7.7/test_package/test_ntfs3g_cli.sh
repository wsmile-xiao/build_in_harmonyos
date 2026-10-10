#!/bin/sh
# 消费者测试:真机执行 ntfsprogs 工具集(文件级 NTFS 操作,不依赖 FUSE)
#
# 设备环境注意(均为真机实证,非推测,证据见卡片评论):
#  · `/tmp` 在 OHOS 上只读 → 工作目录用 $HOME/tmp(见 AGENTS-OPERATIONS.md OP-2)。
#  · conan test 的执行环境 PATH 不含 /system/bin,`mkdir`/`dd` 取不到
#    (实证 "mkdir: inaccessible or not found"),故先补 PATH。
#  · mkntfs/ntfsinfo/ntfsls 动态链接包内 lib/libntfs-3g.so.90,包 lib/ 不在默认
#    搜索路径,需由调用方注入 LD_LIBRARY_PATH(见 test_package/conanfile.py)。
#
# 工具语义要点(读上游源码 + 真机实证,勿凭直觉改):
#  · mkntfs **不建文件**——ntfs_device_unix_io_open() 先 stat(),ENOENT 即报
#    "The device doesn't exist" (mkntfs.c:3492 走 O_RDWR,无 O_CREAT);
#    `-F` 只表示"非块设备也强制格式化"。故须先 dd 预造镜像。
#  · ntfsinfo 的 `-f` 是 --force(不是 --file);要卷信息须加 `-m/--mft`。
#  · ntfsls 的 `-f` 同样是 --force;空卷根目录本就没有用户文件,
#    真正可断言的是系统元数据文件(`-s`)——故本测试据此断言。
PATH="/system/bin:/data/service/hnp/bin:$HOME/usr/local/bin:$PATH"
export PATH
MKDIR=/system/bin/mkdir
BIN="$1"
SRCDIR="$2"
W=$HOME/tmp
$MKDIR -p "$W" 2>/dev/null || { echo "FAIL: cannot create $W"; exit 1; }
W="$W/ntfs3g_test_$$"
$MKDIR -p "$W" || { echo "FAIL: cannot create workdir $W"; exit 1; }
cd "$W" || exit 1

# 1) mkntfs 创建 NTFS 镜像(文件,非块设备)
dd if=/dev/zero of=ntfs.img bs=512 count=4096 > dd.out 2>&1
rcdd=$?
if [ $rcdd -ne 0 ]; then echo "FAIL: dd rc=$rcdd"; cat dd.out; exit 1; fi

"$BIN/mkntfs" -F -Q -s 512 -p 0 -H 0 -S 0 -L "test" ntfs.img > mk.out 2>&1
rc1=$?
if [ $rc1 -ne 0 ]; then echo "FAIL: mkntfs rc=$rc1"; cat mk.out; exit 1; fi
test -s ntfs.img || { echo "FAIL: ntfs.img empty"; exit 1; }
grep -qi "completed successfully" mk.out || { echo "FAIL: mkntfs did not report success"; cat mk.out; exit 1; }

# 2) ntfsinfo 读取卷信息(-m = dump volume info)
"$BIN/ntfsinfo" -m -f ntfs.img > info.out 2>&1
rc2=$?
if [ $rc2 -ne 0 ]; then echo "FAIL: ntfsinfo rc=$rc2"; cat info.out; exit 1; fi
grep -qi "Volume Information" info.out || { echo "FAIL: no volume info"; cat info.out; exit 1; }
grep -qi "Volume Name" info.out || { echo "FAIL: no volume name field"; cat info.out; exit 1; }

# 3) ntfsls 列出根目录的系统元数据文件(空卷的用户目录为空,故断言 -s)
"$BIN/ntfsls" -s -f ntfs.img > ls.out 2>&1
rc3=$?
if [ $rc3 -ne 0 ]; then echo "FAIL: ntfsls rc=$rc3"; cat ls.out; exit 1; fi
for meta in '$MFT' '$Boot' '$Volume'; do
  grep -qF "$meta" ls.out || { echo "FAIL: ntfsls missing $meta"; cat ls.out; exit 1; }
done

echo "ntfs-3g consumer test OK"
