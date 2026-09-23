# E552（草稿）：C 库安装公共头不自包含 — 缺依赖类型头导致消费者编译 unknown type name

> 来源：c-vtapi 0.0-git20230329.226eda8 HarmonyOS PC 适配（archives/c/c-vtapi/0.0-git20230329.226eda8，PR【知识库扩展】）
> 状态：draft（待主编 promote 为正式 E552）

## 问题

库能正常 `conan create` 构建，但消费者（test_package）以**安装后的公共头**独立编译时报：

```
VtObject.h:67: error: unknown type name 'pthread_mutex_t'   （VT_OBJECT_COMMON 宏内使用）
VtResponse.h:127: error: unknown type name 'json_t'          （VtResponse_getJanssonObj 返回 json_t*）
```

## 根因

库安装的公共头直接使用外部依赖类型（pthread_mutex_t / json_t），却未 include 声明这些类型的头：

- `vtcapi_common.h` 中 `#include <pthread.h>` 被上游**主动注释掉**（遗留 bug）；
- `VtResponse.h` 从未 include `<jansson.h>`。

库自身编译因翻译单元 include 顺序巧合（`VtObject.c` 先 include `<pthread.h>`）而侥幸通过，隐蔽性极强；
消费者以安装头为唯一事实源编译必然失败——只有 test_package 这类"独立消费者编译"才能暴露。

## 方案

**库侧补丁补 include，使安装公共头自包含**（modified-file diff，符合 R 规则）：

- `0002-lib-vtcapi_common.h.patch`：恢复 `#if !defined(WINDOWS) #include <pthread.h> #endif`
- `0001-lib-VtResponse.h.patch`：增加 `#include <jansson.h>`

一处修复，所有消费者（含 test_package）受益；配套消费者测试（`test_ohos.c`）覆盖 JSON 解析、字段提取、
refcount 生命周期、setApiKey 内存路径（15 项检查，离线真实 API 调用）。

## 验证

- `conan create`（-pr:h/-pr:b=ohos-aarch64）EXIT 0；test_package 消费者编译通过；
- ctest 2/2 通过（test_c-vtapi + test_ohos）。

## 适用边界

- 任何 C/C++ 库的安装公共头直接使用第三方类型却缺 include（典型：pthread_mutex_t、json_t、FILE*、DIR*、cchar_t）；
- 与平台无关（OHOS/Linux 均可能），表现为"库能构建、消费者编译炸"；
- 库侧自包含修复优先于消费者侧绕过（换消费者仍会炸）。

## 反例 / 不做

- 仅改消费者测试 / 仅加 `-I` 绕过：漏修库公共头，换消费者必复现；
- new-file 补丁补头：toybox patch 在 OHOS 会把 new-file patch 实际应用，污染 orig 目录（E 系列既有规则）。

## 查重差异

- similar_to：E420（Legacy C TU 需 include 拥有 API 声明的头——消费者侧修复，本条目为库侧修复）、
  E342（X11 库头不自包含——consumer include 顺序 + 宏/函数区分，本条目为补 include 使自包含且覆盖 pthread/json 类）；
- 新增差异：库侧自包含修复 + 独立消费者编译暴露 + 不限于 X11 的通用类型头缺失；
- caused_by：上游公共头缺陷（pthread include 被注释 / 从未包含 jansson.h）；
- prerequisite_of：（无）；conflicts_with：（无）。
