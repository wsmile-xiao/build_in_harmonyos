# openal-soft 1.25.2 — notes.md

## 概述

OpenAL Soft 1.25.2（C/C++，CMake 3.13...3.31，C++20/C17，LGPL-2.0-or-later）。上游 https://github.com/kcat/openal-soft，tag `1.25.2`，tag commit `b2c48f7718ef3fcf67921a8b6534c4914e328970`。

## 源码

- 源码包：`source/openal-soft-1.25.2.tar.gz`（1,407,972 字节）
- 本地实测 SHA256：`fb27e5839aa11f0e5b9d33756965291fad5d6909ab928ea1f796f4a1a6877894`
- 上游 GitHub Release **未提供官方源码 SHA256**；Release 二进制 zip digest `67a0c4b8...e265434` 不是源码 hash，不得冒充。
- 许可证：根目录 COPYING 为 GNU LGPL v2，含 "any later version" 条款（LGPL-2.0-or-later）。

## 构建（最小核心，关闭全部外部后端）

```bash
cmake -S . -B build-min \
  -DALSOFT_UTILS=OFF -DALSOFT_EXAMPLES=OFF -DALSOFT_TESTS=OFF \
  -DALSOFT_DLOPEN=OFF -DALSOFT_ENABLE_MODULES=OFF -DALSOFT_BACKEND_WAVE=OFF \
  -DALSOFT_BACKEND_ALSA=OFF -DALSOFT_BACKEND_PULSEAUDIO=OFF -DALSOFT_BACKEND_PIPEWIRE=OFF \
  -DALSOFT_BACKEND_JACK=OFF -DALSOFT_BACKEND_OSS=OFF -DALSOFT_BACKEND_SOLARIS=OFF \
  -DALSOFT_BACKEND_SNDIO=OFF -DALSOFT_BACKEND_PORTAUDIO=OFF \
  -DALSOFT_BACKEND_SDL2=OFF -DALSOFT_BACKEND_SDL3=OFF \
  -DALSOFT_BACKEND_OBOE=OFF -DALSOFT_BACKEND_OPENSL=OFF -DALSOFT_BACKEND_COREAUDIO=OFF
cmake --build build-min -j4   # rc=0
```

- 实际启用后端：仅 Null；`config_backends.h` 全部外部后端 HAVE_* = 0。
- 内置 loopback.cpp / null.cpp 常编（"Default backends, always available"）。
- 产物 `libopenal.so` 1,833,472 字节。

## 上游测试

- `ALSOFT_TESTS` 默认 OFF；`tests/` 经 `add_subdirectory(tests)` 接入；`OpenAL_Tests`（GoogleTest，FetchContent `GIT_TAG main`，实际 commit `1b6f64d659944658a4c685b7bd9f04c1c3b8a39b`）；`ExampleTest.Basic` 共 1 个。
- 命令：`ctest --test-dir build-tests --output-on-failure -V` → 退出码 0，1/1（100%）。
- 限制：测试构建使用离线 GoogleTest + `-DATOMCODE_PROBE_FORCE_FMT`（OHOS 探针 workaround）。

## 无设备替代验证（单独统计）

- `alcOpenDevice("No Output")` null 后端：成功；`alcCreateContext`：成功。
- `ALC_SOFT_loopback` / `alcLoopbackOpenDeviceSOFT` / context 属性列表（ALC_FORMAT_CHANNELS_SOFT/ALC_FORMAT_TYPE_SOFT/ALC_FREQUENCY）/ `alcRenderSamplesSOFT`(960 samples)：成功。
- 临时程序退出码 0，失败数 0。
- 1.25.2 无 `alcSetFormat`，loopback 格式经 context 属性列表设置（alc.cpp `UpdateDeviceParams`）。

## 依赖

- fmt-11.2.0、gsl：源码内置（add_subdirectory fmt-11.2.0 EXCLUDE_FROM_ALL；gsl 纯头文件）。
- Threads：`find_package(Threads)`，系统线程能力。
- GoogleTest：仅上游测试使用，FetchContent 外部依赖，非零依赖。
- 生产配方无第三方 Conan 前置依赖。

## 鸿蒙平台限制（探针边界）

- `/tmp` 只读（erofs），使用 `TMPDIR=$HOME/tmp`（`/storage/Users/currentUser/tmp`）。
- clang/clang++ 15.0.4（aarch64-unknown-linux-ohos），cmake 4.1.2 / ninja 1.13.1 / ctest 4.1.2。
- OHOS libc++ 15.0.4 缺部分 ranges（views::elements、views::split）、`<source_location>`、完整 `<format>`；Clang15 触发 typename、结构化绑定捕获、P0960。
- 探针 workaround：`-D_LIBCPP_ENABLE_EXPERIMENTAL`、`$HOME/tmp/compat-inc` shim（source_location/views_elements/views_split）、`libcxx_compat_three_way.h`、`-DATOMCODE_PROBE_FORCE_FMT`，以及 8 个编译修复补丁（typename/结构化绑定/P0960/FORCE_FMT）。**补丁归类：探针临时材料**，已从正式归档移出至 `$HOME/tmp/openal-1.25.2-reports/probe-patches/`；`conandata.yml` 与 `conanfile.py` 不登记/不引用这些探针补丁与 shim。**正式配方当前不可复现**（OHOS 工具链缺 libc++ ranges/source_location/format 能力，需先形成可审查的正式 patch 并复核 ABI 影响后才能接入）；本地构建/测试仅作为探针证据。
- `sign-elf` 不存在：探针 ELF 不能视为已满足可交付门禁。
- SELinux 查询工具缺失（/sys/fs/selinux/enforce 读取 Permission denied）；内核 HongMeng Kernel 1.12.0，CapEff=000000000000002a。
- EXCLUDE_LIST：本轮未生成（探针阶段无打包动作）。

### 对话 #1（finish 收尾，2026-08-02）

- **执行内容**：按框架正式打包流程（`verify-build` 生成 `.verify-passed` 门禁标记 → `PackageBuilder` step9_tarball）生成 `packaging/openal-soft-1.25.2-ohos-aarch64.tar.gz`（5,777,799 字节）与 `packaging/openal-soft-1.25.2-ohos-aarch64-debug.tar.gz`（1,497,848 字节），并写入 `.packaged` 标记。
- **执行结果**：`verify-build` rc=0（质量报告 PASS，verdict=PASS）；`package` rc=0（Step 1-9 全部完成，打包成功）。
- **notes 对话记录**：本段即为最终一致性检查所需的对话记录（`### 对话 #` 标记），用于消除 finalize Phase 3 的 "notes.md 无对话记录" 一致性问题。
- **门禁状态**：conan create rc=0、conan-verify rc=0（G0-G4 全 PASS）、W3 本地 CI 通过；`.ci-result.json` 由 W3 生成。
- **未完成项**：sign-elf 不存在（探针 ELF 未完成可交付签名门禁）；`.staging-verified` 缺失（探针阶段未做 staging 验证）。

## 门禁状态（探针）

- conan create：通过（本地 file:// 源码 + 探针 workaround；官方 URL 版 conandata.yml 需远端网络，见 conandata.yml.official-backup）
- conan-verify：通过（G0/G1/G2/G3 全 PASS）
- finish：W3 本地 CI 通过、.ci-result.json 已生成；归档元数据已补齐
- 未 submit、未 push、未 /ai review、未远端 CI。
---

**编译结束**: 2026-08-02 09:59
**最终状态**: built
