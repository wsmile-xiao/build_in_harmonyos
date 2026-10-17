# librubberband 4.0.0 适配笔记

## 编译环境
- 构建系统: meson + ninja (上游 4.0.0 现代化构建)
- 编译日期: 2026-09-16
- 编译器: clang 15.0.4 (OHOS SDK)
- 状态: built

## 上游信息
- 上游: https://github.com/breakfastquay/rubberband (tag v4.0.0)
- 上游组织名 breakfastquay，包名独立为 librubberband（区别于仓库已有的
  archives/r/rubberband/3.3.0 历史笔记，两者互不覆盖）
- Rubber Band Library: 音频时间拉伸/音高移动引擎（R2 Faster / R3 Finer 双引擎）

## 构建配置

### meson 选项决策
| 选项 | 取值 | 理由 |
|---|---|---|
| fft | builtin | 内置 FFT 实现；fftw 在仓但可关则关（依赖最小化，上游非 darwin 默认即 builtin） |
| resampler | libsamplerate | 前置仓内核 libsamplerate/0.2.2，优于内置 BQResampler 的可变性支持 |
| jni | disabled | 无 JDK 环境 |
| ladspa | disabled | 可选插件（任务要求关） |
| lv2 | disabled | 可选插件 |
| vamp | disabled | 可选插件 |
| cmdline | disabled | 依赖 libsndfile，核心库不需要 |
| tests | enabled | 上游 boost 单测套，8 个 meson test() 目标 |

### 依赖处理
- `libsamplerate/0.2.2`（requires）：meson 探测 `dependency('samplerate')` →
  Conan PkgConfigDeps 生成的是 `libsamplerate.pc`（按包名），generate() 中
  stage 一份 `samplerate.pc` 别名（内容同 libsamplerate.pc，Name 行改名），
  上游 meson.build 无需打补丁。
- `boost/1.90.0.4.1`（build 辅助）：单元测试框架。上游 test.cpp 硬编码
  `BOOST_TEST_DYN_LINK`，制品仓 boost OHOS 包为 shared 构建，正好匹配；
  运行测试时把 boost 的 libdir 加进 LD_LIBRARY_PATH。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | meson 找不到 samplerate | meson 按上游惯例探测 `samplerate.pc`，Conan 按包名生成 `libsamplerate.pc` | conanfile generate() 中生成 samplerate.pc 别名 |
| 2 | 上游测试需动态 boost unit_test | test.cpp 强制 `BOOST_TEST_DYN_LINK` | requires boost shared 包（制品仓即 shared），测试时设置 LD_LIBRARY_PATH |
| 3 | /tmp 只读 | E002 平台限制 | conanfile `_ensure_tmpdir` 把 TMPDIR 指到 build 目录内 .tmp/ |

## 上游测试（N=8，实测全过）

meson.build 注册 8 个 test() 目标（boost unit_test 框架二进制 `tests`）：
Allocators / FFT / Resampler / VectorOps / VectorOpsComplex / SignalBits /
StretchCalculator / Stretcher。

TestLiveShifter.cpp 与 TestBinClassifier.cpp 被编译进 tests 二进制但上游
未注册独立 test() 目标（其用例随其他套件运行或不参与），按上游注册口径
申报 N=8。

CI/本地执行方式：`meson test` 在 conanfile build() 内执行；worker 本身是
OHOS arm64 设备，交叉编译产物原生可跑（aravis 0.8.36 同款先例）。

## 产物
- lib/librubberband.so.3.0.0 (+.so.3/.so 链接)
- lib/librubberband.a
- include/rubberband/{RubberBandStretcher.h, RubberBandLiveShifter.h, rubberband-c.h}
- lib/pkgconfig/rubberband.pc
