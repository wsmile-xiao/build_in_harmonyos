# expat 2.8.2.1 编译笔记（HarmonyOS PC）

## 本版改了什么

构建路径从 **conan 的 `CMakeToolchain`（conan_toolchain）** 改为本仓已验证的
**「自发现 `ohos.toolchain` + 裸 cmake」**（glfw / libjpeg-turbo / zstd / opus 同法），
并在 `package()` 后重签 `.so`。构建选项与源码 sha256 与 2.8.2 完全一致。

## 为什么需要这个修复：产物无 SONAME，污染下游 DT_NEEDED

`os=OHOS` 下 conan 的 `CMakeToolchain` 把 `CMAKE_SYSTEM_NAME` 映射成 cmake 不认的值（ML-0035），
后果之一是**产物不带 SONAME、也不生成版本化软链**。实测 2.8.2 的产物：

```
$ llvm-readelf -d libexpat.so
 0x0000000000000001 (NEEDED)  Shared library: [libc.so]
（无 SONAME 条目；lib/ 下只有 libexpat.so，无 libexpat.so.1 及软链）
```

**链接器在被链库没有 SONAME 时，会把该库的「路径」原样写进消费方的 DT_NEEDED。**
于是 `fontconfig/2.18.1` 链本包后，其 `libfontconfig.so.1` 的 DT_NEEDED 变成

```
/storage/…/.conan2/p/expat9fb72708ad085/p/lib/libexpat.so
```

——**烤死了 expat 的包目录哈希**。一旦 expat 落到别的包目录（换机器、换 revision、清 cache 后重装），
消费方就在加载期报：

```
Error loading shared library /…/expat9fb72708ad085/p/lib/libexpat.so:
  (needed by /…/fontconfig/lib/libfontconfig.so.1)
Error relocating …/libfontconfig.so.1: XML_ParserCreate: symbol not found
（以下一串 XML_* symbol not found）
```

这个坑很隐蔽：在**恰好路径一致**的机器上一切正常，换个环境才炸。

## 修法

改用裸 cmake + SDK 的 `ohos.toolchain.cmake`，cmake 正常识别平台并生成 SONAME 与版本软链；
下游链接时 DT_NEEDED 记的是 soname（可重定位）而非绝对路径。
另按该路径的惯例补 `_sign_binaries()`（cmake 走 SDK toolchain 产的 `.so` 自签无效，须重签）。

## 版本号

按 R37：`2.8.2` 已发布到制品仓，改配方须递增后缀 → `2.8.2.1`。
下游 `fontconfig` 需同步升到 `2.18.1.1` 以引用本版。


## 2026-08-07 issue #1912 follow-up

`vips/8.18.4` shadow CI exposed a device filesystem limitation while building
this dependency:

```text
CMake Error: failed to create symbolic link 'libexpat.so.1': Permission denied
CMake Error: cmake_symlink_library: System Error: Permission denied
```

The failure happened in the build tree before `package()`, so post-install
symlink cleanup cannot help. The recipe now passes
`CMAKE_PLATFORM_NO_VERSIONED_SONAME=ON` while keeping the OHOS toolchain SONAME
flag (`-Wl,-soname,`). This asks CMake to emit an unversioned shared library on
platforms where versioned shared-object links are not usable, while still
avoiding the previous no-SONAME downstream `DT_NEEDED` path contamination.

The CI registry check reported that `expat/2.8.2.1` has already been published,
so this follow-up fix is carried as the incremented package version
`expat/2.8.2.1.1`.

## Upstream tests

The recipe enables upstream CMake option `EXPAT_BUILD_TESTS=ON`. After building,
it signs and directly runs `build-ohos/tests/runtests` on runnable OHOS targets.
This is Expat's complete bundled C unit/regression runner, using its internal
minicheck implementation and no downloaded test framework. Any non-zero test
exit status fails `conan create`; the final check count and pass rate are taken
from the runner output rather than estimated from source declarations.

Official shadow CI #21766 executed all 402 registered `START_TEST` functions
through the runner's 6 chunk-size configurations and 2 reparse-deferral modes:

```text
Expat version: expat_2.8.2
100%: Checks: 4824, Failed: 0
```

The upstream test pass rate is therefore **4824/4824 (100%)**. No upstream test
source was changed or excluded. The Conan `test_package` API check and the R34
destructive negative check also passed, for an additional **2/2 (100%)**.
