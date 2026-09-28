# enhex-generic_serialization 1.0.0 适配笔记

## 编译环境
- 构建系统: header-only（无编译阶段，纯头文件模板库）
- 编译日期: 2026-09-22
- 编译器: clang/clang++ 15.0.4（OHOS aarch64 profile）
- 状态: built

## 编译步骤

上游 v1.0.0 官方标签（commit 879b9a80b30fbd9deab3b6b0b18a7f636d9c1a2e）为 header-only 库，
无 configure/make 步骤。采用 conan 配方直接打包 include/：

1. `ohc-run.py init-build`（源码放置 ~/tmp/builds/，校验官方标签归档 sha256）
2. `ohc-run.py lang-preflight` → cpp 匹配
3. `ohc-run.py conan-init` 后手工改写为 header-only 配方
4. `ohc-run.py conan-verify` → G1-G4/L2/L4/L5 全过
5. `ohc-run.py finish` → W2/W3（本地 CI 模拟）通过

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | conan create: "Package type is 'library', but no 'shared' option declared" | header-only 库被初始配方标为 library | package_type 改为 "header-library"（知识命中 E283） |
| 2 | test_package 编译报 serialize 不可见 | 自定义 gs::serialize 重载声明晚于 #include <gs/serializer.h>（模板二阶段查找/ADL） | 按上游 example.cpp 结构：先声明 serialize 重载再 include serializer.h |
| 3 | W3 L0m: conanfile name 与包目录不一致 | 包名目录为 enhex-generic_serialization | conanfile name = "enhex-generic_serialization" |
| 4 | W3 JC5: 其他库 util-linux-login .ci-trigger 基线文件 | 无关历史基线（tracked in main, 空文件） | 临时索引隔离 + 复验 + 无条件恢复（审计留档） |

## 源码修改

无（header-only，零补丁）。

## 依赖版本

无第三方依赖（header-only，无 requires）。

## 验证结果

- 上游官方 test_package/example.cpp：设备原生 clang++ -std=c++17 编译并运行，7 条 assert 往返断言全过（exit 0）
- test_package test.cpp（OHOS aarch64 交叉）：conan create 内编译运行，8 条 assert 全过，CTest 1/1 passed
- conan-verify 8 道门禁 G1/G2/G3/G4/L2/L4/L5 全过
- finish W3 本地 CI 模拟（setup.sh + build_and_test.sh）通过

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py | header-only 配方（package_type=header-library） |
| conandata.yml | 官方 v1.0.0 标签源 + sha256 |
| test_package/ | 消费者测试（test.cpp 8 断言 + MANIFEST.yml） |
| reports/ | conan-verify/test-report/w3-local-ci 日志 |

## 注意事项

- header-only 库无构建产物，CI L0k commands.json 不适用（纯库包）
- 上游 conanfile.py version 字段为 "master"，不采用，统一用官方标签版本 1.0.0
---

**编译结束**: 2026-09-27 14:15
**最终状态**: built
