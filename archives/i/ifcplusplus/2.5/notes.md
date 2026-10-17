# ifcplusplus 2.5 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-09-18
- 编译器: clang/clang++ (LLVM 15.0.4, OHOS SDK 26.0.0.18, target aarch64-linux-ohos)
- 状态: built

## 编译步骤
1. `python3 scripts/ohc-run.py init-build ifcplusplus 2.5 --url=https://github.com/ifcquery/ifcplusplus/archive/refs/tags/2.5.tar.gz`
   - 官方 tag 2.5，tarball SHA-256 = 38f19ad500a8aed8ea91bed7db848a026822bdf3c22b159d9844e885d5553802（下载源核验一致）
2. `python3 scripts/ohc-run.py conan-init ifcplusplus 2.5` 生成配方骨架（autotools 模板），随后人工改写为 CMake 配方
3. `python3 scripts/ohc-run.py conan-verify ifcplusplus 2.5`
   - 内部执行 `conan create archives/i/ifcplusplus/2.5 -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=... --build=missing --user=ohpcd --channel=stable`
   - G1/G0/G2/G3/G4 全部 PASS，test_package 1/1 通过

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | BuildingGuid.cpp 编译失败：`constant expression evaluates to -1 which cannot be narrowed to type 'char'` | OHOS/ARM 平台 char 默认为无符号，`base16mask[]`/`base64mask[]` 用 -1 初始化 char 数组触发 -Wc++11-narrowing | 补丁 0001：两个 mask 数组类型改为 `signed char`（功能语义不变：-1 作为非法字符哨兵） |
| 2 | conan-init 生成的配方是 autotools 模板 | 模板按默认构建系统生成，本项目实际是 CMake | 重写 conanfile.py 为 CMake 配方（CMakeToolchain + CMake），注入 CMAKE_SYSTEM_NAME=Linux / CMAKE_SYSTEM_PROCESSOR=armv8（E092 OHOS 识别）、CMAKE_POLICY_VERSION_MINIMUM=3.5（CMake 4 兼容）、BUILD_CONSOLE_APPLICATION=OFF / BUILD_VIEWER_APPLICATION=OFF（纯库交付） |
| 3 | 上游 install 将静态库安装到 bin/ | 上游 CMakeLists ARCHIVE DESTINATION bin | 配方 package() 中把 .a 从 bin/ 规整到 lib/（Conan 惯例） |
| 4 | 消费者测试缺 IfcProject 完整类型 / 无 className() 成员 | BuildingModel.h 仅前置声明 IfcProject；entity 类无 className() | test.cpp 增加 `#include <ifcpp/IFC4X3/include/IfcProject.h>`，改用 `classID()` 输出 |

## 源码修改
- patches/0001-IfcPlusPlus-src-ifcpp-model-BuildingGuid.cpp.patch
  - `static const char base16mask[]` → `static const signed char base16mask[]`
  - `static const char base64mask[]` → `static const signed char base64mask[]`
  - 类型 portability 修复，无平台宏、无行为变更

## 依赖版本
- 无外部 Conan 依赖（requirements 为空）。Carve、RapidJSON、earcut、glm、nowide、utf8、zip-master、zippy 全部为上游内置三方源。

## 验证结果
```bash
# conan-verify（含 conan create + test_package）：
# G1 配方完整性 PASS / G0 风险评估 PASS / G2 conan create PASS / G3 同名库隔离 PASS / G4 产物完整性 PASS
# test_package: 1/1 Test #1: test_ifcplusplus Passed (0.23 sec)
# 产物: lib/libIfcPlusPlus.a + include/ifcpp/**（消费者可 #include <ifcpp/model/BuildingModel.h> 等）
```

## 交付物
| 文件 | 说明 |
|------|------|
| conanfile.py | CMake 配方（静态库、无依赖、纯库交付） |
| conandata.yml | 官方 GitHub URL + SHA-256 + 补丁声明 |
| patches/0001-*.patch | BuildingGuid mask 类型 portability 修复 |
| test_package/ | 消费者测试（IFC4 STEP 解析 + 回写） |

## 注意事项
- 上游 tag `2.5` 为 2024-08-09 提交（3fa8947bd0），无 release 资产，源码包取自官方 tags 归档。
- 上游无任何测试框架、无 ctest 注册、无测试脚本；枚举台账见 reports/upstream-test-ledger.md，双口径统计为 0/0（无独立上游用例）。
---

**编译结束**: 2026-09-18 05:28
**最终状态**: built
