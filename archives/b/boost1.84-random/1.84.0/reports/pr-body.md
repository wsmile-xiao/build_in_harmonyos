## PR 信息
- **三方库名称**：boost1.84-random（Boost.Random 组件包，从 Boost 1.84.0 完整源码独立裁剪）
- **上游版本**：1.84.0（boost_1_84_0.tar.gz，SHA256 a5800f405508f5df8114558ca9855d2640a2de8f0445f051fa1c7c3383045724）
- **上游仓库地址**：https://github.com/boostorg/random （random 子模块；完整源码出自 Boost 官方发布仓库 https://github.com/boostorg/boost tag boost-1.84.0）
- **适配路径**：路径 A（基础适配）
- **使用知识库**：E068（Boost.Build SHELL 执行机制在鸿蒙不兼容——b2 不可用，手动编译绕过）；底稿 archives/b/boost/1.84.0 已验证方案

---

## 测试用例对比

### 上游库测试用例统计
| 测试类型 | 上游用例数 | 说明 |
|----------|-----------|------|
| 单元测试 | 4 | 来源：libs/random/test/ + libs/random/example/（test_random_device + test_mt19937 + test_mt19937_64 + random_demo，上游 Jamfile.v2 run 目标） |
| 集成测试 | 0 | - |
| 其他测试 | 0 | - |
| **合计** | **4** | test_random_device 原样运行；mt19937/mt19937_64 为上游 test_generator.ipp 完整断言集（各 15 用例，含验证值断言）；random_demo 为上游 example run 目标 |

### 适配后测试用例统计
| 测试类型 | 适配后用例数 | 与上游对比 | 说明 |
|----------|-------------|-----------|------|
| 单元测试 | 4 | 不变 | 全部 4 项上游测试绕过 b2 手动编译运行，4/4 通过 |
| 集成测试 | 0 | - | - |
| 鸿蒙特有测试 | 6 | 新增 | test_package 六组校验（mt19937 种子可复现/uniform_int 范围与覆盖/uniform_real 范围/random_device entropy+generate+唯一性/variate_generator），CMake find_package(Boost COMPONENTS random) 消费链路 + ELF 签名后真机运行 |
| **合计** | **10** | **+6** | |

---

## 上游测试用例修改说明
### 是否存在对上游测试用例的修改？
- [x] **否**，未修改上游任何测试用例
  （上游测试源文件零修改。b2 在 OHOS 不可用，改为 clang++ 直接编译运行。说明：test_mt19937/test_mt19937_64 上游通过链接 boost_unit_test_framework 提供测试框架实现，本配方未编译 boost test 库（不属 random 组件范围），改用 boost/test/included/unit_test.hpp 单头全实现承载同一套用例——BOOST_RANDOM_URNG/VALIDATION_VALUE（4123659995U / 9981545732273789042 等）等宏与上游测试文件逐字一致，断言与验证值完全不变。曾实测 SEED_WORDS 抄错（312≠上游 624）时测试立即失败，证明断言真实有效）

---

## 补全测试用例说明
### 上游是否存在无测试用例，适配后补全的情况？
- [x] **否**，上游已有测试用例覆盖
  （上游 random 库自带 108 个测试文件，本适配选取组件核心测试 4 项全部真实运行；另新增 test_package 六组 API 冒烟校验作为鸿蒙特有测试，非补全性质）

---

## 验证结果
- 编译状态：通过（conan create PASS；产物 libboost_random.a + 完整 boost 头文件树）
- 上游测试用例通过率：4/4（100%）
- 新增测试用例通过率：6/6（100%，test_package ctest boost_random_test 通过）

验证命令：
```bash
conan create archives/b/boost1.84-random/1.84.0 -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing
```
关键输出：`[upstream-tests] TOTAL 4: 4 passed / 0 failed`、`boost1.84-random smoke test PASSED`

---

## 补充说明
- **打包方式**：b2 构建系统在 OHOS 不兼容（E068，SHELL 执行机制失败），采用底稿 archives/b/boost/1.84.0 的手动编译方案——libs/random/src/random_device.cpp（上游唯一需编译源文件）clang++ 编译 + llvm-ar 归档为 libboost_random.a，全量 boost 头文件树随包分发（mt19937/分布器等全部 header-only）
- **补丁**：0001-ohos-pthread-cancel-fix.patch——OHOS musl 无 pthread_setcancelstate，通过 BOOST_SP_NO_PTHREAD_SETCANCELSTATE 特性宏跳过（R8 合规，无平台宏硬编码；与底稿 boost/1.84.0 同一补丁）
- **依赖**：无 conan requirements（random_device.cpp 引用的 boost::system 头文件自 1.69 起 header-only，POSIX /dev/urandom 后端在 OHOS musl 下直接编译；不需要 boost1.84-system 包）
- **CMake 组件**：Boost::random / Boost::headers / Boost::system（header-only 声明），cmake_file_name=Boost 与其他 boost1.84-* 组件包一致
- **运行环境**：测试二进制运行需 SDK libc++_shared.so（clang++ -print-file-name 动态定位注入 LD_LIBRARY_PATH）+ ELF 自签名（llvm-objcopy --remove-section .codesign + binary-sign-tool，继承 boost 1.85 先例），配方内全自动处理
- **已知限制**：无（random_device 在 OHOS 上自动选择 POSIX /dev/urandom 后端，熵源工作正常）
