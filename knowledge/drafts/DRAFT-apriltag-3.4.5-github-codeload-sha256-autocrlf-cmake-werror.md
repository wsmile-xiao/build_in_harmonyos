# DRAFT-apriltag-3.4.5：GitHub codeload 源码哈希（autocrlf）与 CMake -Werror 无 CACHE 摘除链

> Contributor: 2301_76770579 | Status: Draft | Updated: 2026-09-08
> Source: PR #9009 feat(apriltag): 3.4.5 适配 HarmonyOS PC（OHOS aarch64 / clang-15 / CMake）

## 背景

apriltag 3.4.5（AprilTag 3，AprilRobotics）是视觉基准 tag 检测库：灰度图上跑四线
检测/编解码/位姿估计，纯 C99 + CMake，仅依赖系统 threads + libm（零第三方依赖）。
迁移到 OpenHarmony PC（OHOS aarch64，clang-15，HMDFS）时，源码哈希核验与
CMake -Werror 硬化各踩一坑。两坑都"看着能本地绕，实则必须按正确姿势做"，
合成一条带证据的通用经验。

## 坑 1：Windows 上算 GitHub codeload sha256 被 core.autocrlf 污染

### 现象

conanfile `source()` 的 conandata sha256 与本机 `git archive` 算出的值不符，
worker `get()` 报 checksum mismatch，构建直接失败。

### 根因

conandata sha256 必须是 GitHub codeload（`/archive/refs/tags/<tag>.tar.gz`）产出
tarball 的**逐字节**哈希。GitHub 在 Linux 上产出，文本文件是 LF。Windows host
上 git for Windows 默认 `core.autocrlf=true`，用 `git archive` 生成归档估算哈希时
会把文本文件转成 CRLF，整包哈希与 GitHub 的 LF 字节不一致 → 核验必失败。

### 修复

1. 哈希必须在干净的 LF 语义下算：
   `git -c core.autocrlf=false archive --format=tar.gz --prefix=<name>-<ver>/ <tag>`
2. **交叉验证**（排除 CRLF/打包差异）：与 distro 同源包比 sha / 解包 diff。
   本包 sha256=3749f48220db78c29c375a373861f4e1f4138e5dbae3c298584e96cfcc556515，
   与 Debian/Ubuntu pool `apriltag_3.4.5.orig.tar.gz` 完全一致（解包全文件 diff=0）。

### 验证

```sh
git -c core.autocrlf=false archive --format=tar.gz --prefix=apriltag-3.4.5/ v3.4.5 \
    | sha256sum                      # 3749f482…（LF 归档哈希）
curl -s https://deb.debian.org/debian/pool/main/a/apriltag/apriltag_3.4.5.orig.tar.gz \
    | sha256sum                      # 3749f482… 一致
tar tzf <codeload tar.gz> | head     # 顶层 apriltag-3.4.5/ 且含 test/
```

## 坑 2：CMake -Werror 无 CACHE，-D 覆盖不掉，只能补丁摘除

### 现象

OHOS clang-15 把上游启用的 -Wpedantic/-Wall 告警抬成错误，`conan create` 构建失败。

### 根因

上游把 -Werror 当"静态库代码卫生"，CMake>=3.24 走
`set(CMAKE_COMPILE_WARNING_AS_ERROR ON)`（**无 CACHE 关键字**），<3.24 走
`add_compile_options(-Werror)`。无 CACHE 的 `set()` 不接受 configure 时的 -D 覆盖，
`-DCMAKE_COMPILE_WARNING_AS_ERROR=OFF` 只在有 CACHE 时生效 → 配方里关不掉。

### 修复

直接打补丁把该 if/else 块摘掉（仅降级为告警，不影响库行为）：

```diff
- if(${CMAKE_VERSION} VERSION_GREATER_EQUAL "3.24.0")
-     set(CMAKE_COMPILE_WARNING_AS_ERROR ON)
- else()
-     add_compile_options(-Werror)
- endif()
```

## 附带坑 3：install 保目录头 + 随包可实跑的上游 ctest

### 现象 / 修复

1. 上游 install 把 `*.h` 与 `common/*.h` 按相对路径装到 `include/apriltag/`
   （`apriltag.h` 相对 include `common/*.h`）。消费者 `includedirs` 应指
   `include/apriltag` 而非 `include`，`#include "apriltag.h"` 才能解析到 common/*.h。
2. `BUILD_TESTING=ON` 时 `test/` 注册 3 个 `test_detection_*` ctest：同一程序对 3 张
   随包真实照片跑 tag36h11 全流程，与 `test/data/*.txt` 真值逐角点比对（容差 0.1px）。
   照片+真值随源码包分发 → 无需网络，build() 内 `cmake.test()` 直接实跑 3/3
   （对比需 guile/submodule 的库，rule4 上游测试可 vendored 实跑）。

## 验证

```sh
conan create . -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=同   # build 内 cmake.test() 3/3
# test_package 消费者：matd 数值断言 + tag36h11 family 字段 + 全白图 detect=0（R34 反空壳）
```

## 关系

- 坑 1 关联源码哈希/CRLF 类（GitHub codeload sha256 在 Windows 计算的通用陷阱）。
- 坑 2 关联 CMake -Werror 类（无 CACHE 的 set 无法用 -D 关闭，只能补丁摘除，
  与 libksba 等上游强制 -Werror 的库同谱）。
- 附带坑 3 关联头保目录 include 解析类（install 保目录 → includedirs 指 include/<name>）。
