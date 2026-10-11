# 测试报告 — achilles 3（上游 v3）

> **项目**：achilles
> **测试日期**：2026-10-08
> **测试环境**：HarmonyOS HongMeng Kernel 1.12.0 aarch64（OHOS 6.0 / clang 15 / libc++ / Release）
> **测试类型**：上游测试入口（零用例）+ 适配后补全的消费者测试

---

## 一、测试摘要

### 1.1 上游测试用例

| 指标 | 数值 | 百分比 |
|:----:|:----:|:------:|
| 总测试数 | 0 | — |
| 通过 (PASS) | 0 | — |
| 失败 (FAIL) | 0 | — |
| 跳过 (SKIP) | 0 | — |

上游零用例，三段式清点证据（三处一致）：

1. `tar tzf achilles-v3.tar.gz | grep -ic test` → **0**（tar 内无任何含 test 的路径）
2. `grep -cE '^TESTS|check_PROGRAMS' Makefile.in` → **0**（`check-am`/`check` 规则体为空）
3. `make -n check` → 仅输出普通编译/链接命令，不构建也不运行任何测试程序

`make check` 仍在 `conanfile.py` 的 `build()` 中执行，使构建日志保留上游测试入口的执行痕迹
（日志可见 `achilles/v3: RUN: make check`），而不是静默跳过。

**上游测试通过率：0/0（无用例可计）**

### 1.2 适配后补全的测试用例

| 指标 | 数值 | 百分比 |
|:----:|:----:|:------:|
| 总断言数 | 49 | 100% |
| 通过 (PASS) | 49 | 100% |
| 失败 (FAIL) | 0 | 0% |
| 跳过 (SKIP) | 0 | 0% |

| 测试文件 | 断言数 | 通过 | 失败 |
|----------|:------:|:----:|:----:|
| `test_package/test_cli.py` | 19 | 19 | 0 |
| `test_package/test_simulation.py` | 12 | 12 | 0 |
| `test_package/test_gl_stack.c` | 18 | 18 | 0 |
| **合计** | **49** | **49** | **0** |

**适配后测试通过率：49/49（100%）**

---

## 二、测试结论

### 2.1 总体评价

✅ **通过** — 编译成功；上游无测试套件（已附清点证据且保留 `make check` 执行痕迹）；
补全的 49 条消费者断言全部通过，且均真实依赖被测产物。

### 2.2 主要问题

| 问题类别 | 影响范围 | 严重程度 |
|----------|----------|----------|
| 平台无窗口 GL（OSMesa-only 交付） | 渲染路径需改为离屏 | 🟡 已解决（补丁 0003） |
| 2001 年版 config.sub 不认鸿蒙三元组 | configure 无法启动 | 🟢 已解决（补丁 0001） |
| setgid hmdfs 下 config.status umask 077 目录不可写 | configure 收尾失败 | 🟢 已解决（补丁 0002） |
| 平台无 `libGL`，GL 符号须由 libOSMesa 提供 | 链接失败 | 🟢 已解决（make 覆盖 LIBS） |

### 2.3 可用功能清单

```
✅ 仿真主循环：世界演化、种群维持、逐帧渲染（实测 10 FPS 目标下稳定 ~9.8–10 FPS）
✅ Hebbian 神经网络与基因/能量/战斗/交配等全部仿真逻辑（源码未裁剪）
✅ GL 固定管线渲染：glBegin/glEnd、gluPerspective、光照/矩阵（经 OSMesa softpipe）
✅ 帧缓冲回读：glReadPixels（截图的底层路径）
✅ SDL 事件与交互：事件队列、键盘状态、SDL_GetTicks 计时、帧率节拍
✅ 命令行接口：-v/-h/--version/--help、-x/-z/-f/--fps/--debug
⚠️ 可见窗口：平台无窗口系统，仅离屏渲染 + SDL 软件表面（需 SDL_VIDEODRIVER=dummy）
⚠️ 交互按键实际输入：无窗口环境无法真机按键，逻辑路径由 SDL 键盘状态接口覆盖
```

### 2.4 已知限制

1. 无可见窗口：鸿蒙 PC 无 X11/Wayland/EGL，程序以 OSMesa 离屏 + SDL dummy 软件表面运行，
   渲染结果不呈现在屏幕上。
2. 实时交互键（方向键/PageUp/PageDown/p/s/ESC）在无窗口环境下无法通过真实键盘触发；
   其代码路径与 SDL 键盘状态接口由 `test_gl_stack.c` 覆盖，但未做端到端按键注入。
3. 帧率受 softpipe 软件渲染性能约束，世界尺寸较大时实际帧率会低于 `--fps` 设定。

---

## 三、测试详情

### 3.1 通过的测试（49 条断言）

**`test_cli.py`（19 条）** — 已安装的 `bin/achilles`

| 测试项 | 功能 | 结果 |
|--------|------|------|
| 安装命令存在 / 可执行 | 产物完整性 | ✅ PASS |
| `-v` 退出码 0 | CLI 返回码 | ✅ PASS |
| `-v` 输出 `Achilles version 3` | 版本号（含上游 ACHILLES_VERSION） | ✅ PASS |
| `-v` 输出 GPL 免责声明 | license.cc 路径 | ✅ PASS |
| `-v` 无视频后端依赖 | 选项路径不初始化 SDL | ✅ PASS |
| `--version` 退出码 0 且与 `-v` 逐字节一致 | 长选项一致性 | ✅ PASS ×3 |
| `-h` 退出码 0 / `Usage:` / `Defaults are` | 帮助输出 | ✅ PASS ×3 |
| `-h` 列出 `-x -z -f --fps --debug` | 选项文档完整性 | ✅ PASS |
| `-h` 含 `ESC quits` | 交互说明 | ✅ PASS |
| `--help` 与 `-h` 逐字节一致 | 长选项一致性 | ✅ PASS ×2 |
| 未知选项被如实报告 | 错误处理 | ✅ PASS |
| 无视频后端时干净失败（退出码 1） | 失败路径 | ✅ PASS ×2 |

**`test_simulation.py`（12 条）** — 真实无头仿真运行

| 测试项 | 功能 | 结果 |
|--------|------|------|
| 13→16s 后主循环仍存活 | `UniverseClass::MainLoop()` 运行 | ✅ PASS |
| 无 `Unable to ...` 错误行 | 初始化成功 | ✅ PASS |
| SDL 视频子系统初始化成功 | SDL_Init | ✅ PASS |
| OSMesa 上下文创建成功 | 补丁 0003 的离屏后端 | ✅ PASS |
| OSMesa 上下文置为当前成功 | OSMesaMakeCurrent | ✅ PASS |
| ≥2 条 `Frames per second:` | 逐帧渲染证据 | ✅ PASS |
| 帧率值可解析 / 全部 >0 | 数值有效性 | ✅ PASS ×2 |
| 帧率 ≤ 目标 1.5 倍 | 帧节拍生效 | ✅ PASS |
| 稳态帧率 ≥ 目标 50% | 未丢帧（实测 9.8/10） | ✅ PASS |
| 终止退出码非负 | 信号处理正常 | ✅ PASS |
| 无 SIGSEGV/SIGABRT/SIGBUS | 渲染无崩溃 | ✅ PASS |

**`test_gl_stack.c`（18 条）** — GL/GLU/SDL 栈探针

| 测试项 | 功能 | 结果 |
|--------|------|------|
| OSMesa 上下文创建/置当前/销毁 | 离屏上下文生命周期 | ✅ PASS ×3 |
| `GL_VERSION` 可读 | GL 版本（实测 3.3 Compatibility Profile / softpipe） | ✅ PASS |
| 固定管线 + GLU 渲染无 GL 错误 | glBegin/glEnd + gluPerspective | ✅ PASS |
| `glReadPixels` 无错 | 截图路径基础 | ✅ PASS |
| 帧含像素 / 非全黑 | 渲染有效 | ✅ PASS ×2 |
| 清屏底色存在 | glClear 生效 | ✅ PASS |
| 存在被光栅化的像素 | 几何真实绘制 | ✅ PASS |
| SDL 视频初始化 / 软件表面创建 | SDL 表面路径（driver=dummy） | ✅ PASS ×2 |
| 表面位深可用 / 暴露像素缓冲 | 表面可用性 | ✅ PASS ×2 |
| 事件队列排空 | SDL_PollEvent | ✅ PASS |
| 键盘状态可用 | SDL_GetKeyState | ✅ PASS |
| 毫秒时基运行 | SDL_GetTicks | ✅ PASS |
| SDL 干净关闭 | 生命周期收尾 | ✅ PASS |

### 3.2 失败的测试

无。

### 3.3 跳过的测试

无（上游 0 用例，无需跳过项）。

---

## 四、关键问题分析

### 问题 1：鸿蒙 PC 无窗口 GL，桌面 OpenGL 程序如何落地

**现象**：

```
Unable to create OpenGL screen: OpenGL not available      # SDL 视频驱动为 dummy
ld.lld: error: undefined symbol: glTexEnvi                   # 平台无 libGL 可链接
```

**根因分析**：平台无 X11/Wayland/EGL，也无窗口 GL 驱动；制品仓的 `mesa/24.3.4.1` 为
OSMesa-only 交付（仅 `libOSMesa.so`，`libGL`/`libEGL` 不存在），`glu/9.0.3` 同样针对
OSMesa 构建。`SDL_SetVideoMode(..., SDL_OPENGL)` 在平台上没有可行等价物。

**解决方案**：不 stub、不改渲染语义，而是把"窗口 GL 上下文"替换为"OSMesa 离屏上下文"：
`SDL_SWSURFACE` 软件表面 + `OSMesaCreateContextExt`/`OSMesaMakeCurrent`，
`SwapBuffers()` 改为按 `SDL_MapRGBA` 把 softpipe 渲出的帧拷到该表面
（补丁 `0003-opengl-osmesa-offscreen.patch`，由配方定义 `OSMESA_RENDER` 选择后端，
补丁内不含平台宏）。GL/GLU 绘制代码、SDL 事件与按键处理、`glReadPixels` 截图路径原样保留。

### 问题 2：`configure` 的 `AC_CHECK_LIB` 重建 LIBS 导致 GL 符号全部缺失

**现象**：

```
ld.lld: error: undefined symbol: gluPerspective
ld.lld: error: undefined symbol: OSMesaCreateContextExt
```

**根因分析**：`configure.ac` 里 `LIBS=$X_LIBS` 起始，随后一串 `AC_CHECK_LIB` 用
"能否链接"判定每个库（`z/m/png/pthread/X11/.../SDL`）并**重写** `LIBS`：configure 期传入的
`-lOSMesa` 从不参与，链接期自然缺失；且平台没有 `libGL`，`AC_CHECK_LIB(GL,...)` 必然失败。

**解决方案**：完整链接集在 `make` 命令行显式覆盖：
`make -j1 LIBS="-lSDL -lasound -lGLU -lOSMesa -lpng -lz -lm -ldl -lpthread"`
（含静态 SDL 所需的 `-lasound`）。与 `lbreakout2`/`sdl` 系配方的同类处置一致。

### 问题 3：setgid hmdfs 上 `config.status` 无法建立临时目录

**现象**：

```
./config.status[751]: can't create ./confObABDo/subs1.awk: Permission denied
config.status: error: could not setup config files machinery
```

**根因分析**：`configure` 以 `umask 077` 创建 `./confXXXXXX`；setgid hmdfs 卷上目录属主
不是构建 UID，0700 目录连创建者也不可写。

**解决方案**：补丁 `0002` 将两处 `umask 077` 改为 `022`（同 `sdl/1.2.15` 的处置）。

---

## 五、测试环境

```
上游版本:  v3 (mrd/achilles, GPL-2.0-or-later)
Conan 制品: achilles/v3
编译器:    clang/clang++ 15 (aarch64-unknown-linux-ohos)
Profile:   ci/conan/profiles/ohos-aarch64 (os=OHOS 6.0, arch=armv8, libc++, Release)
依赖:      sdl/1.2.15, alsa-lib/1.2.16, glu/9.0.3, mesa/24.3.4.1, libpng/1.6.58.3, zlib/1.3.2
渲染后端:  OSMesa softpipe (GL 3.3 Compatibility Profile, Mesa 24.3.4)
运行环境:  SDL_VIDEODRIVER=dummy
构建日志:  reports/conan-create.log
```

---

*报告生成时间: 2026-10-08*
