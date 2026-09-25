# libyajl 2.1.0 适配笔记

## 软件信息
- **名称**: libyajl（任务卡 #13878 名称；生态名与仓内既有 `yajl` 归档/制品区分，制品仓 `libyajl` 净空）
- **上游**: lloyd/yajl tag 2.1.0（Yet Another JSON Library，纯 C）
- **License**: ISC
- **依赖**: 无（纯 C 库，仅 libc）——W0 已核

## 编译环境
- 构建系统: CMake（上游原生 CMakeLists.txt，上游解包根目录 yajl-2.1.0，conan get strip_root）
- 编译日期: 2026-09-23
- 编译器: clang（ohos-aarch64 profile）
- 状态: built

## 构建配置
- `CMAKE_POLICY_VERSION_MINIMUM=3.5`（cache 变量）：上游 cmake_minimum_required(2.6) 被 CMake 4.x 拒绝
- `CMAKE_SHARED_LIBRARY_SONAME_C_FLAG=-Wl,-soname,`（cache 变量）：CMake 4.1.2 无 Platform/HarmonyOS.cmake，默认无 SONAME 标志，.so 会缺 SONAME 字段（上游 SOVERSION 2 → libyajl.so.2）
- yajl 非系统同名库（R26 不适用）：默认动态，Conan 管理依赖链
- 上游 CMake 无条件同时构建 libyajl.so 与 libyajl_s.a，`shared` 选项决定 package_info 导出哪个

## 遇到的问题与解决方案
| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | GET_TARGET_PROPERTY(LOCATION) 报错 | CMake 4.x 移除 LOCATION 属性读取 | patch 0001/0002：生成器表达式 $<TARGET_FILE:target> 替代（reformatter + verify 两处） |
| 2 | CMake 4.x 拒绝 cmake_minimum_required(2.6) | 最低版本策略下限提高 | CMAKE_POLICY_VERSION_MINIMUM=3.5 cache 变量 |
| 3 | libyajl.so 无 SONAME 字段 | CMake 4.1.2 无 Platform/HarmonyOS.cmake，SONAME_C_FLAG 未设置 | generate() 显式设置 -Wl,-soname, |

## 上游测试
上游 test/ 目录自带回归测试：
- test/parsing：58 个 .json 用例（ac_/ag_/am_/ap_ 前缀控制 -c/-g/-m/-p 标志）+ .gold 期望输出，由 yajl_test 二进制驱动（上游 run_tests.sh）
- test/api：1 个 gen-extra-close 可执行（上游 run_tests.sh 遍历执行）

test_package 接入：yajl_test 与 58 个用例数据随包分发，L1 test() 阶段按上游 run_tests.sh 语义逐例执行并 diff .gold，实测 58/58 通过（另含 API 消费者测试 1 项）。

## test_package
1. 自定义 API 消费者测试：yajl_tree_parse 内联 JSON → yajl_tree_get 断言字符串/整数/嵌套值
2. 上游回归：yajl_test × 58 cases（flags 按文件名前缀），输出与 .gold 比对，断言全过

## 验证结果
- L0: pass（conan create 成功）
- L1: pass（ctest + 上游 58 用例全过）
- L2: 主机无法直接运行 aarch64 OHOS ELF 的 json_verify/json_reformat（CLI 无 --version 参数）；验证通过 SONAME/readelf 结构检查 + L1 逻辑覆盖

## 交付物
| 文件 | 说明 |
|------|------|
| `libyajl.so` / `libyajl_s.a` | 动态/静态库（SOVERSION 2） |
| `yajl/yajl_tree.h` 等头文件 | 公开 API |
| `json_verify` / `json_reformat` | 上游 CLI 工具 |
| `yajl_test` + `test/cases/*.json(+.gold)` | 上游回归测试资产（随包分发供 L1 复跑） |
