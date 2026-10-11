- **三方库名称**：achilles
- **上游版本**：v3
- **上游仓库地址**：https://github.com/mrd/achilles
- **适配路径**：路径 A（基础适配） / 路径 B（贡献创新） —— 本包按 **路径 A（基础适配）** 交付，同时包含一处平台能力适配（OSMesa 离屏渲染层）
- **使用知识库**：openharmony-compile-agent（SKILL.md，v12.22）

## 测试用例对比

### 上游库测试用例统计

| 测试类型 | 上游用例数 | 说明 |
|----------|-----------|------|
| 单元测试 | 0 | 上游无测试框架、无测试目录 |
| 集成测试 | 0 | 同上 |
| 其他测试 | 0 | `make check` 目标存在但规则体为空 |
| **合计** | **0** | |

清点证据（三处一致，均见 `archives/a/achilles/3/test_package/MANIFEST.yml`）：

1. `tar tzf achilles-v3.tar.gz \| grep -ic test` → **0**（tar 内无任何含 test 的路径）
2. `grep -cE '^TESTS|check_PROGRAMS' Makefile.in` → **0**（`check-am`/`check` 规则体为空）
3. `make -n check` → 仅输出普通编译/链接命令，不构建也不运行任何测试程序

### 适配后测试用例统计

| 测试类型 | 适配后用例数 | 与上游对比 | 说明 |
|----------|-------------|-----------|------|
| 单元测试（CLI） | 19 | +19 | `test_package/test_cli.py` |
| 集成测试（无头仿真运行） | 12 | +12 | `test_package/test_simulation.py` |
| 鸿蒙特有测试（OSMesa/GLU/SDL 栈探针） | 18 | +18 | `test_package/test_gl_stack.c` |
| **合计** | **49** | **+49** | 上游零用例，全部为适配后补全 |

> 统计口径：断言级（每条 `check()` 计 1）。实测汇总行：
> `test_cli: 19 executed, 0 failed` / `test_simulation: 12 executed, 0 failed` /
> `test_gl_stack: 18 executed, 0 failed` → **49 executed, 0 failed**。

## 上游测试用例修改说明

### 是否存在对上游测试用例的修改？

- [x] **否**，未修改上游任何测试用例
- [ ] **是**，存在对上游测试用例的修改（请在下方逐条说明）

> 上游零用例，因此不存在"修改上游测试"的情形。`make check` 仍在 `conanfile.py`
> 的 `build()` 中执行（日志可见 `achilles/v3: RUN: make check`），保留上游测试入口
> 的执行痕迹，未因零用例而删除。

## 补全测试用例说明

### 上游是否存在无测试用例，适配后补全的情况？

- [ ] **否**，上游已有测试用例覆盖
- [x] **是**，上游无测试用例，适配后补全了测试（请在下方说明）

> - **补全的测试范围**：为 CLI 接口补 19 条断言、为无头仿真主循环补 12 条断言、
>   为渲染所依赖的 OSMesa/GLU/SDL 栈补 18 条断言，共 **49 条**，全部真实依赖被测产物（R34）。
> - **补全原因**：上游 v3 不附带任何测试套件（三段式清点见上），且该程序是
>   OpenGL 固定管线 + SDL 1.2 应用，其可执行性（能否真正渲染、能否跑起主循环）
>   必须由消费者侧实测覆盖。
> - **新增测试文件清单**：
>   1. `archives/a/achilles/3/test_package/test_cli.py` — 运行已安装的 `bin/achilles`：
>      `-v/--version`、`-h/--help` 两种写法（退出码、版本串、GPL 声明、选项文档、
>      长短选项输出逐字节一致），未知选项如实报告，无视频后端时干净失败
>   2. `archives/a/achilles/3/test_package/test_simulation.py` — 以
>      `SDL_VIDEODRIVER=dummy` 真实无头运行仿真 ~16s（4x4 世界、固定种群、`--fps 10`）：
>      主循环存活、无 SDL/OSMesa 初始化错误、周期性帧率报告证明逐帧渲染、
>      帧率节拍符合目标、终止无 SIGSEGV/SIGABRT/SIGBUS
>   3. `archives/a/achilles/3/test_package/test_gl_stack.c` — C 消费者探针：创建 OSMesa
>      离屏上下文并置为当前、上报 `GL_VERSION`/`GL_RENDERER`、以 `gluPerspective` +
>      固定管线绘制并断言 `GL_NO_ERROR`、`glReadPixels` 回读并断言清屏底色与光栅化
>      几何同时存在，随后校验 SDL 软件表面/事件队列/键盘状态/毫秒时基

## 验证结果

- 编译状态：**通过**
- 上游测试用例通过率：**0/0**（上游无用例，非跳过）
- 新增测试用例通过率：**49/49（100%）**

本地 CI 模拟（`ci/conan/build_and_test.sh`，完整日志见
`archives/a/achilles/3/reports/local-ci.log`）：

```
KC_RESULT=pass
  检查模式: incremental (17 个文件)
JC_RESULT=pass
L0_RESULT=pass: all checks passed
L1_RESULT=pass: upstream tests + test_package executed
L2_RESULT=pass: achilles --version OK
L4_RESULT=pass: patches clean
L5_RESULT=pass: bin/ has content
```

关键门禁证据：

- **L1c**（上游测试入口留痕）：日志含 `achilles/v3: RUN: make check`
- **L1e**（破坏性反向验证）：`[sabotage] bin/ moved away` →
  `[ok] L1e: Negative test confirmed — test genuinely depends on achilles`
  （证明 49 条断言确实依赖被测产物，非空壳测试）
- **L2**（smoke test）：`[ok] L2: achilles --version OK`
- **运行证据**（真实执行，非编译期推断）：`Frames per second: 10.000000` /
  `New guy!` / `Frames per second: 9.800000`（目标 10 FPS 稳定达成）

## 全功能适配说明

本题要求特别注意**全功能适配**，逐项核对如下（上游 18 个 .cc 全部参与编译，共 3438 行）：

| 上游功能 | 适配状态 | 依据 |
|----------|---------|------|
| 仿真主循环（世界演化、种群维持、食物衰减） | ✅ 完整 | `test_simulation` 无头运行 16s，帧率报告持续输出 |
| Hebbian 神经网络 / 基因 / 能量 / 战斗 / 交配 | ✅ 完整 | 源码未裁剪；全部对象文件参与链接（18/18 .o） |
| OpenGL 固定管线渲染（`glBegin/glEnd`、光照、矩阵） | ✅ 完整 | `test_gl_stack` 固定管线 + GLU 渲染断言 `GL_NO_ERROR` |
| GLU（`gluPerspective`） | ✅ 完整 | 同上，实测 `GL_VERSION=3.3 (Compatibility Profile) Mesa 24.3.4` |
| 帧缓冲回读 / PNG 截图 | ✅ 完整 | `glReadPixels` 回读断言；`config.h` 实测 `HAVE_LIBPNG 1`，产物依赖 `libpng16.so.16` 且 `PNGScreenShot` 已链接 |
| SDL 事件 / 键盘输入 / 计时 | ✅ 完整 | `test_gl_stack` 覆盖事件队列、`SDL_GetKeyState`、`SDL_GetTicks` |
| CLI 全部选项（`-v/-h/-x/-z/-f/--fps/--debug/生物数`） | ✅ 完整 | `test_cli` 19 条断言覆盖 |
| 可见窗口呈现 | ⚠️ 平台限制 | 平台无窗口系统，改由 OSMesa 离屏渲染 + SDL 软件表面（`SDL_VIDEODRIVER=dummy`），**渲染管线本身未裁剪** |

> 渲染路径的处理是"平台能力替换"而非"功能裁剪"：GL/GLU 绘制代码、SDL 事件与按键
> 处理、`glReadPixels` 截图路径全部原样保留，仅把"窗口 GL 上下文"换成"OSMesa 离屏上下文"，
> 并在 `SwapBuffers()` 中把 softpipe 渲出的帧拷贝到 SDL 软件表面。补丁内不含平台宏
> （`OSMESA_RENDER` 是能力宏，由配方按 R8 定义），无 stub、无空实现。

## 补充说明

### 适配要点（4 个可移植性补丁）

| 补丁 | 内容 | 原因 |
|------|------|------|
| `0001-config-sub-ohos.patch` | `config.sub` 增补 `aarch64` 与 `linux-ohos*` | 2001 年版脚本不认鸿蒙三元组；`configure.ac` 未用 `AC_CANONICAL`，故 `--host` 由 config.sub 校验，`config.guess` 无需改动 |
| `0002-configure-umask-022.patch` | 两处 `umask 077` → `022` | setgid hmdfs 上 `config.status` 建的 0700 临时目录连创建者都不可写（`can't create ./confXXXXXX/...: Permission denied`） |
| `0003-opengl-osmesa-offscreen.patch` | 新增 `OSMESA_RENDER` 离屏后端 | 鸿蒙 PC 无窗口系统也无窗口 GL；制品仓 `mesa/24.3.4.1` 为 OSMesa-only（仅 `libOSMesa.so`，无 `libGL`/`libEGL`），`glu/9.0.3` 亦针对 OSMesa 构建 |
| `0004-long-options.patch` | `main.cc` 增 `--version`/`--help` | 使安装后的二进制可被 CI L2 smoke test 真实执行；复用上游既有的帮助/版本路径，非测试特例 |

### 链接集说明

`configure` 的 `AC_CHECK_LIB` 探测会**重建 `LIBS`**，configure 期传入的 `-lOSMesa`
在链接期已丢失；且平台无 `libGL`。故完整链接集在 `make` 命令行显式覆盖：

```
make -j1 LIBS="-lSDL -lasound -lGLU -lOSMesa -lpng -lz -lm -ldl -lpthread"
```

（`-lasound` 是制品仓静态 `libSDL.a` 的链接期需求；该 SDL 配方默认 `alsa=True`。）

### 依赖

- `sdl/1.2.15`（静态 `libSDL.a`）
- `alsa-lib/1.2.16`（静态 SDL 的链接期依赖）
- `glu/9.0.3`
- `libpng/1.6.58.3`
- 传递依赖：`mesa/24.3.4.1`（OSMesa + GL 头文件）、`zlib/1.3.2`

全部依赖均已在制品仓发布（`conan install` 实测可解析并下载 binary），无捎带适配。

### 版本号说明

归档目录沿用任务卡的 `3`；Conan 2.x 拒绝单字符版本号（`RecipeReference` 正则要求
≥2 字符），故用 `set_version()` 取上游 tag 名，制品为 **`achilles/v3`**（先例一致：
`cronic/3`、`cutmp3/4`、`rapidhash/3`）。

### 已知限制

1. 无可见窗口：程序以 OSMesa 离屏 + SDL dummy 软件表面运行，渲染结果不呈现在屏幕上
   （平台无 X11/Wayland/EGL，属平台限制而非适配缺失）。
2. 实时交互键（方向键/PageUp/PageDown/`p`/`s`/`ESC`）在无窗口环境下无法通过真实键盘
   触发；其代码路径与 SDL 键盘状态接口已由 `test_gl_stack` 覆盖，但未做端到端按键注入。
3. 帧率受 softpipe 软件渲染性能约束，世界尺寸较大时实际帧率会低于 `--fps` 设定值。
