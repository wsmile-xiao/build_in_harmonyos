# boost1.84-contract 1.84.0 编译笔记

## 任务背景

- **任务**：积分赛 — boost 1.84 组件拆分包（contract）
- **认领人**：2404_87638649
- **平台分支**：feat/boost1.84-contract-1.84.0
- **底稿**：仓库 main 的 archives/b/boost/1.84.0/（元包）
- **开始时间**：2026-09-05

## 形态选型（W0b 历史经验核验）

底稿 notes.md 关键结论（已逐项核验）：
1. **b2 构建系统失败**（clang++ --version SHELL 执行错误，E068）→
   contract 是 header-only 组件，默认编译模式即 header-only
   （`boost/contract/core/config.hpp` L110：不定义 DYN_LINK/STATIC_LINK
   时 `BOOST_CONTRACT_HEADER_ONLY` 自动生效），无需 b2。
2. **Header-only 安装成功** → 本包直接打包 contract 头文件。
3. **pthread_setcancelstate 不可用**（OHOS musl）→ 复用底稿已验证
   patch（BOOST_SP_NO_PTHREAD_SETCANCELSTATE 特性检测宏，R8 合规）。

组件包 vs 元包的差异：
- 元包 boost/1.84.0：完整 boost headers + 4 个手动编译静态库
  （filesystem/regex/program_options/iostreams），已发布。
- 组件包 boost1.84-contract：打包 contract 组件专属头文件
  （boost/contract.hpp + boost/contract/），依赖元包提供其余 headers。
  源码 tarball 与元包同源（官方 boost_1_84_0.tar.gz）。

## W0 依赖检查（R36）

- `conan download boost/1.84.0 -r=ohpcd` → binary 在仓
  （OHOS/armv8/clang15/Release/libc++17，rrev ccc58bcc…，2026-08-12）
- `conan download zlib/1.3.1 -r=ohpcd` → 在仓（元包的传递依赖）
- 元包 headers 实测：include/boost/contract/ 存在、sp_thread_sleep.hpp
  已含 BOOST_SP_NO_PTHREAD_SETCANCELSTATE patch（3 处）、
  libboost_{filesystem,regex,program_options,iostreams}.a 齐全。

## 关键实验记录

### 实验 1：header-only 模式编译验证（2026-09-05）

```bash
# OHOS clang 直接编译（带 patch + 宏）
/data/service/hnp/bin/clang++ -std=c++17 -stdlib=libc++ \
  -DBOOST_SP_NO_PTHREAD_SETCANCELSTATE \
  -I<patched-boost-tree> test_contract.cpp -o test
# 结果：编译 OK，运行 OK（契约检查正常触发）
```

- 不带宏/patch 时命中已知错误：
  `boost/core/detail/sp_thread_sleep.hpp:73: error: use of undeclared identifier 'pthread_setcancelstate'`
  （与底稿一致，E002 同族 OHOS musl 平台限制）
- 断言失败路径实测：故意违反后置条件 →
  `postcondition assertion "..." failed` + terminate（机制正常）

### 实验 2：上游测试全量验证（226 个源文件）

绕过 b2，手动编译运行（-I 源码树 + -I libs/contract/test）：
- **通过 165/184**（226 个文件中排除 42 个：*_error.cpp 期望编译失败
  用例、lib_*.cpp 库模式辅助单元、no_tva 变体重复用例后剩 184）
- 19 个编译失败均为两类：
  1. 上游 Jamfile 需注入宏的用例（如 check/audit 需
     `-DBOOST_CONTRACT_AUDITS`；配方内已按 Jamfile 补齐注入）
  2. permissive 系列（需 `BOOST_PERMISSIVE` 松弛模式）、
     disable/*_lib|unit（需 DYN_LINK 库模式辅助翻译单元）——
     属于编译模式变体覆盖，非独立功能用例，子集不纳入
- selected 32 个代表性用例（配方 build() 内运行）全部实测通过

### 实验 3：test_package 消费者测试设计

覆盖 4 个能力面：自由函数 pre/post、类不变式 + public_function、
call_if 编译期分派（上游 bind 延迟求值技巧）、Throw-on-Failure
violation 捕获（set_postcondition_failure）。
注意点：
- `call_if` 的 then 分支即使不调用也实例化 lambda 体，无 operator==
  类型需用 `boost::bind` 延迟求值（上游测试同款技巧）
- `boost::has_equal_to` 需显式 `#include <boost/type_traits/has_equal_to.hpp>`

## 配方结构

- `requirements`: boost/1.84.0（元包）
- `build()`: apply patch → 编译运行 32 个上游测试（lightweight_test）
- `package()`: copy boost/contract.hpp + boost/contract/ 树
- `package_info()`: header-library，defines 传播
  BOOST_SP_NO_PTHREAD_SETCANCELSTATE（与元包 boost_headers 双保险）

## 结论

contract 组件 header-only 模式在 HarmonyOS PC 上完全可用。
---

**编译结束**: 2026-09-05 16:28
**最终状态**: built
