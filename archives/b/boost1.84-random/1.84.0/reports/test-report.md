# test-report: boost1.84-random 1.84.0

日期：2026-09-05 ｜ 编译器：clang 15 (libc++) ｜ 平台：OpenHarmony aarch64

## 一、conan create（本地 W3 等效验证）

命令：`conan create archives/b/boost1.84-random/1.84.0 -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing`

结果：**PASS**（exit 0）
- 产物：libboost_random.a（random_device.cpp）
- test_package：ctest boost_random_test 通过（ELF 签名后运行，6 组 API 校验全过）

## 二、上游测试（绕过 b2，手动编译 libs/random/test + example）

| 测试 | 断言/用例数 | 结果 |
|---|---|---|
| test_random_device.cpp | 6 断言组（entropy/范围/generate） | PASS |
| test_mt19937.cpp | 15 用例（含验证值 4123659995U） | PASS |
| test_mt19937_64.cpp | 15 用例（含验证值 9981545732273789042） | PASS |
| random_demo.cpp（上游 example run 目标） | 演示程序 | PASS |

**TOTAL 4: 4 passed / 0 failed（通过率 100%）**

说明：
1. b2 构建系统在 OHOS 不兼容（E068），改为手动编译测试源文件链接 libboost_random.a 运行
2. mt19937/mt19937_64 的上游测试（test_generator.ipp）用 linked 版 unit_test.hpp（需 boost_unit_test_framework 编译库，本配方不含 test 库），改用 boost/test/included/unit_test.hpp 单头全实现承载：BOOST_RANDOM_URNG/VALIDATION_VALUE 等宏与上游测试文件逐字一致，断言语义不变。实测宏抄错（SEED_WORDS 312≠624）时测试立即失败，证明断言真实有效
3. 测试二进制运行环境：LD_LIBRARY_PATH 动态定位 SDK libc++_shared.so（clang++ -print-file-name）

## 三、test_package 冒烟（CMake 消费链路）

test_boost_random.cpp 六组校验：
1. mt19937 种子可复现（同种子同序列）
2. uniform_int_distribution [1,6] 范围 + 覆盖（≥4/6）
3. uniform_real_distribution [0,1) 范围
4. random_device（编译库源）：entropy≥0 / 取值范围 / generate 批量
5. random_device 唯一性（32 抽取 ≥8 个不同值）
6. variate_generator 经典接口

结果：**boost1.84-random smoke test PASSED**（rc=0）

## 四、conan-verify 门禁（finish step 4 实测）

G1 配方完整性 PASS ｜ G2 conan create 干净构建 PASS ｜ G3 系统同名库隔离 PASS ｜ G4 产物完整性 PASS

## 五、本地 CI 模拟（W3，finish step 5 实测）

setup.sh PASS + build_and_test.sh PASS（junk_check/JC5/JC6/L0-L5 全绿）
.ci-result.json exit_code=0，integrity_hash=5155050616896d80
