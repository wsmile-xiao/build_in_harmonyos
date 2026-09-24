# test-report — ppmd 20050811

> 数据来源：最终设备日志（干净采信轮 + finish 内嵌 W3 本地 CI 模拟，二者
> `conan create` 均为清缓存后干净构建）。统计单位：test_package 消费者断言
> （test.sh 的 check 调用）；上游测试单独计数（上游确无测试设施）。

## 测试统计（TOTAL = PASS + FAIL + SKIP + NOT_RUN）

| 类别 | TOTAL | PASS | FAIL | SKIP | NOT_RUN | 取数命令 |
|---|---|---|---|---|---|---|
| 上游测试 | 0 | 0 | 0 | 0 | 0 | 上游 tarball 清点：11 个条目无测试文件、Makefile 无 check 目标（见 test_package/MANIFEST.yml） |
| test_package 消费者断言 | 23 | 23 | 0 | 0 | 0 | `grep -n "TOTAL:" archives/p/ppmd/20050811/reports/conan-create.log` → `TOTAL: 23  PASS: 23  FAIL: 0` |
| **合计** | **23** | **23** | **0** | **0** | **0** | — |

通过率：23/23（100%）；上游测试：0/0（不适用——上游 0 个可运行测试入口）。

## conan-verify 门禁（同一 SHA 干净轮）

| 门禁 | 结果 | 证据 |
|---|---|---|
| G0/G1 | PASS | reports/conan-verify-report.md |
| G2 conan create | PASS | reports/conan-create.log（`Apply patch` × 6、`RUN: make`、Package folder） |
| G3 R26 | PASS | 无 lib/（纯可执行包） |
| G4 | PASS | bin/ 1 个文件（bin/ppmd） |
| L2 smoke | PASS | `ppmd --version` rc=0；test_package 23/23 |
| L4 checksec | PASS（1 条解析误报） | readelf 实证 GNU_STACK=RW（NX 启用）、DYN+PIE、BIND_NOW（RELRO full），见 reports/conan-verify-supplement.md §3 |
| L5 基线 | PASS | bin/ppmd sha256 76fcdea0012d087a24521a13159b23032f202175cb0d0557d0498c50c2ef45f0，与纯净树 6 补丁链构建逐字节一致 |

## 非 PASS 项归因

无 FAIL / 无 SKIP / 无 NOT_RUN。唯一告警为 L4 "NX=disabled"，经
llvm-readelf 逐字段反证为门禁解析误报（GNU_STACK 行下一行为 NOTE 段），
详见 reports/conan-verify-supplement.md。

## 上游测试清点声明（R51）

上游确无测试设施：tarball 仅含 PPMd.cpp、Model.cpp、Coder.hpp、SubAlloc.hpp、
PPMd.h、PPMdType.h、Makefile、ppmd.1、read_me.txt、README-PACKAGE（10 个文件
+ 1 个顶层目录条目）；Makefile 无 check/test 目标；源码树无 test 目录、无
*test* 文件、无断言宏使用。声明 N=0，下界（上游当前 HEAD 注册项）= 0。
鸿蒙特有测试 23 项单列，不混入上游分母。
