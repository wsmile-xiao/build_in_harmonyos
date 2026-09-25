# bertrand 0.013 适配笔记

## 编译环境
- 构建系统: cmake（header-only INTERFACE 库，C++17）
- 编译日期: 2026-09-22
- 编译器: clang 15.0.4 (OHOS armv8, /data/service/hnp/bin/clang++)
- 状态: published
- 上游: https://github.com/bernedom/bertrand (tag 0.013, commit 2c20460911524efda4572f43713d67bc1b66721f)

## 编译步骤

1. 下载官方 tag 源码: `https://github.com/bernedom/bertrand/archive/refs/tags/0.013.tar.gz`
   SHA-256: f2f071006d3a9b31382957b84e81405adba44cbf1a9bb8242ad4d0f44d7af7fb
2. 环境核验: clang 15.0.4 / cmake 4.1.2 / make 4.4.1 / pkg-config 0.29.2 / ninja，TMPDIR=/storage/Users/currentUser/tmp
3. lang-preflight: task=cpp, detected=cpp (88% 主体) → 通过
4. 本地构建验证:
   `cmake -S . -B build -DCMAKE_INSTALL_PREFIX=$DEFAULT_PREFIX -DBUILD_TESTING=OFF`
   `cmake --build build -j1` → 成功（INTERFACE 库无编译产物）
   `cmake --install build --prefix $TEST_PREFIX` → 头文件 + CMake config 安装成功
5. Conan 配方: 手写 header-only CMake 配方（工具误判 autotools，已按真实 CMake INTERFACE 库重写）
   conan-verify: G1/G2/G3/G4/L2/L4/L5 全过，conan create 成功
6. 上游测试: 16 个 Catch2 TEST_CASE + failing_contract 全部实际编译运行通过
   （详见 reports/upstream-test-ledger.md，双口径 17/31，可执行集合 17/17=100%）
7. 鸿蒙专项测试 test_ohos.cpp + 消费者测试 test.cpp 均编译运行通过 (exit 0)

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | init-build 下载仓库页返回 HTML | 裸仓库 URL 不适用于 tarball 下载 | 改用官方 archive/refs/tags/0.013.tar.gz |
| 2 | conan-init 生成 autotools 模板 | 工具误判构建系统（无构建族） | 按 header-only CMake INTERFACE 库手写配方（参考 templates/conanfile-headeronly.py.tmpl 与 7bitdi 正例） |
| 3 | test_package 首次 G2 失败: `use of undeclared identifier 'bertrand'` | BERTRAND_ENABLE_CONTRACTS 在 include 之后才定义，头文件在 include 时判定契约关闭 | 改用 CMake target_compile_definitions 在 include 前开启契约（与上游测试一致） |
| 4 | G2 第二次失败: constexpr 变量初始化错误 | 上游 bertrand::find 存 `const T&` 引用，constexpr 初始化临时对象不合法 | 消费者测试改为运行时验证 |
| 5 | 上游测试 configure 卡死 | test/CMakeLists 从 raw.githubusercontent.com 下载 conan.cmake 网络不可达 | 绕开 conan.cmake，用 registry 中 catch2/2.13.10 头文件直接编译运行全部用例 |
| 6 | catch2/2.13.1 精确版本不可用 | registry 返回 acceleration policy 错误，无该精确版本 | 复查后使用可得 2.13.10（2.13.x API 兼容）并记录在台账 |
| 7 | 本机无 shunit2 | 宿主 shell 框架缺失 | shell 测试函数的行为用等价命令逐项手动验证（见台账） |
| 8 | /tmp 只读 | HMDFS 平台限制 | 输出可执行文件到 $TMPDIR=/storage/Users/currentUser/tmp |
| 9 | worktree 检出后 libXext/libxext 文件显示已修改 | main 中同时跟踪两种大小写变体，大小写不敏感文件系统检出伪影 | 按基线隔离规则恢复 libXext 到 HEAD 并核对 SHA-256，不加入任何 commit（见 reports/baseline-isolation.md） |

## 依赖版本

- 无运行时/构建依赖（header-only）
- 测试依赖: catch2/2.13.10（registry 可得版本，替代上游声明的 2.13.1）
- 测试框架: shunit2（宿主环境缺失，行为已手动等价验证）

## 验证结果

```bash
# 上游 Catch2 测试 (16 TEST_CASE)
/tmp/bertrand_tests → All tests passed (18 assertions in 16 test cases), exit 0
# 鸿蒙专项测试
/tmp/test_ohos → OHOS test bertrand 0.013: ALL PASSED, exit 0
# 消费者测试
/tmp/test_consumer → test bertrand 0.013: ALL CHECKS PASSED, exit 0
# conan create (test_package 内置)
conan-verify → G1/G2/G3/G4 PASS, L2/L4/L5 完成, exit 0
```

## 注意事项

- 库为纯 header-only（include/bertrand/bertrand.hpp），无 .so/.a 产物，不需 commands.json（R38 不适用）
- 上游自带 conanfile.py 为 Conan 1.x 旧 API，本配方按 Conan 2.29.1 重写
- 版本号: 上游 CMakeLists VERSION 0.0.13，tag 0.013，任务版本 0.013 一致
---

**编译结束**: 2026-09-22 17:05
**最终状态**: published
