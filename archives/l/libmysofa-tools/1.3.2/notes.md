# libmysofa-tools 1.3.2 适配笔记

## 编译环境
- 构建系统: cmake（显式 Ninja 生成器）
- 编译日期: 2026-09-16
- 状态: published
- 工具链: clang 15.0.4 + OHOS NDK sysroot（aarch64-linux-ohos）
- conan: 2.29.1（OHOS 适配版），profile: ci/conan/profiles/ohos-aarch64

## 遇到的问题与解决方案

### 1. mysofa2json 藏在 BUILD_TESTS 守卫内
上游 src/CMakeLists.txt 把 mysofa2json 的 add_executable/install 放在
BUILD_TESTS 块内（依赖 CUnit）。-tools 交付物不应依赖 CUnit，
补丁 0001 将工具目标移出守卫，配方保持 BUILD_TESTS=OFF。

### 2. OHOS /tmp 只读
src/tests/easy.c 使用 /tmp/easy.tmp.json，OHOS /tmp 只读（E002）。
补丁 0002 改为工作目录相对路径。

### 3. OHOS musl 无 pthread_cancel
src/tests/multithread.c 依赖 pthread_cancel。补丁 0003 以
watchdog_stop 标志位 + pthread_join 等价替换。

### 4. cmake_minimum_required 过低
顶层 CMakeLists.txt 要求 2.8.12，低于 CMake 已移除的 3.5 兼容线。
toolchain 变量 CMAKE_POLICY_VERSION_MINIMUM 注入时机晚于
cmake_minimum_required 执行，无效；补丁 0004 直接升级到 3.5。

### 5. 生成器须显式 Ninja
本机环境下 make 的 recipe /bin/sh → clang 派生链存在 exec 异常
（环境回归，clang 无声退出 Error 1），且 -j1/-j4、env 内容、
python 派生域均与之无关；ninja 直接 fork/exec 编译命令不受影响。
配方在 generate() 中 define
tools.cmake.cmaketoolchain:generator=Ninja（必须先于
CMakeToolchain 构造；test_package 在 configure() 中 define，
因 generators 属性先于 generate() 实例化）。

### 6. CMakeDeps 无组件时目标名
test_package 链接目标名为 libmysofa-tools::libmysofa-tools
（无 components 时全局目标名=包名），非 libmysofa-tools::mysofa。

### 7. 包内可执行文件不在 PATH
ctest 经 make test 间接执行、self.run 经 /system/bin/sh 执行，
包 bin/ 均不在 PATH；test_package 从依赖图取 mysofa2json 绝对路径，
经 -DMYSOFA2JSON 传入 CMake 并全程绝对路径调用。

## 上游测试执行（真实设备）
- ctest 共 43 项：**43/43 原生通过**（CTEST_RC=0，
  reports/upstream-ctest.log）。
- 关键适配（补丁 0005）：上游 16 项 JSON 比对测试依赖
  node json-diff.js，而 node/V8 在 OHOS musl 上必崩溃
  （Signal 5, "Check failed: 12 == (*__errno_location())"），
  比对器无法执行；以语义逐条等价的 python 比对器
  tests/json_diff_ohos.py（复刻容差 e=0.05、DiffNew/DiffDeleted、
  JS 数值相等规则、utf8 替换解码）替换 node 调用，并在脚本内
  将软链 .sofa 输入解析为实体路径（OHOS 沙箱对打包二进制
  deny open(2) symlink，如 MIT_KEMAR_normal_pinna.sofa）。
- 历史：替换前 27 项原生通过、16 项环境失败（node 崩溃 15 +
  软链 EACCES 1），当时已用独立等价比对器交叉验证 16/16 EQUAL
  （reports/upstream-pycompare.log），证明替换仅恢复"裁判员"，
  未改变任何判定结果。
- CUnit 套件：external 13/13（20934 断言）、internal 2/2
  （23 断言）、multithread ALL GOOD。
- 日志：reports/upstream-ctest.log（43/43 全绿）、
  reports/upstream-pycompare.log（替换前交叉验证）

## test_package（消费者验证）
- ctest 3/3 通过（含新增鸿蒙工具用例 ohos_tool_mysofa2json）
- test_libmysofa 消费者二进制直跑：PASSED (M=1250 N=256 R=2)
- ohos_special_test 鸿蒙专项 5/5：ALL PASSED
- mysofa2json 工具直跑输出含 "M"/"Dimensions" 键

## 门禁结论
- conan-verify：G0/G1/G2/G3 全部 PASS，可标记 published
- W3：L0 pass、L1 pass（含 L1a/L1b/L1c/L1e R34 负向测试）、
  L2 skip（mysofa2json 无 --version/--help，非阻塞）、
  L4 pass、L5 pass
- W2：仅含配方变更，无框架文件

## 交付物
| 文件 | 说明 |
|------|------|
| lib/libmysofa.a | 静态库（conan 包内） |
| bin/mysofa2json | SOFA→JSON 工具（conan 包内） |
| include/mysofa.h 等 | 头文件（conan 包内） |
---

**编译结束**: 2026-09-16 13:36
**最终状态**: published
