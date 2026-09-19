# zmusic 1.3.0 适配笔记

## 编译环境
- 构建系统: cmake（上游 `cmake_minimum_required(VERSION 3.13...3.19)`）
- 编译日期: 2026-09-18
- 编译器: clang/clang++ 15.0.4（OHOS aarch64，profile `ohos-aarch64`）
- 状态: published
- 目标: OpenHarmony / HarmonyOS PC aarch64（os=OHOS, arch=armv8, Release）

## 软件背景
zmusic 是 GZDoom 音乐系统的独立库（供 GZDoom / Raze / PrBoom+ 使用）。
上游把绝大多数编解码器以 `thirdparty/` 内置方式提供（miniz、game-music-emu、
dumb、adlmidi、opnmidi、timidity、timidityplus、wildmidi、oplsynth、libxmp、
fluidsynth），因此外部依赖面很小。构建产出两个库：
- `libzmusic.so` —— 完整版（含 ADL/OPN/Timidity/WildMidi/OPL 合成器，GPLv3）
- `libzmusiclite.so` —— 精简版（仅保留 FluidSynth，规避 GPL 传染）

## 编译步骤

```bash
# 依赖（全部已发布到制品仓，R36 满足）
conan install --requires=glib/2.88.3.1 -pr:h=ohos-aarch64 -pr:b=ohos-aarch64 \
    -g PkgConfigDeps -g CMakeToolchain

cmake -S <src> -B build \
    -DCMAKE_TOOLCHAIN_FILE=conan_toolchain.cmake \
    -DCMAKE_BUILD_TYPE=Release -DBUILD_SHARED_LIBS=ON \
    -DDYN_SNDFILE=OFF -DDYN_MPG123=OFF
cmake --build build -j4
cmake --install build
```

`conan create archives/z/zmusic/1.3.0 -pr:h=ohos-aarch64 -pr:b=ohos-aarch64`
全流程（含 test_package）一次通过，无需任何源码补丁。

## 依赖分析（W0 预检结果）

| 依赖 | 用途 | 是否必需 | 制品仓 |
|---|---|---|---|
| glib/2.88.3.1 | 内置 `thirdparty/fluidsynth` 通过 `pkg_search_module(GLIB REQUIRED glib-2.0)` 强制依赖 | **必需** | 已发布 |
| libsndfile/1.2.2 | WAV/FLAC/OGG 等解码（`source/CMakeLists.txt` → `find_package(SndFile)`） | 可选（已启用） | 已发布 |
| mpg123/1.33.5 | MP3 解码（`find_package(MPG123)`） | 可选（已启用） | 已发布 |
| alsa-lib | System MIDI（`music_alsa_mididevice.cpp`） | 可选（**未启用**） | 已发布 |

未启用 ALSA 的原因：OHOS 上不存在 ALSA 设备节点（`/dev/snd`），启用
`HAVE_SYSTEM_MIDI` 只会编入无法工作的 ALSA MIDI 后端；不提供 alsa-lib 时
`find_package(ALSA)` 自然失败，上游会跳过该后端并回退到 FluidSynth 等合成器。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `pkg_search_module(GLIB REQUIRED glib-2.0)` 找不到 glib，configure 直接失败 | CMakeDeps 只生成 `xxx-config.cmake`，不生成 `.pc`；内置 fluidsynth 走 pkg-config 查找 | `generate()` 中追加 `PkgConfigDeps(self).generate()`，生成 `glib-2.0.pc` 并把 `PKG_CONFIG_PATH` 注入构建环境 |
| 2 | 上游 `DYN_SNDFILE` / `DYN_MPG123` 默认 `ON`，解码器走运行时 `dlopen` | 上游为发行版打包便利设计；OHOS 上 `dlopen` 第三方 `.so` 路径不可控，解码器会静默失效 | 置 `DYN_SNDFILE=OFF` / `DYN_MPG123=OFF`，改由上游 `cmake/FindSndFile.cmake`、`cmake/FindMPG123.cmake`（老式 `find_path`/`find_library`）链接期绑定到已适配包 |
| 3 | `init-build` 把构建系统误判为 autotools，导致配方模板取用 autotools 版 | 源码树无 `configure.ac` 判定依据时回退默认 | 手工把 `manifest.yaml` 的 `build.system` / `build_system` 修正为 `cmake` 后重跑 `conan-init`，取到 `conanfile-cmake.py.tmpl` |
| 4 | `conan create` 编译阶段大面积 `make: *** Error 1`，但日志中**没有任何 `error:` 输出**；在**同一个** conan 生成的构建目录里手工跑 `make -j4` 却能 100% 编译通过 | build() 用 `self.run("cmake --build ...")` 执行构建时必现失败；改为 `subprocess.run(..., capture_output=True)` 后稳定通过。**与并行度无关**（-j20/-j4/-j2/-j1 均复现），也与源码/编译器无关（手工重跑同样的命令必成功）。根因锁定在 conan `self.run` 的实时管道读取路径与 OHOS/HMDFS 构建目录的交互：子进程（clang）被异常终止且不留错误输出 | build() 与 test_package 均改用 `subprocess.run(cmd, shell=True, capture_output=True, text=True, cwd=self.build_folder, env=os.environ)`，并保留 3 次重试兜底。并行度同时收敛到 4（上游 thirdparty 存在 inst_db/nuked_opl3 等超大翻译单元，按 CPU 核数并行内存压力过大）。**排查提示**：make 报 Error 1 却无 `error:` 行、且手工重跑即成功时，不要再怀疑源码或并行度，直接换执行方式 |

## 源码修改

无。上游源码在 OHOS aarch64 / clang 15 下零补丁编译通过（`patches/` 为空）。

## 上游测试清点（R51）

结论：**上游 1.3.0 不含任何测试用例**。复现命令与实际输出：

```bash
$ cd zmusic-1.3.0 && ls -a
.
..
.edit-tracker.json  .github  .gitignore  CMakeLists.txt  README.md
cmake  include  licenses  samples  source  thirdparty  vcpkg.json
# → 顶层无 tests/ 或 test/ 目录

$ find . -maxdepth 2 \( -iname "*test*" -o -iname "*spec*" \) -print
# → 无任何输出

$ grep -rn "enable_testing\|add_test\|include(CTest)" --include=CMakeLists.txt .
# → 无任何输出（全仓 CMakeLists.txt 未注册 ctest）

$ grep -in "test" README.md
# → 无任何输出（README 未提及测试命令）
```

补充判定：`samples/list_midi_devices` 是示例程序，且未被根 `CMakeLists.txt`
`add_subdirectory`，不属于测试。

因此适配后新增的测试全部由 `test_package` 承担（计入鸿蒙特有测试）。

## 依赖版本

- glib/2.88.3.1（传递依赖：libffi、pcre2、proxy-libintl、zlib）
- libsndfile/1.2.2
- mpg123/1.33.5

## 验证结果

```bash
$ ./test_zmusic
ok  : ZMusic_GetConfiguration() 返回非 NULL
ok  : 配置项数量 > 0
     config entries = 79
ok  : ZMusic_OpenSongMem() 打开 MOD 成功
     sampleRate=44100 channels=2 bufferSize=32768
ok  : ZMusic_GetStreamInfo() 采样率有效
ok  : ZMusic_GetStreamInfo() 声道数有效
ok  : ZMusic_Start() 启动播放
ok  : ZMusic_FillStream() 渲染 PCM 成功
     FillStream -> 1, peak amplitude = 0.390625
ok  : 渲染出的 PCM 含非零音频数据（DUMB 解码链路可用）
ok  : ZMusic_IdentifyMIDIType() 识别 MThd 为 MIDI_MIDI

ALL PASS (failures=0)
```

关键结论：渲染峰值 0.390625（非零），证明内置 DUMB 解码器 + 混音 + PCM 输出
链路在 OHOS aarch64 上真实可用，而非仅"能链接、调用即返回"的空壳适配。

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| `libzmusic.so` | ~7 MB | 完整版音乐库（含全部合成器） |
| `libzmusiclite.so` | ~5 MB | 精简版（仅 FluidSynth） |
| `include/zmusic.h` | — | 公开 C API 头文件 |
| `lib/cmake/ZMusic/*.cmake` | — | 上游 CMake 包配置（`ZMusic::zmusic` / `ZMusic::zmusiclite`） |

纯库包，无可执行文件（上游 `samples/` 不参与构建），故无需 `commands.json`。

## 注意事项

- **许可证**：完整版 `libzmusic.so` 含 GPLv3 组件（libADL、libOPN）与 LGPLv3
  （WildMidi）；下游若需规避 GPL 传染，应链接 `libzmusiclite.so`。
- **运行时**：`shared=True` 时需要 conan 运行时环境提供 `libglib-2.0.so`；
  通过 `conanrun` 环境（test_package 已使用 `env="conanrun"`）自动注入。
- **FluidSynth 音色**：内置 fluidsynth 需要外部 SoundFont（.sf2）才能发声，
  属运行时数据，不在本包范围内；缺少时 MIDI 播放为静音，不影响库可用性。
---

**编译结束**: 2026-09-18 22:57
**最终状态**: published
