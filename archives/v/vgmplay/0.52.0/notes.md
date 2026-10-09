# vgmplay 0.52.0 适配笔记

## 库简介

vgmplay（作者 Valley Bell）是 VGM（Video Game Music）文件的官方命令行播放器。
本包适配的是 `vgmplay-libvgm` 仓库的 0.52.0 tag——它基于 **libvgm**（VGMPlay 的
模块化重写）构建，本身只提供命令行前端，不含声音模拟核心。

- **上游仓库**: https://github.com/ValleyBell/vgmplay-libvgm
- **版本**: 0.52.0（tag，Changes 见源码根 `Updates.txt`）
- **许可证**: GPL-2.0-or-later（链接 libvgm，组件混合许可）
- **构建系统**: CMake ≥ 3.6，语言 C + C++

## W0 依赖检查（2026-09-29，ohpcd 制品仓）

| 依赖 | 类型 | ohpcd 状态 | 说明 |
|------|------|-----------|------|
| libvgm/g20260121 | conan | ✅ 已发布 | 声音模拟 + VGM/S98/DRO/GYM 播放引擎（同仓库已适配） |
| inih/r58 | conan | ✅ 已发布 | INI 配置解析（上游 bundled 为 submodule，tarball 缺失） |
| zlib/1.3.2 | conan（libvgm 传递） | ✅ 已发布 | gzip .vgz 解压 |
| pthread / m / iconv | 系统（musl） | — | 经 libvgm 传递 |

**结论：无缺失依赖，不需要拆依赖库单独适配。**

## 源码包与 submodule 陷阱

上游 `archive/refs/tags/0.52.0.tar.gz`（60 KB，sha256
`dd48e2d9...3da820`）**不包含 git submodule**：

```ini
[submodule "libs/inih"]      # INI 解析 → 改由 Conan inih/r58 提供
[submodule "libs/wingetopt"] # MSVC getopt → OHOS 不需要
[submodule "libvgm"]         # 模拟核心 → 改由 Conan libvgm/g20260121 提供
```

因此 CMakeLists.txt 中 `libs/inih/ini.c` 的 bundled fallback 在 OHOS/Conan
环境下必然缺失，必须走依赖包路径（见 patch）。

## CMake 选项决策

| 选项 | 上游默认 | 配方值 | 原因 |
|------|----------|--------|------|
| MEDIA_CONTROLS | 自动探测（UNIX 找 D-Bus） | **OFF** | OHOS 无 D-Bus 开发包；显式关闭保证确定性 |
| CMAKE_SYSTEM_NAME | — | Linux | OHOS 基于 Linux 内核，CMake 不识别 OHOS |
| CMAKE_SYSTEM_PROCESSOR | — | aarch64 | 目标架构 |
| CMAKE_{C,CXX}_BYTE_ORDER | — | LITTLE_ENDIAN | aarch64 小端，跳过探测 |

## Patch 0001 说明（patches/0001-conan-deps-and-targets.patch）

两处修改：

1. **inih 检测改为 Conan 优先**：原 CMake 只走 `pkg_check_modules(INIH inih)`，
   pkg-config 找不到时 fallback 到 `libs/inih/ini.c`（tarball 缺失）。
   改为先 `find_package(inih QUIET CONFIG)` → 链接 `inih::inih`（Conan
   CMakeDeps 生成），失败再退回 pkg-config / bundled。

2. **libvgm 链接 target 聚合**：原 CMake 链接
   `libvgm::vgm-utils vgm-audio vgm-emu vgm-player` 四个分库 target（这是 libvgm
   submodule 原生 install 导出的）。Conan libvgm 包只导出聚合 target
   `libvgm::libvgm`（cpp_info.libs 四件套 + zlib/pthread/m 传递），改为链接它。

## 非交互测试入口（test_package）

vgmplay 是交互式播放器，但 `main.cpp` 提供了不打开音频设备、不读 stdin 的
自检命令：

- `vgmplay --version` → 打印 `VGMPlay 0.52.0, supports VGM 1.72` 后退出 0
- `vgmplay --lib-info` → 调用 libvgm 的 `GetConfigurableDevices()` /
  `sndEmu_Devices[]`，列出支持格式与声音芯片，退出 0

test_package 用 5 条 `grep -q` 断言验证版本串、VGM 1.72、lib-info 横幅、
VGM 格式引擎、YM2612 核心已链接（证明 libvgm-emu 进入最终二进制）。

## 本机前置验证记录（2026-09-29，Windows）

- [x] 源码 URL/sha256：codeload 下载校验 `dd48e2d971ff8e03c749abbc693a41167a3541169f45689632ca4152d33da820`
- [x] W0：libvgm/g20260121、inih/r58、zlib/1.3.2 均已发布到 ohpcd
- [x] 构建系统识别：CMake ≥ 3.6（C + C++），find_package(libvgm REQUIRED)
- [x] submodule 缺失风险已识别并通过 Conan 依赖 + patch 解决
- [x] patch 0001 生成（unified diff，LF）
- [x] **真机 conan create + test_package 通过**（frp-tip:56267）

## 真机验证结果（2026-09-29，frp-tip:56267）

- conan create 成功，包 ref：
  `vgmplay/0.52.0#473784bd45df872dcc0514886da62f21:17da258aaaad6273c8f0473bba9cb142e3b2818e`
- test_package 5 条断言全部通过：
  1. `--version` 含 `VGMPlay 0.52.0`
  2. `--version` 含 `supports VGM 1.72`
  3. `--lib-info` 含 `Supported formats`
  4. `--lib-info` 含 `- VGM`
  5. `--lib-info` 含 `YM2612`

## 真机踩坑记录（frp-tip:56267）

### 1. 编译器路径与 profile

这台机器的 clang/clang++/cmake 在 `/storage/Users/currentUser/usr/local/bin/`，
**不是** profile `ohos-aarch64` 里写的 `/data/service/hnp/bin/clang`（该路径在此机
不存在）。conan 包已发布的 libvgm 是用正确路径编的，所以 `--build=missing` 只编
vgmplay 本身，不重编 libvgm，内存安全（jobs=1，free 500MB 未 OOM）。

### 2. WavWrt_SetFileName 未声明

playctrl.cpp:1632 调用 `WavWrt_SetFileName`，该声明在 libvgm 的
`audio/AudioStream_SpcDrvFuns.h` 中被 `#ifdef AUDDRV_WAVEWRITE` 包住。OHOS 上
libvgm 仅构建 WaveWriter 驱动，需在 generate() 加
`tc.preprocessor_definitions["AUDDRV_WAVEWRITE"] = "1"`。

### 3. OHOS ELF 代码签名：--code-sign

clang++ wrapper 自动传 `-Wl,--code-sign`，给 ELF 嵌入 OHOS 代码签名段。
**任何事后修改 ELF 的操作（strip、patchelf 改 rpath）都会破坏签名，导致内核
拒绝 execve（"Operation not permitted", exit 126）。**

### 4. cmake.install() 破坏签名（关键）

CMake install(TARGETS) 会清除 RUNPATH（Conan CMakeToolchain 默认
CMAKE_INSTALL_RPATH 为空）。这个清除过程改写了 ELF 的 .dynamic 段，破坏了
--code-sign 签名。现象：build 目录的 vgmplay 能跑，package 目录的同名文件
sha256 不同且不能跑。

**修复**：package() 不调用 cmake.install()，改用 `conan.tools.files.copy`
直接复制 build 目录的 vgmplay 和数据文件，保持 ELF 原样不被改写。

## 下一步真机 / shadow CI 命令

```sh
# 单包 shadow CI 门禁（L0-L5）
CI_PACKAGES="archives/v/vgmplay/0.52.0" zsh ci/conan/build_and_test.sh
```

真机手动 conan create（frp-tip:56267）：

```sh
# profile: $HOME/.conan2/profiles/ohos-frp（基于 ohos-aarch64，改 compiler 路径 + jobs=1）
export PATH=$HOME/.local/bin:$HOME/usr/local/bin:/data/service/hnp/bin:$PATH
export TMPDIR=$HOME/tmp
conan create . --build=missing -pr=ohos-frp
```

预期：
- L0/L1：配方语法 + test_package 5 断言通过
- L2：application 包可 skip（无库 API 可供链接测试）
- L5：bin/vgmplay 产物存在，`vgmplay --version` 输出 0.52.0
