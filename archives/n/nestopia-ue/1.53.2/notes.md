# nestopia-ue 1.53.2 适配笔记

## 编译环境
- 构建系统: Autotools（tarball 无 configure，需 autoreconf -fi 自举）
- 编译日期: 2026-09-12
- 编译器: clang 15.0.4 / clang++ 15.0.4（-std=gnu++17）
- 目标平台: HarmonyOS PC (aarch64, musl libc)
- 状态: built（conan create 本地验证通过 + test_package 真机跑 120 帧通过）

## 上游结构分析

nestopia-ue（Undead Edition）是 Nestopia NES/Famicom 模拟器的维护 fork。
上游 v1.53.2 结构：

| 目录 | 内容 | 本适配处理 |
|------|------|-----------|
| source/core | 模拟器核心（CPU/PPU/APU/板卡/输入设备），纯 C++ | ✅ 原样构建 |
| source/core/api | 核心 C++ API（Emulator/Machine/Video/Sound/...） | ✅ 原样构建 |
| source/nes_ntsc | NTSC 视频滤波器 | ✅ 原样构建 |
| source/fltkui | Linux FLTK GUI 前端（fltkui.cpp + managers） | ⚠️ 拆分：managers 保留，GUI 裁掉 |
| source/win32 | Windows DirectX 前端 | ❌ 不构建（Makefile.am 本就不含） |
| source/7zip/unrar/kaillera | win32 前端的捆绑库 | ❌ 不构建 |

关键发现：**source/fltkui 不是单一的 FLTK 文件集**——它混合了：
1. **FLTK GUI 层**（fltkui.cpp/fltkui_archive/fltkui_cheats/fltkui_settings/uiadapter.cpp/videomanager.cpp）——依赖 FLTK + libepoxy + 桌面 GL
2. **前端无关 manager 层**（jgmanager/setmanager/chtmanager/logdriver/hasher/crc32/md5/lodepng/audiomanager/inputmanager/jg.cpp）——只依赖 JG API + SDL2 + libsamplerate
3. **JG 核心绑定**（jg.cpp，1778 行）——Nestopia 核心 ↔ JG C API 的桥接，纯 C++

## 适配策略（far2l 式裁剪）

FLTK 未在制品仓发布、OHOS 无桌面 GL（GLX/X11）栈——GUI 前端无法构建。
采用与 far2l（USEWX=NO）/actiona 相同的"裁剪未适配 GUI、保留核心"策略：

### 裁剪（0001-drop-fltk-gui-frontend.patch）
- Makefile.am：去掉 fltkui.cpp/fltkui_archive.*/fltkui_cheats.*/fltkui_settings.*/uiadapter.*/videomanager.* 源文件与 LIBEPOXY/FLTK/LIBARCHIVE 编译变量
- configure.ac：去掉 epoxy/FLTK/libarchive 强依赖（libarchive 唯一消费方是被裁掉的 fltkui_archive.cpp）；加 AC_PROG_CXX（automake 1.18 的 am__fastdepCXX conditional）；加 AC_CONFIG_MACRO_DIRS([m4])；samplerate→libsamplerate（conan .pc 名）
- logdriver.cpp：去掉 videomanager.h（GL OSD 渲染）依赖，OSD 消息改 stderr/stdout

### 新增（headless_src/，export_sources 导出）
- nstheadless.cpp/h：headless main——复用 JGManager/SettingManager/CheatManager，分配 vidinfo/audinfo 缓冲，驱动 jg_exec_frame 帧循环；支持 --version/--frames N/--nosound/--nosetup
- uiadapter_stub.cpp：inputmanager.cpp 的 UiAdapter GUI 动作转发（fullscreen/pause/mute/screenshot/quit）no-op 实现

## 依赖链

```
nestopia-ue/1.53.2
├── sdl2/2.32.10        # manager 层编译单元（audiomanager/inputmanager）链接
├── zlib/1.3.1          # 核心状态存档压缩（NstZlib.cpp）
└── libsamplerate/0.2.2 # audiomanager 音频重采样
构建工具: automake/1.18 + autoconf/2.72 + autoconf-archive/2024.10.16 + m4/1.4.19 + perl/5.42.2.3
```

libarchive 已发布（3.7.7/3.8.7）但本构建不需要（消费方被裁）。

## 踩坑记录

### 1. conan perl/5.42.2 包 Cwd.so 权限问题
autoconf/2.72 依赖 perl/5.42.2（老 rev），其 Cwd.so 是 750/file_manager——其他账号 dlopen EACCES，autoreconf 启动即挂。
**修法**：`_write_autoreconf_env()` 生成补充 env 文件（`env=["conanbuild", fix]` 列表，后者 source 顺序在后覆盖前者）：PERL=系统 hnp perl（同 5.42.2，Cwd 可用）+ PERL5LIB=conan automake 包的 share/automake-1.18（Automake/Config.pm）。
注意 `self.run(env=...)` 只接受 env 文件名列表——Python 层 os.environ 修改会被 conanbuildenv source 覆盖。

### 2. aclocal 找不到 pkg.m4
conan automake 包的 aclocal wrapper 用 `--system-acdir` **替换**系统宏目录，hnp pkg-config 的 pkg.m4 被挡住 → PKG_CHECK_MODULES 未展开（configure: syntax error near unexpected token `ZLIB,'）。
**修法**：configure.ac 加 `AC_CONFIG_MACRO_DIRS([m4])` + source() 里 vendor pkg.m4 到源码 m4/ 目录（aclocal 始终扫描源码树 m4/）。

### 3. conftest 运行失败（cannot run C++ compiled programs）
交叉编译下 configure 跑 conftest 因 libc++_shared.so 无法加载而失败。
**修法**（libcupsfilters 先例）：`cross_compiling=yes` + `ac_cv_prog_cxx_c_o=yes` + `ax_cv_cxx_compile_cxx17=yes` 缓存预设绕过运行探测；--build/--host 显式 aarch64-unknown-linux-ohos（config.sub 支持）。

### 4. samplerate .pc 名不匹配
上游 `PKG_CHECK_MODULES([SAMPLERATE], [samplerate])`，conan libsamplerate 包生成 libsamplerate.pc。
**修法**：补丁里改为 `[libsamplerate]`（头文件仍是 samplerate.h，Libs 仍是 -lsamplerate）。

### 5. 运行时 libc++_shared.so
二进制 DT_NEEDED libc++_shared.so（OHOS 工具链 soname，不在 conan 包内）。
真机/CI 设备默认 loader 路径含 /system/lib64；本机验证需 `LD_LIBRARY_PATH=/system/lib64`。

## 测试

上游 v1.53.2 autotools 构建无任何注册测试（无 check_PROGRAMS/TESTS，Makefile.am 仅 bin_PROGRAMS=nestopia；测试形态为 win32 VS 解决方案）——上游注册测试数 N=0。

test_package 消费者测试（补全）：
1. `nestopia --version` → "Nestopia UE 1.53.2 (headless)"（冒烟）
2. `nestopia --frames 120 <generated.nes>` → "Executed 120 frames"（真实模拟：最小 NROM ROM，3 指令 PRG 循环，CPU/PPU/APU 全链路执行 120 帧）

生成 ROM 在测试内联构造（16B header + 16KB PRG + 8KB CHR），不提交二进制 fixture。

## 产物
- bin/nestopia（headless 模拟器）
- share/nestopia/NstDatabase.xml（核心运行时数据库，PWD/NST_DATADIR 查找）
- share/nestopia/palettes/*.pal、shaders/*（数据文件随包）
