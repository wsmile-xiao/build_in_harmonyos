# caps 0.9.26 适配笔记

## 编译环境
- 构建系统: makefile (configure.py + Makefile)
- 编译日期: 2026-08-05
- 编译器: clang 15.0.4 / clang++ 15.0.4
- 目标平台: OpenHarmony aarch64
- 状态: published

## 编译步骤

1. **初始化**: `python3 $SKILL_ROOT/scripts/ohc-run.py init-build caps 0.9.26 --url=https://quitte.de/dsp/caps_0.9.26.tar.bz2`
2. **配置**: `python3 configure.py` — 生成 defines.make (SSE 检测在 aarch64 上自然失败)
3. **编译**: `make -j1 CC=clang++` — 所有 .cc 文件编译成功 (仅 warnings, 无 errors)
4. **安装**: `make install PREFIX=$DEFAULT_PREFIX DESTDIR=$TEST_PREFIX`
5. **测试**: `make check` — 无此 target (LADSPA 插件库，无可执行二进制)
6. **收尾**: `python3 $SKILL_ROOT/scripts/ohc-run.py finish caps 0.9.26 published`

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `__int8_t` 等类型未定义 | basics.h 使用 glibc 内部类型名, musl/OpenHarmony 不提供 | 无条件添加 `#include <stdint.h>`, 使用标准 `int8_t`/`uint8_t` 等类型 |
| 2 | `__builtin_sinf/__builtin_cosf` 模板参数不匹配 | GCC 允许内置函数作为模板参数, clang 不支持 | 无条件替换为 `sinf`/`cosf` (标准 C 数学函数) |
| 3 | `exp10f` 未定义 | GNU 扩展函数, musl 不提供 | 无条件定义为 `powf(10.0f, f)` (替代 `#ifdef __APPLE__` 分支) |
| 4 | configure.py SSE 检测 | aarch64 无 SSE, /proc/cpuinfo 无 SSE 标志 | SSE 检测自然返回 0, 无需特殊处理 |
| 5 | Makefile CC=g++ | g++ 不存在 | 修改为 `CC = clang++` |

## 源码修改

4 个补丁 (全部使用无条件 POSIX/标准 C 适配, 无 #ifdef __OHOS__):
- `0001-Makefile.patch`: CC=g++ → clang++
- `0002-basics.h.patch`: 添加 `#include <stdint.h>`, 替换 glibc 内部类型为标准 C99 类型
- `0003-dsp-v4f.h.patch`: 替换 `__builtin_sinf/cosf` → `sinf/cosf`
- `0004-dsp-v4f_IIR2.h.patch`: 替换 `__builtin_sinf/cosf` → `sinf/cosf`, 将 exp10f 定义为 `powf(10.0f, f)` (替代 `#ifdef __APPLE__` 条件分支)

## 依赖版本

无外部依赖 (LADSPA 插件库, 仅需标准 C/C++ 库)

## 验证结果

```bash
# caps.so 编译成功
# caps.rdf 元数据文件生成
# 质量门禁 G1-G4: PASS
# conan-verify: PASS (G1-G4 + L2/L4/L5)
# W3 本地 CI 模拟: PASS
```

## 注意事项

- caps 是 LADSPA (Linux Audio Developers Simple Plugin API) 音频效果插件库
- 无可执行二进制文件 (仅 caps.so 共享库和 caps.rdf 元数据)
- v4f.h 使用 GCC vector_size 扩展, 在 clang/aarch64 下作为 NEON 向量运行
- `-ffast-math` 和 `-funroll-loops` 为原始 Makefile OPTS, 保留未修改
- make check target 不存在
- configure.py 的 SSE 检测在 aarch64 上自然失败 (无 /proc/cpuinfo 或无 SSE 标志), make clean 失败但不影响构建

---
**编译结束**: 2026-08-05
**最终状态**: published
