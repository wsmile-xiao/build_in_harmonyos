# libideviceactivation

`libideviceactivation` 是 libimobiledevice 生态中的**iOS 设备激活/去激活**库与工具：
它把 Apple 激活服务（buddyML / HTML / plist 三种响应形态）的交互流程封装成
`libideviceactivation-1.0` 库，并提供命令行工具 `ideviceactivation`
（`activate` / `deactivate` / `state` 三个子命令）。

上游：<https://github.com/libimobiledevice/libideviceactivation>
官网：<https://libimobiledevice.org/>

## 功能概述

- 通过 `lockdownd` / `mobileactivation` 与 iOS 设备建立激活会话
- 解析 Apple 激活服务的三种响应：buddyML（XML/XPath）、HTML 表单、plist
- 支持 DRM handshake 会话模式（`drmHandshake`）与现代设备激活流程
- 提供 `--network` / `--version` / `--batch` / `--service` 等命令行能力

## OHOS 适配

适配方式为**构建期 shim**，不修改上游源码（`patches: []`）：

| # | 现象（真实报错） | 根因 | 处置 |
|---|---|---|---|
| 1 | `configure: error: cannot guess build type`（`./config.guess` rc=1，`unable to guess system type`） | 上游 `config.guess` 时间戳 2018-03-08，不认识 `uname -s = HarmonyOS` / `HongMeng Kernel` | `AutotoolsToolchain` 显式追加 `--build=aarch64-unknown-linux-gnu`（本机构建与 CI worker 均为 OHOS aarch64，属原生构建，不传 `--host`/`--target`；上游 `config.sub` 亦不识别 `ohos` 三元组） |
| 2 | `./config.status: line 878: ./confXXXXXX/subs1.awk: Permission denied` → `could not setup config files machinery` | HMDFS 上 `umask 077 && mktemp -d` 生成 **mode 2700 (`drwx--S---`)** 目录，**属主也不可写**；而 `umask 077 && mkdir` 被 HMDFS 归一为 mode 2771 (`drwxrws--x`)，可写 | `generate()` 注入一个恒定 `exit 1` 的 `mktemp` wrapper 并前置 `PATH`，迫使 autoconf/config.status 走 `(umask 077 && mkdir)` 回退分支（同族 libplist / libusbmuxd / libimobiledevice-glue 同一做法） |
| 3 | `libtool: error: '//lib/libplist-2.0.la' is not a valid libtool archive` | 依赖包以 `--prefix=/` 发布，`.la` 内 `libdir='//lib'`、`dependency_libs` 含构建机绝对路径；本库用 libtool 构建，链接时优先解析 `.la` | `build()` 开头把各依赖 `lib/*.la` 改名 `*.la.bak`，使 libtool 回退到 `-L<dir> -l<name>`（同族 ideviceinstaller/1.2.0 先例） |

已知差异 / 注意事项：

- 上游零自动化测试（无 `tests/`、无 `TESTS`/`check_PROGRAMS` 注册），`make check` 为 automake 空操作；
- CLI 的三个子命令均需要真实 iOS 设备 + `usbmuxd`，无设备时统一返回 `ERROR: No device found!`（rc=1）；
- `libxml2` 的 SONAME 为 `libxml2.so.16`，与 OHOS SDK 工具链自带的
  `native/llvm/lib/libxml2.so.16`（libxml2 2.14.0）**同名**——运行期依赖搜索顺序
  必须让 Conan 包的 `lib/` 目录优先（本包 test_package 的 `ohos_runtime_closure`
  用例专门校验这一点）。

## 依赖关系

编译期强制第三方依赖（上游 `configure.ac` 的四个 `PKG_CHECK_MODULES`，均无 fallback）：

| 依赖 | 版本 | pkg-config 名 | 上游约束 |
|---|---|---|---|
| libimobiledevice | 1.3.0 | `libimobiledevice-1.0` | `>= 1.3.0` |
| libplist | 2.3.0 | `libplist-2.0` | `>= 2.2.0` |
| libcurl | 8.5.0 | `libcurl` | `>= 7.20` |
| libxml2 | 2.15.3.1 | `libxml-2.0` | `>= 2.9` |

传递依赖：`libusbmuxd/2.0.2`、`openssl/1.1.1w`（经 libimobiledevice）、`zlib/1.3.1.1`（经 libcurl）。
系统库：`libc` / `libpthread`（`AX_PTHREAD`，clang 分支 `-pthread`）/ `libdl` / `libm`。

运行期：`ideviceactivation` 依赖 `libcurl.so`、`libxml2.so.16`；库本体（默认静态）
不引入额外运行期依赖。

## 产物

- `lib/libideviceactivation-1.0.a`（默认 `shared=False`）+ `lib/pkgconfig/libideviceactivation-1.0.pc`
- `include/libideviceactivation.h`
- `bin/ideviceactivation`（命令行工具，见软件级 `commands.json`）
- `share/man/man1/ideviceactivation.1`

## 版本

| 版本 | 状态 | 说明 |
|---|---|---|
| 1.1.1 | built | 首次 OHOS 适配（Autotools + 三处构建期 shim，无源码补丁） |
