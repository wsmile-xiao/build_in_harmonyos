# DRAFT-libfli-findindi-version-regex-quoted-macro — FindINDI 版本正则不认 INDI 2.x 引号形式

## 现象

`cmake` configure 阶段直接 FATAL_ERROR，报错信息完全没提「正则」二字：

```
CMake Error at cmake_modules/FindINDI.cmake:220 (message):
  failed to detect INDI version
Call Stack (most recent call first):
  CMakeLists.txt:16 (find_package)
```

对应命令：

```bash
cmake -S . -B build -DCMAKE_SYSTEM_NAME=Linux -DCMAKE_SYSTEM_PROCESSOR=aarch64 \
      -DCMAKE_FIND_PACKAGE_PREFER_CONFIG=OFF
```

## 根因

INDI 2.0 起 `indiversion.h` 把版本串写成带引号的字符串字面量：

```c
#define INDI_VERSION_MAJOR   2
#define INDI_VERSION_MINOR   2
#define INDI_VERSION_RELEASE 2
#define INDI_VERSION "2.2.2"      /* ← 带引号 */
```

项目 snapshot 里 vendored 的 `cmake_modules/FindINDI.cmake`（2022 年版）用：

```cmake
MATCHES ".*INDI_VERSION ([0-9]+).([0-9]+).([0-9]+)"
```

要求 `INDI_VERSION` 与数字之间只有空格。实际是空格 + `"`，匹配失败 → 走
`message(FATAL_ERROR "failed to detect INDI version")`。

因为 `find_package(INDI REQUIRED)` 是硬依赖，configure 失败即整个包构建失败。

**关键性质：与平台无关。** Linux 上链接 INDI >= 2.0 一样复现，因为问题出在
项目 snapshot 里的 Find 模块早于 INDI 2.x 的头文件格式变更。这也决定了**不能**
用平台宏绕过（铁律 R8）。

## 排查路径（含一处易走错的岔路）

```bash
# 岔路 1：先怀疑「Conan 的 libindi 包没装对」——排除
$ ls /root/.conan2/p/libin*/p/include/libindi/indiversion.h    # 存在
$ ls /root/.conan2/p/libin*/p/include/libindi/indidevapi.h    # 存在
$ ls /root/.conan2/p/libin*/p/lib/libindidriver.a              # 存在
# → 包是好的，问题不在「装没装」

# 岔路 2：怀疑 INDI_ROOT 没传进去——排除
# CMake 警告: Policy CMP0074 is not set: find_package uses <PackageName>_ROOT
#   CMake variable INDI_ROOT is set to: ... For compatibility, CMake is ignoring
#   the variable.
# → INDI_ROOT 确实被忽略了，但 INDI_INCLUDE_DIR 照样找到了（find_path 走
#   CMAKE_PREFIX_PATH），所以也不是这里

# 定位真因：把被探测的头文件与探测正则并排看
$ grep -n INDI_VERSION <pkg>/include/libindi/indiversion.h
5:#define INDI_VERSION "2.2.2"
$ grep -n INDI_VERSION <src>/cmake_modules/FindINDI.cmake
215:    if(... MATCHES ".*INDI_VERSION ([0-9]+).([0-9]+).([0-9]+)")
# → 正则要求空格后直接是数字，文件里是空格 + 引号。矛盾成立。

# 确认上游是否已修
$ curl -sS https://raw.githubusercontent.com/indilib/indi-3rdparty/master/cmake_modules/FindINDI.cmake \
    | diff -u <src>/cmake_modules/FindINDI.cmake -
@@ -212,10 +244,10 @@
-    if(... MATCHES ".*INDI_VERSION ([0-9]+).([0-9]+).([0-9]+)")
+    if(... MATCHES "INDI_VERSION[ ]+\"?([0-9]+)\\.([0-9]+)\\.([0-9]+)\"?")
# → master 已修，且只有这一处 hunk。走「回移」而非自创。
```

## 修复

逐字回移上游 master 的同一行，成 portability 补丁：

```cmake
-    if(... MATCHES ".*INDI_VERSION ([0-9]+).([0-9]+).([0-9]+)")
+    if(... MATCHES "INDI_VERSION[ ]+\"?([0-9]+)\\.([0-9]+)\\.([0-9]+)\"?")
```

补丁**不含任何平台宏**（Linux 上同样需要，不触发 R8），在 `conandata.yml` 注册：

```yaml
patches:
  - patch_file: "patches/0001-FindINDI.cmake.patch"
    patch_description: "FindINDI.cmake 版本号正则回移上游 master 修复"
    patch_type: "portability"
```

## 验证

```
$ patch -p1 --dry-run < patches/0001-FindINDI.cmake.patch
checking file cmake_modules/FindINDI.cmake        # DRY_RUN_OK

$ conan create . -pr:h=ohos-aarch64-wsl -pr:b=ohos-aarch64-wsl --build=missing
-- Found USB1: .../libusb-1.0.so
-- Performing Test USB1_HAS_LIBUSB_ERROR_NAME - Success
-- Found INDI: .../libindidriver.so;.../libindiAlignmentDriver.so (found version "2.2.2")
-- Configuring done
-- Generating done
# → 14 个源文件全部编译通过，含 unix/linux/libfli-parport.c
```

## 查重差异表

| 既有条目 | 相似点 | 本条差异 |
|---|---|---|
| `E092`（CMake 不识别 HarmonyOS 平台） | 同为 cmake configure 阶段 FATAL_ERROR | E092 是**平台不认识**（需 `CMAKE_SYSTEM_NAME=Linux`）；本条是**自带 Find 模块的版本解析逻辑过时**，平台设对了照样挂。两者可同时命中，libfli 就两个都踩了 |
| `E999-draft-8FBE`（OHOS libc 符号族 configure 误检） | 都发生在 configure 探测层 | E999 是 OHOS libc 导出 fortify `__*_chk` 干扰 `AC_CHECK_FUNCS`（autoconf）；本条是 CMake 正则与头文件宏格式不匹配，**与 libc 符号无关、也与平台无关** |
| `DRAFT-libfli-*` 同仓姊妹包（libfishcamp） | 同一 monorepo 的 FindINDI.cmake | libfishcamp 走的是「本地 `#define INDI_UNUSED(x)` 彻底摘掉 INDI」路线，根本不跑 FindINDI.cmake；libfli 保留上游 `find_package(INDI REQUIRED)`，因此必然命中本条 |

## 禁止做法

| 禁止 | 原因 |
|---|---|
| 补丁里加 `#ifdef __OHOS__` 绕过 | 与平台无关，Linux 用户继续踩坑；违反 R8 |
| 注释掉 `find_package(INDI REQUIRED)` / 改可选 | `libfli.c` / `libfli-camera-usb.c` 真的 include 了 `indimacros.h`（用 `INDI_UNUSED`），去掉依赖编译直接失败 |

## 来源

- 上游任务：archives/l/libfli/2.0-20221221182632
- 上游仓库：https://github.com/indilib/indi-3rdparty（`libfli/` 子目录）
- 修复 commit：indi-3rdparty master `cmake_modules/FindINDI.cmake`
