# handmade-math 2.0.0 适配笔记

## 编译环境
- 构建系统: header-only（无构建系统，上游仅 test/ 内含 Makefile）
- 编译日期: 2026-09-07
- 编译器: clang 15.0.4 / clang++ 15.0.4
- 目标平台: aarch64 (OHOS PC)
- 状态: built

## 编译步骤

handmade-math 为单头文件（HandmadeMath.h）header-only 数学库，无 configure/cmake 构建：
1. 上游测试编译入口为 `test/Makefile`，四个变体：`make c`、`make c_no_sse`、`make cpp`、`make cpp_no_sse`
2. Conan 配方类型为 header-library：`package()` 仅拷贝 `HandmadeMath.h` 到 include、LICENSE 到 licenses，无编译步骤（不伪造编译日志，R34）
3. test_package 消费者测试 test.c 实际 include 并调用 HMM_V4/HMM_NormV4/HMM_LenV4/HMM_DotV4/HMM_M4D/HMM_MulM4 验证 API（R34）

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | init-build 下载失败 | 本机无法直连 github.com（443 超时） | 通过 gitcode 官方镜像 clone v2.0.0 标签（HEAD 422bc588 与官方一致），用 git archive 生成 tar.gz 放入 $TMPDIR/builds 供 init-build 使用 |
| 2 | init-build `_promote_nested_source` 误删根目录文件 | header-only 库根目录无构建标记文件，test/ 含 Makefile 被误判为嵌套源码并提升，丢弃 HandmadeMath.h/LICENSE/update/ | 手动从已校验 tar（sha256 faf7f513）重建 .orig/.work 目录结构（不动框架脚本） |
| 3 | conan-verify G2 报 "package_type library 但无 shared 选项" | header-only 库不能声明为 library | package_type 改为 `header-library`（catch2 同款） |
| 4 | conan-verify package() NameError: os | 导入缺失 | 补 `import os` |
| 5 | 上游测试 InvGeneral 1~2 断言失败 | 浮点精度：HMM_InvGeneralM4 的 Result[1][3]=2.38e-07 略超 FLT_EPSILON=1.19e-07，属通用矩阵求逆数值误差，aarch64 clang 下四变体均同 | 记录为上游测试浮点容差问题，不改源码掩盖（R1）；测试统计如实上报 |

## 源码修改

无。header-only 库无需补丁（patches/ 为空）。

## 依赖版本

无第三方依赖（单头文件库，零 .so 产物）。

## 验证结果

上游测试四变体（aarch64 / clang 15.0.4）：
- `make c`: 86/87 passed, 1 failure（InvGeneral line 139 浮点精度）
- `make c_no_sse`: 86/87 passed, 1 failure（同）
- `make cpp`: 90/91 passed, 2 failures（line 139 + line 163 浮点精度）
- `make cpp_no_sse`: 90/91 passed, 2 failures（同）
- Coverage: C 121 / C++ 280 coverage cases，0 failures

conan-verify：G1/G2/G3/G4 全部 PASS（exit 0）。

## 交付物

| 文件 | 说明 |
|------|------|
| archives/h/handmade-math/2.0.0/conanfile.py | header-library Conan 配方 |
| archives/h/handmade-math/2.0.0/conandata.yml | 官方 GitHub v2.0.0 源 + sha256 3ec811fe |
| archives/h/handmade-math/2.0.0/test_package/ | 消费者测试（实质调用 API）+ MANIFEST.yml 上游声明 |

## 注意事项

- InvGeneral 浮点精度失败为上游测试固有容差（FLT_EPSILON 绝对比较），非适配引入，不阻塞
- conandata.yml 源 URL 保持官方 GitHub（R39），CI 自动注入镜像 fallback（E017）
- 本库为 header-only，无需 commands.json（R38，无 bin 产物）
---

**编译结束**: 2026-09-08 16:12
**最终状态**: built
