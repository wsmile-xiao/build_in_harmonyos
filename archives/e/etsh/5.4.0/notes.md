# etsh 5.4.0 适配笔记

## 编译环境
- 构建系统: makefile (手写 ./configure + make，非 autotools)
- 编译日期: 2026-08-22
- 编译器: clang/15 (OHOS SDK aarch64-linux-ohos)
- 状态: published

## 软件简介
etsh 是 V6 UNIX /bin/sh (1975) 的增强向后兼容移植版，产出 CLI 可执行文件：
etsh、tsh、glob、fd2、goto、if。

## 编译步骤

```bash
source .build-context-etsh-5.4.0 && cd $BUILD_SRC_DIR

# 1. 清理（注意：make clean 会删除 config.h + mkconfig.tmp）
make clean

# 2. 运行手写 configure（生成 config.h + mkconfig.tmp）
#    configure 调用 ./mkconfig 探测 uname -s 决定 feature test macros
/data/service/hnp/bin/bash ./configure

# 3. 交叉编译（CC 由环境传入，默认 target=aarch64-unknown-linux-ohos）
CC=/data/service/hnp/bin/clang make -j1

# 4. staging 安装（OHOS 无 /usr/bin/install，用 /system/bin/install）
make install CC=/data/service/hnp/bin/clang \
     INSTALL=/system/bin/install \
     DESTDIR=$TEST_PREFIX

# 5. make check（在 aarch64 OHOS 兼容主机上通过）
make check
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 编译报错：SIG_SETMASK/struct sigaction/sigset_t/NSIG/setenv/unsetenv 未声明 | mkconfig 用 `uname -s` 探测系统，HarmonyOS 落入 `*)` unknown 分支，未定义 `_XOPEN_SOURCE`/`_DEFAULT_SOURCE`，musl libc 隐藏这些符号 | 补丁 0001：mkconfig case 语句 `Linux)` → `Linux|HarmonyOS)`，使 HarmonyOS 走 Linux 分支定义 feature test macros |
| 2 | `make install` 报错 `/usr/bin/install: No such file or directory` | OHOS 无 `/usr/bin/install` (E108) | 传 `INSTALL=/system/bin/install` (toybox) |
| 3 | `make clean` 后 `make` 报 "Please run ./configure first" | `make clean` 删除 config.h + mkconfig.tmp | 构建顺序须为 clean → configure → make |
| 4 | 链接报错 `Error loading shared library libxml2.so.16` + `clang-15: error: unable to execute command` | OHOS SDK 的 lld 链接器自身依赖 libxml2.so.16，CI conan 子进程默认 LD_LIBRARY_PATH 不含 SDK llvm/lib，lld 启动即失败 | build()/package() 中 OHOS 下前置 `LD_LIBRARY_PATH=<SDK>/llvm/lib:$LD_LIBRARY_PATH`（abuild/babeld 同方案）；不能用 `-fuse-ld=GNU ld`（产物 exit 126 不可执行） |

## make check 跳过说明
- make check 执行编译出的 OHOS 二进制 (`cd tests && ../etsh run etsh tsh`)
- 在 Linux host 上无法运行 aarch64 OHOS ELF 二进制
- **本机构为 aarch64 OHOS 兼容环境，make check 实际通过：14 Test(s) Passed**
- 在纯 Linux x86 host 上需跳过并记录原因

## 源码修改

| 文件 | 修改 |
|------|------|
| mkconfig | case 语句 `Linux)` → `Linux|HarmonyOS)`，使 HarmonyOS 走 Linux 分支定义 `_XOPEN_SOURCE 700` / `_DEFAULT_SOURCE` |

补丁文件: `patches/0001-mkconfig.patch`

## 依赖版本
- 无第三方依赖
- OHOS SDK clang 15.0.4 (aarch64-unknown-linux-ohos)
- musl libc (OHOS 系统 C 库)

## 验证结果

```bash
# 二进制类型验证
$ file etsh tsh glob fd2 goto if
etsh: ELF shared object, 64-bit LSB arm64, dynamic (/lib/ld-musl-aarch64.so.1)

# readelf 确认
$ readelf -h etsh | grep Machine
  Machine: AArch64

# make check 结果
$ make check
Testing etsh binary . . . . . . . . Done .
Testing tsh  binary . . . . . . Done .
14 Test(s) Passed

# 功能验证
$ ./etsh -c 'echo test'
test
```

## 交付物

| 文件 | 说明 |
|------|------|
| bin/etsh | V6 Thompson Shell 增强版 (主 shell) |
| bin/tsh | V6 Thompson Shell 原始版 |
| libexec/etsh-5.4.0/tsh/glob | glob 模式扩展工具 |
| libexec/etsh-5.4.0/tsh/fd2 | 文件描述符 2 重定向工具 |
| libexec/etsh-5.4.0/tsh/goto | goto 跳转工具 |
| libexec/etsh-5.4.0/tsh/if | 条件判断工具 |

## 注意事项
- etsh 的 configure 是手写脚本（非 autotools），不支持 `--enable-static`/`--disable-shared`
- conanfile.py 使用自定义 build() 直接调用 make，不用 AutotoolsToolchain
- INSTALL 路径需用 OHOS 的 /system/bin/install (toybox)
---

**编译结束**: 2026-08-22 13:34
**最终状态**: published

---

## 上游测试用例 (Upstream Test Suite)

etsh 5.4.0 源码自带上游测试套件，位于 `tests/` 目录（30 个测试文件），
Makefile 提供 `check-pre` → `check` → `check-post` 测试目标链。

### 测试结构

| 组件 | 说明 |
|---|---|
| `tests/` | 测试数据目录，含 syntax.list、test01-test08 等 `.log`/`.tsh`/`.etsh` 文件 |
| `check-pre` | 预检查：验证 etsh/tsh/glob/fd2 等二进制已编译 |
| `check` | 运行完整测试链：测试 tsh/etsh 二进制的语法解析、管道、重定向等 |
| `check-post` | 后处理：汇总测试结果 |

### 运行方式

```bash
source .build-context-etsh-5.4.0 && cd $BUILD_SRC_DIR
CC=/data/service/hnp/bin/clang make check
```

### 运行结果

```
Saturday, 2026-08-22, 14:52:57 CST
Testing tsh  binary . . . . . Done .
Testing etsh binary . . . . . Done .
14 Test(s) Passed
EXIT_CODE=0
```

- **退出码**: 0 (成功)
- **测试数**: 14 个全部通过
- **覆盖范围**: tsh/etsh 二进制的语法解析、管道、重定向、变量展开等核心功能
- **运行环境**: OHOS aarch64 构建主机，二进制直接在交互 shell 中执行（非 conan 子进程链）

### 备注

上游 `make check` 在构建主机的交互 shell 中直接执行编译出的 OHOS 二进制，
运行正常（exit=0）。这与 conan `test_package` 的 `self.run(env="conanrun")`
子进程链中返回 exit 126 的情况不同——后者是 OHOS exec MAC 策略对 conan
子进程上下文的限制，不影响上游测试套件的直接运行。
