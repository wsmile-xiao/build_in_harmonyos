# pkgconf 2.5.1 适配笔记

## 编译环境
- 构建系统: meson（绕过 autotools/sh 权限问题）
- 编译日期: 2026-05-26
- 编译器: OHOS SDK clang 15.0.4
- 状态: published（静态链接版本）

## 编译步骤

### 1. 初始化
```bash
python3 $SKILL_ROOT/scripts/ohc-run.py init-build pkgconf 2.5.1
source .build-context-pkgconf-2.5.1
```

### 2. 应用 config.guess 补丁（E007）
```bash
perl $SKILL_ROOT/scripts/patch-autotools-ohos.pl config.guess config.sub
```

### 3. meson 配置（静态链接）
```bash
LLVM_ROOT=/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm
export CC=$LLVM_ROOT/bin/clang
export AR=$LLVM_ROOT/bin/llvm-ar
export RANLIB=$LLVM_ROOT/bin/llvm-ranlib

meson setup build --prefix=$DEFAULT_PREFIX --default-library=static -Dtests=disabled
```

### 4. 手动编译（绕过 ninja 权限问题）
```bash
cd build
# ninja 编译目标文件
ninja -C build -j2  # 编译 .o 文件

# 手动创建静态库（ninja 失败）
$LLVM_ROOT/bin/llvm-ar csrD libpkgconf.a libpkgconf.a.p/*.o

# 手动链接可执行文件（静态链接）
$LLVM_ROOT/bin/clang pkgconf.p/*.o libpkgconf.a -static -o pkgconf
$LLVM_ROOT/bin/clang bomtool.p/*.o libpkgconf.a -static -o bomtool
```

### 5. 安装到 staging
```bash
mkdir -p $TEST_PREFIX/$DEFAULT_PREFIX/{bin,lib,include/pkgconf}
cp pkgconf bomtool $TEST_PREFIX/$DEFAULT_PREFIX/bin/
cp libpkgconf.a $TEST_PREFIX/$DEFAULT_PREFIX/lib/
cp ../libpkgconf/*.h $TEST_PREFIX/$DEFAULT_PREFIX/include/pkgconf/
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | config.guess 无法识别 HarmonyOS | GNU config.guess 不包含 __OHOS__ 检测 | E007 补丁：patch-autotools-ohos.pl |
| 2 | config.status 临时文件创建失败 | /bin/sh 执行权限问题（HMDFS 限制） | 切换到 meson 编译 |
| 3 | ninja 创建静态库失败 | ninja 使用 /bin/sh 执行 rm 命令失败 | 手动用 llvm-ar 创建静态库 |
| 4 | 动态链接无法运行 | HarmonyOS 动态链接器权限限制 | 添加 -static 完全静态链接 |

## 源码修改

无补丁文件，但应用了：
- **E007 补丁**：config.guess + config.sub（HarmonyOS 平台识别）

## 依赖版本

- LLVM: 15.0.4（OHOS SDK）
- meson: 1.11.1
- ninja: 1.13.0

## 验证结果

```bash
# 静态链接验证
file $TEST_PREFIX/$DEFAULT_PREFIX/bin/pkgconf
# 输出: ELF executable, 64-bit LSB arm64, static, not stripped

# 功能验证（⭐ 关键成功）
$TEST_PREFIX/$DEFAULT_PREFIX/bin/pkgconf --version
# 输出: 2.5.1 ✅

$TEST_PREFIX/$DEFAULT_PREFIX/bin/bomtool --version
# 输出: bomtool 2.5.1 ✅
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| pkgconf | 1.1M | 静态链接可执行文件 |
| bomtool | 1.0M | 静态链接可执行文件 |
| libpkgconf.a | 371K | 静态库 |
| libpkgconf.pc | - | pkg-config 文件 |

## 注意事项

1. **必须静态链接**：动态链接版本因 HarmonyOS 动态链接器权限限制无法运行
2. **优先使用 meson**：autotools 在 HMDFS 上有权限问题
3. **手动链接步骤**：如果 ninja 失败，需手动创建静态库和链接可执行文件
---

**编译结束**: 2026-05-26 16:33
**最终状态**: built
