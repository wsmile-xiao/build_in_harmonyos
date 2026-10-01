# isight-firmware-tools 1.6-4.3 适配笔记

## 上游构成

`isight-firmware-tools_1.6.orig.tar.gz` 是 autotools 工程（自带 `configure`、
`Makefile.in`、`config.h.in`），包含三个用户态程序：

| 文件 | 程序 | 说明 |
|---|---|---|
| `src/extract.c` | `ift-extract` | 从 AppleUSBVideoSupport 驱动文件里定位并提取 iSight 固件 |
| `src/export.c`  | `ift-export`  | 把提取出的固件转成 Intel HEX |
| `src/udev.c` + `src/load.c` | `ift-load` | 通过 USB（libusb-compat/usb.h）把固件上传到摄像头 |

`tests/Makefile.am` 只定义一个 `tests` 目标，循环遍历
`AppleUSBVideoSupport*` 驱动文件——该文件不随包发布、且需要真实 iSight 硬件，
**没有可运行的上游用例（上游 N=0）**。

## 构建

- 上游 2012 年的 `configure`/`config.sub` 不认 aarch64/HarmonyOS，且 configure
  阶段需要 intltool/gettext 引导链。为绕开整条链，配方按 sxid / libblocksruntime
  的既有做法**直接用 OHOS clang 编译三个程序**，并提供最小 `config.h`。
- 依赖与 configure 期 pkg-config 会找到的一致：`glib/2.84.0`、`libgcrypt/1.11.0`、
  `libusb-compat/0.1.7`（传递 `libgpg-error` / `libusb`）。
- **gettext-tiny/0.3.3 依赖**：glib 2.84 的 `<glib/gi18n.h>` **无条件**
  `#include <libintl.h>` 并把 `_()` 展开为 `gettext()`；而 OHOS sysroot 自带的
  `libintl.h` 只是一个 23 行的空壳（只定义了 `__USE_GNU_GETTEXT` 等宏，**没有
  `gettext` 声明**），因此直接编译会报 `call to undeclared function 'gettext'`
  与 `incompatible integer to pointer conversion`。制品仓已有的 `gettext-tiny/0.3.3`
  提供真正的 `libintl.h`（`gettext` 等展开为 identity 宏）+ 静态 `libintl.a`，
  加入依赖后编译与链接即通过。
- 链接器：显式加 `-L<dep>/lib` 与 `-l<lib>`，未依赖 Conan 的包名推导。

## 产物

| 路径 | 说明 |
|------|------|
| `bin/ift-extract` | 提取固件 |
| `bin/ift-export`  | 转 Intel HEX |
| `bin/ift-load`    | USB 上传固件 |
| `share/man/man1/ift-*.1` | 手册 |
| `share/doc/isight-firmware-tools/{README,NEWS,HOWTO}` | 文档 |

## 测试

上游无测试套件 → 上游 N=0（取数：
`grep -rlE 'check_PROGRAMS|TESTS' tests; ls tests` → 只有 `Makefile.am/.in`）。

`test_package/test_isight.sh` 共 **13 项断言**：

- `ift-extract --help` 退出 0 且打印 `Usage`；
- `ift-extract` 无 `-a` 退出 1 且提示 `Option -a is mandatory`；
- `ift-extract -a <缺失驱动>` 失败；
- `ift-export --help` 退出 0 且打印 `Usage`；
- `ift-export -i <缺失输入>` 失败；
- 对合成固件（`len=4`，请求地址 0x0000，数据 `ABCD`）做**真实 Intel HEX 转换**，
  校验数据记录 `:0400000041424344F2` 与 EOF 记录 `:00000001FF`；
- `ift-load --help` 退出 0；无固件时失败。

真机 `conan create`：`CREATE_RC=0`，消费者 13/13。
