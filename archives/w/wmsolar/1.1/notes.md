# wmsolar 1.1 适配笔记

## 编译环境
- 构建系统: makefile（手写 Makefile，非 autotools）
- 编译日期: 2026-09-23
- 编译器: clang/clang++ 15.0.4（OHOS aarch64）
- 状态: 编译成功，待配方验证

## 编译步骤

1. 上游源码：https://github.com/engerim42/wmsolar tag 1.1（X11 dockapp，天文计算）
2. 依赖注入：`conan install --requires=libxpm/3.5.17 --requires=libxext/6.4.0.1 -pr:h=.../ohos-aarch64 -pr:b=.../ohos-aarch64 -of=build -g=PkgConfigDeps`
3. 编译：`clang++ -O2 -Wall $(pkg-config --cflags xpm x11 xext) -c <源文件>`（11 个源文件全部成功）
4. 链接：`clang++ -O2 -o wmSolar <11个.o> $(pkg-config --libs xpm x11 xext) -lm`
5. 运行验证：`./wmSolar` → `can't open display`（X11 GUI 程序在无 X server 环境的正常 XOpenDisplay 失败，依赖加载全部成功）

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `static const double SYNODIC_MONTH` 报错需 constexpr | C++17 类内静态浮点常量初始化要求 constexpr | Lunar.h 改为 `static constexpr double` |
| 2 | LunarTerms.h/PlutoTerms.h char 窄化错误 | OHOS arm64 上 char 默认 unsigned，-1/-2 无法表示 | Lunar.h LunarTerms1/2、Pluto.h PlutoCoeffs 的 char 改为 signed char |
| 3 | Vsop.cpp `cos` 未声明 | 缺 math.h 头文件 | Vsop.cpp 增加 `#include <math.h>` |
| 4 | 链接报 libxml2.so.16 错误 | OHOS lld 依赖 llvm/lib 下 libxml2.so.16 | LD_LIBRARY_PATH 注入 `/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/lib` |
| 5 | zsh 下 `$CXXFLAGS` 变量展开不分词导致 -I 失效 | zsh 变量默认不分词（区别于 bash） | 用 `${=var}` 强制分词或内联 `$(pkg-config ...)` |

## 源码修改
- Lunar.h: `static const` → `static constexpr`（SYNODIC_MONTH）；LunarTerms1/2 的 char → signed char
- Pluto.h: PlutoCoeffs 的 char → signed char
- Vsop.cpp: 增加 `#include <math.h>`

## 依赖版本
- libxpm/3.5.17（force libx11/6.4.0）
- libx11/6.4.0（依赖 xorgproto/2025.1, libxau/1.0.11, libxcb/1.17.0, xtrans/1.4.0, xcb-proto/1.17.0）
- libxext/6.4.0.1（依赖 libx11/6.4.0, xorgproto/2025.1）
- libm（系统库）

## 验证结果

```bash
# 编译+链接成功，产物 wmSolar (ELF 64-bit LSB arm64, 137664 字节)
# 运行：can't open display（X11 GUI 在无 X 环境正常失败，依赖链完整）
```

## 注意事项
- wmsolar 为 X11 GUI dockapp，OHOS 无 X server，GUI 无法实际运行；但天文计算库（Lunar/Pluto/Vsop/RiseSet）为纯计算逻辑，可作为测试覆盖面
- 上游无测试目录、无 make test/check 目标，需自研 test_package 覆盖核心功能
---

**编译结束**: 2026-09-23 09:57
**最终状态**: built
