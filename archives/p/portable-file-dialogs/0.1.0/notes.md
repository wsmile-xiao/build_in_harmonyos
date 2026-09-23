# portable-file-dialogs 0.1.0 适配笔记

## 编译环境
- 构建系统: none（header-only，v12.21 模板变体 A；上游 CMakeLists 仅定义 INTERFACE 目标，无需构建）
- 编译日期: 2026-09-13
- 编译器: clang++（消费者测试编译用）
- 状态: built

## 上游测试清点（R51 第一步）

- tarball 仅含头文件 `portable-file-dialogs.h`、CMakeLists（INTERFACE 库）、examples/、doc/，无任何测试套件
- **上游静态测试数 N_static = 0**（如实申报）

## 消费者测试（test_package，N_consumer = 1）

`test.sh`：以消费者身份用 `clang++ -std=c++11 -I<pkg>/include` 编译 test.cpp 并运行（R34：真实 include 并调用接口）：

1. `pfd::settings::verbose(false)` + `pfd::settings::rescan()`（公开静态 API，rescan 仅做 PATH 扫描、无对话框派生）
2. `pfd::choice` 枚举真实使用；`pfd::message` 完整类型 static_assert

注：0.1.0 尚无 `settings::available()`（后续版本 API）；无头环境下真实派生对话框是环境相关行为，不在断言范围。

## 四维测试账本

| 维度 | 数值 | 来源 |
|---|---|---|
| 上游静态声明 N_static | 0 | tarball 清点 |
| 构建系统注册 N_registered | 0 | 无测试目标 |
| 实际执行 N_executed | 0 | 无上游套件 |
| 未执行分类 | 0 | — |
| 消费者测试 N_consumer | 1（编译+运行） | test_package/test.sh + test.cpp |

## 源码修改

无补丁（patches: {}）。

## 依赖版本

无（纯 C++11 标准库头文件）。

## 路径 B 判断

- header-only 直打包，无构建期问题触发，无新错误签名。
- 结论：**纯路径 A，不申报路径 B**。

## 验证结果

- conan-verify（2026-09-13 11:37，rc=0）：G0/G1/G2（conan create 干净构建）/G3/G4/L2/L4/L5 全部通过
- 消费者测试 test_package/test.sh 真机执行输出（见 reports/conan-create.log）：
  - `[test] consumer compile`：clang++ -std=c++11 -I<pkg>/include 编译通过 → `OK: header compiles standalone`
  - `[test] run consumer program`：`pfd api ok` / `OK: API calls executed`
  - `ALL CONSUMER TESTS PASSED`
- 配方要点：package() 用显式拷贝（conan `copy()` 通配在 HMDFS 上曾静默匹配 0 文件）；`package_type="header-library"`；G1 要求 build()/export_sources() 存在（header-only 亦然），build() 仅做补丁应用（无补丁即 no-op）
---

**编译结束**: 2026-09-13 11:42
**最终状态**: built
