# libcapi20 3.27 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-09-15
- 编译器: clang (HarmonyOS PC aarch64 toolchain, /data/service/hnp/bin)
- Shell: `CONFIG_SHELL=bash`（HiShell/`/bin/sh` 不足以跑 configure 的 `print` 探测与 libtool 阶段）
- 状态: built

## 编译步骤

Conan 驱动（模式 A：`conan create` 单命令完成），关键点：

1. `source()`：下载 Debian 官方源 `libcapi20-3_3.27.orig.tar.bz2`（GitHub 直连在当前网络不可达），sha256 校验。
2. `configure()`：AutotoolsToolchain 仅注入 `--prefix`（R1 参数最少化），额外注入 `CONFIG_SHELL=bash` 与 `extra_cflags`。
3. `build()`：`autotools.make()`——上游插件模块使用 `-module -no-undefined`，必须以共享库方式链接，故配方保持上游默认（shared+static），不对本包强制静态（R26 只针对系统同名库）。
4. `package()`：`autotools.install()`，安装 `libcapi20.so.3`、`lib/capi/*.so` 插件与头文件。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | configure 早期失败，`config.status` 临时目录不可写 | configure 用 `(umask 077 && mktemp -d ...)` 建探测目录；HMDFS 忽略 chmod/umask，目录权限固定，探测目录随即不可写（E114/E118 同类） | 补丁 `0001`：`umask 077` → `umask 022` |
| 2 | `convert.c:15 #include <byteswap.h>` 经 `compat/byteswap.h` 引到 glibc 专属头 | `compat/byteswap.h` 依赖 glibc `<features.h>` + `<bits/byteswap.h>`，HarmonyOS 无 glibc 头 | 补丁 `0002`：改为自带可移植实现（保留原有 `bswap_16/32/64` 接口） |
| 3 | 链接阶段 `-module -no-undefined` 报未定义符号 | 插件模块必须链接为共享库，而本包曾禁用 shared | 配方回归上游默认 shared+static，由 `library` 类型声明 `shared` 选项 |
| 4 | 库名不匹配（配方写 `libcapi20`，产物为 `libcapi20.so`= `-lcapi20`） | 上游 `lib_LTLIBRARIES = libcapi20.la` 的实际输出名为 `capi20` | `cpp_info.libs = ["capi20"]` |
| 5 | 包内插件无法被定位（运行时加载失败） | 加载代码用编译期绝对 `LIBDIR`，包被安装到任意 prefix 后该路径不存在 | 补丁 `0003`：支持 `CAPI20_MODULE_DIR` 覆盖，并在 `package_info().runenv_info` 导出 `<pkg>/lib/capi` |

## 源码修改

- `patches/0001-configure-hmdfs-umask.patch`：configure 的 `umask 077` → `022`（HMDFS 权限限制）。
- `patches/0002-compat-byteswap-portable.patch`：`compat/byteswap.h` 改为自包含可移植实现（去 glibc 依赖）。
- `patches/0003-runtime-module-dir-override.patch`：`capi20.c` 模块目录支持 `CAPI20_MODULE_DIR` 环境变量覆盖编译期 `LIBDIR`。

> 补丁均不属于「平台宏」范畴（未引入 `__OHOS__`），是纯可移植性修复，符合 R8。

## 依赖版本

无依赖（`requirements()` 为空；上游无第三方库依赖）。

## 验证结果

```bash
# 配方验证（G1-G4 + L2/L4/L5）：全部通过
conan create . -pr:a ci/conan/profiles/ohos-aarch64

# 消费方测试（test_package，上游无测试，全部为新增）
test_libcapi20      : assertions: 17/17 passed   # CAPI 2.0 编解码 + 库状态访问器
test_libcapi20_ohos : assertions: 4/4 passed     # 鸿蒙平台特有：模块目录重定位 + 插件 dlopen
```

上游测试套件：**无**（`Makefile.am` 无 `TESTS`，发布包内无任何测试源码/脚本），故无上游用例可执行，全部用例均为本次适配新增。
---

**编译结束**: 2026-09-16 00:17
**最终状态**: built
