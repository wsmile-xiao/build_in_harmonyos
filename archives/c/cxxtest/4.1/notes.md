# cxxtest 4.1 适配笔记

## 软件信息
- 软件：cxxtest 4.1（上游 CxxTest/cxxtest tag 4.1，2012-11-30 发布，LGPL-2.1）
- 定位：轻量级 C++ 单元测试框架——纯 header-only（cxxtest/ 头文件集即"库"）+ Python 驱动脚本 cxxtestgen（构建期工具，目标机不需要 Python 运行时）
- 构建系统：上游无构建系统（纯源码分发，test/ 有 Makefile 仅做清理；SCons builder 在 build_tools/ 供下游可选使用）
- 分支 feat/cxxtest-4.1；worktree ~/huawei/worktrees/j669539/cxxtest-4.1

## W0/W0b
- W0 preflight：PASS（零依赖——无 requires/tool_requires，header-only + 源码包内自带 Python 驱动）
- W0b：本仓库无 cxxtest 历史归档；同类测试框架先例 catch/1.12.2（header-library 模式，package_id clear，cmake_file_name/target）作为配方骨架参照
- lang-preflight：cpp 判定（cxxtest/ 头文件集为主体，python/ 为构建期辅助脚本——按 R47 辅助脚本不算主体规则，不构成 mixed）

## 源码检查（上游 4.1 tarball，SHA256 9b4b624f02d088c8fa79c116870451acf2d0aefdb2a1ab76407915bdb7058566）
- cxxtest/：头文件集（TestSuite.h/TestRunner.h/ErrorPrinter.h 等）+ Root.cpp 等源片段——被生成器 #include 进 runner，非预编译库
- python/python3/cxxtest/：Python 3 驱动包（cxxtestgen.py 入口 + cxxtest_parser.py 解析器）；python/cxxtest/ 为 Python 2 老线，不打包
- bin/cxxtestgen：驱动入口脚本（sys.path 拼接 + import cxxtest; cxxtest.main(sys.argv)）
- 无需任何源码补丁 → patches 为空

## 关键实测记录（设备 aarch64 OHOS）
1. cxxtestgen 在 Python 3.12 下正常工作：
   `PYTHONPATH=<src>/python/python3 python3 <src>/python/python3/scripts/cxxtestgen --error-printer -o tests.cpp MyTestSuite.h`
   仅出一条 SyntaxWarning（cxxtest_parser.py 的 `if p.type is ""`），生成输出正确
2. 生成 runner → clang++ 交叉编译（--target=aarch64-unknown-linux-ohos）→ E077 四步签名 → 设备运行输出 `Running 1 test.OK!` exit 0
3. 运行期需要 LD_LIBRARY_PATH 指向 SDK libc++（aarch64-linux-ohos），与所有 OHOS C++ 程序一致
4. 直接 `python3 -c "import cxxtest; cxxtest.main(sys.argv)"` 调用同样可行——消费者无需安装 bin/cxxtestgen 到 PATH，直接 python3 <res>/cxxtest/cxxtestgen.py 即可

## 上游测试统计与执行（rule4 口径）
- 上游自带 PyUnit 自测套件 test/test_cxxtest.py（CxxTest 是测试工具，它的自测就是"用自己测自己+驱动器"）：
  - 静态：62 个 `def test_` 方法（其中 1 个 `test_inheritance` 被后面的同名 def 遮蔽——上游自身代码形态）
  - 注册：按编译器类分发（TestGpp/TestCpp/TestClang/TestCL + FOG 变体）；每类的 run() 先探测编译器是否存在，不存在则不注册任何用例（上游自带门控）
  - FOG 变体类额外依赖可选模块 ply（try/except 导入）；test_doc.py 依赖 pyutilib.th；test/unit/LinkedList_test.t.h 依赖 SCons builder
- 本环境（OHOS 设备，仅 clang++ 可用，无 ply/pyutilib/SCons）实测：
  - **TestClang：60 用例注册，59 passed + 1 skipped，0 failed，exit 0**
  - skip 明细：test_int64——套件自带编译器探针（int64.cpp 用 MSVC 专有 `__int64` 类型，clang/Itanium ABI 不支持）探测失败后主动 skipTest；同套的 test_longlong 用标准 `long long` 正常通过
  - TestGpp/TestCpp/TestCL：0 用例注册（g++/c++/cl 在设备上不存在，上游 run() 门控直接返回）；FOG 类 0 注册（无 ply）；test_doc.py 因 pyutilib 缺失不产生用例；LinkedList_test.t.h 需 SCons 环境
  - 实测证据：~/huawei/builds/cxxtest/upstream_TestClang_run.log、upstream_all_run.log（Ran 60 tests in 136.4s, OK (skipped=1)）
- N 口径结论：框架自身测试按编译器类分形，clang 类全绿。CI 环境（Linux x86_64 worker）有完整 clang++，test_package 链路在 CI 内验证；上游套件已按 clancyxie 口径在本地设备实跑并如实申报

## 适配后测试（消费者，test_package）
- test_cxxtest.h：4 个用例（testArithmetic/testStrings/testExceptions/testFloatingPoint），12 个断言
  （TS_ASSERT/TS_ASSERT_EQUALS/TS_ASSERT_DIFFERS/TS_ASSERT_LESS_THAN/TS_ASSERT_STR_EQUALS/TS_ASSERT_THROWS/TS_ASSERT_THROWS_NOTHING/TS_ASSERT_DELTA）
- 消费流程三步全真：①调用包内 cxxtestgen（res/cxxtest/cxxtestgen.py，经 user_info.cxxtestgen 暴露）生成 runner ②CMake 对 CxxTest::CxxTest 编译 ③E077 签名后运行 grep "OK!"
- run_check.sh 断言 ErrorPrinter 输出 "OK!"（Running 4 tests.OK!）

## OHOS 平台要点
- header-library 无交叉编译环节；消费者编译的测试二进制必须签名（E077）
- binary-sign-tool 调用剔除 LD_LIBRARY_PATH（sign-tool 依赖系统 libc++.so，SDK 路径遮蔽会 86 符号 not found）
- python3 在 PATH（/usr/local/bin/python3）即可驱动 cxxtestgen，目标机不需要额外 Python 运行时部署（生成发生在构建期）

## 验证记录
- conan create（G2）+ test_package 全链路本地通过（见 reports/）
- status：built（上传发布须等合并后 release 流水线）
