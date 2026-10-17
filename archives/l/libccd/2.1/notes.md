# libccd 2.1 编译笔记（HarmonyOS PC · 标准 Conan cmake）

## 定位
- 产出 libccd.so 等 1 个库，供链接与 dlopen。

## 关键适配
- 无特殊适配：上游源码直接可用鸿蒙 PC 原生工具链构建。

## 补丁说明

### 0001-libm-optional-on-musl.patch —— libm 在 musl 上不是独立库

上游 `src/CMakeLists.txt` 用 `find_library(LIBM_LIBRARY NAMES m)` 找数学库，
找不到就 `message(FATAL_ERROR "Could NOT find required library LibM")`。

鸿蒙是 musl：**数学函数已并入 libc**，sysroot 里只有静态 `libm.a`、没有 `libm.so`，
而 conan toolchain 下 `find_library` 落空 → 配置期直接失败。

**试过两种「填个值绕过去」，都不行**（各撞一次）：

| 尝试 | 结果 |
|---|---|
| `-DLIBM_LIBRARY=m` | `make: No rule to make target 'm'` —— CMake 当成文件依赖 |
| `-DLIBM_LIBRARY=-lm` | `make: No rule to make target '-lm'` —— 同样当成文件 |

设备实测：`clang x.c -lm` 与**不带** `-lm` 都能链接并运行，证明这个链接项本就多余。
所以正解是让它**可选**（找到就链、找不到就跳过），而不是造一个假值。
对 glibc 平台无影响——那里 `find_library` 能找到，行为不变。

## 状态
built（真机 conan create + test_package 通过）
