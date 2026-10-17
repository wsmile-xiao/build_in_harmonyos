# DRAFT — CMake `find_library(m)` 在 OpenHarmony NDK 上返回 NOTFOUND

> Status: **Draft**（待主编 promote） | severity: `2` | category: `cmake` | Updated: 2026-09-26
> 源文件：`knowledge/drafts/DRAFT-mapcode-2.5.7-cmake-find-library-m-notfound.kv`
> 来源：mapcode 2.5.7 适配（`feat/mapcode-2.5.7`）

---

**关键词**：find_library, NOTFOUND, M_LIB-NOTFOUND, libm.a, aarch64-linux-ohos, GNUInstallDirs

## 现象（error_signature）

```text
CMake Error: The following variables are used in this project, but they are set to NOTFOUND.
Please set them or make sure they are set and tested correctly in the CMake files:
M_LIB
    linked by target "mapcode" in directory /root/.conan2/p/mapco59cf2891ad24a/s
    linked by target "unittest" in directory /root/.conan2/p/mapco59cf2891ad24a/s
    linked by target "mapcodelib" in directory /root/.conan2/p/mapco59cf2891ad24a/s
---
ld.lld-15: error: unable to find library -lM_LIB-NOTFOUND
```

## 根因（root_cause）

OpenHarmony NDK 把库放在 sysroot 的**目标三元组目录**下：

```text
sysroot/usr/lib/aarch64-linux-ohos/libm.a     # 只有静态库，没有 libm.so
```

CMake 的 `find_library` 不探测该三元组子目录 → `M_LIB = M_LIB-NOTFOUND`。
上游无条件 `target_link_libraries(... ${M_LIB})` → 链接器收到字面量
`-lM_LIB-NOTFOUND`。

**关键判断：库本身是存在的**（只是只有 `.a`）。所以正确解法不是改工具链、
不是造 sysroot 软链、也不是把 libm 静态编进 libc —— 而是让 CMake 退回纯链接器
标志 `-lm`，由链接器按自己的搜索路径找到 `libm.a`。

## 处方（rec_approach）

```cmake
find_library(M_LIB m)
if(NOT M_LIB)
    set(M_LIB m)
endif()
```

该写法**不含任何平台宏**（符合 R8 / PF5），对所有平台都是幂等的：
查得到时兜底完全不生效。mapcode 的补丁用的就是它。

## 备选（fallback）

若目标库连 `.a` 都没有，可显式给出 sysroot 内路径：

```cmake
set(M_LIB "${CMAKE_SYSROOT}/usr/lib/${CMAKE_LIBRARY_ARCHITECTURE}/libm.a")
```

或在 recipe 里 `tc.cache_variables["M_LIB"] = "<path>"`。
缺点是把平台布局写死进配方，可移植性差，仅作兜底。

## 反模式（forbid_1）

```text
find_library\([A-Za-z_]+\s+[a-z]+\)[\s\S]{0,200}?target_link_libraries\([^\n]*\$\{[A-Za-z_]+\}
```

`find_library` 的结果未经 `NOTFOUND` 校验就传给 `target_link_libraries`，
在库只存在于目标三元组子目录的 sysroot 上必然产生 `-lXXX-NOTFOUND`。

## 验证

```bash
ls "$SYSROOT/usr/lib/aarch64-linux-ohos/" | grep '^libm'   # 期望看到 libm.a
```

看到 `libm.a` 即确认「库存在、只是 find_library 找不到」，按主处方处理。

---

*本条目为草稿。正式化请用 `ohc-run.py graph promote` 提升到 `knowledge/graph/`。*
