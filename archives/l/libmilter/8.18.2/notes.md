# libmilter 8.18.2 适配笔记

## 编译环境
- 构建系统: sendmail Build (非 autotools)
- 编译日期: 2026-05-28
- 编译器: clang/clang++
- 平台: HarmonyOS HongMengKernel 1.12.0 aarch64
- 状态: published

## 编译步骤

sendmail 项目使用自定义 Build 系统，不是标准的 autotools。

### 1. 配置平台支持
创建 `devtools/OS/HarmonyOS` 配置文件，基于 Linux 配置：
- 定义平台特定的编译选项
- 添加 `HASSTRERROR` 和 `ERRLIST_PREDEFINED` 宏（musl libc 兼容）

### 2. 编译
```bash
cd libmilter
./Build
```

Build 脚本会自动：
- 检测平台（基于 devtools/OS 目录）
- 生成 Makefile
- 编译生成 libmilter.a 静态库

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | musl sys_errlist 兼容性 | musl libc 不提供 sys_errlist/sys_nerr | 修改 libsm/strerror.c，添加 __OHOS__/__MUSL__ 守卫，使用标准 strerror() |
| 2 | 静态库签名 | 静态库是 ar 格式，非 ELF | 无需签名，仅动态库和可执行文件需要 ELF 签名 |

## 源码修改

### 补丁 1: devtools/OS/HarmonyOS
- 类型: 平台配置
- 守卫: 无（平台识别文件）
- 内容: 定义 HarmonyOS 平台的编译选项和宏

### 补丁 2: libsm/strerror.c
- 类型: musl 兼容性修复
- 守卫: `#if defined(__OHOS__) || defined(__MUSL__)`
- 内容: 使用标准 strerror() 函数替代 sys_errlist 数组访问

## 依赖版本

- 无外部依赖（libmilter 是独立的静态库）

## 验证结果

```bash
# 检查静态库
ar -t libmilter.a
# 输出: main.o engine.o listener.o worker.o handler.o comm.o smfi.o signal.o sm_gethost.o monitor.o errstring.o strl.o

# 验证头文件
ls include/libmilter/
# 输出: libmilter.h mfapi.h mfdef.h milter.h
```

## 上游测试说明（R28 常规做法）

libmilter **无独立上游测试套件**：sendmail 源码树中 `libmilter/` 目录只包含库源文件
（main.c engine.c listener.c worker.c handler.c comm.c smfi.c signal.c sm_gethost.c monitor.c
+ LIBMILTER_EXTRAS: errstring.c strl.c）、docs/、example.c（示例过滤器，非测试），
没有 tests/ 目录，也没有针对 libmilter 的 make check 目标（树顶层 `make check` 只覆盖
sendmail 主程序）。

处理方式：按 R28/R34 惯例，由 `test_package/` 补全 API 冒烟验证——
`smfi_version`（运行时版本校验 1.0.x + MI_SUCCESS）、`smfi_settimeout/setbacklog/setdbg`、
`smfi_register`（注册完整 smfiDesc 过滤器）、`smfi_setconn + smfi_opensocket`
（在 TMPDIR 下真实 AF_UNIX socket bind+listen，非空壳调用）。

## R38 判断依据（纯静态库，无需 commands.json）

libmilter 8.18.2 的构建产物只有 `libmilter.a`（ar 归档静态库）+ 3 个头文件
（mfapi.h mfdef.h milter.h）。sendmail Build 系统对 libmilter 子目录只生成 library 产品
（Makefile.m4: `bldPRODUCT_START('library', 'libmilter')`），无任何可执行文件安装目标。
conanfile.py `package_type = "static-library"`，`package()` 只拷贝 lib/ 与 include/，
不涉及 bindirs/bin/。依据 R38（"库类型不需要 commands.json"），**不需要 commands.json**。
CI 门禁 L0k 的判定条件（bindirs / RUNTIME DESTINATION bin / package_type="application"）
均不命中。

## 适配后 conan 配方要点（2026-09-01 补全）

- 源码 URL：官方源仅 ftp 可达（https 404），conan 2.x 的 requests 下载器不支持 ftp://
  协议（"No connection adapters were found"），故 conandata.yml 采用
  mirrorservice.org（UK Mirror Service，ftp.sendmail.org 官方权威镜像）https URL，
  实测与官方 ftp 包 sha256 字节一致。
- 编译器注入（R33）：通过 `devtools/Site/site.config.m4`（generate() 中动态生成）
  `define(confCC, clang)` 注入 profile 的 `tools.build:compiler_executables` 指定的
  编译器，禁止裸用 ${CC} 环境变量。sendmail Build 默认 confCC=cc（OHOS 无 cc），
  实测必须显式覆盖，`APPENDDEF` 会拼接出 `cc clang` 导致失败，必须用 `define` 整体覆盖。
- 平台检测：Build 脚本用 uname 检测平台（HarmonyOS → devtools/OS/HarmonyOS 配置，
  由补丁 0001 提供）。
- 测试注意：OHOS 沙箱内 AF_UNIX socket bind 仅在部分沙箱目录
  （/data/storage/el2/base/temp 等）允许；用户数据目录 bind 返回 EPERM、
  /tmp 只读，且 CI Worker 的 TMPDIR（$HOME/.cache/tmp）可写但禁止 socket bind。
  test_package 用 pick_writable_socket_dir() 在运行时对候选目录
  （$TMPDIR、/data/storage/el2/base/temp、/data/storage/el2/base/cache、/dev/shm、/tmp）
  逐个真实 bind 探测取第一个可用目录；全部失败时按平台限制 SKIP（E046/E051 同类先例），
  不判 FAIL（CI #36525 修复）。

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| libmilter-8.18.2-ohos-aarch64.tar.gz | 10KB | 预编译包（静态库 + 头文件） |
| libmilter.a | 78KB | 静态库 |
| libmilter.h, mfapi.h, mfdef.h, milter.h | - | 头文件 |

## 注意事项

1. **构建系统**: sendmail 使用 Build 系统，不是 autotools，无需 configure 步骤
2. **静态库**: libmilter 编译为静态库（libmilter.a），不是动态库
3. **签名**: 静态库无需 ELF 签名，仅动态库和可执行文件需要
4. **补丁**: 只修改源文件（devtools/OS 和 libsm/），不修改生成文件（obj 目录）
---

**编译结束**: 2026-09-02 03:56
**最终状态**: published
