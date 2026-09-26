# minimodem 0.24 适配笔记

## 编译环境
- 构建系统: autotools（configure.ac 自举，git-tag tarball 不带 configure）
- 编译日期: 2026-09-22
- 编译器: clang 15（HNP 基线）
- 状态: built
- 依赖: libsndfile/1.2.2、fftw/3.3.10.3（ohpcd 制品仓 armv8/OHOS 二进制）
- 构建工具: automake/1.18（tool_requires）、autoconf 2.73 / pkg-config 0.29.2（HNP 基线）

## 编译步骤

1. `conan create` 由 conan-verify/W3 驱动，配方 `build()` 内：
   - `apply_conandata_patches`（0001 改 configure.ac，须在 autoconf 前）
   - 自举：`aclocal --force` → `autoconf` → `autoheader` →
     `automake --add-missing --foreign`（conanbuild 环境，取 tool_requires 的
     automake/1.18 与其导出的 ACLOCAL_PATH/PERL5LIB）
   - E490：对 configure/config.guess/config.sub/install-sh/missing/depcomp/
     compile/test-driver 显式恢复执行位
   - E007（防御性，本包实测未触发）：config.guess 幂等补 HarmonyOS 分支。
     本包 configure.ac 无 AC_CANONICAL_*，automake --add-missing 不拷
     config.guess/config.sub，configure 也不做三元组识别，故该修复实际不
     生效；保留为防御代码（automake/1.18 自带的 config.guess 已离线验证
     修复后输出 aarch64-unknown-linux-ohos，带引号/不带引号两种 case 形态
     的锚点均可匹配）
   - E011/E114：configure 内 `umask 077`→`umask 022`、`ac_tmp=$tmp`→配方预建
     可写目录并中和退出 trap
   - `configure --without-alsa --without-pulseaudio`（PKG_CONFIG_PATH 指向
     PkgConfigDeps 生成的 fftw3.pc/sndfile.pc）
   - `make -j4` → `make check -j1`（上游 28 个测试）
2. `package()`：`make install` 交付 `bin/minimodem` + man 页 + COPYING。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 上游依赖 `fftw3f`（pkg-config 名），ohpcd 无此模块 | 制品仓 fftw 全系（3.3.10–3.3.11）都是双精度构建（configure 无 `--enable-single`），包内只有 `libfftw3`+`fftw3.pc`；fftw/2.1.5 虽是 float 但属 FFTW2 API（sfftw_*），不兼容 | 补丁 0001：`deps_packages="fftw3f"`→`"fftw3"`，`src/fsk.{h,c}` 的 `fftwf_*`→`fftw_*`、`fftwf_complex`→`fftw_complex`、变换缓冲 `float*`→`double*`（样本喂入处 memcpy 改逐点转换）；幅值仍按 float 口径（`band_mag` 返回 float），测试阈值语义不变 |
| 2 | tests/ 下 30 个脚本依赖 `#!/bin/bash`（20 个无 shebang 靠 shell ENOEXEC 回退），OHOS 无 `/bin/bash` | 脚本用 `let`/`function`/`echo -e`/`echo -n` 等 bash 特性，toybox sh 无这些特性 | 补丁 0002：全部脚本统一显式解释器 `/data/service/hnp/bin/bash`（HNP 基线，设备与 CI worker 一致；10 处替换 + 20 处新增），内核按 shebang 直启、不依赖 ENOEXEC 回退 |
| 3 | 测试硬编码 `/tmp`（4 个文件），OHOS `/tmp` 只读 | `self-test`、`04/16/70-*.test` 直接写 `/tmp/minimodem-test*` | 补丁 0002：改 `${TMPDIR:-/tmp}`；配方把 configure/build/check 环境的 TMPDIR 指到构建目录下可写目录 |
| 4 | （防御性）automake 1.18 自带 config.guess 不识别 HarmonyOS | `uname -s`=`HarmonyOS` 不在其主 case 分支，若被调用会 exit 1 "unable to guess" | E007：build() 内幂等补 HarmonyOS 分支；本包 configure.ac 无 AC_CANONICAL_*，configure 不做三元组识别，修复实测未触发（防御保留，离线实证可用）；不传 --build/--host |
| 5 | conan Release 默认 `-DNDEBUG`，上游 `simpleaudio_tone()` 唯一的音频写在 `assert(simpleaudio_write(...)>0)` 内被整体编译掉，`--tx` 产出 44 字节空 WAV，依赖 rx 的上游用例全部失败（TX 一致性用例因 md5 相同反而假 PASS） | 上游将写操作放进 assert 的潜伏缺陷，Release 构建必现 | 补丁 0003：写入无条件执行，失败时报错 exit(1)（保留上游非 NDEBUG 构建的响亮失败语义）；修复后 28 个上游用例全部通过 |
| 6 | git-tag tarball 无 configure | 上游 release 页无 dist 资产（HTTP 404 实证），权威发布点是 git tag | build() 内 aclocal/autoconf/autoheader/automake 自举；automake 用 tool_requires（CI worker PATH 无 automake） |

## 源码修改

| 补丁 | 文件 | 内容 |
|------|------|------|
| 0001-fftw-double-precision.patch | configure.ac, src/fsk.h, src/fsk.c | 单精度 FFTW3 → 双精度适配（见上表 #1） |
| 0002-tests-bash-path-and-tmpdir.patch | tests/ 下 28 个 *.test + self-test + run-self-tests | 解释器显式路径（30 处）+ /tmp 只读（4 处 TMPF），见上表 #2/#3，仅测试基础设施 |

## 依赖版本

- libsndfile/1.2.2（ohpcd，shared）
- fftw/3.3.10.3（ohpcd，shared，双精度）
- tool: automake/1.18（ohpcd）

## 验证结果

（证据与计数见 reports/ 与 test-report.md；此处留运行时更新）

## 交付物

| 文件 | 说明 |
|------|------|
| bin/minimodem | FSK 调制解调器可执行文件（application 包） |
| share/man/man1/minimodem.1 | 手册页 |

## 注意事项

- 上游测试全部走 `--file` WAV 往返（纯用户态），不需要 ALSA/PulseAudio 设备；
  `--without-alsa --without-pulseaudio` 不影响任何上游测试。
- test_package 的消费者断言逻辑在 `test_package/test.sh`（`conanfile.py` `test()`
  以 `bash test.sh <minimodem> <workdir>` 参数方式执行），该静态文件同时是
  CI L0c 门禁（`build_and_test.sh` 扫 test_package 白名单后缀、排除
  conanfile.py）所要求的测试源——断言逻辑不再由 conanfile 运行期生成。
- 测试 `40-noise.test` 使用实验参数 `--Xrxnoise`（上游自带），属预期。
- `04-self-test-0.5.test` 以 0.5 波特收发 6 字节（约 2 分钟音频），全套
  `make check` 需数十分钟量级，勿以单测时长判断挂死。
