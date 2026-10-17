# libvgm g20260121 适配笔记

## 库简介

libvgm（作者 Valley Bell）是 VGMPlay 大部分组件的模块化重写，用于播放视频游戏音乐。
提供四个子库：

| 子库 | 语言 | 内容 |
|------|------|------|
| vgm-utils | C | 数据加载器（File/Memory，gzip 实时解压）、线程/互斥工具、字符集转换（iconv） |
| vgm-emu | C | 芯片模拟核心（SN76496、YM2612、YM2151、YM2413、OPL*、C140、C352、ES550x、SCSP 等 70+） |
| vgm-player | C++ | 文件格式播放器：VGM、S98、DRO、GYM |
| vgm-audio | C | 音频输出库（OHOS 上仅构建 WaveWriter 文件输出） |

- **上游仓库**: https://github.com/ValleyBell/libvgm
- **版本**: g20260121 = master 分支 commit `57585ea7a53f56bcf5a56071068c6ef9154ca299`
  （2026-01-21 当天最后一次提交 "simplify list returned by GetSongDeviceInfo()"，上游无 release tag）
- **许可证**: 上游**无顶层 LICENSE 文件**；组件自带各自许可（33 个 MAME BSD-3-Clause 核心、
  Nuked* LGPL/GPL、Gens YM2612 GPL、Maxim SN76489 等）。配方记为 NOASSERTION。
- **构建系统**: CMake ≥ 3.12，语言 C + C++14

## 依赖情况

| 依赖 | 类型 | 说明 |
|------|------|------|
| zlib/1.3.2 | conan（ohpcd 已发布） | vgm-utils 的 DataLoader gzip 路径（UTIL_LOADERS，默认 ON） |
| pthread | 系统（musl 内建） | vgm-utils 线程工具（UTIL_THREADING） |
| iconv | 系统（musl libc 内建） | vgm-utils 字符集转换（UTIL_CHARSET_CONV → StrUtils-CPConv_IConv.c） |
| libm | 系统 | vgm-player 链接 |

W0 已确认 zlib/1.3.2 在 ohpcd 制品仓发布（另有 1.3.1 系列），无缺失依赖。

## CMake 选项决策

| 选项 | 上游默认 | 配方值 | 原因 |
|------|----------|--------|------|
| LIBRARY_TYPE | STATIC | STATIC（随 shared 选项映射） | 上游用 LIBRARY_TYPE 而非 BUILD_SHARED_LIBS |
| USE_SANITIZERS | **ON** | **OFF** | 默认 ON 会经 cmake/sanitizers 注入 -fsanitize，OHOS 不需要 |
| BUILD_TESTS | OFF | OFF | 测试程序是交互式开发工具（vgmtest/player 需交互 + VGM 数据） |
| BUILD_PLAYER | ON | OFF | CLI 播放器不随库分发（与 grokj2k 等先例一致） |
| BUILD_VGM2WAV | ON | OFF | 同上 |
| AUDIODRV_ALSA/PULSE/LIBAO/OSS/SADA | 自动探测 | 显式 OFF | OHOS 无这些音频开发包；保持构建确定性 |
| AUDIODRV_WAVEWRITE | ON | ON | 纯文件输出，无系统依赖，唯一保留的驱动 |
| UTIL_LOADERS/THREADING/CHARSET_CONV | ON | ON | 播放功能必需（DataLoader gzip、线程、GD3 标签转换） |
| SNDEMU__ALL | ON | ON | 全部声音核心（库的核心价值） |

另设：`CMAKE_SYSTEM_NAME=Linux`、`CMAKE_SYSTEM_PROCESSOR=aarch64`、
`CMAKE_{C,CXX}_BYTE_ORDER=LITTLE_ENDIAN`（OHOS 惯例，aarch64 小端）。

## 平台适配要点

1. **iconv**：非 Windows 下 CPConv 走 `StrUtils-CPConv_IConv.c`（纯 iconv_open/iconv，
   无 iconvctl 等 GNU 扩展），musl libc 内建 iconv 可满足链接与探测
   （CMake FindIconv 编译探测程序应判定 Iconv_IS_BUILT_IN）。
   **风险点（待真机确认）**：若 FindIconv 探测失败，UTIL_CHARCNV_ICONV 默认为 OFF，
   vgm-player 链接将缺 CPConv_* 符号——届时不需补丁，只需在 toolchain 传入
   `UTIL_CHARCNV_ICONV=ON`（前提是探测真失败，否则 CMake 会自动 REQUIRED 找到）。
2. **musl 无 CP932**：s98player.cpp 用 `CPConv_Init(&x, "CP932", "UTF-8")` 转换 Shift-JIS
   标签。musl iconv 不实现 CP932/Shift-JIS 等东亚遗留编码 → 运行时 iconv_open 失败，
   S98Player 优雅降级（`_cpcSJIS = NULL`，标签不转换，播放不受影响）。
   vgmplayer 的 UTF-16LE→UTF-8 与 gymplayer 的 CP1252→UTF-8 均为 musl 支持的编码，正常。
   **运行时限制，记录即可，不做补丁**。
3. **端序**：公共头不依赖 VGM_LITTLE_ENDIAN（仅 8 个 .c 私有使用，构建期已注入）；
   公共头 stdtype.h 依赖 HAVE_STDINT_H → 已加入 `cpp_info.defines`。
4. **_stdbool.h**：用 `__has_include` 探测，clang 15 下走系统 stdbool.h，无兼容问题。
5. **上游安装布局**：头文件 → `include/vgm/`（含 utils/audio/emu/player 子目录 +
   根目录 common_def.h/_stdbool.h/stdtype.h），另安装 libvgm CMake Config 与
   各子库 .pc 文件（上游 CMake 无开关禁用 .pc，与 Conan 自生成 .pc 并存，无害）。

## 消费者用法（test_package 覆盖）

- 头文件包含：`#include "player/playera.hpp"`（includedirs 含 include/vgm）
  或 `#include "vgm/player/playera.hpp"`（includedirs 含 include），两种拼写均支持
- 静态链接顺序已由 `cpp_info.libs = [vgm-player, vgm-audio, vgm-emu, vgm-utils]`
  保证（依赖者在前）
- zlib 经 `cpp_info.requires = ["zlib::zlib"]` 传递；pthread/m 经 system_libs 传递
- CMakeDeps 消费：`find_package(libvgm REQUIRED)` + 链接 `libvgm::libvgm`

## 上游测试与裁剪说明

上游**无 ctest 目标**（全仓库无 add_test）。`BUILD_TESTS=ON` 构建的
audiotest/emutest/audemutest/vgmtest 是开发用交互程序，需外部 VGM 数据。
处理方式：上游 emutest.c 的 SN76496 直渲染流程、vgm2wav.cpp 的
PlayerA 加载-播放流程移植进 test_package/test.cpp（17 个断言），
生成最小合法 VGM 1.50 文件在测试内自建，无外部数据依赖。

## 本机验证记录（2026-09-19，Windows 前置阶段）

- [x] 源码 URL/sha256：codeload 下载校验 `7a5677921eaf4c0d3cef07c8b6b6da2cbf2d5da90e54d7d65fd955a409189954`
- [x] W0：zlib/1.3.2 已发布（ohpcd），无缺失依赖
- [x] 构建系统识别：CMake ≥ 3.12（C + C++14），另有仅供开发用的裸 Makefile/VS 工程（不使用）
- [x] `conan export` 配方语法校验通过
- [x] test_package 断言设计（非空壳）：17 个断言，含渲染非静音硬断言
- [x] 最小 VGM 字节布局 Python 复验（抓出时钟/采样数两处硬编码错误）

## 真机验证记录（2026-09-19，10.62.178.77:2222）

- [x] `conan create + test_package` 全绿：**37/37 断言通过，零 FAIL**
      （test_libvgm 17 + 消费者用例 consumer_vgm_to_wav 20）
- [x] 包引用：`libvgm/g20260121#55fe95e0:f3c312b6ea9f88861a156775d2025ed86042673a`
- [x] **iconv 以 musl 内建探测成功**（`Iconv_IS_BUILT_IN - Success`，`/lib64/libc.so`），
      StrUtils-CPConv_IConv.c 正常编译——前置阶段标记的风险点干净解除
- [x] 渲染实测：PlayerA 输出 4096 帧、8192/8192 采样非零（SN76496 方波 100% 非静音）；
      消费者用例整段渲染 4330 帧，与 VGM 头 total samples 完全一致
- [x] 消费者用例覆盖 gzip 输入路径：zlib gzwrite 造 .vgz 夹具 → FileLoader
      魔数检测透明解压 → PlayerA 渲染 → RIFF/WAVE 落盘回读逐字段校验
- [x] L5 产物：lib/{libvgm-player,libvgm-audio,libvgm-emu,libvgm-utils}.a（ar 归档）+ include/vgm/ 完整树
- 内存安全：全程 tools.build:jobs=1（真机 global.conf 已配置），单作业编译未对共享真机造成压力

### 该真机（第二台）环境差异备忘

- 机器：HarmonyOS aarch64 32GB，`/storage/Users/currentUser/usr/local/bin/conan`（2.29.1 OHOS 适配版），
  clang 15.0.4 与 cmake 4.1.2 在 `/data/service/hnp/bin/`（`ls` 该目录会 Permission denied 但直接执行可用）
- 本机 `ohos-aarch64` profile 缺 `os.version` 且 `libcxx=libstdc++11`（OHOS clang 只认 libc++），
  需命令行补 `-s os.version=6.0 -s compiler.libcxx=libc++`
  并显式 `-c tools.build:compiler_executables={.../hnp/bin/clang,...}`
  （PATH 中 `usr/local/bin/cc|clang|bash` 为指向不可达目标的坏符号链接，CMake 会误选）
- 必设 `TMPDIR=$HOME/tmp`（默认临时目录只读，clang 报 unable to make temporary file）
- 该版 conan 拒绝命令行 `-c core.*`（仅 tools.* 可用），download cache 预置需写 global.conf；
  实测 conan 自带 CA 直连 codeload.github.com 可用（仅首包慢约 4 分钟），无需预置
- 当前用户编译的未签名 ELF 可直接运行（无 E064 签名问题）
- 实际命令（nohup 后台，日志 `$HOME/tmp/libvgm_create.log`）：

```sh
export PATH=/data/service/hnp/bin:/storage/Users/currentUser/usr/local/bin:$PATH
export TMPDIR=$HOME/tmp
cd $HOME/tmp/libvgm-build/g20260121
conan create . --build=missing -pr=ohos-aarch64 \
  -s os.version=6.0 -s compiler.libcxx=libc++ \
  -c 'tools.build:compiler_executables={"c":"/data/service/hnp/bin/clang","cpp":"/data/service/hnp/bin/clang++"}'
```

## 下一步

真机 conan create + test_package 已全绿（37/37，见上）。剩余：

```sh
# shadow CI 单包门禁（L0-L5）
CI_PACKAGES="archives/l/libvgm/g20260121" zsh ci/conan/build_and_test.sh
```

- [ ] PR 评论 /rebuild 触发仓库 CI → 绿
- [ ] /ai review
- [ ] issue 待补
- L4 已在真机确认 iconv 内建探测成功；L5 已确认 4 个 .a 与 include/vgm/ 完整

## 路径B 交付物（知识库扩展）

随 PR 新增 3 份知识草稿（knowledge/drafts/，.md + .kv 成对）：

1. `libvgm-g20260121-cmake-bundled-sanitizers-default-on` —
   上游 CMake 内置 sanitizers 模块且默认 ON，目标设备无 runtime 必炸
2. `libvgm-g20260121-musl-iconv-east-asian-charset-gap` —
   musl iconv 无 CP932/GBK/Big5 等东亚遗留码表：构建期探测必过、运行时
   iconv_open -1/ENOENT；libvgm S98 标签优雅降级范式
3. `libvgm-g20260121-multi-static-lib-cppinfo-packaging` —
   单配方聚合上游多兄弟静态库的 cpp_info 四件套
   （libs 依赖序/HAVE_* 探测宏 defines/includedirs 双拼写/requires 传递）

消费者用例：`test_package/consumer_vgm_to_wav.cpp`（20 断言）——
下游"VGM→WAV 音乐转换器"场景，端到端覆盖 zlib→vgm-utils→vgm-player→vgm-emu
全链路（含 gzip 压缩输入与 WAV 落盘回读校验）。
