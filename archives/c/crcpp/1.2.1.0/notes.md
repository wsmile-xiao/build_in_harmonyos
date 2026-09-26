# crcpp 1.2.1.0 适配笔记

## 库简介

CRC++（d-bahr/CRCpp）——header-only 单头文件 C++ CRC 计算库，交付物只有
`inc/CRC.h` 一个头 + `LICENSE`。支持逐位/查表、multipart 续算、非 8 位整倍数
输入（`CalculateBits`）、任意位宽；预置 CRC-32/16/8/64 等定义（小众定义在
`CRCPP_INCLUDE_ESOTERIC_CRC_DEFINITIONS` 宏后）。零依赖、无编译产物。

## 编译环境

- 构建系统: header-only（`package_type = "header-library"` + `implements = ["auto_header_only_mode"]`）
- 编译日期: 2026-09-25
- 编译器: clang 15 / clang++（OHOS SDK）
- 状态: built（conan-verify + W3 本地 CI 通过，未 upload）

## 编译步骤

本包无编译交付物；`conan create` 的两个执行面：

1. **`build()` = 上游测试集成（R51）**：在 build 目录复刻 `inc/`、`test/src/`、
   `test/prj/gcc/` 相对结构（保持 source 目录只读），驱动上游原生 Makefile：
   `make -C test/prj/gcc CXX=<clang++> LINKER=<clang++> LDFLAGS="-Wall -static-libstdc++"`
   → 运行 `test/prj/gcc/bin/unittest`。只覆盖编译器名与链接选项，测试源与宏定义
   与上游字节一致（`-DCRCPP_INCLUDE_ESOTERIC_CRC_DEFINITIONS` 由上游 Makefile
   默认给出，与上游 CI `make -C test/prj/gcc` 同口径）。
2. **`package()`**：`copy CRC.h → include/`、`copy LICENSE → licenses/`。
3. **`test_package`**：CMake 消费者 `test_crcpp.cpp`，`find_package(crcpp)` 后
   `#include <CRC.h>` 真实调用 API 并断言。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | conan-init 默认给 Autotools 模板（含 `AutotoolsToolchain`/`cpp_info.libs=["crcpp"]` 占位） | registry 无 crcpp 条目（新包），模板回退猜 autotools | 手写 header-only 配方（参照 compile-time-regular/3.11.0 先例） |
| 2 | 上游无测试框架，只有 `test/src/main.cpp` 自研程序；用例由宏声明且部分在 `#ifdef CRCPP_INCLUDE_ESOTERIC_CRC_DEFINITIONS` 区 | 按源码宏数申报（62）会与断言实测（242）差 180 → rule4 少报 | ifdef 感知清点：59×4 + 3×2 = **242**（esoteric on，候选数法取最大）；宏数 62 作为次口径写说明 |
| 3 | unittest 全过时 stdout/stderr 皆空、rc=0，没有任何 "N tests passed" 汇总行 | 只看 rc=0 会漏"提前退出"假绿 | 判绿双条件：`rc==0` ∧ stderr 无 `Invalid CRC` 行（失败才打印），`build()` 内抛异常拦 G2 |
| 4 | 设备无 `g++`（上游 Makefile 写死 `CXX=g++`/`LINKER=g++`） | 设备只有 clang 15 | make 命令行覆盖 `CXX`/`LINKER`（不改上游 Makefile） |
| 5 | 测试二进制默认动态链接 `libc++_shared.so`，conanrun 环境不含 SDK 库路径时 rc=127 | `compiler.libcxx=libc++` 动态链接 | `LDFLAGS += -static-libstdc++`（build() 与 test_package 各一处），readelf 实测 NEEDED 只剩 `libc.so` |

## 源码修改

无补丁（`patches: []`）——上游测试源、头文件零改动。

## 依赖版本

无（header-only，零依赖；W0 硬依赖面为空，无需 `conan list` 前置）。

## 验证结果

```bash
# 上游测试（配方 build() 内，conan-create 干净轮日志可核）
[upstream-tests] 清点 test/src/main.cpp: CRC_TEST=59 (common 13 + esoteric 46),
                 CRC_PARTIAL_BYTE_TEST=3; esoteric on 断言=242, esoteric off 断言=52
[upstream-make] clang++ ... -c -o obj/main.o ../../src/main.cpp   # rc=0
[upstream-tests] RUN rc=0, stderr 无 'Invalid CRC' 行 → 242/242 断言通过

# 消费者测试（test_package，鸿蒙特有测试行）
[consumer] PASS CRC.h self-reported version == 1.2.1.0    got=0x01020100
[consumer] PASS CRC-32/ISO-HDLC bitwise                   got=0xCBF43926
...
[consumer] summary: 13/13 assertions passed (runtime), compile-time static_assert=1
```

计数口径（四口径分列，不混用）：

| 口径 | 数值 | 归属 |
|------|------|------|
| 源码宏数（次口径） | 62（59 CRC_TEST + 3 CRC_PARTIAL_BYTE_TEST） | 说明列 |
| 上游断言数（申报 N） | 242（esoteric on） | 上游用例表 |
| 消费者断言数 | 13（+1 编译期 static_assert 单列） | 鸿蒙特有测试行 |
| test_package 程序数 | 1 | 附注 |

## 交付物

| 文件 | 说明 |
|------|------|
| `include/CRC.h` | 单头交付件（上游 `inc/CRC.h` 原样） |
| `licenses/LICENSE` | 上游 BSD 许可证 |

## 注意事项

- header-only 形态：conan-verify 的 G4/L2/L4/L5 走「跳过」分支（包内无 bin/、无
  lib/*.so）——按 device-facts §二.17 人工补测写 `reports/conan-verify-supplement.md`
  （产物清单↔package_info、消费者真跑、消费者二进制 readelf、交付件 sha256）。
- **header-only 交付形态·消费者须按 device-facts §二人工补测**：不能只跑包内自测，
  消费者面读数见上文验证结果与 PR 正文。
- 知识草稿：`knowledge/drafts/E740-crcpp-header-only-unittest-assertion-counting.{kv,md}`
  （manifest `knowledge_gained` 行尾 `# knowledge_ref: E740`）。
