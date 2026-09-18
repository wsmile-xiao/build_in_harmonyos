# libnewuoa 0.1.2 适配笔记

## 编译环境
- 构建系统: cmake（上游 CMakeLists.txt 3.16+，C++11 库 + C 接口）
- 编译日期: 2026-09-18
- 编译器: clang/clang++ 15.0.4（OHOS aarch64，conan profile ohos-aarch64）
- 状态: built（conan-verify W3 全绿：G0–G4、L2、L4、L5 PASS）
- worktree: ~/qzy/GLM-50-libnewuoa-0.1.2（分支 feat/libnewuoa-0.1.2，基于 upstream/main e321afdc8c）
- CONAN_HOME: ~/tmp/ch/home-glm50-libnewuoa

## 编译步骤

1. `ohc-run.py init-build libnewuoa 0.1.2 --auto --url <官方 GitHub archive>`：下载源码（SHA256 660274f2…）、建归档骨架。
2. 编写 conanfile.py（CMakeToolchain + BUILD_SHARED_LIBS 开关 + cmake.install）、conandata.yml（官方 URL + 真实 SHA256）、test_package（消费者测试）。
3. `ohc-run.py conan-verify libnewuoa 0.1.2`：conan create 全链路（source→build→package→test_package）通过。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 首次 conan-verify G1 FAIL：conandata.yml sha256 未填写 | `ohc-run.py build` 的 conan-init 步骤用占位模板覆盖了已上传的 conandata.yml | 重写 conandata.yml 为真实 SHA256；配方文件改在 build 一条龙后核对/单独 verify |
| 2 | 二次 verify G2 FAIL：create 走了 autotools.configure() 报 configure not found | conan-init 同样用 autotools 模板覆盖了 conanfile.py 与 test_package 脚手架 | 重传 CMake 配方与 test_package 三件套后单独跑 conan-verify（不再触发 init） |
| 3 | 三次 verify 前自查：find_package 参数须与 CMakeDeps 生成名一致 | CMakeDeps 按 package_info 的 cmake_file_name=newuoa 生成 newuoa-config.cmake | test_package CMakeLists 用 `find_package(newuoa REQUIRED CONFIG)` + target `newuoa::newuoa`，与配方 cpp_info 属性对齐 |

## 源码修改

无补丁（patches_applied: []）。上游源码未做任何修改。

## 依赖版本

无外部依赖（零依赖纯库）。

## 验证结果

```bash
# conan create（conan-verify 内部执行，profile ohos-aarch64）
newuoa: f=7 x=(3.000000,-1.000000)
PASS
# G0–G4 / L2(smoke) / L4(checksec) / L5(产物基线) 全部 PASS
```

## 测试账本（五维）

- N_static（上游静态用例数）：0 —— 上游 CMakeLists.txt 无 enable_testing()/add_test()，无 test/ 目录，无自动化测试
- N_registered：0
- N_executed（上游实际执行）：0（上游无测试，如实申报；非跳过）
- 未执行分类数：0（无测试可执行，不存在跳过项）
- N_consumer（消费者测试）：1 个程序 test_newuoa（test_package/test_newuoa.c），真实编译+链接+运行，3 个断言全过（f→7、x[0]→3、x[1]→-1）

## 路径 A/B/C 判断

- 判定：纯路径 A。
- 理由：本次适配无跨仓库复用的通用障碍——上游零依赖、CMake 直配即过，无稳定错误签名可沉淀；消费者测试模式与知识库既有 E 系条目（header-only/消费者测试）重复，无新增价值；不满足路径 B 证据门槛。
---

**编译结束**: 2026-09-18 02:31
**最终状态**: built
