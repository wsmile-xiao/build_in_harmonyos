# pc6001vx 4.3.0 适配笔记（HarmonyOS PC aarch64）

## 软件识别

- **pc6001vx 4.3.0** = eighttails 的 PC-6001/PC-6001mkII/PC-6601 模拟器
  （PC6001V 的跨平台版），上游仓库 <https://github.com/eighttails/PC6001VX>，
  tag `v4.3.0`，commit `2b927d5bcf229734eb35df472571ef863694b2d5`，
  许可证 LGPL-2.1。
- **任务情报与上游实际不符（重要）**：派活提示词按"SDL2 模拟器"描述本库，
  但 4.3.0 的构建入口 `PC6001VX.pro` 是 **Qt6 + qmake** 工程，SDL2 只服务
  手柄输入（`PKGCONFIG += sdl2`，未找到时可 `NOJOYSTICK` 关闭）。按执行规范
  第 12 条"以 tarball 实际为准"，本适配按 Qt6/qmake 真实构建链推进；SDL2 仍
  作为真实依赖保留（静态链接，见下）。

## 源码获取

- URL: `https://github.com/eighttails/PC6001VX/archive/refs/tags/v4.3.0.tar.gz`
  （等价 codeload 地址写在同一 conandata `sources.url` 列表里）
- sha256: `aee8c8175d81314ebf8698b861b76cc30ae5c1ffae2265799b6204f5e7a9990c`
  （5991358 B；两个独立镜像分别下载后哈希一致）
- tarball 顶层目录 `PC6001VX-4.3.0/`，conan `strip_root=True`。

## 上游测试审计（0 个上游测试）

上游**完全没有测试套件**（详见 `test_package/MANIFEST.yml` 的逐项审计）：
tarball 无 tests 目录、无 `.github/` 工作流；`PC6001VX.pro` 只有单一
`TEMPLATE = app` 目标，无 `CONFIG(testcase)`/check 目标/QTest 文件；README
只给构建步骤；上游 AppImage 发布脚本也只有 qmake+make+linuxdeploy。
因此本库的测试证据全部来自消费者侧（test_package），不声明任何上游用例数。

## 构建系统与关键适配点

产物：单可执行文件 `bin/PC6001VX`（qmake shadow build；上行 `make install`
未定义 INSTALLS，故配方按构建产物手工打包）。

### 1. Qt6 依赖与 qtbase 能力面（NO_HWACCEL）

OHOS 制品仓 `qtbase/6.11.1` 构建时 `INPUT_opengl=no`/`FEATURE_opengl=OFF`
（不提供 Qt6OpenGLWidgets），QPA 插件只有 `minimal` 与 `offscreen`。上游
`PC6001VX.pro` 在未定义 `NO_HWACCEL` 时会 `QT += opengl openglwidgets`，
故适配定义 **NO_HWACCEL**（上游支持的开关，`renderview.cpp` /
`p6vxapp.cpp` / `qtel6.cpp` / `configdialog.cpp` 都有对应 `#ifndef`
分支）。副作用：显示走非硬件加速渲染路径。

### 2. Qt Multimedia 是独立 conan 包（补丁 0001）

上游 `QT += multimedia`（Qt Multimedia 提供 `QAudioSink` 音频输出，且
`src/Qt/wavfile.cpp` 参与构建）。但 conan 的 Qt 是 split-prefix 安装：
`qtmultimedia` 的模块文件 `mkspecs/modules/qt_lib_multimedia.pri` 位于自己的
前缀，而其中 `QT.multimedia.libs = $$QT_MODULE_LIB_BASE` /
`.includes = $$QT_MODULE_INCLUDE_BASE` 在包含时会被解析成 **qtbase** 的
lib/include 目录，指向的路径里既没有 `libQt6Multimedia` 也没有
`QtMultimedia/` 头文件。故补丁 0001 让 `.pro` 在 `P6VX_QTMULTIMEDIA_INCDIR`
非空时改用配方传入的显式 `INCLUDEPATH`/`LIBS`，否则保持上游
`QT += multimedia` 行为（Linux 原生构建不受影响）。

### 3. 音频后端现状（已知限制）

OHOS 制品仓 `qtmultimedia/6.11.1` 只带测试用的 mock 多媒体插件
（`plugins/multimedia/libmockmultimediaplugin.a`），没有可用音频后端，真机
运行期 Windows 之外的音频设备枚举会为空。故音频输出"接口/代码路径完整、
编译链接通过"，但**真机有声输出待平台补齐 Qt Multimedia 后端**（无头冒烟
不经音频初始化，不受影响）。

### 4. lrelease 来自 qttools（CONFIG += lrelease embed_translations）

上游 `.pro` 有 `CONFIG += lrelease embed_translations`（.ts → .qm 并嵌入
资源），而 qtbase 不含 `lrelease`（Qt Linguist 工具在 `qttools`）。适配用
`tool_requires("qttools/6.11.1")` 并把 `QT_TOOL.lrelease.binary` 指向包内
`bin/lrelease`（`qtPrepareTool` 优先读该变量），翻译功能保留。
坑：`qttools` 的 `lrelease` **没有 RUNPATH**（qtbase 的 moc/uic/rcc 有
`$ORIGIN/../lib`），构建期必须把它能看到的 Qt 库目录放进 `LD_LIBRARY_PATH`，
否则 lrelease 起不来，报一串 `Error relocating ... symbol not found`。

### 5. SDL2 手柄输入（静态链接）

`PC6001VX.pro` 用 `packagesExist(sdl2)` 探测并 `PKGCONFIG += sdl2`。制品仓
`sdl2/2.30.10` 是静态包（`libSDL2.a`），但其自带 `sdl2.pc` 不可重定位
（`prefix=/`），故配方在 `generate()` 用 `PkgConfigDeps` 生成 conan 重写版
`.pc` 并把生成目录加入 `PKG_CONFIG_PATH`，qmake 由 `PKGCONFIG += sdl2` 得到
`-lSDL2` 并静态链接。结果：`bin/PC6001VX` 的 DT_NEEDED 里**没有** libSDL2，
手柄功能代码已编入（test_package 断言 `SDL_JoystickOpen` 符号存在）。

### 6. X11（xcb）后端关闭（补丁 0001）

上游对 `unix:!macx:!android:!ios` 一律 `DEFINES += USE_X11` +
`PKGCONFIG += x11`。OHOS 无 X server、qtbase 也没有 xcb 插件，故补丁把这段
改为 `!contains(DEFINES, P6VX_NO_X11)` 包裹，由配方传 `P6VX_NO_X11`。
注意：`harmonyos-clang` mkspec 复用 `linux.conf`，`QMAKE_PLATFORM` 是
`linux unix posix`，**没有** `ohos`/`harmonyos` scope，无法用 qmake scope
判平台，只能用显式开关。

### 7. NOSINGLEAPP：OHOS 无 SysV 信号量

上游默认编入 bundled `SingleApplication`（`QSharedMemory` + `QLocalServer`）
实现单实例。OHOS 上 `semget` 系统调用不可用（实测直接 `Bad system call`
SIGSYS，退出码 159），而 Qt 的 `QSharedMemory` 依赖 `QSystemSemaphore`
（SysV 信号量）做锁，故窗口程序在 `QApplication` 构造阶段就死。
适配定义 **NOSINGLEAPP**（上游支持的配置，Android 构建同款），
`p6vxapp.h` 会切到 `using ParentAppClass = QApplication;`。
已知限制：不再阻止多实例（其余行为一致）。

### 8. 无头冒烟设计（先审 display 依赖，再定断言）

`main()` 先构造 `QApplication`（**必然需要 QPA 平台插件**）再解析命令行，
所以纯 IO 退出路径必须在 QPA 就绪之后：
- `QT_QPA_PLATFORM=offscreen bin/PC6001VX --version` → `PC6001VX 4.3.0`，rc=0；
- `QT_QPA_PLATFORM=offscreen bin/PC6001VX --help` → 选项清单，rc=0；
- `QT_QPA_PLATFORM=minimal …--version` → 同上（另一插件路径）；
- 未知选项 → rc=1 + `Unknown option '…'`；
- 不给 `QT_QPA_PLATFORM`（默认 xcb 不存在）→ **优雅失败**：Qt 打印
  `Could not find the Qt platform plugin "xcb"` +
  `Available platform plugins are: minimal, offscreen`，rc=134（SIGABRT）。
**刻意不跑**正常启动路径：它会进 Qt 事件循环常驻（无头环境里等于挂死），
不是可判定的冒烟（对应执行规范第 9 条 GUI 库无头测试原则）。

### 9. 打包与签名

`make install` 无 INSTALLS 定义 → 手工打包 `bin/PC6001VX` + LICENSE。OHOS
要求可执行文件带有效 `.codesign`：OHOS clang 链出的 ELF 已含空 `.codesign`
段，配方按仓内既有做法用 `binary-sign-tool sign -selfSign 1` 重签（先
`llvm-objcopy --remove-section .codesign` 去掉旧签名），签后可正常执行。
`package_info()` 额外把 qtbase 的 `plugins/` 注入 `QT_PLUGIN_PATH`，使消费者
运行环境能找到 `minimal`/`offscreen` 平台插件。

## 依赖版本

| 依赖 | 版本 | 角色 |
|------|------|------|
| qtbase | 6.11.1 | Qt Core/Gui/Widgets/Network + qmake6/moc/uic/rcc |
| qtmultimedia | 6.11.1 | 声音输出（`QAudioSink`）与 `wavfile.cpp` |
| sdl2 | 2.30.10 | 手柄输入（静态 `libSDL2.a`） |
| qttools | 6.11.1 | `tool_requires`：lrelease（翻译资源） |

## 补丁说明

| 补丁 | 文件 | 内容 |
|------|------|------|
| 0001-PC6001VX.pro-ohos-qmake.patch | `PC6001VX.pro` | ①X11(xcb) 后端改为可关（`P6VX_NO_X11`）；②`QT += multimedia` 在收到 `P6VX_QTMULTIMEDIA_INCDIR` 时改用显式 `INCLUDEPATH`/`LIBS` |

补丁纪律：per-file `diff -u --label a/PC6001VX.pro --label b/PC6001VX.pro`；
黄金验证 = `git apply --check` 通过 + 干净 `orig/` 树应用后与 `work/` 树
`diff` 为空 + GNU patch 可反向 `--dry-run`。

## 验证结果

```bash
$ conan create archives/p/pc6001vx/4.3.0 -pr:h ci/conan/profiles/ohos-aarch64 -pr:b ci/conan/profiles/ohos-aarch64 --build=missing
# rc=0（从零构建 + test_package，实测 360s）
# 构建：qmake6 + make -j20，0 个 error（682 条上游代码 warning，未做任何压制）
# 打包：package(): Packaged 2 files: LICENSE, PC6001VX（OHOS 重签名成功）
# test_package（真实执行包内二进制）：
#   ELF check: AArch64 ELF64 little endian PIE
#   ELF check: PIE + RELRO + non-executable stack + musl interpreter
#   ELF check: .codesign section present (binary re-signed for OHOS)
#   ELF check: DT_NEEDED whitelist ok (7 entries, SDL2 static)
#   ELF check: SDL2 joystick entry points linked in
#   RESULT: 14 passed, 0 failed

$ QT_QPA_PLATFORM=offscreen bin/PC6001VX --version      # PC6001VX 4.3.0（rc=0）
$ QT_QPA_PLATFORM=minimal   bin/PC6001VX --version      # PC6001VX 4.3.0（rc=0）
$ QT_QPA_PLATFORM=offscreen bin/PC6001VX --help         # 选项清单（rc=0）
$ bin/PC6001VX --no-such-option                         # Unknown option（rc=1）
$ bin/PC6001VX --version                                # Qt 平台插件缺失诊断（rc=134，非零）
```

上游无测试套件（审计见 `test_package/MANIFEST.yml`），故不存在"上游用例
通过率"分子；可执行用例全部来自消费者侧，共 **20 项断言**（14 项运行时冒烟 +
6 项 ELF/打包断言），实测 **20/20 通过**。


## 交付物

| 文件 | 说明 |
|------|------|
| `bin/PC6001VX` | Qt6 模拟器主程序（AArch64 ELF64 PIE，musl，已重签名，静态含 SDL2） |
| `licenses/LICENSE` | 上游 LGPL-2.1 许可证 |

## 注意事项 / 已知限制

1. **无桌面 QPA 插件**：qtbase/6.11.1 只提供 `minimal`/`offscreen`，真机桌面
   窗口显示需要平台补齐 Qt 的 OHOS QPA 插件。CI 可验证到"二进制可执行 +
   无头退出路径"，图形窗口渲染未在真机验证。
2. **音频输出**：见上文第 3 点（后端插件缺失）。
3. **多实例**：NOSINGLEAPP 后不再单实例约束（第 7 点）。
4. **硬件加速**：NO_HWACCEL，走软件渲染路径。
5. 手柄输入代码已编入且 SDL2 静态链接，但真机手柄设备（`/dev/input`）未实测。
