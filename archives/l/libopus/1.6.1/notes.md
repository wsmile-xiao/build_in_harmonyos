# libopus 1.6.1 — 适配笔记

> 档案创建时间: 2026-09-18
> 最后更新: 2026-09-18

## 一、基本信息
| 项目 | 值 |
|------|-----|
| 软件 | libopus（Xiph Opus 音频编解码，IETF RFC 6716） |
| 版本 | 1.6.1 |
| 状态 | built |
| 构建系统 | cmake（上游另有 meson/autotools） |
| 源码路径 | https://downloads.xiph.org/releases/opus/opus-1.6.1.tar.gz |
| 依赖 | 无（零外部依赖叶子） |

## 二、包名说明（多包名并存先例）

本配方包名 **libopus**，与既有归档 `opus/*`（1.4 / 1.5.2 / 1.5.2.1）**不同包名、可并存**——
同 `vorbis`/`libvorbis`（1.3.7 双双在库）、`ogg`/`libogg` 先例。上游 pkg-config 名即
`opus`（lib/pkgconfig/opus.pc），Debian/发行版二进制包名 libopus1/libopus-dev，
ffmpeg `--enable-libopus` 生态习惯命名。

## 三、编译阶段

### Phase 2: 编译（cmake 裸构建，opus/1.5.2 同款）
- [x] 自发现 ohos.toolchain.cmake（profile user_toolchain → OHOS_NDK_HOME → glob SDK）
- [x] -DCMAKE_INSTALL_LIBDIR=lib（ohos.toolchain 64 位默认装 lib64/，改回 lib）
- [x] -DOPUS_BUILD_PROGRAMS=ON（opus_demo/opus_compare 供测试证据链）
- [x] cmake --build 全绿（含 celt/arm、silk/arm NEON 内建函数源）
- [x] cmake --install + binary-sign-tool 签名（XPM dlopen 门槛）

### Phase 3: 测试验证（上游测试铁律：CI 跑不了→本地执行+附证据）

**上游测试注册口径（CMake ∪ Meson 并集，1.5.2 测试注册分歧草稿 DRAFT-opus-1.5.2 口径）**：
- CMakeLists.txt：5 个无条件 add_test（test_opus_decode/padding/api/encode/extensions）
  + 1 个 OPUS_DRED=ON 条件项（默认 OFF，未注册）
- tests/meson.build：6 个无条件 test()（额外含 test_opus_projection，需 celt/silk/dnn
  内部符号）+ 同款 DRED 条件项
- **N = 7（CMake 5 无条件 ∪ Meson 独有 projection 1）+ DRED 条件项如实标注**

**本地实测（HarmonyOS PC aarch64 真机，2026-09-18）**：

| # | 测试 | 注册来源 | 执行方式 | 结果 |
|---|------|---------|---------|------|
| 1 | test_opus_decode | CMake+Meson | ctest（静态构建） | PASS 11.81s |
| 2 | test_opus_padding | CMake+Meson | ctest | PASS 0.09s |
| 3 | test_opus_api | CMake+Meson | ctest | PASS 6.91s |
| 4 | test_opus_encode | CMake+Meson | ctest（含 opus_encode_regressions.c） | PASS 26.17s |
| 5 | test_opus_extensions | CMake+Meson | ctest | PASS 52.32s |
| 6 | test_opus_projection | **Meson 独有** | 手动 clang 编译链接 libopus.a（-Icelt -Isilk -Idnn 内部符号） | PASS "All projection tests passed." |
| - | test_opus_dred | 条件项 | OPUS_DRED 默认 OFF 未注册（上游默认形态），DRED 需 DNN 模型数据，非默认特性 | 未实例化（标注条件开关） |

**ctest 总输出：`100% tests passed, 0 tests failed out of 5`（Total 97.32s）**

test 命令记录：
```bash
# ctest 五件套（静态构建 + BUILD_TESTING）
cmake -B build-ohos-test -S . -DCMAKE_TOOLCHAIN_FILE=<ohos.toolchain.cmake> \
  -DOHOS_ARCH=arm64-v8a -DCMAKE_BUILD_TYPE=Release -DBUILD_SHARED_LIBS=OFF \
  -DOPUS_BUILD_TESTING=ON -DCMAKE_RANLIB=/data/service/hnp/bin/llvm-ranlib
cmake --build build-ohos-test -j4
ctest --output-on-failure          # → 5/5 PASS
# meson 独有 projection（1.5.2 草稿口径手动补）
clang tests/test_opus_projection.c -o test_opus_projection \
  -Iinclude -Ibuild-ohos-test -Icelt -Isilk -Idnn -I. build-ohos-test/libopus.a -lm
./test_opus_projection             # → All projection tests passed.
```

### test_package（消费者视角）
- [x] test.c：dlopen libopus.so + dlsym opus_get_version_string 真调用 → PASS
- [x] test_ohos_roundtrip.c：48kHz 立体声正弦 PCM opus_encode→opus_decode 真实回环 →
  PASS "opus roundtrip 16 blocks @48000Hz/2ch (enc 4223 B, dec 15360 samples)"

## 四、关键发现

### 1. 上游 CMake ARM 运行时检测不含 HarmonyOS（非致命）
`cmake/OpusFunctions.cmake` `opus_supports_cpu_detection()` 对 ARM 只认
`CMAKE_SYSTEM_NAME MATCHES "(Windows|Linux|Android|FreeBSD|OpenBSD)"`——HarmonyOS
不在列，`RUNTIME_CPU_CAPABILITY_DETECTION=0` → `message(ERROR "Runtime cpu capability
detection needed for MAY_HAVE_NEON")`。该 ERROR **不阻断 configure**（CMake 的
message(ERROR) 在 CMake 3.x 中只是严重警告语义，Configuring done 照常），且 aarch64 下
`OPUS_PRESUME_NEON=ON`（OpusConfig.cmake:75-80 对 aarch64 强制 presume），NEON 内建
函数源（celt/arm、silk/arm）在 MAY_HAVE 分支外照常编译。动态库构建（主配方）与测试
静态构建均验证通过。

### 2. SDK llvm-ranlib 缺失（静态测试构建小坑）
ohos-sdk_26.0.0.18 的 llvm/bin/ 有 llvm-ar 无 llvm-ranlib，静态库 make 链接报
"Error running link command: no such file or directory"。主配方动态库不受影响；
本地测试构建传 `-DCMAKE_RANLIB=/data/service/hnp/bin/llvm-ranlib`（hnp/bin 有）解决。

### 3. 与 opus/1.5.2 配方差异
仅包名（libopus vs opus）+ 版本（1.6.1 vs 1.5.2）；构建打法完全复用（裸 cmake +
自发现 toolchain + 签名）。1.6.1 上游 cmake_minimum_required 3.16（1.5.2 是 3.16 相同）。

## 五、最终状态
- **最终状态**: built（本地 conan create + test_package 全绿 + 上游测试 6/6 PASS）
- **结束时间**: 2026-09-18
