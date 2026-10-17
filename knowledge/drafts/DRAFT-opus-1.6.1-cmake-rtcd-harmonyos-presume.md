# DRAFT — 上游 CMake ARM 运行时 CPU 检测正则不含 HarmonyOS：message(ERROR) 非致命，aarch64 PRESUME 兜底

## 现象 (What happened)

对 libopus 1.6.1（xiph 官方 tarball）做 OHOS PC aarch64 交叉构建（ohos.toolchain.cmake）：

```
ERRORRuntime cpu capability detection needed for MAY_HAVE_NEON
-- Configuring done (8.5s)
-- Generating done (0.1s)
-- Build files have been written to: .../build-ohos-test
```

configure 报一行 `ERRORRuntime cpu capability detection needed for MAY_HAVE_NEON` 后**照常
Configuring done**。全量构建（含 celt/arm、silk/arm 全部 NEON intrinsics 源）+ 5 个上游
ctest + meson 独有 test_opus_projection 手动补跑，**6/6 全 PASS**。

## 根因 (Root cause)

`cmake/OpusFunctions.cmake` 的 `opus_supports_cpu_detection()`：

```cmake
elseif(OPUS_CPU_ARM)
    # ARM cpu detection is implemented for Windows, Linux, Android, FreeBSD
    # and OpenBSD.
    if (CMAKE_SYSTEM_NAME MATCHES "(Windows|Linux|Android|FreeBSD|OpenBSD)")
      set(RUNTIME_CPU_CAPABILITY_DETECTION 1 PARENT_SCOPE)
    endif ()
```

OHOS 工具链注入 `CMAKE_SYSTEM_NAME=HarmonyOS` 不在白名单正则内 →
`RUNTIME_CPU_CAPABILITY_DETECTION=0` → CMakeLists.txt:568
`message(ERROR "Runtime cpu capability detection needed for MAY_HAVE_NEON")` 触发。

两个关键语义：
1. **CMake `message(ERROR)` ≠ fatal**：只有 `FATAL_ERROR` 才终止 configure。ERROR 在
   CMake ≥3.0 是「严重警告」语义，configure 继续。
2. **aarch64 强制 PRESUME**：`cmake/OpusConfig.cmake:75-80` 对
   `CMAKE_SYSTEM_PROCESSOR MATCHES "aarch64"` 强制 `OPUS_PRESUME_NEON=ON`——NEON 被视为
   架构必备而非运行时探测目标。MAY_HAVE 分支内的 rtcd 源组（celt_sources_arm_rtcd 等）
   不加载，但 NEON intrinsics 源（celt/arm、silk/arm）在 `if(COMPILER_SUPPORT_NEON)` 分支
   外照常编译进库。

## 解法 (Fix)

**aarch64 OHOS 构建：无需任何补丁**。验证三步：
1. configure 输出确认 `Configuring done`（ERROR 行只是噪音）
2. 构建产物确认 NEON 源编译（`cmake --build ... | grep -cE "celt/arm|silk/arm"` > 0）
3. 上游测试全绿（本例 5 ctest + projection 6/6）

仅当目标含 armv7（真需 RTCD）或上游逻辑分支依赖 `OPUS_HAVE_RTCD` 宏时，才 patch
正则追加 HarmonyOS（portability 补丁）。

## 验证 (Verification)

HarmonyOS PC aarch64 真机（2026-09-18）：

- `conan create libopus/1.6.1`（ohos-aarch64 profile）全绿，libopus.so 签名打包成功
- 上游测试：ctest 5/5（decode 11.81s / padding 0.09s / api 6.91s / encode 26.17s /
  extensions 52.32s，Total 97.32s）+ 手动编译 meson 独有 test_opus_projection
  （clang 直链 libopus.a + -Icelt -Isilk -Idnn）PASS "All projection tests passed."
- test_package：dlopen 探针 + 48kHz 立体声 encode/decode 真实回环 PASS

## 通用性 (Generality)

去掉「opus」库名，本条对以下场景通用：
- 任何 CMake 上游库按 `CMAKE_SYSTEM_NAME` 白名单做 ARM RTCD/feature 探测且白名单不含
  HarmonyOS——OHOS 交叉工具链普遍注入 HarmonyOS 系统名
- 判定要点：先分清 `message(ERROR)`（可继续）与 `message(FATAL_ERROR)`（真终止）；
  再确认目标架构是否走 PRESUME（必备）路径——aarch64 上 NEON 属必备

相关：E007（autotools config.guess 不认 HarmonyOS——同家族不同层）
