# pcaudiolib 1.3 适配笔记

## 编译环境
- **构建系统**: autotools
- **编译日期**: 2026-09-03
- **平台**: arm64-ohos（OpenHarmony PC）
- **状态**: built（Conan 配方验证通过）
- **补丁数量**: 1

## 编译步骤（conan create 全流程）

```bash
conan create archives/p/pcaudiolib/1.3 --build=missing -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
```

### 1. 源码获取（source()）
`get()` 从 conandata 声明的 GitHub gh-proxy tarball 下载（1.3 release）。

### 2. 依赖注入（generate()）
- 无硬依赖（PulseAudio/ALSA/OSS/Cygwin 为可选 --with-* 后端）
- autotools configure 传 `--host=aarch64-unknown-linux-ohos` + 关闭音频后端

### 3. 构建（build()）
- 0001-config-ohos.patch：config.guess/config.sub 加 HarmonyOS 分支
  （aarch64-unknown-linux-ohos），否则交叉编译报 unable to guess system type
  （沿用 main 已收录版本）
- E114：config.status/configure 的 umask 077 临时目录 HMDFS 拒绝 → 改写
  umask 022（与 asterisk/speech-dispatcher 同款）
- ac_cv_func_malloc_0_nonnull=yes / ac_cv_func_realloc_0_nonnull=yes
  （交叉编译 rpl_malloc 误判）
- autotools configure + make

### 4. 打包（package()）
- autotools install；产物：libpcaudiolib.so（便携 C 音频库）+ 头文件

## 依赖
- 无硬依赖（PulseAudio/ALSA/OSS/Cygwin 可选后端，OHOS 无音频设备关闭）

## 上游测试（rule 4）
- pcaudiolib 无独立测试套件（configure.ac 无 check_PROGRAMS/TESTS、顶层无
  test/ 目录）——按 rule 1.2 如实声明（非跳过）；make check 尝试执行并
  记录结果
- 本地验证：conan create 通过，pcaudiolib 库与头文件编译链接成功
- 适配后：test_package R34 真实产物校验——libpcaudiolib.so 存在 + ELF
  shared object，1/1 = 100%

## 已知限制
- espeak-ng 的便携 C 音频库——OHOS 无音频设备，跨平台音频后端
  （PulseAudio/ALSA/OSS）关闭；API 可编译打包
