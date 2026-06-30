# caps 0.9.26 适配笔记

## 编译环境
- 构建系统: makefile (configure.py + Makefile)
- 编译日期: 2026-05-29
- 编译器: clang 15.0.4 / clang++ 15.0.4
- 目标平台: OpenHarmony aarch64
- 状态: built

## 编译步骤

1. **初始化**: `python3 $SKILL_ROOT/scripts/ohc-run.py init-build caps 0.9.26 --url=https://quitte.de/dsp/caps_0.9.26.tar.bz2`
2. **配置**: `OHOS_BUILD=1 python3 configure.py` — 生成 defines.make (无 SSE 标志, 适合 aarch64)
3. **编译**: `make -j2` — 所有 .cc 文件编译成功 (仅 warnings, 无 errors)
4. **安装**: `make install PREFIX=$DEFAULT_PREFIX DESTDIR=$TEST_PREFIX`
5. **测试**: `make check` — 无此 target (LADSPA 插件库，无可执行二进制)
6. **打包**: `python3 $SKILL_ROOT/scripts/ohc-run.py package caps 0.9.26`
7. **收尾**: `python3 $SKILL_ROOT/scripts/ohc-run.py finish caps 0.9.26 built`

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `__int8_t` 等类型未定义 | basics.h 使用 glibc 内部类型名, musl/OpenHarmony 不提供 | 添加 `#ifdef __OHOS__` 守卫, 使用标准 `int8_t`/`uint8_t` 等类型 |
| 2 | `__builtin_sinf/__builtin_cosf` 模板参数不匹配 | GCC 允许内置函数作为模板参数, clang 不支持 | 替换为 `sinf`/`cosf` (标准 C 数学函数), 并 `#include <math.h>` |
| 3 | `exp10f` 未定义 | GNU 扩展函数, musl 不提供 | 定义 `__ohos_exp10f(x) = powf(10.0f, x)` 并 `#define exp10f __ohos_exp10f` |
| 4 | configure.py 尝试 `make clean` 用 g++ | g++ 不存在 | 添加 OHOS 环境检测, 跳过 make clean |
| 5 | `/proc/cpuinfo` SSE 检测不适用 | aarch64 无 SSE, 无 /proc/cpuinfo | 添加 OHOS 平台判断, 返回 0 跳过 SSE 检测 |
| 6 | Makefile CC=g++ | g++ 不存在 | 修改为 `CC = clang++`, 添加 `-D__OHOS__` 到 OPTS |

## 源码修改

5 个补丁:
- `0001-Makefile.patch`: CC=g++ → clang++, 添加 -D__OHOS__ 到 OPTS
- `0002-basics.h.patch`: `#ifdef __OHOS__` 守卫, 替换 glibc 类型名为标准类型
- `0003-configure.py.patch`: 添加 OHOS 平台检测, 跳过 SSE/SSSE3 检测和 make clean
- `0004-dsp-v4f.h.patch`: 替换 `__builtin_sinf/cosf` → `sinf/cosf`, 添加 `<math.h>` include
- `0005-dsp-v4f_IIR2.h.patch`: 替换 `__builtin_sinf/cosf` → `sinf/cosf`, 添加 `<math.h>` include, 定义 exp10f 为 powf(10,x)

## 依赖版本

无外部依赖 (LADSPA 插件库, 仅需标准 C/C++ 库)

## 验证结果

```bash
# caps.so 编译成功, 416192 bytes
# caps.rdf 元数据文件生成
# 质量门禁 G1-G4: PASS
# G2: 无二进制文件 (LADSPA 插件库是 .so 而非可执行程序, 为正常预期)
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| caps-0.9.26-ohos-aarch64.tar.gz | 460KB | 预编译包 (stripped) |
| caps-0.9.26-ohos-aarch64-debug.tar.gz | 51KB | 调试符号包 |

## 注意事项

- caps 是 LADSPA (Linux Audio Developers Simple Plugin API) 音频效果插件库
- 无可执行二进制文件 (仅 caps.so 共享库和 caps.rdf 元数据)
- v4f.h 使用 GCC vector_size 扩展, 在 clang/aarch64 下作为 NEON 向量运行
- `-ffast-math` 和 `-funroll-loops` 为原始 Makefile OPTS, 保留未修改
- make check target 不存在

---
**编译结束**: 2026-05-29 16:10
**最终状态**: built