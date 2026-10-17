# i2util 1.2 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-08-12
- 编译器: clang (15.0.4) / clang++
- 平台: HarmonyOS aarch64 (aarch64-unknown-linux-ohos)
- 状态: built

## 编译步骤

```bash
# 1. 初始化（下载/解压/骨架/依赖解析）
python3 scripts/ohc-run.py init-build i2util 1.2 --url=http://software.internet2.edu/sources/I2util/I2util-1.2.tar.gz

# 2. 打 config.guess/config.sub 平台补丁（E007）
perl scripts/patch-autotools-ohos.pl config/config.guess config/config.sub
# 补丁脚本对 2009 旧版 config.sub 三处未命中，需手动补丁：
#   - maybe_os 列表追加 linux-ohos*
#   - OS 合法列表追加 -linux-ohos*
#   - -linux*) 分支前追加 -linux-ohos) 保持 os=-linux-ohos（防止被改写为 -linux-gnu-ohos）
# config.guess 分支旧版为 echo;exit 模式，补丁写入的 GUESS 变量不会输出，需补 echo "$GUESS"; exit

# 3. 修 config.status/configure 的 umask（E011）
#    config.status 与 configure 中 "umask 077" → "umask 022"（各 2 处）

# 4. 构建
./configure --prefix=$DEFAULT_PREFIX && make -j1 && make install DESTDIR=$TEST_PREFIX
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `configure: error: cannot guess build type` | config.guess (2009-11-20) 无 HarmonyOS 识别分支，uname -s=HarmonyOS 无法匹配 | 按 E007 补 config.guess（HarmonyOS→aarch64-unknown-linux-ohos）+ config.sub（linux-ohos 三元组/OS/内核三处） |
| 2 | `./config.status[678]: can't create ./confXXXXXX/subs1.awk: Permission denied` | HMDFS 下 umask 077 创建的临时目录（0700/setgid）owner 与进程 UID 映射不匹配（E011） | configure 与 config.status 中 `umask 077`→`umask 022`，tmp 目录变为组可写 |

## 源码修改

工作目录 `config/config.guess`、`config/config.sub`、`configure`、`config.status`（生成文件随构建再生成，仅修改工作区副本，归档补丁由 refresh-patch 统一生成）。

## 依赖版本

- clang 15.0.4
- GNU Make 4.4.1
- autoconf 2.72
- 无第三方库依赖（仅 libc/socket/nsl，Linux 下均含于 glibc）

## 验证结果

```bash
$ ./config/config.guess
aarch64-unknown-linux-ohos
$ ./config/config.sub aarch64-unknown-linux-ohos
aarch64-unknown-linux-ohos
$ ./configure --prefix=$DEFAULT_PREFIX   # exit 0，config.h 与全部 Makefile 生成
$ make -j1                                # exit 0
$ make install DESTDIR=$TEST_PREFIX       # exit 0
```

## 交付物

| 文件 | 说明 |
|------|------|
| lib/libI2util.a | 静态库 |
| include/I2util/*.h | 20+ 头文件（errlog/io/random/sha1/pbkdf2/table 等） |
| bin/aespasswd, bin/pfstore | 命令行工具（R38 需 commands.json） |

## 注意事项

- 构建产物同时包含**库文件**（libI2util.a）与**可执行文件**（aespasswd、pfstore）→ R38 判定为 tool 类型，软件级目录需建 commands.json。
- `pfstore` 依赖随机设备（I2_RANDOMDEV 检测 /dev/urandom），HarmonyOS 上存在该设备。
- E007/E011 均为 autotools 项目通用坑，已命中知识图谱，无新知识需沉淀。
---

**编译结束**: 2026-08-12 19:38
**最终状态**: built
