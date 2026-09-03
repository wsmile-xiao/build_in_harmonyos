# E548 — 依赖版本低于上游最低要求时的选择性 API 回移：版本探测、静态内联兼容层与依赖元数据同步

## 问题概述

上游项目声明了最低依赖版本并使用该版本新增的公开 API，而本仓库制品仓只提供更旧的依赖版本。被依赖库的公共头文件不导出版本宏，编译期无法 feature-test，于是在旧版依赖下出现隐式函数声明、类型/枚举缺失和链接期 undefined reference。

解决思路不是整体升级依赖，也不是降低版本约束硬编，而是**选择性 API 回移**：只把实际缺失的少数 API 从依赖库可信上游源码逐字提取为 static inline 兼容头，用构建期版本探测门控，仅旧版本启用，同时同步构建系统、pkg-config 与 Conan 三处依赖元数据。该方案跨库通用，适用于任何"C 库版本落后 + 缺版本宏"的组合。

## 典型错误

```
src/tss.c:312:9: warning: implicit declaration of function 'plist_dict_get_uint' [-Wimplicit-function-declaration]
src/tss.c:345:15: error: use of undeclared identifier 'PLIST_OPT_NONE'
aarch64-unknown-linux-gnu-ld: undefined reference to `plist_dict_get_bool'
configure: checking for libplist >= 2.6.0... no
```

触发条件：
- 构建系统: autotools（也适用于 cmake/meson + pkg-config）
- 阶段: configure（版本检查失败）、编译（隐式声明/标识符缺失）、链接（符号未定义）

## 根因

1. 上游按其声明的最低依赖版本写代码（libtatsu 1.0.5 要求 libplist >= 2.6.0，tss.c 使用 2.6.0 新增的 `plist_dict_get_bool/get_uint`、`plist_dict_copy_item/_bool/_uint/_string/_data` 共 7 个函数，另加 `PLIST_OPT_NONE` 枚举值）。
2. 制品仓锁定的依赖版本更旧（本仓库仅有 libplist/2.3.0），configure 的版本门禁直接失败；即使放行，旧版头文件没有这些声明。
3. 依赖库公共头不导出版本宏（libplist 无 `LIBPLIST_VERSION` 类宏），无法用 `#if VER >= X` 做编译期 feature-test，只能由构建系统在配置期探测。
4. 旧版依赖其实已具备全部底层原语（2.3.0 有 `plist_get_bool_val/uint_val/string_ptr/data_ptr`、`plist_new_bool/uint/data/string`、`PLIST_IS_STRING/PLIST_IS_DATA`、`plist_err_t`），缺的只是便捷包装层——这正是可回移的判定依据。

## 适用范围

- 上游代码使用依赖库新版才有的**公开**辅助 API，且这些 API 在旧版上有等价原语可组合实现。
- 依赖库无编译期版本宏，版本只能在配置期判定。
- 回移函数体量小、语义独立、无内部数据结构依赖。
- 上游实现许可证与被适配项目兼容（libplist 与 libtatsu 同属 libimobiledevice 项目，同为 LGPL-2.1+）。
- 需要长期同时支持新旧两版依赖（新版本环境必须走原生实现）。

## 不适用范围

- 缺失 API 依赖旧版不存在的私有结构体布局或内部状态（无法核验等价性）。
- 回移面覆盖大半个依赖库（应直接升级依赖版本）。
- 依赖库有意移除/废弃的 API（回移会复活已删除语义）。
- 语义含时间、随机、加密等环境敏感行为，无法用确定性测试验证等价。
- 许可证不兼容（如 GPL 实现回移进非 GPL 项目）。

## 检测流程

1. **版本差比对**：制品仓可用版本 vs 上游 configure.ac/cmake 声明的最低版本。
2. **缺失 API 定位**：编译一次拿到完整错误清单；对每个符号在旧版依赖头文件 grep，确认"缺失"；在依赖库 changelog/tag/NEWS 确认首次出现版本。
3. **原语完备性核验**：逐个确认每个缺失 API 的函数签名、返回语义、所涉数据结构在旧版上可等价构造。
4. **许可证核验**：确认上游实现的许可证与本项目兼容，记录来源（文件、版本、commit/tag）。

## 修复流程（通用算法）

1. 比较上游最低依赖版本与制品仓可用版本，确认存在版本缺口。
2. 精确确定缺失 API 清单及每个 API 在依赖库中的首次出现版本。
3. 从依赖库**可信上游源码**（官方 release tarball / tag）提取公开实现，逐字复制，不做改写。
4. 核验函数签名、语义、数据结构布局与许可证；任一无法证明即停止。
5. 只回移实际缺失的 API，不多带一个函数。
6. 构建期版本探测门控：configure 用 `pkg-config --atleast-version=X dep` 判定，旧版本时向 CPPFLAGS 追加 `-DDEP_LT_X=1`；无 pkg-config 的构建系统用等价的编译/运行测试。
7. 兼容层放入独立头文件，全部函数标记 `static inline`，随消费 TU 编译，不进入导出 ABI，不与库符号冲突。
8. 新版依赖环境：门控宏不定义，兼容头完全不参与编译，行为与上游一致。
9. 同步三处依赖元数据，保证"真实要求 = 元数据声明"：
   - configure 最低版本字面量降为实际可用的旧版本；
   - `*.pc.in` 的 `Requires:` 同步降版本；
   - Conan 配方 `self.requires()` 指向制品仓实际版本。
10. 验证（见下节）全部通过后才算完成；任何一项证明不了等价即回退到升级依赖方案。

## 验证流程

- **新旧路径等价测试**：在旧版依赖上跑完整功能测试，覆盖每个回移 API 的真实调用路径（不能只验证编译链接成功）。
- **序列化/往返测试**：涉及数据编码的 API（如 uint 的 LE 字节序组装）验证字节级往返一致。
- **异常输入测试**：NULL、缺 key、类型不匹配、0/1/2/4/8 字节边界长度，验证错误码与默认值路径。
- **内存释放测试**：所有新建对象在测试尾部逐一释放，无泄漏才算通过。
- **门控验证**：确认新版依赖下兼容头不参与编译（预处理器输出比对），原生符号被引用。
- **元数据一致性**：`pkg-config --modversion` 与 `Requires:`、Conan requires 三者互检。

## 安全边界

- 兼容层只编译进静态消费 TU，不生成导出符号，不污染被适配库的 ABI。
- 许可证：逐字回移的上游代码保留原始版权与许可证声明（LGPL-2.1+，与被适配库同族同许可证），在兼容头中显式记录来源与依据。
- 版本门控必须覆盖"旧版启用、新版禁用"两个方向，单向门控视为不完整。
- 回移范围以"缺失 API 清单"为白名单，任何额外函数进入兼容层都应拒绝。

## 禁止方案

- ❌ **只降低版本约束**：把 configure/pkg-config/Conan 的版本号降下来但不补齐 API —— 元数据与源码事实不一致，必然编译或链接失败。
- ❌ **依赖隐式函数声明**：`-Wno-implicit-function-declaration` 掩盖缺失声明，C99 起即未定义行为。
- ❌ **关闭编译或链接错误**：删 `-Werror`、加 `-Wl,--unresolved-symbols=ignore` 等只是把错误推迟到运行期。
- ❌ **猜测私有 API 行为**：凭"大概是这么实现的"自行编写等价物，行为漂移无法审计。
- ❌ **复制整个依赖源码**：体积、许可证、维护成本全部失控，升级即冲突。
- ❌ **无版本门控地覆盖新版原生 API**：`#define` 顶层劫持原生函数名，新版环境下符号冲突或语义被替换。
- ❌ **只验证编译成功**：无功能等价测试即视为未验证。
- ❌ **真实依赖要求与元数据不一致**：源码实际需要 2.6.0 语义而元数据声明 2.3.0 且无兼容层，消费者被误导。

## libtatsu 真实案例

libtatsu 1.0.5（TSS 签名服务客户端库）适配：

- **版本缺口**：上游 configure.ac 要求 libplist >= 2.6.0，制品仓仅 libplist/2.3.0。
- **实际回移 API（7 个 + 1 枚举）**：`plist_dict_get_bool`、`plist_dict_get_uint`、`plist_dict_copy_item`、`plist_dict_copy_bool`、`plist_dict_copy_uint`、`plist_dict_copy_string`、`plist_dict_copy_data`，另补 `PLIST_OPT_NONE`（2.6.0 新增，值恒为 0）。
- **实际调用点规模**：tss.c 中共 192 处调用。
- **static inline 兼容层**：`src/plist_dict_compat.h`，7 个函数按 libplist 2.6.0 `src/plist.c` 上游实现逐字回移，全部 `static inline`，带 `#ifndef PLIST_DICT_COMPAT_H` include guard 与 `#ifndef PLIST_OPT_NONE` 宏守卫。
- **版本门控**：configure（预生成脚本，不动 configure.ac 以免触发损坏的 autoreconf maintainer rebuild）在 libplist 检测成功后追加纯 shell 探测：`$PKG_CONFIG --atleast-version=2.6.0 libplist-2.0`，失败则 `CPPFLAGS="$CPPFLAGS -DLIBPLIST_LT_2_6=1"`；tss.c 中 `#ifdef LIBPLIST_LT_2_6` 才包含兼容头，否则仅补定义 `PLIST_OPT_NONE` 为 0。
- **元数据同步**：configure 的 `LIBPLIST_VERSION=2.6.0` 字面量改为 `2.3.0`；`src/libtatsu-1.0.pc.in` 的 `Requires: libplist-2.0 >= @LIBPLIST_VERSION@` 改为 `>= 2.3.0`；Conan 配方 `self.requires("libplist/2.3.0")`。
- **C 消费者测试（test_package.c，62 项断言）**：本地 mock HTTP 服务器（127.0.0.1）验证离线请求/响应契约——请求构建/overrides/manifest 参数、tag 构建器（含必填字段缺失）、精确序列化 XML 请求体、线上头（POST/Content-Type/User-Agent/Cache-Control）、SUCCESS 响应解析、ticket/path/blob 访问器、负路径（HTTP 503 + STATUS=100、连接拒绝、畸形响应体、空响应体）、内存清理。即：等价序列化、异常输入、内存释放三类测试均由真实调用路径覆盖。
- **C++ 消费者测试（test_cpp.cpp，6 项断言）**：extern "C" 头文件包含、链接与 API 调用（版本、请求构建、tag 构建、debug 级别）。
- **许可证依据**：libplist 与 libtatsu 同属 libimobiledevice 项目，同为 LGPL-2.1+；兼容头保留原版权声明并注明来源。
- **结果**：62 + 6 = 68 项断言全部 PASS，0 FAIL；`pkg-config --modversion libtatsu-1.0` 输出 1.0.5；libplist >= 2.6.0 环境下 LIBPLIST_LT_2_6 不定义，行为与上游完全一致。

## 与相似条目的区别

- **E531（OHOS musl 缺 glibc 风格 qsort_r，本地 shim 委托 qsort）**：相似点——都是"目标环境缺符号 + 用本地兼容层补齐 + 条件编译门控 + 不修改调用方"。实质差异——E531 缺的是 **libc 层**符号（musl vs glibc 签名差异），shim 需要**自行实现**并靠静态全局变量保存上下文（有单线程限制，多线程需 fallback）；E548 缺的是**依赖库版本**符号（2.3.0 vs 2.6.0），实现**逐字取自依赖库上游源码**（无自创逻辑、无线程限制），且多了元数据同步（configure/pc/Conan）与"上游最低版本 vs 制品仓版本"的版本探测维度。E531 的门控是 `#ifndef __GLIBC__`（编译器预定义宏），E548 的门控是构建期 pkg-config 探测注入的宏（因依赖库无版本宏）。
- **E235（OpenSSL OHOS 熵源选择）**：相似点——都涉及依赖配置期选择 + 验证需真实消费者调用。实质差异——E235 是**配置开关选择**（`--with-rand-seed=getrandom`），不引入任何回移代码；E548 是**源码级回移**。E235 处于安全关键路径（熵源错误即密码学事故），E548 是常规 API 等价性。E235 的 forbid 针对 shim 猜测 SDK 私有语义，E548 的 forbid 针对元数据不一致与无门控覆盖。

## 跨库复用方式

把"libtatsu + libplist"替换为任意"项目 P + 依赖 D"：

1. `pkg-config --modversion D` vs P 的 configure.ac/cmake 最低声明 → 确认缺口。
2. 编译收集缺失符号清单 → 在旧版 D 头文件确认缺失、在 D 的 tag/changelog 确认首次出现版本。
3. 核对 D 旧版原语能否等价构造每个缺失 API 的语义 + 许可证兼容。
4. 从 D 官方源码逐字提取实现 → `dep_compat.h`（全 static inline）→ 放入 P 的源码树。
5. 构建系统版本探测 → 注入 `D_LT_X` 宏 → `#ifdef` 门控包含。
6. configure 最低版本、`*.pc.in` Requires、Conan requires 三处同步为实际可用版本。
7. 用等价测试（真实调用路径、序列化往返、异常输入、内存释放）验证旧版路径；用预处理器比对验证新版路径不走兼容层。
8. 任一环节证明不了 → 升级依赖版本，不回移（fail closed）。

## 关联条目
- 相似: E531（libc 符号 shim，自行实现）、E235（依赖配置选择，无回移）
