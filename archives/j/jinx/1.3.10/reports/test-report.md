# jinx/1.3.10 真机测试报告（HarmonyOS PC / aarch64）

- 任务：#7636（活动「开源鸿蒙PC专项积分赛」），分支 `feat/jinx-1.3.10`
- 设备：HongMeng Kernel 1.12.0 / HarmonyOS aarch64 / Toybox 用户态
- 工具链：harmonybrew clang 15.0.4（profile `ohos-aarch64`：os=OHOS, os.version=6.0,
  arch=armv8, compiler.cppstd=17, libcxx=libc++）、cmake 4.4.3、conan 2.29.1
- 缓存：`CONAN_HOME=~/work/psj/ch-jinx7636`（私有 home，`conancenter` 置 disabled，只留 `ohpcd`），
  profile 从 `~/.conan2/profiles/ohos-aarch64` 拷入（host = build）
- 日志：`~/work/psj/jx7636-ch3.log`

## 命令

```sh
conan create archives/j/jinx/1.3.10 -pr:h=ohos-aarch64 -pr:b=ohos-aarch64 --build=missing
```

## 结果

```
CREATE_EXIT:0
jinx/1.3.10: HMOS_UPSTREAM_TEST_RESULT={"status": "passed",
  "framework": "Catch2 (bundled Tests/UnitTests/catch.hpp)", "command": "./UnitTests",
  "declared_TEST_CASE_macros": 14, "declared_SECTION_blocks": 326,
  "declared_REQUIRE_macros": 1044, "test_cases_reported": 14,
  "assertions_reported": 1045, "assertions_failed": 0}
```

### 上游套件（配方在 `build()` 内构建并真实执行 `./UnitTests`）

上游 Catch2 的汇总行只在**全通过**时输出单行、有失败时才输出 `test cases: …` 汇总表，
所以解析器两种形态都要读；配方对 `test cases >= 14`、`assertions >= 1044`、`failed == 0`
三条设硬下限，不满足直接抛 `ConanException`（第一轮就是因为只认汇总表，把 14/14 全通过
误判成「没跑测试」→ `CREATE_EXIT:1`，见 `notes.md`）。

`hmos_unit_tests.log`（构建目录内）：

```
===============================================================================
All tests passed (1045 assertions in 14 test cases)
```

用例来源与取数命令（pristine v1.3.10 归档）：

```sh
grep -cE '^TEST_CASE' Tests/UnitTests/*.cpp               # 14
grep -cE '^[[:space:]]*SECTION' Tests/UnitTests/*.cpp     # 326
grep -cE '^[[:space:]]*REQUIRE\(' Tests/UnitTests/*.cpp   # 1044
```

编译侧证据（`-Wall -Wextra -pedantic -Werror` 原样保留，无告警、无补丁；日志原文）：

```
-- The CXX compiler identification is Clang 15.0.4
[  2%] Building CXX object CMakeFiles/Jinx.dir/Source/JxBuffer.cpp.o
[ 56%] Linking CXX static library libJinx.a
[ 56%] Built target Jinx
[100%] Linking CXX executable UnitTests
[100%] Built target UnitTests
```

编译单元计数（同一份日志 `grep -c`）：库 21 个 `CMakeFiles/Jinx.dir` 目标文件
（`Source/*.cpp` 全部）、测试 16 个 `CMakeFiles/UnitTests.dir` 目标文件
（`Tests/UnitTests/` 的 14 个 `Test*.cpp` + `Main.cpp` + `UnitTest.cpp`，
`catch.hpp`/`UnitTest.h` 为头文件不计）。

### 消费者测试（`test_package`，`find_package(Jinx CONFIG REQUIRED)` + `Jinx::Jinx`）

```
jinx/1.3.10 (test package): Running test()
JINX_CONSUMER_RESULT assertions=33 failed=0
JINX_HARMONYOS_RESULT assertions=33 failed=0
```

- `test_package.cpp` 33 条：版本串 `GetVersionString()=="1.3.10"`、runtime 创建、
  `Compile → CreateScript → 循环 Execute 到 IsFinished`、上游 TestCasts 的四个强制转换语义、
  集合大小、循环累加 55、未声明变量返回 Null、上游 TestErrors 的负例（裸 `---` 编译失败）、
  两个 runtime 变量互不串扰与同一 runtime 复用。
- `harmonyos_test.cpp` 33 条：`__OHOS__` 平台标识、LP64 数据模型（pointer/size_t/long 均 8
  字节）、>INT32_MAX 的整数仍以 int64 保存、musl 下 UTF-8 字符串按字节存
  （`αβ⨉` 共 7 字节）、协程 `async call` 在 aarch64 上的上下文切换取值 4242、
  默认 `maxInstructions=2000` 护栏对超大脚本返回失败而不是挂死、
  按上游文档抬高预算后同一 1001 条语句脚本得到 500500、4 线程各自持有 runtime 的并发结果、
  2000 轮 runtime/script 建销稳定性。

其中默认预算护栏这一条在日志里留有真实输出（这是**用例主动断言**的行为，不是缺陷）：

```
Runtime error in script 'harmonyos' at line 501: Exceeded max instruction count
```

### 产物与依赖

```
jinx/1.3.10: package(): Packaged 1 '.a' file: libJinx.a
jinx/1.3.10: package(): Packaged 7 '.h' files
jinx/1.3.10: package(): Packaged 1 file: LICENSE
jinx/1.3.10: Created package revision 9a93ae235881c19b6ad0b9bcee304718
jinx/1.3.10: Package '21b17f8b2bc0e9511e276e3d57a23893067cefe5' created
jinx/1.3.10: Full package reference:
  jinx/1.3.10#69d6241f0c97715f060a801ee5801929:21b17f8b2bc0e9511e276e3d57a23893067cefe5#9a93ae235881c19b6ad0b9bcee304718
```

包内布局（无 `bin/`，不触发 L0k/R38）：

```
include/Jinx.h  include/JxBuffer.h  include/JxCollection.h  include/JxCoroutine.h
include/JxMemory.h  include/JxTypes.h  include/JxVariant.h
lib/libJinx.a
licenses/LICENSE
```

外部依赖 0 个（L0i/R36 天然满足）；制品仓 `jinx/1.3.10` 未发布（L0j/R37 预检通过）。
源码包两端字节对拍：本机与真机同为 24596620 B、sha256
`5b3a3e6c2c4b976dfdb16519aee7299c98dbf417b8179099a5509a5fd4d513ac`（真机 5 秒下完）。
