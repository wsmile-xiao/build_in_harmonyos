# dcled — OpenHarmony PC 适配

## 基本信息
- 软件: dcled
- 版本: 2.2
- 描述: Dream Cheeky USB LED 点阵信息板的用户态驱动（`dcled` 显示消息/时钟/测试图案，`cpuload` 输出 CPU 负载采样供仪表模式使用）
- 构建系统: makefile（plain make，无 configure）
- 目标平台: ohos-aarch64
- 上游: https://www.jeffrika.com/~malakai/dcled
- 许可: GPL-2.0-or-later（上游源码树无 LICENSE 文件，依据 README 声明登记）

## 编译指导
- 编译器: clang —— 上游 makefile 硬编码 `CC=gcc`，**必须覆盖**
- 全部 make 变量由 Conan 交付，不从 shell 环境裸取（R33）：

| make 变量 | 取值 |
|-----------|------|
| `CC` | `tools.build:compiler_executables["c"]`，缺省 `clang` |
| `FONTDIR` | `'"<pkg>/share/dcled"'`（**值内自带双引号**，makefile 以 `-DFONTDIR='$(FONTDIR)'` 传递） |
| `LIBUSB_CFLAGS` | `-I<libusb>/include/libusb-1.0`（dcled.c 写 `#include <libusb.h>`） |
| `LIBUSB_LIBS` | `-L<libusb>/lib -lusb-1.0 -Wl,-rpath,<libusb>/lib` |

- `make install` 不使用：上游 install 目标把 `/usr/local/...` 绝对路径写进宿主构建机，
  且只安装 `dcled`；改由 `package()` 按 Conan 布局拷贝两个可执行文件与字体数据。
- `all:` 目标一次产出 `dcled` + `cpuload`，二者都必须存在于包内。

## 依赖
- `libusb/1.0.27`（制品仓已发布）
- `libusb-1.0.so` 非 OHOS 系统同名库，保留默认动态链接，运行时路径用 `-Wl,-rpath` 固定

## 补丁清单
- `patches/0001-init-ledscreen-maindisp.patch`: 在 `disp = &maindisp;` 前插入
  `memset(disp, 0, sizeof(*disp));`。`maindisp` 是栈上未初始化的
  `struct ledscreen`，免硬件模式（`-n`，即全部自动化测试所用路径）下
  `close_usbdev()` 会把垃圾 handle 交给 `libusb_release_interface()`，必然
  SIGSEGV（exit 139）。属纯上游缺陷修复，非平台适配，不使用任何平台宏。

## 已知限制
- `dcled` 需要真实 USB 消息板才能显示；无设备时用 `-n`（nodev）模式，
  帧内容打印到 stdout 而不是发送到设备 —— 这是本项目全部验证的基础。
- `FONTDIR` 为编译期常量烧进二进制，包必须整体交付 `bin/` + `share/dcled/`。
- 22 处 K&R 风格函数定义在 clang 下产生弃用警告，不影响功能。
- `-t` / `--test` / `--clock --repeat` / `cpuload` 设计上无限循环，测试须加超时窗口。

## 功能验证
- 上游测试（README EXAMPLES 全量 9 条 + `-h` + `cpuload`，共 11 项，`-n` 免硬件）：11/11 passed
- 消费者测试（已安装产物）：15/15 assertions passed
- conan-verify: G1/G2/G3/G4 PASS，L2 smoke / L4 静态安全扫描 / L5 产物基线 通过
- 手工验证：
  - `dcled -n -e -m "Hello World!"` → `Hello World!`（补丁前 exit 139）
  - `dcled -h` → 用法横幅（1404 B）
  - `echo 'Hello World!' | dcled -n -e` → `Hello World!`
  - `dcled -n -e -p static -m "Hello World"` → `Hello World`
