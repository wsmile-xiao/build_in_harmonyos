# achilles 3 适配笔记（上游 tag v3，HarmonyOS PC）

## 版本说明

- 归档目录：`archives/a/achilles/3`（任务卡版本号）
- Conan 制品：`achilles/v3`（Conan 2.x 拒绝单字符版本号，用 `set_version()` 取上游 tag 的 `v3`；
  先例 `cronic/3`、`cutmp3/4`、`rapidhash/3`）
- 上游源码：官方 tag `v3`（2026-02-11 提交），GPL-2.0-or-later

## 编译环境

- 构建系统：autotools（仓库自带 Autoconf 2.71 生成的 `configure`，无需 autoreconf）
- 编译日期：2026-10-08
- 编译器：clang/clang++ 15（aarch64-unknown-linux-ohos）
- Profile：`ci/conan/profiles/ohos-aarch64`（os=OHOS 6.0 / arch=armv8 / clang 15 / libc++ / Release）
- 状态：built

## 核心适配问题：平台上没有「窗口 GL」

Achilles 是 OpenGL 1.x 固定管线 + SDL 1.2 的桌面程序，用
`SDL_SetVideoMode(SCREEN_W, SCREEN_H, 0, SDL_OPENGL)` 直接创建 GL 表面。
鸿蒙 PC 既无窗口系统（X11/Wayland/EGL），也无窗口 GL 驱动；制品仓的 `mesa/24.3.4.1`
是 **OSMesa-only** 交付（仅 `libOSMesa.so`，无 `libGL`/`libEGL`），`glu/9.0.3` 也针对
OSMesa 构建。故窗口 GL 路径在平台上不存在可行的等价物。

处理方式（不是 stub，也不改语义）：

1. `OpenGLClass` 构造函数改为创建 **SDL 软件表面**（`SDL_SWSURFACE`，`SDL_VIDEODRIVER=dummy`
   即可）并创建 **OSMesa 离屏上下文**（`OSMesaCreateContextExt(OSMESA_RGBA, 16, 0, 0, NULL)`
   + `OSMesaMakeCurrent` + `OSMesaPixelStore(OSMESA_Y_UP, 0)`）；
2. `SwapBuffers()` 不再调用 `SDL_GL_SwapBuffers()`，而是 `glFinish()` 后把 softpipe 渲出的
   帧按 `SDL_MapRGBA` 映射到该软件表面（含 `SDL_LockSurface`/`SDL_UpdateRect`）；
3. 其余全部 GL/GLU 渲染代码、SDL 事件与按键处理、截图（`glReadPixels`）路径**原样保留**。

由此程序在无窗口环境下功能完整：世界演化、逐帧渲染、按键控制、PNG 截图都不受影响，
只是输出目标是离屏缓冲 + 软件表面，而非屏幕上的窗口。

## 编译步骤

```bash
# 补丁对齐后（build() 内部顺序）
sh ./configure \
    CC=<profile c> CXX=<profile cpp> \
    CPPFLAGS="-I<各依赖>/include" \
    LDFLAGS="-L<各依赖>/lib -Wl,-rpath,<各依赖>/lib" \
    CXXFLAGS="-O2 -DOSMESA_RENDER" \
    --host=aarch64-unknown-linux-ohos \
    ac_cv_prog_cc_works=yes ac_cv_prog_cc_cross=yes

# 注意：LIBS 必须在 make 命令行覆盖（见下）
make -j1 LIBS="-lSDL -lasound -lGLU -lOSMesa -lpng -lz -lm -ldl -lpthread"

make check      # 上游测试入口（零用例，仅留痕）
```

打包：直接拷贝 `achilles` 到 `bin/`、`COPYING`/`README` 到 `licenses/`（不走
`make install`——install-sh 在 setgid hmdfs 上不可靠，与 `sdl/1.2.15` 同处置）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `configure` 拒绝 `aarch64-unknown-linux-ohos` | 2001 年版 `config.sub` 不认 aarch64、也不认 linux-ohos；`configure.ac` 未用 `AC_CANONICAL`，故 `--host` 由 config.sub 校验 | 补丁 0001：`config.sub` 的 kernel-OS 列表加 `linux-ohos*`、CPU 列表加 `aarch64`（config.guess 无需改动） |
| 2 | `config.status` 报 `can't create ./confXXXXXX/out: Permission denied` | `configure` 以 `umask 077` 建临时目录；setgid hmdfs 上目录属主非构建 UID，0700 连创建者都不可写 | 补丁 0002：两处 `umask 077` → `umask 022`（同 `sdl/1.2.15` 0003） |
| 3 | 链接报大量 `undefined symbol: glBegin/glVertex3f/gluPerspective/glReadPixels` | 平台无 `libGL`，GL 符号来自 `libOSMesa.so`；且 `configure` 的 `AC_CHECK_LIB` 探测会**重建 LIBS**，configure 期传入的 `-lOSMesa` 链接期已丢失 | 配方在 `make` 命令行显式覆盖 `LIBS="-lSDL -lasound -lGLU -lOSMesa -lpng -lz -lm -ldl -lpthread"` |
| 4 | `make` 试图执行 `aclocal-1.16`（CI 无 automake）而失败 | tarball 内 `configure.ac`/`aclocal.m4` mtime 同秒；本机探测时用 `cp -r` 复制源码导致 mtime 相对关系被改写。conan 的 source 拷贝保留 mtime，实测不触发；但为稳妥不依赖该性质 | 不引入额外补丁：确认 conan 构建目录中 `aclocal.m4` 与 `configure.ac` mtime 相同、`make` 不重生。若未来上游刷新 tarball 打破该性质，需在 `build()` 中 `touch aclocal.m4` |
| 5 | `conan create` 报 `TypeError: expected str, bytes or os.PathLike object, not NoneType` | 用 `self.dependencies["zlib"]` 这类按名取用法时，传递依赖可能解析不到（`package_folder` 为 None） | 改为遍历 `self.dependencies.host.values()` 动态收集存在的 `include`/`lib` 目录 |
| 6 | test_package 的 CMake 报 `Target "test_gl_stack" links to: SDL::SDL but the target was not found` | 各包声明的 CMake 目标名为 `sdl::sdl`/`glu::glu`/`mesa::mesa`（小写，由 `cmake_file_name`+`cmake_target_name` 决定），非 `SDL::SDL` | CMakeLists 改用实际目标名 |
| 7 | test_package 编译报 `GL/osmesa.h: file not found` | producer 侧 `mesa` 的 `includedirs` 正常，但 consumer 侧 CMakeDeps 对**仅传递依赖**（mesa 经 glu 引入）生成的 `*_INCLUDE_DIRS` 为空 | 测试包把 `mesa/24.3.4.1` 声明为直接 `requires` |
| 8 | 被测进程未知选项的提示行抓不到 | stdio 块缓冲：用 SIGKILL 结束进程会丢弃未 flush 的输出 | 测试改为给一个不存在的 `SDL_VIDEODRIVER`，让程序自己 `exit()`（输出正常 flush），断言随之稳定 |
| 9 | 探针断言 `every read-back byte was written` 失败 | 顶点色插值本就会把个别通道压到 0，"无零字节"是错判据 | 改为断言「清屏底色存在」且「存在被光栅化覆盖的像素」 |

## 源码修改（补丁清单）

| 补丁 | 内容 | 说明 |
|------|------|------|
| `0001-config-sub-ohos.patch` | `config.sub` 增补 `aarch64` 与 `linux-ohos*` | 端口性补丁，上游脚本年代过久 |
| `0002-configure-umask-022.patch` | `configure` 中两处 `umask 077` → `022` | 平台文件系统限制（setgid hmdfs） |
| `0003-opengl-osmesa-offscreen.patch` | `opengl.h`/`opengl.cc`：新增 `OSMESA_RENDER` 后端（OSMesa 上下文 + 帧拷贝到 SDL 软件表面） | 平台能力补丁，宏由配方定义，补丁内不含平台宏（R8） |
| `0004-long-options.patch` | `main.cc`：`--version`/`--help` 长选项 | 使安装后的二进制可被 L2 smoke test（`--version`/`--help`）真实执行 |

> `0004` 属功能增强而非平台绕行：CI 的 L2 会用 `--version`/`--help` 探测可执行文件，
> 上游仅有 `-v`/`-h`；补上长选项即可复用上游的帮助与版本路径，无需为测试引入特例。

## 依赖版本

| 依赖 | 版本 | 说明 |
|------|------|------|
| sdl | 1.2.15 | 静态 `libSDL.a`（配方 `alsa=True`），故需 `-lasound` |
| alsa-lib | 1.2.16 | 静态 SDL 的链接期依赖 |
| glu | 9.0.3 | GLU（针对 OSMesa 构建） |
| mesa | 24.3.4.1（经 glu 传递） | OSMesa 离屏软件渲染（softpipe）与全部 GL 头文件 |
| libpng | 1.6.58.3 | `HAVE_LIBPNG` → PNG 截图路径 |
| zlib | 1.3.2（经 libpng 传递） | PNG 压缩 |

## 验证结果

本地 CI 模拟（`ci/conan/build_and_test.sh`，见 `reports/local-ci.log`）：

```
L0_RESULT=pass: all checks passed
L1_RESULT=pass: upstream tests + test_package executed
L2_RESULT=pass: achilles --version OK
L4_RESULT=pass: patches clean
L5_RESULT=pass: bin/ has content
JC_RESULT=pass
KC_RESULT=pass
```

上游测试：`make check` 零用例（三段式清点见 `test_package/MANIFEST.yml`），
适配后补全 3 组消费者测试，实测 **49 executed, 0 failed**：

```
test_cli:        19 executed, 0 failed
test_simulation: 12 executed, 0 failed
test_gl_stack:   18 executed, 0 failed
```

真实运行证据（`SDL_VIDEODRIVER=dummy`，4x4 世界、`--fps 10`）：

```
Frames per second: 10.000000
More food!
New guy!
Frames per second: 9.800000
```

## 注意事项

- 运行需 `SDL_VIDEODRIVER=dummy`（或其它可用的软件视频驱动）；平台无窗口系统，不会有可见窗口。
- 安装后的二进制 RUNPATH 指向构建期的 conan 依赖目录；常规消费方式是 `conan install`
  拉取依赖并由 `VirtualRunEnv` 提供 `LD_LIBRARY_PATH`。
- `--fps` 上限受软件渲染（softpipe）性能约束，大世界尺寸下实际帧率会低于设定值。

---

**编译结束**: 2026-10-08
**最终状态**: built
