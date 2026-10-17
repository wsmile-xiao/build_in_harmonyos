# Draft: libmysofa OHOS 交叉工具链 find_library(m) NOTFOUND 的 sysroot libm 注入

> Source event: `libmysofa/1.3.5` OHOS 适配 conan create 配置阶段，2026-09-07。
> Draft only. Do not promote to `knowledge/graph/` without reviewer assignment.

## Problem

libmysofa 上游 `src/CMakeLists.txt` 使用：

```cmake
find_library(MATH m)
target_link_libraries(mysofa-static LINK_PRIVATE ${MATH} ${ZLIB_LIBRARIES})
```

在 OHOS 交叉构建（conan profile `ohos-aarch64` 仅注入
`tools.build:compiler_executables`，未设置 `CMAKE_SYSROOT`/
`CMAKE_FIND_ROOT_PATH`）时，CMake 无法在默认搜索路径找到
sysroot 内的 libm：

```text
CMake Error: The following variables are used in this project, but they are set to NOTFOUND.
MATH
    linked by target "mysofa-shared" ...
    linked by target "mysofa-static" ...
```

## Root cause

OHOS SDK 的 libm.a 位于
`<sysroot>/usr/lib/aarch64-linux-ohos/libm.a`，但 conan 交叉 profile
不注入 sysroot 搜索路径，`find_library` 看不到它。与 E376 不同——
E376 的场景是"目标无需独立 libm，可空绑定"；本案例 libm 是真实
必需且确实存在于 sysroot，E376 的 empty-binding 方案在其自身禁止
做法中被排除（无证据证明符号无需独立 libm 时禁止空 cache 绑定）。

## Recommended handling

在 conanfile.py 的 `generate()` 中对 OHOS 显式注入 MATH 缓存变量：

```python
import glob, os
if self.settings.os == "OHOS":
    sysroots = sorted(glob.glob("/data/service/hnp/ohos-sdk.org/*/ohos/native/sysroot"))
    if sysroots:
        arch_dir = {"armv8": "aarch64-linux-ohos",
                    "armv7": "arm-linux-ohos",
                    "x86_64": "x86_64-linux-ohos"}.get(str(self.settings.arch))
        if arch_dir:
            libm = os.path.join(sysroots[-1], "usr", "lib", arch_dir, "libm.a")
            if os.path.isfile(libm):
                tc.variables["MATH"] = libm
```

验证（libmysofa 实测）：注入后 `conan create` 配置/编译/链接全部通过，
test_package 2/2 ctest 通过，exit 0。

## Applicability

- 适用：CMake 工程 `find_library(MATH m)`/FindMath 且 OHOS sysroot 含
  `<arch>-linux-ohos/libm.a` 的配方；任何 C 库在 ohos-aarch64 profile
  下数学库链接场景。
- 反例/边界：目标确实无需独立 libm（符号由 libc/toolchain 提供）时
  不应注入路径，应按 E376 做证据支撑的空绑定；非 OHOS 平台（Linux
  本机）find_library 默认路径即可命中，无需注入。
- 关系: similar_to E376（同为 libm NOTFOUND cache 问题，方案方向相反）；
  conflicts_with E376 的 empty-binding（本案例需要真实 libm）。
