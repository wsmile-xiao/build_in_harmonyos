# wmtop 0.85 功能测试报告

**日期**: 2026-09-27
**平台**: HarmonyOS PC (OHOS, aarch64)
**构建方式**: Conan 2.29.1 (OHOS adapted) + Autotools（perl 直调 aclocal/automake 自举 + sh 执行 configure）
**Profile**: ohos-aarch64 (os=OHOS, os.version=6.0, arch=armv8, compiler=clang 15)
**依赖**: libdockapp 0.7.3、libx11 6.4.0、libxext 6.4.0、libxpm 3.5.17（全部远端二进制消费，R36 无阻塞）

## 上游测试用例统计（R51）

| 测试类型 | 用例数 | 证据 |
|----------|--------|------|
| `make check`（实际执行） | 0 | 原始输出 `make: Nothing to be done for 'check'.`（logs/21:193） |
| `TESTS`/`check_PROGRAMS` | 0 | Makefile.am 未声明；无 tests/ 目录；configure.ac 无测试宏 |
| **合计** | **0** | 上游确无自动化测试（清点结论，非环境结论） |

## 适配后测试统计（test_package 消费者测试）

| # | 测试 | 描述 | 结果 |
|---|------|------|------|
| 1 | wmtop on PATH | VirtualRunEnv 暴露包 bin 目录 | ✅ PASS |
| 2 | wmtop executable | 安装产物可执行 | ✅ PASS |
| 3 | ELF AArch64 | 目标机 ISA 正确 | ✅ PASS |
| 4 | ELF64 | ELF 类正确 | ✅ PASS |
| 5 | `wmtop -v` exit 0 | 版本路径（无 X11 依赖） | ✅ PASS |
| 6 | `wmtop -v` 输出 | 报告 `wmtop v0.85` | ✅ PASS |
| 7 | `wmtop -Z` exit 0 | 未知选项进入 usage 路径 | ✅ PASS |
| 8 | usage banner | 输出上游 WMtop 横幅 | ✅ PASS |
| 9 | LINUX-only `-m` 行 | configure.ac 的 linux* 分类在 OHOS 生效 | ✅ PASS |
| 10 | `-a 99` exit 1 | 参数越界校验 | ✅ PASS |
| 11 | `-x` exit 1 | 缺操作数校验 | ✅ PASS |
| 12 | `-disdisplay` exit 1 | 拼错选项校验 | ✅ PASS |
| 13-16 | DT_NEEDED 链 | libdockapp.so / libX11.so / libXext.so / libXpm.so | ✅ PASS |
| 17 | 无 RPATH/RUNPATH | 可重定位安装 | ✅ PASS |
| 18 | man page | share/man/man1/wmtop.1 就位 | ✅ PASS |
| **HMOS-USECASE** | **鸿蒙消费者执行用例**（非断言） | gated on HarmonyOS 内核；端到端启动已安装 wmtop（无参数），运行时完整解析共享库链、执行到 libdockapp X11 初始化，以程序自身干净的 "can't open display"（exit 1）退出；动态链接器失败(127)/崩溃(≥128)均判 FAIL | ✅ PASS |

**通过**: 19/19 | **失败**: 0/19（18 条断言 + 1 条鸿蒙执行用例）

## 鸿蒙特有测试说明

test.sh 第 8 节为 HarmonyOS 特有消费者用例：`uname` 仅作运行前置条件（gate，非被测项、非断言）；
用例本体是**执行型**测试——真实启动安装后的 wmtop 二进制，验证其在 HarmonyOS 上的
消费者可行性（动态依赖运行时解析 + dockapp 初始化路径可达）。测试日志：
`reports/conan-create.log`（conan create 内嵌 test_package 运行）与
`test_package/test.sh`。

## 测试环境

- Conan 2.29.1 (OHOS 适配版)，隔离 CONAN_HOME
- Profile: ci/conan/profiles/ohos-aarch64
- 原始日志（仓库外索引，见 notes.md）: `~/ohc-work/wmtop-0.85/logs/`
  - 31-conan-create-fixed.log（最终构建 + test_package 全绿）
  - 33-verify-fixed.log（conan-verify G0-G4 PASS）
  - 34-finish-final.log（finish 管线 W2/W3）

## 结论

wmtop 0.85 在 HarmonyOS PC 上构建、安装、消费者运行全部通过；上游无自动化测试
（0 用例），test_package 以 18 条断言 + 1 条鸿蒙执行用例覆盖消费者可行性。
