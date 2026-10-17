# libserial 1.0.0-git20250903 HarmonyOS PC 适配笔记

## 上游信息

- 仓库：https://github.com/crayzeewulf/LibSerial（master 分支）
- 版本依据：上游最新发布 tag 为 `v1.0.0`（2018-12-03）；master 最后一次推送时间为
  2025-09-03T03:44:29Z。本任务版本 `1.0.0-git20250903` = v1.0.0 版本线 + 2025-09-03
  的 master 快照，对应 commit `50e0f443666d48d7c7e181dc73a6b35700517fae`
  （"Update gtest 1.13.0 -> 1.17.0"，master 在该日期的最后一个提交）。
- 源码包：`https://github.com/crayzeewulf/LibSerial/archive/50e0f443666d48d7c7e181dc73a6b35700517fae.tar.gz`
  SHA256 `1befff3e41355dcbd292db79624764687a49b981b20998887b14e1c48a03f4fe`（125,424 字节）。
  本地 macOS 与设备端（OHOS）各下载一次，哈希逐字一致。
- 许可证：BSD-3-Clause（LICENSE.txt）。
- 语言：C++17（CMAKE_CXX_STANDARD 17，CMAKE_STANDARD_REQUIRES ON）。
- 第三方依赖：无。库本体只依赖 C++17 标准库与 POSIX threads
  （`target_link_libraries(libserial_static Threads::Threads)`）。

## 构建系统与配方决策

上游同时提供 autotools 与 CMake 两套构建，配方采用 CMake（上游主推，且安装规则完整：
`include/libserial/`、静态/共享库、`libserial.pc`）。顶层 CMakeLists 的 REQUIRED 依赖
均为非库目标，全部通过选项关闭：

| 选项 | 取值 | 原因 |
| --- | --- | --- |
| `LIBSERIAL_ENABLE_TESTING` | OFF | 测试需要 Boost.Test（REQUIRED）与构建期 ExternalProject 下载 googletest 1.17.0；且 gtest 套件硬编码物理串口（见下节） |
| `LIBSERIAL_BUILD_EXAMPLES` | OFF | 示例程序非库本体 |
| `LIBSERIAL_PYTHON_ENABLE` | OFF | SIP 绑定需要 FIND_PACKAGE(PythonLibs) REQUIRED |
| `LIBSERIAL_BUILD_DOCS` | OFF | FIND_PACKAGE(Doxygen REQUIRED) |
| `INSTALL_STATIC` | ON | 静态库始终安装 |
| `INSTALL_SHARED` | =shared option | `shared=True` 时才构建/安装 `libserial.so.1`（VERSION 1.0.0，SOVERSION 1） |

无需任何补丁：configure/编译全程零修改。CMake 配置阶段会打印
"System is unknown to cmake, create: Platform/HarmonyOS"，为状态提示非错误，
线程探测 `Looking for pthread_create in pthread - found` 正常。

## R51 上游测试申报表

清点命令（对 commit `50e0f443` 源码树执行）：

```
grep -oE "\bTEST(_F)?\(" test/SerialPortUnitTests.cpp test/SerialStreamUnitTests.cpp test/MultiThreadUnitTests.cpp | sort | uniq -c
  -> SerialPortUnitTests.cpp:28 (TEST_F)
     SerialStreamUnitTests.cpp:25 (TEST_F)
     MultiThreadUnitTests.cpp:2 (TEST_F)
grep -c "BOOST_AUTO_TEST_CASE" test/unit_tests.cpp -> 2
grep -n "ADD_TEST" test/CMakeLists.txt -> 仅注册 gtest 套件：ADD_TEST(NAME UnitTests COMMAND UnitTests)
```

| 套件 | 框架 | 用例数 | 适配后执行 | 原因 |
| --- | --- | --- | --- | --- |
| `UnitTests`（test/SerialPortUnitTests.cpp） | googletest | 28 | NOT_RUN | 硬编码 `/dev/ttyUSB0`、`/dev/ttyUSB1`（test/UnitTests.h:53,58），需两台物理串口设备互写；OHOS 设备与 CI 均无串口硬件 |
| `UnitTests`（test/SerialStreamUnitTests.cpp） | googletest | 25 | NOT_RUN | 同上（同一可执行程序） |
| `UnitTests`（test/MultiThreadUnitTests.cpp） | googletest | 2 | NOT_RUN | 同上 |
| `unit_tests`（test/unit_tests.cpp） | Boost.Test | 2 | NOT_RUN | 目标链接 `${Boost_LIBRARIES}`，顶层 `FIND_PACKAGE(Boost COMPONENTS unit_test_framework REQUIRED)`；构建上游测试需引入 Boost 依赖且会连带触发 gtest ExternalProject 下载，配方按最小库交付关闭测试构建。该套件本身无硬件依赖（仅构造器与对不存在设备 Open 抛 `OpenFailed` 断言） |

原始清单 N=57（gtest 55 + Boost 2），执行 N′=0，PASS=0，FAIL=0，SKIP=0，NOT_RUN=57。
全部为 NOT_RUN（环境硬件缺失/依赖取舍），非执行失败；此口径与 PR 正文、
`manifest.yaml` 的 `test_results` 一致。

无硬件依赖的库行为由 `test_package/test_libserial.cpp` 消费者测试覆盖（8 个独立断言
用例，1 个程序）：SerialPort/SerialStream/SerialStreamBuf 默认构造处于关闭状态、
未打开端口调用 `SetBaudRate` 抛 `NotOpen`、对不存在设备 `Open` 抛 `OpenFailed` 且保持
关闭状态、失败的 `SerialStream::Open` 后流处于非 good 状态——后三条与上游
`test/unit_tests.cpp` 的无硬件断言同源。

## 探索性验证（设备端，2026-09-19）

1. 设备端下载源码包，SHA256 与本地一致（见上）。
2. OHOS clang 工具链原生 cmake 配置 + `cmake --build -j2`：一次通过，产物
   `libserial.a`（238,444 字节），仅编译警告（libc++ 弃用提示）。
3. `cmake --install` 安装到私有 prefix：`include/libserial/{SerialPort,SerialPortConstants,SerialStream,SerialStreamBuf}.h`
   + `Makefile.am`（上游 `install(DIRECTORY libserial)` 原样行为）、
   `lib/libserial.a`、`lib/pkgconfig/libserial.pc`。
4. 消费者程序 `test_libserial.cpp` 链接安装后的静态库，`binary-sign-tool` 签名后在
   设备实跑：8/8 PASS，退出码 0（日志 `run-consumer-20260919-r2.log`，sha256
   `2b6f2b2e4b8dff0c8e58d671466beee78634e9522becf693a5081f16d1666f89`）。
   注：首次实跑（`run-consumer-20260919.log`，8 行 PASS 但程序内成功提示字符串
   误写为 "7 checks"）后修正该提示字符串并重跑取证；断言逻辑从未变化，两次
   运行均为 8 行 PASS、退出码 0。

## 已知怪癖与如实披露

- 上游会把 `src/libserial/Makefile.am` 安装进 `include/libserial/`——
  `install(DIRECTORY libserial ...)` 无过滤，属上游行为，未修改。
- 上游默认同时构建静态库（`libserial_static` 无条件构建，注释说明单测需要它），
  `shared=False` 时包内只有 `libserial.a`；包为纯库（无 bin/），按 R38/L0k
  不需要 `commands.json`。
- `libserial.pc` 由上游 CMake 规则安装，`pkg_config_name=libserial` 与之一致。
- `package_info.libs=["serial"]`：文件名 `libserial.a` 对应链接旗标 `-lserial`。
- 每轮验证使用随机命名的私有 CONAN_HOME，上游 `libserial.pc.in` 以 `CMAKE_INSTALL_PREFIX`
  生成 `lib/pkgconfig/libserial.pc`，其 prefix 行逐轮变化（+0 -0 ~1 的基线差异）。
  2026-09-19 第二轮重验时按 conan-verify L5 自带指引删除 `reports/baseline.json`
  重立基线（语义等同首轮），制品差异仅此路径行，无实质内容变化。

## 交付口径

- 状态：`built`（finish/W3 验证通过、未 upload）；`published` 仅在合并进 main
  由 release 流水线实际上传后成立。
- PR 只包含 `archives/l/libserial/`（软件级 README.md、manifest.yaml 与
  1.0.0-git20250903/ 版本目录），不改 SUMMARY.md、archives/_index.yaml、
  他人归档或任何框架文件。

---

**编译结束**: 2026-09-19 02:53
**最终状态**: built
