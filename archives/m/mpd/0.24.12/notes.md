# mpd 0.24.12 编译笔记

## 编译日期
2026-05-25

## 编译环境
- 系统: HarmonyOS (HongMeng Kernel 1.12.0)
- 编译器: clang/clang++
- 构建系统: meson + ninja

## 依赖
- fmt 11.1.1 ✅
- glib2 2.84.0 ✅

## 问题与解决

### 问题1: meson.build 中 is_linux 检测不包含 harmonyos
**原因**: meson.build 使用 `host_machine.system() == 'linux'` 判断 Linux 平台，但 HarmonyOS 返回 'harmonyos'。

**解决**: 将条件改为 `'linux' or host_machine.system() == 'harmonyos'`。

### 问题2: OHOS libcxx 不支持 std::make_unique_for_overwrite
**原因**: HarmonyOS 的 libcxx 实现未包含 C++20 的 `std::make_unique_for_overwrite<T[]>`。

**解决**: 替换为 `std::make_unique<T[]>`（影响 FileCommands.cxx, Queue.cxx, ApeLoader.cxx）。

### 问题3: OHOS libcxx 不实现 <=> for std::chrono::time_point
**原因**: HarmonyOS libcxx 不支持 `operator<=>` for `std::chrono::time_point`。

**解决**: 在 TimerList.hxx 中添加自定义 `CompareTimePoint` 比较器，使用 `<` 运算符实现 `weak_ordering`（E080）。

### 问题4: OHOS libcxx 限制 std::span range 构造函数
**原因**: HarmonyOS libcxx 限制 `std::span` 的 range 构造函数。

**解决**: 在 SpanCast.hxx 中放宽 clang 版本检测条件，添加 `defined(__OHOS__)` 以启用 workaround。

### 问题5: src/system/meson.build 中 Linux 检测不包含 harmonyos
**原因**: 同问题1，system 模块的 meson.build 也需要支持 harmonyos。

**解决**: 将 `host_machine.system() == 'linux'` 改为包含 harmonyos 条件。

## 编译步骤

```bash
# init
python3 $SKILL_ROOT/scripts/ohc-run.py init-build mpd 0.24.12

# meson setup
meson setup builddir --prefix=$DEFAULT_PREFIX \
  -Dcurl=disabled -Dsndio=disabled -Dpipe=disabled

# build
ninja -C builddir

# install (DESTDIR staging)
ninja -C builddir install DESTDIR=$TEST_PREFIX

# package
python3 $SKILL_ROOT/scripts/ohc-run.py package mpd 0.24.12
python3 $SKILL_ROOT/scripts/ohc-run.py package mpd 0.24.12 --debug
```

## 补丁文件
- 0001-meson.build.patch: 添加 harmonyos 平台检测
- 0002-src-command-FileCommands.cxx.patch: make_unique_for_overwrite → make_unique
- 0003-src-event-TimerList.hxx.patch: 自定义 time_point 比较器
- 0004-src-queue-Queue.cxx.patch: make_unique_for_overwrite → make_unique
- 0005-src-system-meson.build.patch: 添加 harmonyos 平台检测
- 0006-src-tag-ApeLoader.cxx.patch: make_unique_for_overwrite → make_unique
- 0007-src-util-SpanCast.hxx.patch: 放宽 span 构造条件

## 验证结果
- ✅ mpd --version 正常输出
- ⚠️ 部分功能受限（无 curl/sndio/pipe 支持）

**编译结束**: 2026-05-25
**最终状态**: built