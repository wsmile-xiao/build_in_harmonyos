# libmbim-tools 1.34.0 适配笔记

## 编译环境

- 构建系统: **meson**（不是 autotools；dispatch 元数据里的 "autotools" 是错的）
- 编译日期: 2026-09-24
- 编译器: clang / clang++ 15.0.4（经 profile `tools.build:compiler_executables` 注入）
- 状态: built
- Conan: 2.29.1（OHOS 适配版），profile `ci/conan/profiles/ohos-aarch64`（os=OHOS, os.version=6.0, armv8, clang 15, libc++）

## 包定位（同名工具包 same-source tools-only）

上游 **libmbim 不是独立 "tools" 项目**：freedesktop libmbim 源码树同时构建 GLib 库
（libmbim-glib）**和**面向用户的命令行工具（mbimcli、mbim-proxy、mbim-network）。
本包 `libmbim-tools` `package_type="application"` 只交付工具，打包时删除
lib/include/share/libexec（先例：`libimobiledevice-progs/1.4.0`、
`libcpuid-tool 0.8.0` 同款 same-source tools-only 模式）。

- `mbimcli`（bin/，meson 安装到 bindir）
- `mbim-network`（bin/，meson 生成的 /bin/sh 脚本）
- `mbim-proxy`（上游装到 libexec/；本包移动到 bin/ —— 无库交付，代理以独立工具形态提供）

工具以 `-Ddefault_library=static` **静态链入 libmbim-glib**，交付的 bin/ 自含，
不依赖被丢弃的 lib/ 目录。glib 为 Conan 动态依赖，运行需 conanrun env 提供
LD_LIBRARY_PATH（libimobiledevice-progs 同款）。

> 说明：`freedesktop GitLab 无 libmbim-tools 项目`；`search-url` 返回的 savannah
> `libmbim-tools-1.34.0.tar.gz` 实测 404，为无效 URL。官方源 = libmbim 1.34.0：
> `https://gitlab.freedesktop.org/mobile-broadband/libmbim/-/archive/1.34.0/libmbim-1.34.0.tar.gz`
> （tag 1.34.0，2026-01-03；顶层目录 `libmbim-1.34.0/`；sha256
> `55bb88df358f8a36b6e01e63877500d7c6420f5907d2d3101812b4912eabe08f`）。

## 编译步骤

```bash
cd archives/l/libmbim-tools/1.34.0
conan create . \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
```

配方要点：
- `requirements()`: `glib/2.84.0.1`（提供 glib-2.0 / gio-2.0 / gio-unix-2.0 / gobject-2.0）
- `build_requirements()`: `tool_requires("meson/1.11.0")`（worker PATH 无 meson；制品仓有该工具包二进制）
- meson 选项：`-Dbash_completion=false -Dintrospection=false -Dman=false -Dgtk_doc=false -Dfuzzer=false -Ddefault_library=static -Dwrap_mode=nodownload`
- `build()`: `apply_conandata_patches()` → `meson configure` → `meson build` → `meson test`（上游 9 项）
- `package()`: `meson install` → 移动 libexec/mbim-proxy → bin/ → 删除 lib/include/share/libexec → **ELF 签名**
- `package_info()`: `bindirs=["bin"]`，libs/includedirs/libdirs 清空

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 编译 `src/libmbim-glib/{mbim-helpers-netlink,mbim-net-port-manager*.c}` 报 `redefinition of 'sockaddr_storage'`（E091） | OHOS 内核 UAPI `<linux/socket.h>`（经 `<linux/netlink.h>` 间接包含）与 musl libc `<sys/socket.h>` 都定义 `struct sockaddr_storage`；这两个文件先包含 linux 头（netlink.h→socket.h）后包含 sys/socket.h，两个定义同时可见 → 冲突（本机已用 `clang -xc` 最小复现证实） | 4 个补丁：在包含 3 个 linux 头之前 `#define sockaddr_storage __linux_uapi_sockaddr_storage`，包含后立即 `#undef`。libmbim 不使用 UAPI 的 sockaddr_storage，重命名只在内核头处理期间生效 → 通用、**不使用平台宏**（`__OHOS__`），在 glibc/其他平台亦无害 |
| 2 | test_package 执行 `mbimcli` 报 `Operation not permitted`（exit 126） | OHOS PC 拒绝执行未签名 ELF | `package()` 内对 bin/ 下所有 ELF 调 `binary-sign-tool sign -selfSign 1`，并校验 `.codesign` section 数=1（922 个配方同款做法，见 accountsservice/abx） |
| 3 | `/system/bin/sh`(mksh) 不能 exec ELF，test.sh 无法直接调用工具 | OHOS 控制台 shell | test_package 经 bash（`CONFIG_SHELL`）包裹执行（模板 test_package-executable 同款） |
| 4 | meson 找不到 `dependency('gio-unix-2.0')`（潜在） | `PkgConfigDeps` 只产出 glib 配方声明的组件（无 gio-unix-2.0.pc），但 glib 包的 `lib/pkgconfig` 内有 gio-unix-2.0.pc | 把依赖包的 lib/pkgconfig + generators 目录写入 meson machine file 的 `pkg_config_path`，并注入 `PKG_CONFIG_PATH`（accountsservice 同款） |
| 5 | meson 缺 ar/ranlib/pkg-config | MesonToolchain 不一定写 `[binaries]` | `_inject_meson_tools()` 把 llvm-ar/llvm-ranlib/pkg-config 注入 conan_meson_native.ini |

## 源码修改

`patches/` 4 个补丁（strip 1），全部为 E091 sockaddr_storage 冲突的通用修复：

1. `0001-src-libmbim-glib-mbim-helpers-netlink.c.patch`
2. `0002-src-libmbim-glib-mbim-net-port-manager-wdm.c.patch`
3. `0003-src-libmbim-glib-mbim-net-port-manager-wwan.c.patch`
4. `0004-src-libmbim-glib-mbim-net-port-manager.c.patch`

每个补丁：在 `#include <linux/if_link.h>` 前插入注释 + `#define sockaddr_storage
__linux_uapi_sockaddr_storage`，在 `#include <linux/rtnetlink.h>` 后插入 `#undef
sockaddr_storage`。补丁不含任何平台宏（`__OHOS__`），避免 R8/PF5 违规。

（调用点全集实核：`grep -rn "sockaddr_storage\|linux/netlink.h" src/` 仅上述 4 文件
包含 `<linux/netlink.h>`；其余文件不触发 E091。）

## 依赖版本

| 依赖 | 版本 | meson.build 要求 | 说明 |
|---|---|---|---|
| glib | 2.84.0.1 | glib-2.0 >= 2.56 | 同时提供 gio-2.0 / gobject-2.0 / gio-unix-2.0 |
| meson | 1.11.0 | >= 0.53.0 | tool_requires（构建工具） |

未使用的可选特性（全部关闭）：bash-completion、gobject-introspection、man(help2man)、
gtk-doc、fuzzer；`mbim_username`/`mbim_groupname` 留空 → 不需要 udev。

## 验证结果

```bash
# conan create（W3 本地 CI）成功；上游 meson 测试：9/9
meson test  ->  Ok: 9   Fail: 0
#   1/9 uuid · 2/9 cid · 3/9 message · 4/9 fragment · 5/9 message-fuzzer-samples
#   6/9 message-parser · 7/9 message-builder · 8/9 proxy-helpers · 9/9 quectel

# 产物：bin/{mbimcli,mbim-network,mbim-proxy}（3 个工具）；lib/include/share/libexec 已丢弃
#   mbimcli / mbim-proxy 已 ELF 签名（各含 1 个 .codesign section）

# test_package（conanrun env，经 bash）：
#   完整消费者用例（device-free 端到端）：mbimcli --printable 解码完整 MBIM_OPEN 报文  OK
#     -> Header: / length = 16 / type = open (0x00000001) / max control transfer = 4096
#   负向：非法报文（声明 length=4 < 最小 16）被拒绝（非零退出）                    OK
#   mbimcli --version    -> "mbimcli 1.34.0"        OK
#   mbimcli --help       -> usage                    OK
#   mbim-proxy --version -> "mbim-proxy 1.34.0"      OK
```

## 上游测试清点（R51 三步法）

- 清点：meson 注册测试单元 9 个 —— `src/libmbim-glib/test/meson.build` 8 个
  （uuid/cid/message/fragment/message-fuzzer-samples/message-parser/message-builder/
  proxy-helpers）+ `src/mbimcli/tests/meson.build` 1 个（quectel）。（`message-fuzzer`
  仅 `-Dfuzzer=true` 时注册，本包 fuzzer=false）
- 实跑：`build()` 内 `meson.test()` 真实执行，**9/9 通过（Ok: 9, Fail: 0）**。
- 回填：见 `test_package/MANIFEST.yml`（upstream_tests 9 项 + 计数）。

> 历史 `archives/l/libmbim/1.30.0`（库包）notes 记录的 meson 适配要点已比对：
> meson 构建系统、E091 sockaddr_storage、禁用 bash_completion/introspection/man
> 三条一致沿用；历史补丁用 `#ifdef __OHOS__` 平台宏，本包改用不含平台宏的通用
> 重命名方案（R8/PF5 要求 patches 默认禁平台宏）。

## 交付物

| 文件 | 说明 |
|------|------|
| `bin/mbimcli` | MBIM 命令行客户端（已签名） |
| `bin/mbim-proxy` | MBIM 代理守护（由 libexec 移入 bin/，已签名） |
| `bin/mbim-network` | MBIM 网络管理 shell 脚本 |
| `licenses/GPL-2.0-or-later.txt`、`licenses/LGPL-2.1-or-later.txt` | 许可证 |

## 注意事项

- 运行期需要 conanrun env（glib 共享库）；直接裸调 bin 下工具会报
  "Error loading shared library libglib-2.0.so.0"。
- 本包不含库产物（库由 `libmbim/1.30.0` 等库包承担）；如后续需要库包，另开 `libmbim` 版本。
- `mbimcli` 无设备时联网类子命令会失败，属正常（无设备），冒烟一律用 `--version`/`--help`。
---

**编译结束**: 2026-09-24 13:10
**最终状态**: built
