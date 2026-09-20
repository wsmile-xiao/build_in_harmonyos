# E999: 旧版 /proc/cpuinfo 式 FindSSE 在非 Linux 系统名下误开 SSE2

## 基本信息
- **严重度**: 2
- **类别**: build-system, cmake, sse, simd, cross-compile, aarch64
- **来源 PR**: feat(libvidstab): 1.1.0 适配 HarmonyOS PC
- **状态**: 草稿（待审核 promote）

## 错误特征
```
xmmintrin.h.*No such file | -msse2.*error | SSE2_FOUND | emmintrin.h.*No such file | __builtin_ia32.*undeclared
```

## 现象
在 OHOS（aarch64）上用 conan CMakeToolchain 构建 vid.stab 1.1.0 等自带旧式
FindSSE 模块的库时，configure 后编译报 x86 头文件/内联函数不存在
（`xmmintrin.h: No such file or directory`），编译命令里出现 `-msse2`。

## 根因分析
旧式 `CMakeModules/FindSSE.cmake`（vid.stab ≤1.1.0 及同期项目）按
`CMAKE_SYSTEM_NAME` 三分支检测：

- `Linux` → `cat /proc/cpuinfo` 正则找 `sse2`
- `Darwin` → `sysctl machdep.cpu.features`
- `Windows` / **其余全部** → 最终 `ELSE` 分支 `set(SSE2_FOUND true CACHE BOOL ...)`

OHOS 适配版 conan 生成 `CMAKE_SYSTEM_NAME=HarmonyOS`，既非 Linux 也非
Darwin/Windows，落入 ELSE 分支被硬编码为 `SSE2_FOUND=true`；顶层
`if(SSE2_FOUND)` 于是给 aarch64 目标注入 `-msse2 -DUSE_SSE2`，x86-only
内联块被启用，编译必然失败。

## 推荐方案
**预置同名 cache 变量拦截**（配方内，不改上游源码）：

```python
def generate(self):
    tc = CMakeToolchain(self)
    tc.cache_variables["SSE2_FOUND"] = "FALSE"   # 生成 -DSSE2_FOUND=FALSE
    tc.generate()
```

CMake 语义：已存在的 cache 条目不会被**无 FORCE** 的 `set(... CACHE ...)`
覆盖，FindSSE 的 ELSE 置 true 因此失效；`if(SSE2_FOUND)` 为假，全部 x86
内联块保持在 `#ifdef USE_SSE2` 守卫内，走可移植 C 路径。

**验证**：
- configure 输出包含 `Could not find hardware support for SSE2 on this machine.`
- 编译日志 `grep msse2` 无输出

## 适用范围
- 自带旧式 FindSSE / /proc/cpuinfo 检测的 SIMD 库（vid.stab ≤1.1.0 等）
- OHOS conan（CMAKE_SYSTEM_NAME=HarmonyOS）交叉编译场景

## 上游修复参考
vid.stab 1.1.2 起将 FindSSE 换成 `check_c_compiler_flag(-msse2)` +
`try_compile(TestSSE2.c)`，在 aarch64 上自然失败（无需人工干预）；本条仅
旧版本需要。
