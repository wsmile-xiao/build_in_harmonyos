# linalg.h 2.2 适配笔记

## 编译环境
- 构建系统: header-only（单头文件，无编译步骤；上游测试 samples/ 用 Makefile/CMake 构建 doctest 二进制）
- 编译日期: 2026-09-19
- 编译器: /data/service/hnp/bin/clang++ 15.0.4（Target: aarch64-unknown-linux-ohos）
- 状态: published

## 编译步骤
1. 下载官方 v2.2 tag tarball：`https://github.com/sgorsten/linalg/archive/refs/tags/v2.2.tar.gz`
   - SHA-256: 28640228988186edaf7729177bfab4c91170b303ad489407a4228ceb55a73ec2
2. 编写 header-only Conan 配方（conanfile.py + conandata.yml + test_package/）
3. conan create（ohos-aarch64 profile，host=build=OHOS arm64）→ 通过
4. 当轮 conf 使用 E017 镜像（ghfast.top）下载 GitHub URL，核验 sha256 一致后恢复官方 URL

## 遇到的问题与解决方案
| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | init-build 把 samples/ 提升为源码根，删除 linalg.h | 嵌套源码提升逻辑把含 CMakeLists.txt 的 samples/ 误判为源码根 | 重新解析官方 tarball 为正确布局（linalg.h/README/UNLICENSE/samples），保持 .tarball-sha256 标记 |
| 2 | conan-init 生成 Autotools 模板配方 | build_system 探测误判为 autotools | 重写为 header-only 配方（package_type=library，仅 copy linalg.h 到 include/，无 build 步骤） |
| 3 | test.c 空壳（仅 print）违反 R34 | 自动生成的 test_package 模板空壳 | 重写为真实 C++ 消费者测试（test.cpp：vec/mat/dot/cross/四元数/constexpr 断言） |
| 4 | linalg.h v2.2 API 与猜测不符 | rotation_quat(axis, angle) 而非 (angle, axis)；无 rotation_matrix3x3 | 按实际头文件 API 修正（rotation_matrix(rotation_quat(...)) 4x4） |

## 源码修改
无（header-only，未打补丁）

## 依赖版本
无外部依赖（仅 C++11 标准库 + 单头文件）

## 验证结果
- conan-verify：G0-G4 全 PASS（含 G2 conan create 干净构建 + test_package 消费者测试）
- 上游测试：linalg-test（doctest 2.4.0）222 用例 / 21698 断言全过（通过率 222/222 = 100%）
- HarmonyOS 专项测试 test_ohos.cpp：ABI 布局/constexpr/矩阵/四元数全部通过（OHOS clang 15 aarch64 实测）

## 交付物
| 文件 | 说明 |
|------|------|
| conanfile.py | header-only 配方 |
| conandata.yml | 官方源 + sha256 |
| test_package/ | 消费者测试 test.cpp + OHOS 专项测试 test_ohos.cpp |
| MANIFEST.yml | 版本级结构声明 |

## 注意事项
- 上游测试统计双口径：源码声明 68（29 TEST_CASE + 39 TEST_CASE_TEMPLATE），doctest 实际注册执行 222（含类型实例化与 SUBCASE 展开），全部通过；SUBCASE 子节不计独立用例
- 该库为纯头文件数学库（Unlicense 公共领域），无平台配置/宏需求，OHOS 上天然可编译运行
---

**编译结束**: 2026-09-19 22:31
**最终状态**: published
