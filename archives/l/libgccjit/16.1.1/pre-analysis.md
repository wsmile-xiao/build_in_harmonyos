# 预分析报告: libgccjit 16.1.1

> 生成日期: 2026-09-15
> 源码目录: /storage/Users/currentUser/runner/libgccjit-wt/archives/l/libgccjit-16.1.1/src

## 1. 构建系统

- ✅ **autotools**
- ✅ **makefile**
- ✅ **python**
- ✅ **rust**

## 2. 图形依赖

- ✅ 未检测到图形依赖

## 3. 音视频依赖

- ⚠️ **ALSA**: 鸿蒙PC音视频API不同。无ALSA/PulseAudio/Pipewire，有OHAudio
  - `gcc/testsuite/gcc.dg/pr33692.c`
  - `gcc/testsuite/gcc.misc-tests/gcov-23.c`
  - `gcc/testsuite/gcc.misc-tests/gcov-31.c`

## 4. 系统集成

- ⚠️ **open_cmd**: 鸿蒙PC可能不支持此功能
  - `configure`
  - `c++tools/configure`
  - `c++tools/configure.ac`
  - `c++tools/resolver.cc`
  - `c++tools/server.cc`

## 5. 平台特定代码

- ⚠️ **linux_only**: 高: 鸿蒙不是Linux，__linux__未定义
  - `gcc/ChangeLog-2002`
  - `gcc/ChangeLog-2006`
  - `gcc/ChangeLog-2009`
  - `gcc/ada/ChangeLog-2014`
  - `gcc/ada/ChangeLog-2015`
- ⚠️ **glibc_only**: 高: 鸿蒙用musl，无__GLIBC__
  - `gcc/configure`
  - `gcc/configure.ac`
  - `gcc/ada/ChangeLog-2008`
  - `gcc/ada/adaint.c`
  - `gcc/ada/adaint.h`
- ⚠️ **posix_ext**: 中: 需确认_POSIX_C_SOURCE在musl下的行为
  - `config/mt-android`
  - `config/mt-gnu`
  - `config/ChangeLog`
  - `fixincludes/config.h.in`
  - `fixincludes/configure`
- ⚠️ **syscall_direct**: 高: 鸿蒙syscall行为可能与Linux不同
  - `gcc/testsuite/ChangeLog-2023`
  - `gcc/config/loongarch/larchintrin.h`
  - `gcc/config/nds32/nds32_intrinsic.h`
  - `gcc/testsuite/gcc.c-torture/execute/20001229-1.c`
  - `gcc/testsuite/gcc.target/i386/strub-pr118006.c`
- ⚠️ **dlopen**: 中: dlopen可用但需注意ELF签名
  - `gcc/plugin.cc`
  - `gcc/cobol/symbols.cc`
  - `gcc/config/rs6000/aix.h`
  - `gcc/testsuite/g++.dg/asan/dlclose-test-1-so.cc`
  - `gcc/testsuite/gcc.target/i386/pr80732.c`

## 6. 关联未关闭需求

- ✅ 需求图谱中无关联未关闭需求

## 7. 适配建议

⚠️ 本软件需要平台适配，不能仅编译通过。重点关注:
- 音视频: 需使用OHAudio或多媒体框架替代
- 系统集成: 需用鸿蒙等价API或降级处理
- 平台代码: 需用#ifdef __OHOS__守卫做兼容

**如遇系统能力缺失，提交需求图谱条目:**
```bash
python3 $SKILL_ROOT/scripts/ohc-run.py req add \
  --title "libgccjit需要XXX能力" \
  --category graphics \
  --severity 2 \
  --software libgccjit \
  --description "详细描述" \
  --needed "需要的API/能力"
```