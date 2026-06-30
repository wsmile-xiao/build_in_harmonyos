# libdc1394 2.2.7 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-06-02
- 编译器: clang/clang++ (15.0.4)
- 状态: published

## 编译步骤

```bash
# 1. 修复config.guess/config.sub添加ohos支持
perl $SKILL_ROOT/scripts/patch-autotools-ohos.pl config.guess config.sub
# 或应用 patch: 0003-config.guess.patch + 0005-config.sub.patch

# 2. 应用源码级patch (仅5个)
patch -p1 < 0002-configure-ac-SDL.patch      # 注释AM_PATH_SDL宏
patch -p1 < 0009-dc1394-juju-capture.c.patch  # VLA→固定数组[2048]
patch -p1 < 0010-dc1394-juju-control.c.patch  # VLA→固定数组[512]

# 3. autoreconf + libtoolize (替代19个autoreconf/libtool升级patch)
autoreconf -fi
libtoolize --copy

# 4. HMDFS临时目录修复 (替代0006-configure.patch中的嵌入修复)
sed -i 's|mktemp -d "./confXXXXXX"|mktemp -d "$TMPDIR/confXXXXXX"|' configure
sed -i 's|tmp=./conf$$-$RANDOM|tmp=$TMPDIR/conf$$-$RANDOM|' configure

# 5. 编译安装
./configure --prefix=$DEFAULT_PREFIX
make -j1
make install DESTDIR=$TEST_PREFIX
make check
make install
```

## 补丁精简说明 (2026-06-02)

原23个patch中，19个是autoreconf重新生成产物和libtool升级替换，总计61,446行。
这些不应作为patch追踪（违反R2: Phase3不生成.patch），改为构建步骤：

| 原patch类别 | 原数量 | 原行数 | 替代方案 | 新行数 |
|-------------|--------|--------|----------|--------|
| config.guess/sub | 2 | 111 | 保留 | 111 |
| VLA修复(C源码) | 2 | 115 | 保留 | 115 |
| SDL configure.ac | 0 | — | 新建源码级patch | ~15 |
| autoreconf产物 | 10 | ~28,743 | `autoreconf -fi` | 0 |
| libtool升级 | 7 | ~32,929 | `libtoolize --copy` + autoreconf | 0 |
| HMDFS mktemp | (嵌入0006) | (4行) | post-autoreconf sed | 2行 |
| **合计** | **23** | **61,672** | **构建步骤替代** | **5 patch + 2 sed** |

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | config.guess无法识别系统 | E007: 缺少HarmonyOS检测 | 0003-patch 或 patch-autotools-ohos.pl |
| 2 | AM_PATH_SDL宏未展开 | SDL m4宏未随源码提供 | 0002-patch: 注释configure.ac中AM_PATH_SDL |
| 3 | VLA in struct不支持 | clang不支持GCC扩展 | 0009/0010-patch: 固定大小数组 |
| 4 | HMDFS mktemp Permission denied | umask 077+mktemp组合 | post-autoreconf sed修复 |
| 5 | libtool版本不匹配 | 源码自带2.4.2 vs 系统2.4.7 | `libtoolize --copy` 替代 |

## 依赖版本

- libraw1394: 2.1.2 (预编译包)
- clang: 15.0.4
- autoreconf: 2.72
- automake: 1.16.5
- libtoolize: 2.4.7

## 验证结果

```bash
pkg-config --modversion libdc1394-2  # 2.2.7
ls ~/usr/local/lib/libdc1394.so.26.0.1  # 198KB stripped+signed
ls ~/usr/local/bin/dc1394_reset_bus      # 14KB stripped+signed
```

## 功能测试结果 (2026-06-02)

- 总测试项: 45, 通过: 44, 失败: 1 (预期)
- 通过率: 97.8%
- dc1394_new()返回NULL: 无FireWire硬件(预期行为)

---

**编译结束**: 2026-06-02
**最终状态**: published
**补丁数**: 5 (从23精简，精简率99.6%)
**交付物**: libdc1394-2.2.7-ohos-aarch64.tar.gz (stripped+signed)
**质量门禁**: G1-G4 PASS