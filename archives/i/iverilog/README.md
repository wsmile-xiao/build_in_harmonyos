# iverilog

## 简介

Icarus Verilog（`iverilog`）是一个开源的 Verilog HDL 编译与仿真工具：
`iverilog` 把 Verilog 源码编译为 `vvp` 字节码，`vvp` 负责仿真运行；
另含 `iverilog-vpi` 用于编译 VPI 模块。

- 上游: https://github.com/steveicarus/iverilog （tag `v13_0`）
- 许可证: GPL-2.0-or-later
- 平台: OpenHarmony PC (aarch64-linux-ohos), musl, clang 15 / libc++
- 构建: autotools（`configure` + `Makefile.in`）
- 版本状态: 13.0 = built（conan-verify G0-G3 PASS）

## OHOS 适配（13.0）

- **生成工具**：源码只带 `parse.y` / `lexor.lex` / `*.gperf`，必须 bison/flex/gperf；
  CI 原生（OHOS aarch64）用注册表二进制（`tool_requires`），交叉构建改用宿主工具。
- **`AX_PROG_CC_FOR_BUILD` 与 `LIBS`**：iverilog 的 build-compiler 可用性检查用全局
  `LIBS` 链接本机 gcc；conan 注入的目标库（aarch64）会让它失败 → configure 传 `LIBS=`；
  `CPPFLAGS/LDFLAGS` 保留供 `AC_CHECK_LIB` 使用。
- **静态 readline/ncurses**：注册表只有静态库，final link 需显式
  `-lreadline -lhistory -lformw -lmenuw -lpanelw -lncursesw -lpthread`（LIBS 含空格，须转义后传给 make）。
- **默认关闭 zlib/bzip2**：注册表 zlib 仅静态且非 PIC、bzip2 仅静态，链入共享 VPI 模块会报
  `z_errmsg ... recompile with -fPIC` / 运行 `gzip: symbol not found` 类错误；压缩 VCD 等特性暂不可用。
- **运行期模块路径**：conan 以 `--prefix=/` + `DESTDIR` 安装，编译期模块路径
  `$(prefix)/lib/ivl` 与实际 `<pkg>/lib/ivl` 不符 → 运行需 `-B <pkg>/lib/ivl`。

## 参考

- 文档：https://steveicarus.github.io/iverilog/
- 回归套件 `ivtest/`（源码内置，主驱动 `vvp_reg.py`）
