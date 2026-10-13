# lisgd

## 简介

lisgd 是 suckless 风格的 **libinput 合成手势守护进程**：读取 libinput 触摸事件，
识别 1–4 指的合成滑动手势（LR / RL / UD / DU 及四个对角线方向），并执行用户绑定的
shell 命令。它用"触摸点合成滑动"而非 libinput 原生 gesture 事件，因此可用于触摸屏
（原为 PinePhone 设计）。支持 **X11 与 Wayland 双显示后端**（上游以
`WITHOUT_X11` / `WITHOUT_WAYLAND` 两个编译开关控制，运行期按
`$WAYLAND_DISPLAY` / `$DISPLAY` 自动选择）。

- 主页：<https://git.sr.ht/~mil/lisgd>（suckless **风格**，但不托管在 suckless.org）
- 许可：MIT
- 形态：单文件 C 程序 + suckless 裸 `Makefile`（无 configure / CMake）

## OHOS 适配

- **构建系统**: 裸 Makefile（suckless 风格），无 configure
- **适配方式**: **零补丁** —— 用 `make` 命令行变量覆盖注入 Conan 依赖路径：
  - `CC` ← Conan conf `tools.build:compiler_executables`（上游烧死 `CC=cc`，OHOS 无 cc 别名）
  - `CFLAGS` ← 携带全部依赖的 `-I`（`libinput.h` / `libudev.h` / `wayland-client.h` / `X11/X.h`…）
  - `X11INC` / `X11LIB` ← 覆盖烧死的 `/usr/X11R6/{include,lib}`
    （上游 `CPPFLAGS += -I${X11INC}`、`LIBS += -L${X11LIB} -lX11` **内联引用**它们，
    覆盖路径变量即让 `+=` 追加自动落到依赖目录）
  - `LDFLAGS` ← 携带全部依赖的 `-L`
  - ⛔ **不可覆盖 `CPPFLAGS` / `LIBS`** —— 覆盖聚合变量会吞掉 `+=` 追加的
    `-DWITH_X11` / `-lX11` / `-lwayland-client`，双后端静默缺失
- **依赖链**: libinput → libevdev / mtdev / eudev；libx11 → xorgproto / libxau / libxcb / libxdmcp；
  wayland → libffi（共 12 个节点全部来自 ohpcd 制品仓）
- **编译选项**: 无平台宏、无 `-Werror`；源码零改动，`patches` 为空

## 依赖

- `libinput/1.26.2`
- `libx11/1.8.13`
- `wayland/1.24.0`
- `xorgproto/2025.1`（**显式**：`X11/Xlib.h` → `X11/X.h` 是本包直接 include 的头；
  HEADER 型传递依赖会被 conan 标 `Skip` 而不安装）

## 功能验证

上游无测试套件（无 `tests/`、Makefile 无 `check`/`test` 目标，N_static=0）⇒ 以
消费者测试 `test_package/test.sh`（4 组断言）补位：PATH 可解析、未知选项走 usage
分支、`-h` 缺值走 `die()`、清空显示变量后无参数运行给出确定性诊断且**运行期动态
加载零错误**（验证 conan 依赖注入在运行期生效）。

## 参考

- 官网/仓库: <https://git.sr.ht/~mil/lisgd>
- 归档版本: `archives/l/lisgd/0.3.7/`
