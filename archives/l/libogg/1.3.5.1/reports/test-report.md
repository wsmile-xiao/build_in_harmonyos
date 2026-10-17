# libogg 1.3.5.1 测试报告

> 所有数据均为本轮在 OpenHarmony PC（HarmonyOS aarch64，triplet `aarch64-linux-ohos`）真机实测结果。

## 一、测试环境

| 项目 | 值 |
|------|-----|
| 目标平台 | OHOS (HarmonyOS PC) / aarch64 / Release |
| 编译器 | clang 15.0.4（`/data/service/hnp/bin/clang`） |
| Conan | 2.29.1（OHOS 适配版），profile `ohos-aarch64` |
| 上游源码 | libogg-1.3.5.tar.gz，sha256 `0eb4b4b9…b664` |
| 源码修改 | 无（未引入任何 patch） |

## 二、上游测试用例清点

清点方式：对上游 tarball 全文检索 `add_test`、`enable_testing`/`include(CTest)`、`tests/` 目录，并交叉核对 `src/Makefile.am`。

| 来源 | 位置 | 用例 |
|------|------|------|
| CMake 路线 | `CMakeLists.txt` → `if(BUILD_TESTING)` | `test_bitwise`、`test_framing` |
| Autotools 路线 | `src/Makefile.am` → `check_PROGRAMS` | 同上两个（同一批，非新增） |
| tests/ 目录 | 上游不存在 | — |

**上游独立用例数 = 2**

两个程序均以 `-D_V_SELFTEST` 从各自的 `.c` 编译（来源见 `MANIFEST.yml`），自包含、不链接库——与上游 `add_test()` 目标的定义完全一致。

> 重要：直接运行 `ctest` 会发现 **0 条**用例，因为上游 `BUILD_TESTING` 默认为 OFF。因此本适配不走 ctest，而是在 `build()` 内用相同的源文件、宏定义与头文件布局显式编译并**直接执行**两个程序，取真实退出码作为结果。

## 三、上游用例实测结果

```
+ clang -O2 -Wall -fPIC -D_V_SELFTEST src/bitwise.c -o tests/test_bitwise
+ clang -O2 -Wall -fPIC -D_V_SELFTEST src/framing.c -o tests/test_framing

HMBS_UPSTREAM_TEST_RESULT={"status":"passed",
  "framework":"official-selftest-programs",
  "discovered":2,"executed":2,"passed":2,"failed":0,"skipped":0}
```

| 用例 | 结果 |
|------|------|
| `test_bitwise` | PASS（rc=0） |
| `test_framing` | PASS（rc=0） |
| **合计** | **2/2，通过率 100%** |

**反例（可证伪性校验）**：同一 runner 下编译一个 `return 1` 的桩程序，必须被判为失败。
本轮实测该桩被正确识别为红灯，证明「全部通过」不是空转结果。

## 四、安装后包测试（新增补全）

`test_package/test_package.c` 是一个完整消费者程序：编译、链接、运行三步都针对**已安装的产物**（头文件 + 库），验证真实可消费性。

流程：初始化流 → 灌入一个 packet → flush 成 page → 交给第二个流解码 → 逐字节比对还原结果。

```
CHECK 1 OK: ogg_stream_init (encoder)
CHECK 2 OK: ogg_stream_packetin + ogg_stream_flush
CHECK 3 OK: ogg_stream_pagein + ogg_stream_packetout
CHECK 4 OK: payload round-trip identical (22 bytes)
libogg installed-package round trip passed (4/4 stage lines)

HMBS_TEST_PACKAGE_RESULT={"executed":true,"passed":true,"discovered":1,"passedCount":1}
```

判定条件为「退出码 0 **且** 4 条 CHECK 行齐全」，因此空输出桩无法伪造通过。
4 个阶段共享同一进程命运，按 **1 个集成流**计。

| 测试 | 结果 |
|------|------|
| 安装后包往返（含 4 个阶段） | **1/1，通过率 100%** |

## 五、汇总

| 类别 | 用例数 | 通过 | 通过率 |
|------|-------|------|--------|
| 上游用例 | 2 | 2 | 100% |
| 新增补全（鸿蒙安装后验证） | 1 | 1 | 100% |

- 编译状态：通过
- conan-verify 八道门禁：G0 / G1 / G2 / G3 / G4 / L2 / L4 / L5 全部 PASS
- 上游测试用例是否被修改：**否**（源文件、编译定义、include 布局均与上游一致）
- 是否补全了上游没有的测试：**是**（新增安装后消费者端到端验证，见第四节）
