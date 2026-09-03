# sqlite_orm 1.9.1 适配笔记

## 编译环境
- 构建系统: cmake（header-only INTERFACE target）
- 编译日期: 2026-09-03
- 编译器: clang 15.0.4 / clang++（aarch64-linux-ohos 交叉工具链）
- 状态: published

## 编译步骤

sqlite_orm 是纯 header-only 库（`include/sqlite_orm/sqlite_orm.h`，约 945KB 单头文件），
上游 CMakeLists 定义 `add_library(sqlite_orm INTERFACE)`，无编译产物：

1. `ohc-run.py init-build sqlite_orm 1.9.1` — 引导（源码通过 gitcode 镜像核验 v1.9.1 tag，
   github.com 直连不可用；上游标签 v1.9.1 = `5f1a2ce84a3d72711b4f0a440fdaba977868ae67`）
2. 语言预检 R47：cpp 匹配（cmake 构建系统，204 个 cpp 源）
3. conan-init 生成配方骨架后人工修正为 header-library 类型：
   - `conanfile.py`：`package_type = "header-library"`，`requirements(): sqlite3/3.49.1`，
     `package()` 拷贝 include/，`package_info()` 暴露 `sqlite3::sqlite3` 传递依赖
   - `conandata.yml`：官方 tag tarball URL + SHA-256（ghfast.top 与 gh-proxy.com 双镜像实测一致）
   - `test_package/`：C++ smoke test 实际调用 sqlite_orm API（内存数据库建表/插入/查询，R34）
4. `conan create`（conan-verify G2）验证配方自包含性

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | github.com 直连下载返回 HTML | 网络受限 | 用 gitcode 镜像核验 tag + gh-proxy.com 官方 tarball 镜像 |
| 2 | conan-init 误判 autotools/0 依赖 | 模板按 URL 猜测构建系统 | 人工重写为 CMake header-only 配方并声明 sqlite3 依赖 |

## 源码修改

无补丁（patches/ 为空）。header-only 库本体零修改。

## 依赖版本

- sqlite3/3.49.1（ohpcd 制品仓已发布）

## 验证结果

- Conan L1 smoke test（test_package）：内存数据库 2 行插入 + 查询校验通过
- 上游单测（unit_tests，Catch2）：见门禁报告（ctest -R All_in_one_unit_test）

## 注意事项

- header-only 库 `build()` 为空实现（无可编译产物），补丁仍 apply 保持一致
- 下游使用需链接 sqlite3（`cpp_info.requires` 已传递）
- 版本号按 R37：首次适配使用上游版本 1.9.1，后续修复需递增后缀
---

**编译结束**: 2026-09-03 13:06
**最终状态**: published
