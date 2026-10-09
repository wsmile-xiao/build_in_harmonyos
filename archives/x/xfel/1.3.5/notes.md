# xfel 1.3.5 适配笔记

## 编译环境
- 构建系统: makefile（上游只有 GNU Makefile，无 configure/CMake/meson）
- 编译日期: 2026-10-03
- 编译器: clang 15.0.4（target `aarch64-unknown-linux-ohos`）
- sysroot: `/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/sysroot`
- 依赖: libusb/1.0.27（Conan，动态链接）
- 状态: built

## 源码核验（R39 / W0）

| 项 | 值 |
|---|---|
| 上游仓库 | `https://github.com/xboot/xfel`（tag `v1.3.5`） |
| tarball | `https://github.com/xboot/xfel/archive/refs/tags/v1.3.5.tar.gz` |
| size | 726887 |
| sha256 | `2bdb9a7b80bdb699536afffb083524ad4efb7c738eb0dd9de03d2f2d00066fbb` |
| 二次核验 | 独立再下载一次，sha256 逐字节一致；且与 Debian 源包 `xfel_1.3.5.orig.tar.gz` 声明一致 |

依赖可消费性（W0，R35 用 `conan download` 不用 `conan list`）：

```
$ conan download libusb/1.0.27 -r=ohpcd
...
    libusb/1.0.27
      revisions
        0e6a7c47e7b3b5c19d0bdb3887145a1e (2026-08-04 07:49:04 UTC)
rc=0
```
recipe 级 rc=0 + 二进制级 rc=0（OHOS/6.0/armv8/clang15/libc++/cppstd17）。传递依赖：无。

## 上游测试入口清点（R51）

**上游没有自动化测试套件**，清点证据：

| 检查项 | 命令 | 结果 |
|---|---|---|
| tests/ 或 test/ 目录 | `ls -d tests test` | 不存在 |
| 测试命名文件 | `find . -iname "*test*"` | 0 个 |
| CMake/ctest | `find . -iname CMakeLists.txt -o -iname '*.cmake'` | 0 个 |
| Makefile 测试目标 | `grep -niE '^[a-z_-]*(test\|check)[a-z_-]*:' Makefile` | 无（仅 all/install/uninstall/clean） |
| CI 配置 | `.github/`、`*.yml`、`.travis*` | 不存在 |
| shell 脚本 | `find . -name '*.sh'` | 0 个 |
| 上游文档 | `docs/README.md` "Build from source" | 仅 `make` / `make install` |

唯一真实入口是 **CLI 本身**（`main.c:main()` → `usage()`）。上游未提供任何测试样例
数据（`payloads/` 是目标 SoC 固件，不进入宿主构建：`Makefile` 的 `SRCDIRS := . chips`）。
详见 `test_package/MANIFEST.yml` 与 `reports/upstream-tests.md`。

## 编译步骤

```bash
# 1) 下载 + 解压（init-build）
python3 scripts/ohc-run.py init-build xfel 1.3.5 \
  --url=https://github.com/xboot/xfel/archive/refs/tags/v1.3.5.tar.gz --tar=tar.gz --auto

# 2) 真实构建（Makefile 变量全部由 Conan 提供；GNU Make 命令行赋值覆盖 makefile 内的 :=）
make CC="<clang --target=aarch64-linux-ohos --sysroot=...>" \
     INCDIRS="-I. -I<libusb>/include/libusb-1.0" \
     LIBS="-L<libusb>/lib -lusb-1.0 -Wl,-rpath,<libusb>/lib" -j1
```

说明：`CFLAGS` **未覆盖**，沿用上游默认 `-g -ggdb -Wall -O3`。
`AS`/`LD`/`AR`/`OC`/`OD` 未被使用（`.` 与 `chips` 下无 `.S`；`SRCDIRS` 不含 `payloads/`）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 裸 `make` 失败：`/bin/sh: gcc: inaccessible or not found`，`make: *** [Makefile:63: ecdsa256.o] Error 127`；同时 `Package libusb-1.0 was not found in the pkg-config search path` | `Makefile` 把工具链硬编码为 `CC := $(CROSS)gcc`（OHOS 无 gcc，`which gcc` 不存在）；libusb 由 Conan 提供，不在系统 pkg-config 搜索路径 | 命令行覆盖 `CC`（GNU Make 命令行变量优先级高于 makefile 内的 `:=`），并用 `INCDIRS`/`LIBS` 直接指向 libusb 包，绕开 pkg-config |
| 2 | `libusb-1.0.pc` 内置 `prefix=/usr/local`（非可重定位）：裸 `pkg-config --cflags libusb-1.0` 返回 `-I/usr/local/include/libusb-1.0`（错误路径） | 上游 .pc 用绝对 prefix | 不依赖 pkg-config，配方直接传 `-I<libusb>/include/libusb-1.0`（配方内以 `cpp_info.includedirs[0]` 定位） |
| 3 | **所有设备类子命令 SIGSEGV（rc=139）**：`xfel version` 等 24 条入口全部段错误、无任何输出 | `main.c` 调用 `libusb_init()` 后**不检查返回值**，随后把可能为 NULL 的 context 交给 `libusb_get_device_list()`。OHOS 受限 `/dev/bus` 下 `libusb_init()` 返回 -1（详见下方 libusb 调试日志） | 补丁 `patches/0001-main.c.patch`：检查 `libusb_init()` 返回值，失败时打印 `ERROR: Can't initialize libusb` 并退出；24 条入口由 SIGSEGV(139) 变为可预期的 rc=255 |
| 4 | 上游 `make install` 硬编码 `/usr/local/bin`、`/etc/udev/rules.d/`、`/usr/share/licenses/`（OHOS 无 udev，且会污染构建机） | 上游 install 目标无 DESTDIR/PREFIX | 配方不使用 `make install`，由 `package()` 把 `xfel`→`bin/`、`99-xfel.rules`→`share/xfel/`、`LICENSE`→`licenses/` |

### 问题 3 的根因证据（libusb 调试日志）

```
$ LIBUSB_DEBUG=4 ./probe2
[libusb: debug] [get_kernel_version] HongMeng/OHOS kernel detected (HongMeng Kernel 1.12.0), assuming modern Linux kernel
[libusb: debug] [op_init] found usbfs at /dev/bus/usb
[libusb: debug] [op_init] sysfs is available
[libusb: error] [sysfs_get_device_list] opendir devices failed, errno=13
libusb_init r=-1 ctx=0
```

即 `libusb_init()` 因 `sysfs_get_device_list` 打不开 `/sys/bus/usb/devices`（errno=13
EACCES，沙箱无 USB 访问权限）而返回 -1。**值得注意的是 libusb 1.0.27 本身已识别
HongMeng/OHOS 内核**，失败原因是环境权限而非内核不识别。

## 源码修改

`patches/0001-main.c.patch`（+5/-1，唯一补丁）：

```diff
 	libusb_device ** list = NULL;
 	libusb_context * context = NULL;
-	libusb_init(&context);
+	if(libusb_init(&context) != 0)
+	{
+		printf("ERROR: Can't initialize libusb\r\n");
+		return -1;
+	}
 	int count = libusb_get_device_list(context, &list);
```

无平台宏守卫（R8）：这是通用健壮性修复——任何平台上 `libusb_init()` 失败时，
上游都会崩溃，补丁使其退化为可预期的错误退出。

## 依赖版本

| 依赖 | 版本 | 类型 | 说明 |
|------|------|------|------|
| libusb | 1.0.27 | 强制第三方 | 动态链接（OHOS 无系统同名库，R26 不适用）；`-Wl,-rpath` 固定搜索路径 |

## 验证结果

```bash
# 真实 conan create（见 reports/ 与 .ci-result.json）
conan create archives/x/xfel/1.3.5 -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
```

- 构建：`make rc=0`（1 个上游既有无害告警：`chips/a537_a333.c:28 unused function 'payload_write32'`）
- 上游 CLI 入口矩阵：**27/27**（usage 3 条 rc=0；设备类 24 条 rc=255 且不崩溃）
- test_package：**9/9**（含 5 项鸿蒙特有断言）
- ELF 属性：AArch64 / PIE / full RELRO / NX stack / interpreter `/lib/ld-musl-aarch64.so.1`
- 运行期依赖：仅 `libusb-1.0.so.0` + `libc.so`

## 交付物

| 文件 | 大小（约） | 说明 |
|------|------|------|
| `bin/xfel` | 见 conan create 日志 | 命令行工具（AArch64 OHOS ELF） |
| `share/xfel/99-xfel.rules` | 352 B | 上游 udev 规则（留档） |
| `licenses/LICENSE` | 1091 B | MIT |

## 注意事项

- xfel 是**真实 USB 硬件工具**：所有设备类子命令需要 FEL 设备（USB `1f3a:efe8`）与
  `/dev/bus/usb` 访问权限（root/udev 规则）。容器、CI 与无 USB 权限的环境下设备功能
  不可验证——本适配能验证的是「产物在 OHOS 上可加载、可执行、入口行为符合预期、不再崩溃」。
- `/etc/udev/rules.d/99-xfel.rules` 在 OHOS 上无对应机制，随包放 `share/xfel/` 供需要时手工取用。
---

**编译结束**: 2026-10-03 13:12
**最终状态**: built
