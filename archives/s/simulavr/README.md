# simulavr

SimulAVR 是一个 AVR 系列单片机（ATmega/ATtiny/AT90 等）的模拟器，可在主机上执行
AVR 固件（ELF），并支持以 GDB remote server 方式单步/断点调试。移植到 OpenHarmony PC
（OHOS / aarch64），本地原生构建。

- 上游项目：https://www.nongnu.org/simulavr/ （savannah git：`git://git.savannah.nongnu.org/simulavr.git`）
- 官网下载区：https://download.savannah.nongnu.org/releases/simulavr/
- 当前适配版本：`1.0.0-git20160221.e53413b`（对应上游提交 `e53413b230637b75e1cfa5c316e988480f5cea14`，2016-02-21）
- 归档目录：`archives/s/simulavr/1.0.0-git20160221.e53413b`
- 支持的 OpenHarmony 架构：armv8（aarch64）
- 同时安装 `simulavr` 命令行工具（见 `commands.json`）

## 功能概述

- `libsim`：AVR 指令级仿真核心（解码器、外设/定时器/UART/SPI/ADC/E²PROM 等模型）。
- `simulavr`：命令行模拟器，可加载 AVR ELF 固件、设定 CPU 频率/运行时长，
  可作为 GDB remote server（`-g`）供 `avr-gdb` 连接调试。
- 内置 ElfIO 2.2（bundled，MIT）解析 ELF 固件，因此不依赖外部 libelf。

## OHOS 适配

适配要点（详见版本级 `notes.md`）：

- **构建系统引导**：原始源码树只带 `configure.ac` / `Makefile.am`，**不含**
  预生成的 `configure`、`config.guess`/`config.sub`、`ltmain.sh`，故配方在
  `build()` 中执行 `autoreconf -fi`；构建主机只提供 autoconf 家族、无
  automake/libtool，因此二者以 `tool_requires` 引入（同 ykclient 2.15 先例）。
- **libc++ 头文件自洽**：`avrfactory.h` 缺 `<map>`、`avrmalloc.h` 缺 `<stddef.h>`，
  在 libc++ 下编译失败（libstdc++ 会传递包含，libc++ 不会）。已打补丁。
- **`std::bind` 名称冲突**：`cmd/gdbserver.cpp` 在 `using namespace std` 下调用
  POSIX socket `bind()`，C++ 的 `std::bind` 变参模板赢得重载解析，已限定 `::bind`。
- **上游测试套件为 Python 2**：`regress/` 回归套件需移植到 Python 3 才能在
  Python 3 环境运行（`make check`）。已提供 `patches/0004`（取自 Debian 打包补丁
  系列中 `regress/` 子集并补充整除修正）。
- **文档依赖 makeinfo**：`configure.ac` 在缺 `makeinfo` 时 `AC_MSG_ERROR` 硬失败，
  且 `doc/` 用 `$(MAKEINFO)` 生成 `simulavr.info`；CI 无 texinfo，注入
  `MAKEINFO=true` 跳过（API 文档非交付物）。
- **静态库优先**：默认 `shared=False`，产出 `libsim.a`；`simulavr` CLI 始终构建/安装。
  注意 AVR 设备经 `AVR_REGISTER` 宏在静态初始化期自注册，静态链接必须对 `libsim`
  使用 `-Wl,--whole-archive`（否则注册对象被丢弃，CLI 报未知设备）；配方已通过
  `patches/0005` 固化。OHOS musl 忽略 `DT_RUNPATH` 且 CI 的 L2 smoke test 不设
  `LD_LIBRARY_PATH`，故 CLI 必须静态自包含。

## 依赖关系

- 编译依赖：无第三方 Conan 依赖。内置 ElfIO（MIT）随源码提供。
- 构建工具依赖：`automake/1.18`、`libtool/2.5.4`（tool_requires，用于 autoreconf）。
- 运行依赖：仅基础 libc/libm（musl）。
- 需要 AVR 交叉工具链（`avr-gcc`/`avr-libc`）才能构建 `regress/{avrtest,gtest,...}`
  与 `examples/`；缺失时上游 configure 自动关闭（`USE_AVR_CROSS=no`），不影响
  libsim 与 CLI 交付物。

## 参考资料

- 项目主页：https://www.nongnu.org/simulavr/
- 源码仓库：https://git.savannah.nongnu.org/cgit/simulavr.git
- GitHub 镜像（非官方）：https://github.com/Traumflug/simulavr
