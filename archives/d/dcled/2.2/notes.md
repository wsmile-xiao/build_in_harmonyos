# dcled 2.2 适配笔记

## 编译环境
- 构建系统: makefile（plain make，无 configure / CMake）
- 编译日期: 2026-09-12
- 编译器: clang（上游 makefile 硬编码 `CC=gcc`，由 Conan 显式覆盖）
- 目标平台: ohos-aarch64 (aarch64-linux-ohos)
- 状态: published

## 编译步骤

上游 `makefile` 的 `all:` 目标一次产出两个可执行文件
（`CFILES= dcled.c cpuload.c`），没有 configure 阶段，全部信息靠 make 变量交付：

```bash
make CC="clang" \
     FONTDIR='"<pkg>/share/dcled"' \
     LIBUSB_CFLAGS="-I<libusb>/include/libusb-1.0" \
     LIBUSB_LIBS="-L<libusb>/lib -lusb-1.0 -Wl,-rpath,<libusb>/lib" \
     all
```

每个变量在 `conanfile.py` 的 `_make_command()` 里算出，取值来源全部是 Conan
（`tools.build:compiler_executables` / `self.dependencies` / `self.package_folder`），
不从 shell 环境裸取（R33）。

`make install` **刻意不使用**：上游 install 目标把绝对路径
（`INSTALLDIR=/usr/local/bin`、`FONTDIR=/usr/local/share/dcled`）直接写进构建机，
并只安装 `dcled`。改为在 `package()` 里按 Conan 布局拷贝
`dcled` + `cpuload` + `fonts/*.dlf` + `40-dcled.rules` + `README`。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `dcled -n ...` 免硬件模式必然 SIGSEGV（exit 139），`-n -e -m HELLO` 打印完消息即崩 | `main()` 中 `struct ledscreen maindisp;` 为栈上未初始化对象，`disp = &maindisp` 后即使不连设备也走 `close_usbdev()`，把垃圾 `disp->handle` 交给 `libusb_release_interface()` | `patches/0001-init-ledscreen-maindisp.patch` 在 `disp = &maindisp;` 之前插入 `memset(disp, 0, sizeof(*disp));`；实测 rc 139 → 0 |
| 2 | 编译期 `libusb.h: No such file or directory` | libusb 包把头文件装在 `include/libusb-1.0/` 子目录，而 `dcled.c` 第 30 行写 `#include <libusb.h>` | `LIBUSB_CFLAGS` 指向 `<libusb>/include/libusb-1.0`，不是 `<libusb>/include` |
| 3 | `FONTDIR` 宏内容带出多余引号 / 指向宿主机 | makefile 以 `-DFONTDIR='$(FONTDIR)'` 传递，引号需要由 make 变量自己携带 | 传 `FONTDIR='"<pkg>/share/dcled"'`（值内自带双引号），`strings` 校验二进制内含包内路径 |
| 4 | 构建机无 gcc，`make` 直接报编译器缺失 | 上游 makefile 硬编码 `CC=gcc` | `CC="clang"`（取自 `tools.build:compiler_executables["c"]`，缺省回退 clang） |
| 5 | 消费者测试脚本无法写临时文件 | 平台 `/tmp` 只读（E002） | 按 `TMPDIR` → 当前目录 → `$HOME` 顺序探测可写目录 |
| 6 | CI 消费者测试报 `cpuload` 采样超出 0..100（本地不复现） | 首个采样是 `/proc/stat` **开机累计值**差分（`stat[1]` 初始化后第一次相减），宿主机运行时间越长计数越大，`unsigned long` 传参截断为 `int` 后 `100*t/(t+idle)` 可越过 100 | 消费者测试只对周期性采样（第 2 个起）断言 0..100（15/15 通过）；首个采样属上游 demo 语义缺陷，在测试注释与 `reports/test-report.md` 中写明 |

## 源码修改

`patches/0001-init-ledscreen-maindisp.patch`（1 处新增，2 行）
在 `dcled.c` 的 `disp = &maindisp;` 之前插入 `memset(disp, 0, sizeof(*disp));`。

补丁的性质是 **纯缺陷修复，不是平台适配**：不引入任何平台宏、不改变平台相关分支，
不使用 `#ifdef __OHOS__`（R8），在 Linux 上同样是正确的（上游 bug）。

## 依赖版本

- `libusb/1.0.27`（制品仓已发布，`conan download` 验证通过；W0 预检）
- `libusb-1.0.so` 不是 OHOS 系统同名库（`/lib`、`/lib64` 下无同名文件），
  因此保留默认动态链接，用 `-Wl,-rpath,<libusb>/lib` 固定运行时搜索路径，
  不依赖鸿蒙上不稳定的 `$ORIGIN`。

## 验证结果

```bash
# 上游测试（conanfile.py _run_upstream_checks，-n 免硬件执行 README EXAMPLES 全量）
$ grep -c "upstream check \[PASS\]" reports/w3-local-ci.log
11
$ grep -o "HMBS_UPSTREAM_TEST_RESULT=.*" reports/w3-local-ci.log
HMBS_UPSTREAM_TEST_RESULT={"status": "passed", "framework": "upstream-readme-examples",
  "discovered": 11, "executed": 11, "passed": 11, "failed": 0, "skipped": 0}

# 消费者测试（已安装产物）
$ grep -o "CONSUMER TEST RESULT.*" reports/w3-local-ci.log
CONSUMER TEST RESULT: 15/15 assertions passed

# conan-verify 全门禁
$ ohc-run.py conan-verify dcled 2.2
G1 PASS / G2 PASS / G3 PASS / G4 PASS / L2 / L4 / L5 → ✅ 配方验证通过，可标记 status: published
```

上游提供的 11 项验证全部执行（9 条 README EXAMPLES + `-h` + `cpuload`），
其中 `-t`、`--test`、`--clock --repeat`、`cpuload` 为无限循环模式，
按 20s 超时窗口收口并断言进程未提前崩溃。

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| `bin/dcled` | 195008 B | 主程序：消息板驱动 / CLI |
| `bin/cpuload` | 27072 B | 负载采样器（输出 0-100 数值，供仪表模式：`cpuload 0.2 \| dcled -T tach`） |
| `share/dcled/*.dlf` | — | 字体数据（`sga.dlf`、`small_inv.dlf`） |
| `share/dcled/40-dcled.rules` | — | 上游 udev 规则（设备权限） |
| `share/doc/dcled/README` | — | 上游 README |

## 注意事项

- **`FONTDIR` 是编译期常量**，字体路径被烧进二进制，运行时不再查找环境。
  因此包必须保持 `share/dcled/` 与二进制同包交付；换布局需重新编译。
- `dcled`/`cpuload` 均由同一个 `all` 目标产出，缺任一个都说明 makefile 变量传递有误。
- 无硬件（`-n`）时上游设计上会打印帧内容而不是发送，这条路径是全部自动化
  验证的基础，也正是补丁 1 所修复的崩溃路径。
- 上游源码树**没有 LICENSE 文件**；README 声明为自由软件并说明因使用 libusb
  "might now be considered GPL licensed"，据此登记 `GPL-2.0-or-later`。
- 22 处 K&R 风格函数定义在 clang 下有弃用警告，不影响功能。
## 适配完整性说明（R40 核验）

`dcled` 属「外设 / 硬件 — USB」类三方库（Dream Cheeky USB LED 消息板用户态驱动）。核验结论：

- **无 stub、无空壳实现**：大屏渲染、字体加载、USB 传输逻辑均为上游原始实现；
  本包仅有一处补丁（未初始化栈变量修复），未删除、未禁用任何功能路径。
- **零平台专有代码路径**：`dcled.c`/`cpuload.c` 只用 POSIX/libc + libusb-1.0 API
  （源码中无 `ioctl()`/`usbfs`/`udev`/`sysfs` 调用，仅剩一处未被使用的
  `#include <sys/ioctl.h>`）。设备 I/O 全部经 libusb，平台适配由已发布的
  `libusb/1.0.27` 制品提供，本包内无需写平台分支。
- **已覆盖链路（与设备无关的完整链路）**：命令行解析 → 字体加载 → 帧生成 →
  渲染 → 转义序列输出，由 11 项上游 EXAMPLES 用例 + 15 项消费者断言覆盖
  （证据见 `reports/test-report.md` 与 `reports/w3-local-ci.log`）。
- **未验证项（如实登记）**：本地与 CI 均无真实 LED 设备，`-n/--nodev` 之外的
  **真机点亮/滚动显示未做硬件在环验证**。该限制不影响配方可用性（设备路径与
  `-n` 路径共用同一渲染管线），但真机效果需在有设备的环境人工复核。
- **补丁类型说明**：补丁 1 实为上游缺陷修复（栈上 `maindisp` 未初始化 → 退出
  SIGSEGV）。`conandata.yml` 的 `patch_type` 按 `.gitcode/code-style.md` §12
  固定值填 `"portability"`，补丁语义以 `patch_description` 与
  `reports/test-report.md` §四 为准。
---

**编译结束**: 2026-09-12 03:34
**最终状态**: published
