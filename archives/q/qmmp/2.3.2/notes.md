# qmmp 2.3.2 适配笔记（HarmonyOS PC / aarch64-linux-ohos）

## 适配概况

- Qt6 音频播放器（<https://qmmp.ylsoftware.com/>），官方源码
  <https://qmmp.ylsoftware.com/files/qmmp/2.3/qmmp-2.3.2.tar.bz2>
  （sha256 `4d8bbae619e99cfd665d96c3688d2d306f5ffc30144e07b37ca701a99e326365`，
  官方 md5 `80bda64526a9c28470c3282ac3326380`）。
- 构建系统：CMake（>=3.18，`project(qmmp)`，同时仓库内含 qmmp.pro 旧 qmake 工程）；
  上游要求 `Qt6 >= 6.2`（Widgets/LinguistTools/Network），可选 DBus/OpenGLWidgets/Sql/Multimedia。
- 产物（实测安装清单）：
  - `bin/qmmp` 应用可执行文件（含 `qmmp_launcher` 安装脚本来源 `bin/`）；
  - `lib/libqmmp.so.2.3.2`、`lib/libqmmpui.so.2.3.2`（含 `.so`/`.so.2` 符号链接）；
  - `lib/qmmp-2.3/<Category>/*.so` **50 个插件**，10 个类别目录
    （CommandLineOptions/Effect/FileDialogs/General/Input/Output/PlayListFormats/Transports/Ui/Visual）；
  - `include/qmmp/`、`include/qmmpui/` 公共头文件、`lib/pkgconfig/qmmp.pc`、`share/qmmp/`。

## 上游测试入口核验（R51）

核验命令与结果（对解压后的 qmmp-2.3.2 源码树）：

```
$ grep -rn "enable_testing\|add_test\|BUILD_TEST" CMakeLists.txt src/*/CMakeLists.txt
（无输出：上游 CMake 工程未注册任何 CTest 用例）
$ find . -type d -name tests
（无输出：无 tests/ 目录）
$ grep -n add_subdirectory CMakeLists.txt
114:add_subdirectory(src/qmmp)      115:add_subdirectory(src/qmmpui)
116:add_subdirectory(src/plugins)   117:add_subdirectory(src/app)   118:add_subdirectory(doc)
（只构建库/插件/应用/文档，无测试目标）
```

结论：**上游无自动化测试入口**（无 CTest/pytest/make check 注册项），因此
上游测试通过率一栏为 N/A；本适配按 R51 要求以 test_package 的消费者测试与
鸿蒙特有测试提供可执行验证证据（不把 test_package 冒充上游测试）。

## W0 依赖预检（conan install --build=never 全绿）

- 顶层必需：Qt6 Widgets/Network/LinguistTools；`lrelease` 由 **qt6linguisttools/6.11.1**
  提供（配方的 `QT_ADDITIONAL_PACKAGES_PREFIX_PATH` 让 Qt6Config.cmake 找到它）。
  LinguistTools 在 configure 阶段被 `execute_process` 调用生成 .qm；实测不影响构建
  （Qt6::lrelease 目标存在即通过 `get_target_property`，工具执行失败不阻塞）。
- Qt 提供者：**qtbase-sql-dbus/6.11.1**（qmmp 可选组件含 DBus/Sql，而 plain qtbase
  是 FEATURE_sql/dbus=OFF；与 ktextaddons 2.0.2 / akonadi 25.12.3 同一模式）。
- 已发布且启用：taglib/1.13.1、enca/1.19、libmad/0.15.1b、mpg123/1.33.5、flac/1.4.3、
  vorbis/1.3.7、opus/1.5.2.1、opusfile/0.12、wavpack/5.9.0、libsndfile/1.2.2、
  wildmidi/0.5.0、libarchive/3.8.7、libcdio/2.3.0、libcdio-paranoia/10.2-2.0.2、
  soxr/0.1.3、libcurl/8.5.0、qtmultimedia/6.11.1。
- 统一底层库版本（overrides）：`libogg/1.3.5`（opusfile/0.12 的**精确** pin）、
  `openssl/3.5.6`（opusfile 精确 pin，libshout/libcurl 接受 3.5.x）、
  `zlib/1.3.1.1`（libarchive/libcurl 要求，taglib 为 minor pin）。
  ohpcd 的 libogg 两套 pin 互斥：libvorbis/1.3.7 需要 libogg/1.3.6，而 opusfile/0.12
  锁死 libogg/1.3.5 → 取舍：保留 opusfile 与独立 vorbis/1.3.7 包（提供 vorbis.pc/
  vorbisfile.pc，无 libogg 依赖），**放弃 Icecast 输出插件**（libshout/2.4.6）。
- 未启用（ohpcd 未发布或平台不适用）：libxmp、libgme、faad2、libcddb、libbs2b、
  mpcdec、pipewire、alsa-lib、xcb（全局热键需要 X11）、projectM（需要 OpenGL，
  已发布 qtbase 为 FEATURE_opengl=OFF）、ffmpeg（本适配未引入）。

## 平台适配要点

1. **pkg-config 是本构建的主依赖通道**：qmmp 每个插件都先 pkg_search_module/
   pkg_check_modules，再 `if(<VAR>_FOUND)` 决定是否构建。已发布依赖包自带的 .pc
   常把 `prefix` 烤成构建机目录（`/…/conan2/p/b/xxx/p`）或 `/usr/local`（实测
   taglib/libcdio/libvorbis/Qt6 等），会让 CMake 生成含不存在 include 目录的
   imported target 而 configure 失败。配方用 **PkgConfigDeps + prefix 修正 shim**
   覆盖：`<generators>/` 与 `<generators>/pkgconfig-shims/` 置于 PKG_CONFIG_PATH 最前，
   shim 把 `prefix/exec_prefix/libdir/includedir/bindir/datadir` 中指向包目录之外的
   取值就地改成当前包目录。
2. **Qt 双树与附加 Qt 包**：qtbase-sql-dbus 作为 Qt 提供者并置于 CMAKE_PREFIX_PATH
   最前；qtmultimedia / qt6linguisttools / qtshadertools / qtsvg / qtdeclarative 通过
   `QT_ADDITIONAL_PACKAGES_PREFIX_PATH` 暴露给 Qt6Config.cmake。
3. **soname 旗标**：CMake 无 Platform/HarmonyOS 模块，配方显式设置
   `CMAKE_SHARED_LIBRARY_SONAME_CXX_FLAG/C_FLAG=-Wl,-soname,`，使 libqmmp/liblqmmpui
   带 DT_SONAME（实测 `libqmmp.so.2` / `libqmmpui.so.2`）。
4. **插件可重定位（package() 阶段修正 DT_NEEDED）**：链接没有 DT_SONAME 的依赖库时，
   链接器把打开时的**绝对路径**写进 DT_NEEDED（实测 libvorbisfile/libvorbisenc/
   libsoxr/libQt6Multimedia 均无 SONAME）。配方在 package() 解析自己产物的
   `.dynamic`/`.dynstr`，把这些条目就地缩短为纯文件名（等长写回、尾部补 NUL），
   实测重写 6 条 → 50/50 插件 DT_NEEDED 全部为纯文件名，模块在任意机器上按
   soname/LD_LIBRARY_PATH 解析。
5. **源码补丁（1 条，纯可移植性，无平台宏）**：`skinned` UI 插件的
   `symboldisplay.cpp` 在 `Q_OS_LINUX` 分支调用 GNU 扩展 `exp10()`，本平台 C 库不声明
   该符号 → 改为等价 `pow(10, i)`（去掉 GNU-only 分支）。
6. **构建参数**：`USE_SKINNED=ON`、`USE_ENCA=ON`、`USE_DIR_ASSOC=OFF`、C++17；
   未引入任何上游没有的选项。

## 实测结果（本机 conan create，2026-10-10）

- 构建：`602/602` 目标，0 error（Ninja -j8；设备文件系统不支持 FIFO，Makefile
  jobserver 不可用，故本地用 `-c tools.cmake.cmaketoolchain:generator=Ninja`）。
- 包：`qmmp/2.3.2@ohpcd/stable#b2def26072d6349081d5f9a38bd49f57:252ad1fc98510606b7e249623ad163a449058974#a49b12ad7612138bbe4fe75235203b2b`
  （package_id `252ad1fc98…`）。
- 插件启用清单（configure 摘要实测）：HTTP、MPEG(libmad)、FLAC、Ogg Vorbis、Wave
  (libsndfile)、WavPack、CUE、CD Audio、Midi(wildmidi)、Ogg Opus、Archive、Null 输出、
  **Qt Multimedia 输出**、SoX Resampler、LADSPA、Crossfade、Extra Stereo、File Writer、
  Mono⇄Stereo、Analyzer、MPRIS、Scrobbler、ListenBrainz、Tray、Notifier、Lyrics、
  UDisks、GNOME 热键、File ops、Cover manager、KDE 通知、Audio converter、ReplayGain、
  Stream browser、Track change、Copy/Paste、History、Sleep inhibition、Media library；
  禁用：Musepack/MOD/FFmpeg/AAC/Game music/SID/ALSA/JACK/Pulse/PipeWire/OSS/Icecast/
  BS2B/ProjectM/Windows 专属插件。
- 上游测试：无自动化入口（见上），N/A。
- test_package（消费者）：**12/12 断言通过** —— `Qmmp::strVersion()==2.3.2`、
  `configDir()/pluginPath()` 非空、`findPlugins("Input/")` 逐项确认 flac/vorbis/opus/
  mpeg/sndfile/wavpack/wildmidi/archive/cue 九个解码器、Output/Effect 非空、
  `CueParser` 解析内存 CUE 表（files=1、offset(2)=210000ms、createPlayList()==2 轨）。
- test_package（**鸿蒙专项**）：全部通过 —— libqmmp/liblqmmpui 的 DT_SONAME、
  50/50 插件为可重定位 ELF64（DT_NEEDED 无含 `/` 路径）、10 个插件类别目录齐备、
  解码器集合与 `bin/qtmultimedia` 输出插件、`bin/qmmp` 应用产物、offscreen
  Qt Widgets 运行链路（platform=offscreen）。
- 日志：`reports/conan-create.log`（构建+测试全量输出）。

## 已知限制

1. 上游无自动化测试，本适配的验证证据来自 test_package（消费者 + 鸿蒙专项）。
2. Icecast（libshout）输出插件未启用：其传递依赖 libvorbis/1.3.7 需要 libogg/1.3.6，
   与 opusfile/0.12 精确锁定的 libogg/1.3.5 在同一依赖图内互斥（见 W0 取舍）。
3. `Qmmp::pluginPath()` 的 QMMP_PLUGIN_DIR 编译期常量是 configure 时的安装前缀
   （conan 默认取配方目录），消费者应设置 `QMMP_PLUGINS` 环境变量或把插件放在
   `<可执行文件目录>/../lib/qmmp-2.3`（上游 fallback 布局）；test_package 已按
   `QMMP_PLUGINS` 方式验证。（插件目录本身随包发布在 `lib/qmmp-2.3/`。）
4. 平台不适用而禁用：ALSA/JACK/PulseAudio/PipeWire/OSS（OHOS 无这些音频后端）、
   全局热键（需要 X11）、Windows 专属输出/任务栏插件。
