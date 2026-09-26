# orbuculum 2.2.0 — HarmonyOS PC (aarch64) 适配笔记

## 0. 上游与任务

| 项 | 值 |
|----|----|
| 软件 | orbuculum |
| 版本 | 2.2.0（tag `V2.2.0`，commit `21285f8`） |
| 上游 | https://github.com/orbcode/orbuculum |
| 语言 / 构建 | C / meson（`meson_version >= 0.63`） |
| 产物 | `liborb.so` + 11 个命令行工具 |
| 源码 sha256 | `6614fba7044aa62e486b29ff4a81d0408d6e88499249bf2b839ccadfc54eec83` |

功能：从 ARM Cortex-M 目标（orbtrace/BMP 探针、TTL 串口、文件/套接字流）采集
SWO/SWV（ITM）追踪数据，并提供后处理工具链：

`orbuculum`（采集）、`orbfifo`、`orbcat`、`orbtop`、`orbdump`、`orbstat`、
`orbmortem`（崩溃现场/源码级回溯）、`orbprofile`、`orbtrace`、`orbzmq`、`orblcd`。

## 1. 源码可达性先验（开工第一步）

`codeload.github.com/orbcode/orbuculum/tar.gz/refs/tags/V2.2.0` 返回 200（17.2 MB）。
双源核对 sha256 一致：

- 源 1：`https://codeload.github.com/orbcode/orbuculum/tar.gz/refs/tags/V2.2.0`
- 源 2：github 官方 archive 的代理镜像（同一 URL 路径）

> 注意：`api.github.com/repos/orbcode/orbuculum/tarball/V2.2.0` 的顶层目录名是
> `orbcode-orbuculum-<sha>/`（而非 `orbuculum-2.2.0/`），字节不同，不能用来比 hash。
> 仓内约定用 `archive/refs/tags/<tag>.tar.gz` 这条官方源。

## 2. 依赖矩阵（W0 预检全部命中 ohpcd）

上游 `meson.build` 的依赖 → ohpcd 制品：

| meson 依赖 | Conan 包 | 生成 .pc 名 | 备注 |
|-----------|----------|------------|------|
| `threads` | 内置 | — | `-pthread` |
| `libusb-1.0` | `libusb/1.0.27` | `libusb-1.0.pc` | 仅暴露 `include/libusb-1.0` |
| `libzmq` | `libzmq/4.3.5` | `libzmq.pc` | |
| `ncurses` / `ncursesw` | `ncurses/6.6` | `ncursesw.pc` | 默认即静态（`.a`），符合 R26 |
| `libelf` | `libelf/0.8.13.1` | `libelf.pc` | |
| `libdwarf`（subproject） | `libdwarf/0.11.1` | `libdwarf.pc` | 关键：见 §3 |
| `capstone`（可选，代码里是硬依赖） | `capstone/5.0.7` | `capstone.pc` | `loadelf.c` 无条件使用 `cs_*` |
| `SDL2`（可选） | `sdl2/2.32.10` | `sdl2.pc` | 上游问的是 `SDL2`，见 §4 |

`libdwarf/0.11.1` 传递依赖 `zlib/1.3.1`、`zstd/1.5.6`，自动进入 `.pc` 的 `Requires`。

## 3. 关键点一：把 meson wrap subproject 换成 Conan 依赖

上游 `meson.build`：

```meson
libdwarf = subproject('libdwarf').get_variable('libdwarf')
```

`subprojects/libdwarf.wrap` 指向 `https://www.prevanders.net/libdwarf-0.7.0.tar.xz`，
即 **configure 期联网下载**。CI 的预下载机制只覆盖 `conandata.yml` 里的源码 URL，
不覆盖 meson wrap；且 0.7.0 与制品仓的 0.11.1 版本不一致。

做法（补丁 0001）：

```meson
libdwarf = dependency('libdwarf')
```

配合 recipe 的 `PkgConfigDeps(self).generate()`：它为每个依赖在 generators 目录生成
`.pc`，而 `MesonToolchain` 生成的 `conan_meson_native.ini` 里
`pkg_config_path` 默认就指向该目录 → `dependency('libdwarf')` 直接命中，完全离线。

> 好消息：ohpcd 的 libdwarf 0.11.1 **头文件仍保留旧 API 名**
> （`dwarf_attrlist` / `dwarf_whatattr` / `dwarf_get_AT_name(u,&name)` 等），
> 因此 `Src/loadelf.c` 无需为 API 漂移做任何改动。

## 4. 关键点二：HMDFS 大小写不敏感击碎了 SDL2.pc 别名方案

上游问 `dependency('SDL2')`，而 Conan 的 sdl2 包生成的是 `sdl2.pc`。
最初打算在 generators 目录写一个 `SDL2.pc` 别名（`Requires: sdl2`），**失败**：

> OHOS/HMDFS 文件系统大小写不敏感（`git config core.ignorecase=true`），
> 写 `SDL2.pc` 实际覆盖了 `sdl2.pc` → 别名自我引用（`Requires: sdl2` 解析到自己），
> pkg-config 返回"找到但零 flags" → `orblcd.c` 报 `SDL.h` not found。

最终做法（补丁 0001 内一行）：

```meson
libSDL2 = dependency('sdl2', 'SDL2', required: false)
```

meson 支持多名字回退，`sdl2` 是 Linux/OHOS 发行版与 Conan 包的正规模块名，
保留 `SDL2` 兼容 Windows/macOS 布局。**不要在大小写不敏感的文件系统上做纯大小写别名。**

## 5. 关键点三：OHOS 的 linux uapi 头

| 上游写法 | 问题 | 适配 |
|---------|------|------|
| `Src/nwclient.c`: `#include <linux/tcp.h>` | OHOS sysroot 无该文件；其引入的 `linux/socket.h` 与 `sys/socket.h` 重复定义 `struct sockaddr_storage` | 直接删除（全文无 `TCP_*` 符号使用） |
| `Src/orbuculum.c`: `#include <asm/ioctls.h>` / `<asm/termios.h>` | OHOS 无 `asm/` 下的这两个头 | 改用 `asm-generic/ioctls.h` / `asm-generic/termbits.h`（OHOS 与 glibc 均具备，`TCGETS2`/`struct termios2`/`BOTHER`/`CBAUD` 同源，termios2 自定义波特率路径保持可用） |

验证：`clang -c` 小样确认 OHOS 上 `sys/ioctl.h`+`termios.h` 不定义 `TCGETS2`，
而 `asm-generic/ioctls.h`+`asm-generic/termbits.h` 可用。

## 6. 关键点四：包含路径与符号冲突

- `Inc/orbtraceIf.h`：`#include <libusb-1.0/libusb.h>` → `<libusb.h>`。
  理由：Conan 的 libusb 包 pkg-config 只给 `-I<prefix>/include/libusb-1.0`，
  `libusb-1.0/libusb.h` 这种写法依赖系统 include 根；上游 OSX/FreeBSD/Win32 三个分支
  本来就用 `<libusb.h>`，此举是把 LINUX 分支对齐。
- `Inc/loadelf.h`：`#include <capstone.h>` → `<capstone/capstone.h>`（官方推荐写法，
  系统安装与 Conan 包布局都能命中）。
- `Src/loadelf.c`：删除未被引用的 `_dwarf_error()`。
  libdwarf 0.11.1 静态库（`libdwarf.a`）自带内部符号 `_dwarf_error`，
  静态链接时 `ld.lld` 报 `duplicate symbol: _dwarf_error`。
  该函数在 orbuculum 全树无任何调用点（仅定义），属死代码，删除即可（未使用 `--allow-multiple-definition` 之类的掩盖手段）。

## 7. 上游测试

`Tests/test_cobs.c` 是唯一的测试文件，但**相对当前 `cobs.h` 已陈旧**，clang 15 直接编译不过：

1. `int main( int argc, void **argv )` → 非法原型（第二参必须是 `char **`）；
2. `COBSEncode(NULL, 0, buf, len, &out)` 是 5 参旧签名，当前原型是 7 参
   `(front, lfront, back, lback, input, linput, out)`（两处调用点）。

补丁 0007 做最小现代化修复（`COBSEncode(NULL, 0, NULL, 0, buf, len, &out)`），
随后实测：**33 个 OK / 0 个 FAILED**（11 组向量 × 简单解码 / 流式解码 / 编码），
外加 10000 次随机编解码往返压力无输出异常。

> 测试程序 `main` 恒返回 0，因此 pass/fail 只能从输出判断（出现 `FAILED` 即失败）。
> 上游 `meson.build` 没有 `test()` 目标，所以 recipe 在 `build()` 里显式编译执行
> （`upstream_test_in_build: true`）——这样 CI 每次构建都会真实跑一遍上游测试。

## 8. 消费者测试

`test_package/`（2 个测试）：

- `test_orb.c`（CMake + CMakeDeps，链接已安装的 `liborb`）：**8 项断言**
  —— COBS 编码增长、`COBSgetFrameExtent` 一致性、`COBSSimpleDecode` 往返、
  0x00-free 载荷往返、`COBSInit/COBSPump/COBSGetErrors/COBSDelete` 流式解码。
- `test.sh`（conanrun 环境）：11 个工具均已安装，10 个工具 `-V` 输出含 `2.2.0`
  （`orbprofile` 是上游"开发预览"版，无版本开关）。

## 9. 统计口径

| | 上游 | 适配后 |
|---|------|--------|
| 单元测试 | 33 | 33（不变） |
| 集成测试 | 0 | 0 |
| 其他测试（随机压力） | 1 | 1 |
| 鸿蒙特有 | — | 0（补丁均为可移植修复，未引入平台宏/鸿蒙专属分支） |
| PC 特有 | — | 11（CLI 工具在 OHOS PC 上可执行） |
| 消费者用例 | — | 8（liborb COBS API 断言） |
| 消费者测试 | — | 2 个测试文件 |
| **合计** | **34** | **53** |

## 10. 已知限制

- `orbprofile` 是上游的开发预览工具（自述"This utility is in development"），未提供版本开关。
- 采集类工具（`orbuculum`/`orbtrace`）需要真实 orbtrace/BMP 硬件与 USB 访问权限；
  PC 上的行为取决于 libusb 能否枚举到设备（无设备时打印 "No devices found"）。
- `orblcd` 依赖 SDL2 视频输出，无显示环境下只能验证到二进制可运行/版本打印。
- 上游 `Support/60-orbcode.rules`（udev 规则）与 `gdbtrace.init` 照原样安装到
  `lib/udev/rules.d`、`share/orbcode`，未做 OHOS 特化。
