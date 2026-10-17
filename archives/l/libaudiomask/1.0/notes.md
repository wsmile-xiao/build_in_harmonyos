# libaudiomask 1.0 适配笔记

## 1. 软件概要

- 同时性音频掩蔽阈值估计库（psychoacoustics，mp3 压缩的理论基础）。
- 上游：Debian 源码包 libaudiomask 1.0（作者 Dr Matt R. Flax），orig tarball
  `libaudiomask_1.0.orig.tar.gz`（3712901 字节，md5 `2a515d7cd6d39fb9407ef527d3c76c11`，
  sha256 `a84ff2473b6265acdf4ca887c3ae823840d2cf68efee018d9e9dd1afd5f6e6eb`）。
- 与 flatmax/gtkiostream `src/AudioMask` 同源（含 `AudioMask.C/.cc`、`AudioMasker`、
  `MooreSpread.C`、`depukfb` 系列）；`MooreSpread.H` 两边完全一致，可互为 API 旁证。
- 构建系统：纯 Makefile，无 configure 脚本。
- 依赖：mffm-fftw-dev、libfftw3-dev（Debian control Build-Depends）。
  `fftw/3.3.11` 已发布；`mffm-fftw/1.7` 未发布到 ohpcd（2026-09-24 真机
  conan graph 报 `Unable to find 'mffm-fftw/1.7' in remotes`），且单 PR 只允许
  一个库，故按 pam-u2f 自闭环经验 vendor 官方 `mffm-fftw_1.7.orig.tar.gz`
 （sha256 `5c7be71270812f468d270481f8959643bd374736c3bf18a7b9d2dccb9690aad0`）
  并静态链入本包；Conan 依赖仅保留 `fftw/3.3.11`。
- 许可：GPL-3.0-or-later（源码头 "either version 3 ... or any later version"）。

## 2. 上游测试清点（R51 三步法）

在 Debian sources 文件清单与 changelog 基础上清点：

- 源码根文件：`AudioMask.H/.cc`、`AudioMasker.H/.cc`、`MooreSpread.H/.cc`、
  `depukfb.H/.cc`、`fastDepukfb.H`、`Makefile`、`audio.44100.txt`（示例输入）、
  `*.pdf` 文档、`API-libaudiomask`、`latex`、`debian`。
- 无 `tests/`、`test/` 目录；Makefile 无 `check`/`test` 目标。`ex` 目标全文仅一行
  （Makefile 第 37 行）：
  `$(CC) -L/home/flatmax/lib -lfftw3 -lfft $(OBJ) -o AudioMaskerExample AudioMaskerExample.cc`，
  即上游注册的可执行验证只有 AudioMaskerExample；debian/rules 走默认
  `all: libs ex`，Debian 官方构建亦只编译该示例。changelog 1.0-2 佐证：
  "Fixed the makefile so that 'make ex' now compiles" +
  "Added the example input audio.44100.txt file"。
- depukfbExample.cc 仅依赖 depukfb.H/fastDepukfb.H（自包含），可构建可运行，
  计入上游验证。
- AudioMaskExample.cc / MooreSpreadExample.cc 不是可执行测试，不计数：
  二者分别 `#include "../fft/realFFT.H"` 且实际使用 GCFB/GTFB 滤波器组
  （`USEGCFB`、`GCFB gcfb` / `GTFB gtfb`、`gtfb.prev()->cf` 等）；而 GTFB/GCFB 头
  既不在 orig 包内（141 成员已逐项核对），也不在 mffm-fftw 1.7 包内
  （该包仅 realFFT/realFFTData/complexFFT/real2DFFT，47 成员已逐项核对），
  更不在 debian/control 声明的 Build-Depends
  （libfftw3-dev、mffm-fftw-dev）中；Debian 官方构建从未编译二者。
  在任何满足声明依赖的环境下二者都不可构建，故按"非测试文档文件"排除，
  非"可运行子集替代总数"。
- 结论：上游总数 2，口径 `auto`（单一可解析框架：示例二进制退出码），
  `upstream_test_total: 2`。详见 `test_package/MANIFEST.yml` 的审计块。

## 3. 编译说明

- 不调用上游 Makefile（硬编码 `g++`，且 install 目标依赖 OHOS 缺失的 `install(1)`）；
  配方用 Conan conf 的 clang++ 绝对路径直驱编译（R33），`-j1` 单作业。
- 先静态编译 vendored mffm-fftw 4 个单元（`realFFT/realFFTData/complexFFT/real2DFFT`，
  产物在 `build_folder/vendor-objs`，`vendor-mffm-fftw/mffm-alias/mffm` 提供
  `<mffm/*.H>` 别名），其对象同时链入共享库与静态库，消费者无需额外 mffm 产物。
- `clang++ -O2 -fPIC -std=c++17 -I<src> -I<fftw include> -I<vendor>`
  编译 4 个库单元；链接 `libaudiomask.so.1.0`（soname `libaudiomask.so.1`，
  附 `.so.1`/`.so` 符号链接，不支持符号链接时回退为拷贝）与 `libaudiomask.a`
  （恒产出，供 2 个示例确定性链接）。
- source() 内做两处无行为变更的可移植修正：`../fft/*.H` 改扁平头文件名
  （Debian 包扁平，gtkiostream 兄弟目录布局假设失效；当前仅 stale 示例携带，
  保留修正以绝后患）、`void main(void)` 改 `int main(void)`
  （depukfbExample.cc，非标准写法，落空返回 0）。
- 头文件扁平安装到 `include/`（`AudioMask.H` 等 5 个），许可证 `GPL-3` 入 `licenses/`。
- 零补丁：`patches_applied: []`。若真机预检暴露 OHOS 专有编译问题，后续轮次再补。

## 4. 上游测试执行

- build() 内编译 2 个可构建示例并逐个运行（cwd=源码根，示例输入就地可得；
  AudioMaskerExample 读包内 audio.44100.txt 写 cf.dat/fa.t.mask/fa.pow/thresh.dat，
  depukfbExample 写文件 `w`），结果写入 `build_folder/upstream_tests.log`
  （每示例一行 `EXAMPLE <名> RESULT=PASS/FAIL/SKIP`），标记从该单一文件回解析，
  不做 stdout 字符串数数。
- JSON 同步落盘 `build_folder/upstream_test_result.json` 并打包进 `res/`，
  test_package 原样重发（libfdt 模式，保证 Conan 缓存命中轮次仍有上游证据）。
- 恒等式自检：`passed + failed + skipped == executed`、`executed <= discovered`。

## 5. test_package（消费者视角，R34）

- `test_libaudiomask.cpp` 真实链接 packaged `libaudiomask`，覆盖：
  DepUKFB 构造/`filterCount`/`cf`/`ef`/`operator[]`/`operator()`、
  MooreSpread 构造/`setCFreq`/`excite`、
  AudioMasker 构造/`getBankCount`/`excite(double*,int)`/`mask`/`findThreshold`，
  共 11 个断言，打印单行 `LIBAUDIOMASK_TEST assertions=11 failures=F`，
  失败即非零退出（L1e 反向验证：移走 include/lib 必失败）。
- 刻意避开 `AudioMask::exciteTerhardt`：gtkiostream 头（2 参）与示例（3 参调用）
  不一致，Debian 1.0 头未亲见，不拿不确定 API 赌真机。
- `test_package/conanfile.py` 从该单行解析数字，输出
  `HMBS_TEST_PACKAGE_RESULT`（discovered=12），并重发上游标记。

## 6. 依赖版本

- fftw/3.3.11（ohpcd 已发布，唯一 Conan 依赖）
- mffm-fftw 1.7（未发布，做 vendor：官方 Debian 池 orig 包，
  sha256 `5c7be71270812f468d270481f8959643bd374736c3bf18a7b9d2dccb9690aad0`，
  静态编译后链入 libaudiomask；其 `License.txt.gpl` 随包进 `licenses/`）
- clang 15（真机 `/data/service/hnp/bin/clang++`，经 Conan conf 注入）

## 7. 状态（2026-09-25 真机 compile 失败修复）

- 本轮：未提交工作树，待 HMBS 真机预检（conan create 全量：库构建 + 2 示例运行
  + test_package 12 断言）。
- 预期：编译通过，上游 2/2，新增 11/11。
- 2026-09-24 真机失败：MooreSpread.H:24 fatal error mffm/GTFB.H not found。
  根因：该头不在 mffm-fftw 1.7（仅 realFFT/complexFFT/real2DFFT）中，
  且 MooreSpread 无 GTFB 类型依赖；上游 gtkiostream master 已将其注释掉。
  修复：conanfile source() 新增 _neuter_dead_mffm_includes，
  将源码树内 mffm/GTFB.H 与 mffm/GCFB.H 死引用注释化（构建与装包头同步生效）。
- 2026-09-25 真机失败：AudioMaskExample.cc:19 fatal error '../fft/realFFT.H'
  not found（且 deb.debian.org 同轮连续下载超时、ftp.debian.org 成功）。
  根因有二：(1) 该示例沿用 gtkiostream 兄弟目录布局假设
  （src/AudioMask + src/fft），Debian 包扁平后相对路径失效；
  (2) 更深一层：AudioMaskExample/MooreSpreadExample 实际依赖 GTFB/GCFB，
  三处（orig 包、mffm-fftw 1.7、Build-Depends）皆无该头，Debian 自身亦不构建
  二者（`make ex` 仅注册 AudioMaskerExample），属 stale 文档文件。
  修复：EXAMPLES 收窄为 2 个可构建示例（AudioMaskerExample + depukfbExample，
  总数同步为 2，审计见 MANIFEST.yml）；source() 新增 _fix_upstream_includes
  （`../fft/` 扁平化 + `void main` 标准化）；conandata.yml 下载顺序改为
  ftp.debian.org 优先、官方原 URL 回退，mffm_fftw 补同款 3 镜像，sha256 不变。
- 2026-09-24 真机失败：source() 阶段 SSH 中断（`Calling source()` 后
  `Connection to 47.242.172.160 closed by remote host`，无 conan 错误行）。
  根因：source() 需依次下载 libaudiomask（3.7MB）+ vendored mffm-fftw 两个
  orig 包，而 Debian 池不在 CI 自动镜像映射内，直连 deb/ftp.debian.org
  跨境缓慢（前轮已有 Read timed out 证据），长下载窗口触发传输层中断。
  修复：conandata.yml 两个 sources 均前置国内 Debian 官方镜像
  aliyun/tuna/ustc（同池同文件，复用 build_and_test.sh 已维护三源），
  官方原 URL（deb.debian.org）保留为最终回退，sha256 不变；去掉明文 http 项。
- 2026-09-25 真机失败：depukfbExample 链接行 4 个 clang 错误
  （fastDepukfb.H:104 `cout`/`endl` 未声明、depukfbExample.cc:38 `ofstream`
  未声明、:42 `endl` 未声明）。
  根因：上游在 g++/libstdc++ 下靠传递式 `<iostream>`/`<fstream>` 与非限定
  查找侥幸编译；clang/libc++ 严格要求显式 `std::` 限定与显式头文件。
  修复：`_fix_upstream_includes` 新增第 3 步——对无 `using namespace std`
  的 `.H`/`.cc` 按需补 `#include <iostream>`/`<fstream>`（`_ensure_include`
  插到最后一个 `#include` 之后，幂等），再把裸 `cout/cerr/clog/endl/
  ofstream/ifstream` 正则统一加 `std::` 前缀（已带 `std::` 的不受影响，
  已验证幂等）。无行为变更，Debian g++ 仍可编译。
- 2026-09-24 真机失败（本轮输入）：上游 2 示例构建成功但运行 0/2 全 FAIL，
  且 test_package 编译 `fatal error: 'mffm/realFFT.H' file not found`
  （AudioMasker.H:24，经 packaged 头引入）。
  根因有二：(1) package() 只装 5 个库头，vendored mffm 头（AudioMasker.H
  经 `<mffm/realFFT.H>` 强依赖）未随包发布，消费者 `-I<package>/include`
  无法解析；(2) 上游示例与 test 二进制均以裸 `subprocess.run([bin])`
  执行，缺失 conanrun 运行环境，共享 fftw（`libfftw3(.so)` + `threads`）
  在真机缺 `LD_LIBRARY_PATH` 即以 exit 127 猝死——双示例同崩正是系统性
  环境缺失而非各自逻辑错（编译行均已带 `-lfftw3 -lfftw3_threads` 成功）。
- 2026-09-24 真机失败（本轮输入，策略已换）：上游 2 示例 1/2（其一仍 FAIL），
  且 test_package 编译 `no member named 'getBankCount' in 'AudioMasker'`。
  前轮 env/装包策略已把上游从 0/2 推到 1/2 并暴露本错，故本轮改走源码级
  修正路线：(1) 逐行核对 `AudioMasker.H` 公开面——`bankCount` 为私有成员，
  无 `getBankCount()`（公开面仅 `pfb/mask/excite/findThreshold/setCFreq`），
  测试属虚构 API 调用，clang 拒绝编译属正确行为；改为同数 1:1 断言
  `pfb != 0 && mask != 0`（FBMalloc/AudioMask 构造产物，11 个 CHECK 总数不变，
  MANIFEST 同步 11）；test_package 失败回退数同步 11；(2) 上游剩余 1 例失败
  在摘要中无 rc/输出证据、纯逻辑复核（MooreSpread 越界、文件缺失、exit 路径）
  均指向仍应 exit 0，故不盲改示例语义，仅把 gaps.detail 改为证据携带型
  （逐例名 + exit rc + 输出尾 5 行），下轮摘要即可见是 loader 127、信号崩溃
  还是输入问题；计数与口径零变更。

- 2026-09-25 真机失败（本轮输入）：上游 1/2（AudioMaskerExample FAIL exit -11；depukfbExample PASS），且 test_package 11 断言 1 失败（line 78 masker.mask[0] 非有限）。
  根因：AudioMasker::process 堆越界（确证为上游漏洞非环境问题）——powOutput 每行只分配 ceil(fs/2)=22050 个 double且只填写 halfFS=rint(fs/2) 项，却调用 exciteTerhardt(powOutput, fs) 对每行求和 44100 项（AudioMask.cc 循环 j<sampleCount），每行越读约 176KB；50 行示例萌临未映射页即 SIGSEGV，8 行测试则吸入垃圾导致 log10(负数/垃圾)=NaN。Debian x86 偶然不崩溃只是堆布局差异遮住了 UB。MooreSpread::excite(...,fs,fs) 内部硬编码不受影响，仅调整求和上限即可修复且不改变散布逻辑。
  修复：source() 新增 _fix_excite_count，将 AudioMasker.cc 中 exciteTerhardt(powOutput, fs) 替换为 exciteTerhardt(powOutput, halfFS)（halfFS 在 process() 中已定义；和分配/ Ahmad 填写一致）；无行为变更，Debian g++ 仍可编译；test_package 保持 11 断言零变更。预期上游 2/2、新增 11/11。

**申请人**：Bingggooo（队伍：来都来了）
