# bossa 1.9.1 适配笔记

## 编译环境
- 构建系统: makefile（纯 Makefile 项目，无 autotools configure）
- 编译日期: 2026-06-17
- 编译器: clang 15.0.4 / clang++
- 状态: published

## 编译步骤

bossa 是纯 Makefile 项目，无 configure 步骤。Makefile 已内置 HarmonyOS 规则（`ifeq ($(OS),Harmony)`），只构建 CLI 工具 bossac 和 bossash。

```bash
# Step 2: 编译（仅 CLI 工具）
cd $BUILD_SRC_DIR
make CXX=clang++ VERSION=1.9.1 PREFIX=$DEFAULT_PREFIX \
    LDFLAGS="-L$DEFAULT_PREFIX/lib" CXXFLAGS="-fPIC -O2 -I$DEFAULT_PREFIX/include" \
    bossac bossash

# Step 2.5: staging 安装（DESTDIR 模式，R20）
make -B install DESTDIR=$TEST_PREFIX PREFIX=$DEFAULT_PREFIX CXX=clang++ VERSION=1.9.1

# Step 2.6: 预编译包制作
python3 $SKILL_ROOT/scripts/ohc-run.py package bossa 1.9.1

# Step 2.6a: 本地安装（模拟用户部署）
make -B install PREFIX=$DEFAULT_PREFIX CXX=clang++ VERSION=1.9.1

# Step 2.6b: 用户验证
$DEFAULT_PREFIX/bin/bossac -h  # 输出: BOSSA Version 1.9.1

# Step 3: 收尾
python3 $SKILL_ROOT/scripts/ohc-run.py finish bossa 1.9.1 published
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | VERSION 变量为空 | Makefile 使用 `git describe --tags --dirty` 获取版本（line 6），但源码目录不是 git 仓库 | 手动覆盖 `VERSION=1.9.1` 作为 make 参数 |
| 2 | make all 包含 bossa GUI 导致编译失败 | Makefile generic `all` 目标（line 243: bossa+bossac+bossash）覆盖了 HarmonyOS `all` 目标（line 109: 仅 bossac+bossash），GNU Make 后定义优先 | 指定目标 `make bossac bossash` 而非 `make all`，避免触发 wxWidgets 依赖 |
| 3 | make install 输出 "up to date" 不执行安装 | Makefile `install` 目标名与源码 `install/` 目录同名（`INSTALLDIR=install`），Make 误认为目标已完成 | 使用 `make -B install` 强制重新执行 |
| 4 | arm-none-eabi-as/objcopy 不可用 | 源码 applet 编译规则（line 259-268）使用 `arm-none-eabi-as` 和 `arm-none-eabi-objcopy` 编译 WordCopyArm.asm ARM Thumb 汇编 | WordCopyArm.cpp/.h 预生成文件已存在于源码目录，当 .cpp 时间戳晚于 .asm 时 make 自动跳过 applet 生成步骤 |
| 5 | bossash 需要 readline 库 | Makefile `BOSSASH_LIBS=-lreadline $(COMMON_LIBS)`（line 238） | readline 8.2 预编译包已安装于 ~/usr/local/lib，LDFLAGS 指向该路径 |
| 6 | 二进制补丁误生成 | refresh-patch 基于 edit-tracker 检测到 bin/bossac、bin/bossash 变更并生成补丁，但这些是编译产物而非源码修改 | 删除二进制补丁（R6 规则：只改源文件不改生成文件），清理 edit-tracker 的 edited 列表 |

## 源码修改

**无补丁。** bossa Makefile 已有 HarmonyOS 规则（line 100-115），源码无需任何修改。仅需 make 参数覆盖（CXX、VERSION、PREFIX、LDFLAGS、CXXFLAGS）。

## 依赖版本

| 依赖 | 版本 | 来源 |
|------|------|------|
| readline | 8.2 | 预编译包（~/usr/local/lib） |

## 验证结果

### bossac 命令行工具

```bash
$ bossac -h
Usage: bossac [OPTION...] [FILE]
Basic Open Source SAM-BA Application (BOSSA) Version 1.9.1
Flash programmer for Atmel SAM devices.
Copyright (c) 2011-2018 ShumaTech (http://www.shumatech.com)

$ bossac -i
No device found on /dev/ttyACM0
```

### bossash 交互式 Shell

```bash
$ bossash
Press Ctrl-D or enter "exit" to end session.
Enter "help" to display a command list.
bossa>
```

### 二进制格式

```bash
$ file bossac bossash
bossac: ELF shared object, 64-bit LSB arm64, dynamic (/lib/ld-musl-aarch64.so.1)
bossash: ELF shared object, 64-bit LSB arm64, dynamic (/lib/ld-musl-aarch64.so.1)

$ readelf -d bossac | grep NEEDED
  NEEDED: libc++_shared.so
  NEEDED: libc.so

$ readelf -d bossash | grep NEEDED
  NEEDED: libreadline.so.8
  NEEDED: libc++_shared.so
  NEEDED: libc.so
```

## 交付物

| 文件 | 大小 | SHA256 | 说明 |
|------|------|--------|------|
| bossa-1.9.1-ohos-aarch64.tar.gz | 841KB (841876B) | 2a6cb4363a8759589af91bd08b50138385f0a0ef8246357563ffe92e2f29b234 | 预编译包（bossac + bossash + libreadline） |
| bossa-1.9.1-ohos-aarch64-debug.tar.gz | 1.4MB (1469683B) | 50a7ebb6ab2d32aca6d1c6b0c82b31a0eec05c1d4cda6146a1f57e85650a1d31 | 调试符号包 |

## 注意事项

1. bossa GUI（bossa）不可编译——需要 wxWidgets，HarmonyOS 平台不提供
2. arm-none-eabi 工具链不可用时，需确保 WordCopyArm.cpp/.h 预生成文件存在于源码目录
3. Makefile 的 HarmonyOS `all` 目标（line 109）被通用 `all` 目标（line 243）覆盖，这是 Makefile 设计缺陷，需指定显式目标
4. Makefile `install` 目标名与 `install/` 目录同名冲突，需 `make -B` 强制执行
5. R6 规则：bin/bossac 和 bin/bossash 是编译产物，不应作为补丁追踪

---

**编译结束**: 2026-06-17 01:19
**最终状态**: published
