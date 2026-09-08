## PR 信息
- **三方库名称**：boost1.84-chrono（Boost.Chrono 组件包，从 Boost 1.84.0 完整源码独立裁剪）
- **上游版本**：1.84.0（boost_1_84_0.tar.gz，SHA256 a5800f405508f5df8114558ca9855d2640a2de8f0445f051fa1c7c3383045724）
- **上游仓库地址**：https://github.com/boostorg/chrono （chrono 子模块；完整源码出自 Boost 官方发布仓库 https://github.com/boostorg/boost tag boost-1.84.0）
- **适配路径**：路径 A（基础适配）
- **使用知识库**：E068（Boost.Build SHELL 执行机制在鸿蒙不兼容——b2 不可用，手动编译绕过）；底稿 archives/b/boost/1.84.0 已验证方案

---

## 测试用例对比

### 上游库测试用例统计
| 测试类型 | 上游用例数 | 说明 |
|----------|-----------|------|
| 单元测试 | 21 | 来源：libs/chrono/test/（clock/duration/time_point/io 四组，上游 Jamfile.v2 的 chrono-run / chrono-compile 目标） |
| 集成测试 | 0 | - |
| 其他测试 | 0 | - |
| **合计** | **21** | 17 个 run 型 + 4 个 compile-only 型（typedefs/types/default_ratio/ratio_alias，上游定义即编译验证，无 main） |

### 适配后测试用例统计
| 测试类型 | 适配后用例数 | 与上游对比 | 说明 |
|----------|-------------|-----------|------|
| 单元测试 | 21 | 不变 | 全部 21 项上游测试绕过 b2 手动编译运行，21/21 通过 |
| 集成测试 | 0 | - | - |
| 鸿蒙特有测试 | 7 | 新增 | test_package 七组校验（steady_clock 单调性/duration 算术/duration_cast/time_point 算术/thread_clock CPU 时间/process_cpu_clocks/chrono_io 输出），CMake find_package(Boost COMPONENTS chrono) 消费链路 + ELF 签名后真机运行 |
| **合计** | **28** | **+7** | |

---

## 上游测试用例修改说明
### 是否存在对上游测试用例的修改？
- [x] **否**，未修改上游任何测试用例
  （上游测试源文件零修改。b2 在 OHOS 不可用，改为 clang++ 直接编译 libs/chrono/test/ 原始测试源文件链接 libboost_chrono.a 运行，测试内容与断言与上游完全一致；4 个 compile-only 型按上游 Jamfile 语义以编译通过计）

---

## 补全测试用例说明
### 上游是否存在无测试用例，适配后补全的情况？
- [x] **否**，上游已有测试用例覆盖
  （上游 chrono 库自带 21 项测试，全部真实运行；另新增 test_package 七组 API 冒烟校验作为鸿蒙特有测试，非补全性质）

---

## 验证结果
- 编译状态：通过（conan create PASS；产物 libboost_chrono.a + 完整 boost 头文件树）
- 上游测试用例通过率：21/21（100%）
- 新增测试用例通过率：7/7（100%，test_package ctest boost_chrono_test 通过）

验证命令：
```bash
conan create archives/b/boost1.84-chrono/1.84.0 -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing
```
关键输出：`[upstream-tests] TOTAL 21: 21 passed / 0 failed`、`boost1.84-chrono smoke test PASSED`

---

## 补充说明
- **打包方式**：b2 构建系统在 OHOS 不兼容（E068，SHELL 执行机制失败），采用底稿 archives/b/boost/1.84.0 的手动编译方案——libs/chrono/src/{chrono,process_cpu_clocks,thread_clock}.cpp 逐文件 clang++ 编译 + llvm-ar 归档为 libboost_chrono.a，全量 boost 头文件树随包分发
- **补丁**：0001-ohos-pthread-cancel-fix.patch——OHOS musl 无 pthread_setcancelstate，通过 BOOST_SP_NO_PTHREAD_SETCANCELSTATE 特性宏跳过（R8 合规，无平台宏硬编码；与底稿 boost/1.84.0 同一补丁）
- **依赖**：无 conan requirements（boost::system 自 1.69 起 header-only，chrono 的 error_code 用法由头文件覆盖；zlib 亦不需要——底稿的 zlib 依赖来自 iostreams，chrono 不引用）
- **CMake 组件**：Boost::chrono / Boost::headers / Boost::system（header-only 声明），cmake_file_name=Boost 与其他 boost1.84-* 组件包一致
- **运行环境**：测试二进制运行需 SDK libc++_shared.so（clang++ -print-file-name 动态定位注入 LD_LIBRARY_PATH）+ ELF 自签名（llvm-objcopy --remove-section .codesign + binary-sign-tool，继承 boost 1.85 先例），配方内全自动处理
- **已知限制**：无（chrono 三源文件在 OHOS musl + libc++ 下编译无平台障碍）
