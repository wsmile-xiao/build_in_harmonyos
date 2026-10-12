# popt 1.19 — 编译进度

> 档案创建时间: 2026-10-08
> 当前状态: conan create 验证中

## 基本信息

| 项目 | 值 |
|------|-----|
| 软件 | popt |
| 版本 | 1.19 |
| 性质 | 升级件（main 已有 1.16） |
| 构建系统 | autotools |
| 下载源 | https://ftp.osuosl.org/pub/rpm/popt/releases/popt-1.x/popt-1.19.tar.gz |
| sha256 | c25a4838fc8e4c1c8aacb8bd620edb3084a3d63bf8987fdad3ca2758c63240f9 |
| 平台 | aarch64-linux-ohos |

## 与 1.16 的差异

- popt 1.16 → 1.19：上游三年演进（2012 → 2020），新增 POPT_ARG_ARGV、
  POPT_ARGFLAG_RANDOM、POPT_ARG_SHORT、--usage 输出改进、大量解析器修复
- 构建系统不变（autotools），无新增依赖，增量适配路径：
  同样的三平台补丁策略（E007 config.guess/config.sub + E129 umask）
- 1.19 源码 build-aux/config.guess 为 2018-08-29 版本，同样不含 OHOS 检测，
  需要替换（补丁从 1.16 的 automake-1.16 2023 版本对齐到 1.19 目录结构）
- 1.19 的 configure 生成临时目录处同样存在 umask 077（HMDFS 兼容问题）

## 补丁清单

| 补丁 | 文件 | 说明 |
|------|------|------|
| 0001-build-aux-config.guess.patch | build-aux/config.guess | E007: 替换为含 OHOS 检测的版本 |
| 0002-build-aux-config.sub.patch | build-aux/config.sub | E007: aarch64-linux-ohos 三元组支持 |
| 0003-configure.patch | configure | E129: umask 077 → 022 (HMDFS 权限兼容) |

## 上游测试套件

- tests/testit.sh: 62 个 test1 用例 + 3 个 test3 diff 用例 = 65 用例
- test2/tdict 编译但不被 testit.sh 调用
- 1.16 时 test58 失败（libtool wrapper 命名差异）；1.19 待实测

## 编译记录 (2026-10-08)

- conan create -pr=ohos-aarch64 全绿：configure → make → install → test_package 1/1 PASS
  （test_popt -v -i 42 -o out.txt → "popt test PASSED: verbose=1 int=42 output=out.txt"）
- 源码 sha256 实测：c25a4838fc8e4c1c8aacb8bd620edb3084a3d63bf8987fdad3ca2758c63240f9
  （osuosl 官方源下载 + sha256sum，与 goblinrs 旧配方同源一致）
- 上游测试套件实测（本机 OHOS aarch64，同款 clang 工具链构建）：
  tests/testit.sh → 65 PASS / 0 FAIL，exit 0
  （62x test1 + 3x test3 diff 用例全部通过；1.16 时代 test58 libtool
  wrapper 命名差异问题在 1.19 已不存在）

## 上游测试执行方式

```bash
# 在 conan create 使用的同一源码（打完三补丁）上：
cd <srcdir>
bash ./configure --prefix=$HOME/usr/local --enable-static --disable-shared CC=<ohos-clang>
# 时间戳规整阻止 automake 重生成（本地环境无 autoconf 主程序）：
touch configure; sleep 1; touch config.status Makefile src/Makefile tests/Makefile config.h
make -j1
cd tests && sh testit.sh
# → 65 PASS / 0 FAIL
```

## 遇到的问题

### 本地复现上游测试时的 automake 重生成问题（不影响 CI 配方）
- **现象**: make 触发 `Makefile.in` 重生成，报 `autoconf: inaccessible or not found` (127)
- **根因**: 本地 `~/usr/local/bin` 有 automake-1.16 但缺 autoconf 主程序；且复制源码目录后
  时间戳顺序被打乱（Makefile.in 比 Makefile.am 旧触发重生成规则）
- **解决**: `touch configure; sleep 1; touch config.status Makefile ...` 规整时间戳后
  make -j1 成功——此问题仅存在于手工复制目录复现场景，conan create 流水线
  （每次全新下载解压）不受影响
- **make jobserver mkfifo**: HMDFS 不支持 FIFO，`make: jobserver mkfifo: Operation not
  permitted` 为已知告警，降级串行执行，不影响构建结果（配方统一 -j1）

### E007: config.guess/config.sub 不识别 HarmonyOS
- **原因**: popt 1.19 源码 build-aux/config.guess 为 2018-08-29 版本，不含 OHOS 检测
- **修复**: 补丁替换为含 OHOS 支持的版本，实测 `config.guess` 输出
  `aarch64-unknown-linux-ohos` ✅

### E129: configure umask 077 在 HMDFS 下权限错误
- **修复**: 0003-configure.patch umask 077 → 022

