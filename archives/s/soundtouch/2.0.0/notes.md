# SoundTouch 2.0.0 — 编译笔记

## 软件信息

- **名称**: soundtouch — 开源音频变速变调 DSP 库（WSOLA 算法），可独立调整音频节奏(Tempo)、音高(Pitch)与播放速率(Rate)
- **版本**: 2.0.0（gitlab tag 2.0.0，commit abf79cf6252）
- **许可证**: LGPL-2.1-or-later
- **构建系统**: autotools（源码包不含 configure，1.6.0 起移除——需 bootstrap；CMake 支持是 2.1.0 才加入，2.0.0 只有 autotools）
- **目标平台**: OHOS aarch64 (鸿蒙 PC)
- **上游**: https://gitlab.com/soundtouch/soundtouch（主仓） / https://www.surina.net/soundtouch/（官网发布包）
- **sha256**: efa1f63b1bb60cae4565307757234936b0a19e2fa7913651eba9b9f82eeeb915（gitlab tag 归档与 surina.net 官方发布包逐字节一致）

## 与仓库已有 sound-touch 归档的关系

仓库已有 `archives/s/sound-touch/`（2.4.0 与 homebrew=2.4.1 版本，conan 包名 `sound-touch`）。
本归档为 `soundtouch`（无连字符，conan 包名 `soundtouch`），版本 2.0.0——不同 conan recipe 名，制品仓查重零冲突
（`conan list sound-touch/*` 与 `conan list soundtouch/*` 均已核实）。

## 编译步骤（本地实测）

1. **Bootstrap**（顺序关键）:
   ```bash
   libtoolize --copy --force          # 生成 ltmain.sh → 移到 config/
   mv ltmain.sh config/ltmain.sh      # automake 要求 AC_CONFIG_AUX_DIR(config)
   AUTOMAKE="automake --add-missing --foreign --copy" autoreconf -fisv
   ```
   直接跑 autoreconf 会报 `required file 'config/ltmain.sh' not found`——
   AM_PROG_LIBTOOL 需要 ltmain.sh，而 automake --add-missing 不会自动装它（2.0.0 的
   AC_CONFIG_AUX_DIR(config) 与 libtoolize 默认放项目根不一致）。
2. **confstat umask 修复**: configure 文本替换 `umask 077` → `umask 000`
   （config.status 用 `(umask 077 && mktemp -d "./confXXXXXX")` 创建临时目录，
   HMDFS 上 0700 目录不可写导致 configure 中止——E100/boa/catdoc/adplay 同款）
3. **Configure**:
   ```bash
   ./configure --prefix=$PREFIX \
     --build=aarch64-unknown-linux-gnu --host=aarch64-unknown-linux-ohos \
     --disable-x86-optimizations
   ```
   - config.guess（automake 1.18 生成）已能识别 HarmonyOS → aarch64-unknown-linux-ohos，
     但按 E205 仍显式传 triplet
   - `--disable-x86-optimizations`：MMX/SSE 仅 x86；aarch64 上 configure 探测
     cpuid.h 缺失也会自动关，显式关闭更稳
   - 2.0.0 的 configure **没有** `--disable-neon-optimizations` 开关（那是
     2.3.0+ 才加的 NEON ARM 支持）；2.0.0 的 ARM 路径是纯 C++ 标量代码，无需处理
4. **编译**: `make -j4` — 一次通过，零报错
5. **安装**: `make install DESTDIR=...` → bin/soundstretch + lib/libSoundTouch.so.1.0.0
   + include/soundtouch/*.h + lib/pkgconfig/soundtouch.pc

## 上游测试实测（N 实测）

上游 2.0.0 的 autotools 构建系统**无注册测试目标**（Makefile.am 无 check/TESTS；
`bin/run_test` 是需外部测试音频 `~/dev/test_sounds` 的手动 shell 脚本，非 make check 目标）。
因此 N（上游注册测试数）= 0，改用**本地实测替代**（clancyxie 口径：有测试就跑，给证据链）：

本地生成 2 秒 440Hz 正弦波 WAV（44100Hz/16bit/mono），实测 soundstretch（链接 libSoundTouch 的官方 CLI）：

| 测试 | 命令参数 | 输出时长 | 输出主频(DFT) | 判定 |
|---|---|---|---|---|
| T1 纯变速 | `-tempo=50`（加速 50%） | 1.333s（=2.0/1.5 ✓） | 440.0Hz（不变调 ✓） | PASS |
| T2 纯变调 | `-pitch=3`（+3 半音） | 2.000s（不变速 ✓） | 523.3Hz（=440×2^(3/12)=523.25 ✓） | PASS |
| T3 变速率 | `-rate=-20`（-20%） | 2.500s（=2.0/0.8 ✓） | 352.0Hz（=440×0.8 ✓） | PASS |
| T4 BPM 检测 | `-bpm` | 2.000s | —（正弦波无节拍，"Couldn't detect BPM rate." 符合预期，BPMDetect 正常运行不崩溃） | PASS |

物理验证结论：WSOLA 变速算法在 OHOS aarch64 上**数值正确**——tempo 改变时长不变频率、
pitch 改变频率不变时长、rate 同时改变两者，全部符合 DSP 理论预期。

另 test_package 消费者测试（C++ 链接 libSoundTouch）：
- getVersionId() == 20000（2.0.0 版本核验）PASS
- tempo=1.0 恒等管线 44100 样本进/出流量验证 PASS

## 关键问题与解决方案

### 问题 1: CI/本地缺 automake、aclocal、libtoolize

**现象**: `autoreconf` 报 `Can't exec "aclocal": No such file or directory`；
automake 报 `required file 'config/ltmain.sh' not found`。

**根因**: SDK 只有 autoconf 2.72/autoreconf/m4/perl，无 automake 家族（homebrew 版
sound-touch 历史笔记同样实锤：CI worker 只有 autoconf 无 automake）。

**解决方案**: conanfile.py `build_requirements()`:
```python
self.tool_requires("automake/1.18")   # aclocal + automake
self.tool_requires("libtool/2.5.4")   # libtoolize + ltmain.sh
```
（accel-config/adplay 等 159 个先例配方同款；autoconf/m4 不声明——声明会拉
perl/5.42.2 与 SDK perl 5.42.0 的 XS .so 冲突）

### 问题 2: config/ltmain.sh 缺失（自举顺序）

**现象**: `automake --add-missing` 报 `error: required file 'config/ltmain.sh' not found`。

**根因**: AC_CONFIG_AUX_DIR(config) 要求辅助文件在 config/ 下，但 libtoolize 把
ltmain.sh 放在项目根目录。

**解决方案**: build() 中先 `libtoolize --copy --force`，再把 `ltmain.sh` 移到
`config/ltmain.sh`，然后 autoreconf。

### 问题 3: config.status umask 077（HMDFS）

见上文编译步骤 2。文本替换生成的 configure 文件（非源码补丁——R6 只改生成文件不入 patch）。

### 问题 4: 运行时 libc++_shared.so 找不到（本地验证时）

**现象**: 直接执行 soundstretch 报 `Error loading shared library libc++_shared.so`。

**根因**: 本机测试环境 LD_LIBRARY_PATH 未含 OHOS SDK llvm lib 路径（设备上由系统提供）。

**解决方案**: 本地验证时 `LD_LIBRARY_PATH=<sdk>/llvm/lib/aarch64-linux-ohos` 前置。CI 上由 profile 的 buildenv LD_LIBRARY_PATH 提供。

## 历史经验比对（W0b sound-touch 2.4.0/homebrew 笔记）

| 历史坑 | 2.0.0 实测结论 |
|---|---|
| E098 __powidf2 需 -lclang_rt.builtins | **未复现**——clang 15 对 2.0.0 代码生成 exp/exp2/ldexp 调用（libm 已覆盖），llvm-nm 无 powidf2 未定义符号，无需加链接参数 |
| E099 NEON 需 --disable-neon-optimizations | **不适用**——2.0.0 configure.ac 无此开关（NEON 优化 2.3.0 才引入）；ARM 路径纯标量 C++ |
| bootstrap 缺 automake（homebrew CI 坑） | **复现并解**——tool_requires automake/1.18 + libtool/2.5.4 |
| soundtouch_config.h stub 补丁（homebrew） | **不需要**——2.0.0 走完整 autotools configure，include/soundtouch_config.h.in 由 configure 正常生成 |
| umask 077（E100） | **复现并解**——umask 077→000 文本替换 |

## 产物清单

- lib/libSoundTouch.so.1.0.0（+ .so/.so.1 符号链接）— 主库
- bin/soundstretch — WAV 变速变调 CLI（commands.json 软件级声明）
- include/soundtouch/{SoundTouch,BPMDetect,FIFOSampleBuffer,FIFOSamplePipe,STTypes,soundtouch_config}.h
- lib/pkgconfig/soundtouch.pc
---

**编译结束**: 2026-09-15 06:02
**最终状态**: published
