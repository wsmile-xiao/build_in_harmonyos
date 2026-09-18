# c_check 平台探测不一致记 CROSS=1 时，GotoBLAS 系 Makefile 静默跳过全部就地测试执行——设备原生构建的测试步骤需显式 CROSS=0 覆盖

slug: `ohos-gotoblas-cross-silent-skip`｜B【知识库扩展】次条（run liblapacke-0.3.30，Curator 判定 + Auditor CONFIRMED）｜2026-09-15

## 问题描述（规则陈述）

GotoBLAS 谱系（OpenBLAS、lapack-netlib 内嵌 TESTING 体系）在 OHOS 设备上**原生构建**（构建机=目标机）时，`c_check` 会因平台探测不一致写入 `CROSS=1`；上游 Makefile 用 `ifneq ($(CROSS),1)` 守卫全部就地测试执行，导致 `make test / ctest / lapack-test` **静默跳过且正常退出**（假 PASS）。设备原生构建的测试步骤必须命令行显式 `CROSS=0` 覆盖。

这是**静默型**问题：无任何错误输出，唯一特征是测试目标"秒退"且日志中没有 `run_test`/`----- PASS -----` 块。

## 根因（完整因果机理链，行号实测 0.3.30 构建树）

1. **CROSS=1 仅由 c_check 记录**（Auditor 修正点 a）：
   - `c_check:4`：`hostos=`uname -s | sed -e 's/\-.*//'`` → OHOS 设备上取值 `HarmonyOS`；
   - `os` 来自**编译器探针**：`c_check:40-67` 对 `$CC` 预处理输出匹配 `*OS_LINUX*` → `os=Linux`，`:506` 大写为 `OS_LINUX`；
   - `c_check:399` `cross=0` 起，`:409` `[ "$os" != "$hostos" ] && cross=1`，`:492` `printf "CROSS=1\n"`；
   - 产物落 `Makefile.conf`（本 run 实测 `Makefile.conf:6-7` = `CROSS_SUFFIX=/data/service/hnp/bin/` + `CROSS=1`）；
   - **`f_check` 不写 CROSS**（`grep CROSS f_check` 零命中）——任何"`f_check` 也写 CROSS"的理解都是错的。
2. **触发条件**（Auditor 修正点 b）：GotoBLAS 系在 OHOS 设备原生构建时，`uname -s=HarmonyOS` 与编译器探针 `OS_LINUX` 不一致 → 被误判为交叉编译（实为原生）。与 E064 的 conftest 弹窗超时误判同属"OHOS 原生被误判成 cross"家族。
3. **静默跳过点**：`Makefile:410` `ifneq ($(CROSS), 1)` 守卫 `lapack-test` 的 INSTALL 自检 + `lapack_testing.py` 执行段；`test/Makefile`（`:49/:109/:198/:270`）与 `ctest/Makefile`（`:84/:129/:181`）的就地执行门（run_test/blat）同理。`CROSS=1` 时 make 正常退出、无告警。
4. **归类**：构建系统语义（L1 平台/构建系统层；阻塞面=上游测试整体未执行）。

## 影响面

不覆盖则上游测试**整体**不执行而呈现"通过"——本 run 即 5,195,617 项 lapack-test 判定加 blat/ctest 全部为假 PASS。这是"测试执行门"级缺陷，优先于任何单条测试用例问题。

## 验证（自包含，2026-09-15 设备实测；新 shell 可复现）

```bash
cd <OpenBLAS 构建树根>          # 含 make.inc/Makefile.conf 的构建目录
grep ^CROSS Makefile.conf       # =1（误判产物）
make -n lapack-test CROSS=1 | grep -c lapack_testing.py   # =0：执行段被静默跳过
make -n lapack-test CROSS=0 | grep -c lapack_testing.py   # =1：执行段恢复展开
```

## 方案空间

| 层 | 方案 | 诚实权衡 |
|---|---|---|
| rec | 设备原生构建时，测试步骤命令行显式 `CROSS=0`（只覆盖测试执行判定变量，不改构建语义/上游）；`make -n` 对照留证 | 仅对"原生被误判"合法；需在交付记录注明"设备原生构建"前提 |
| fallback | 若主编判定为 GotoBLAS 谱系私有、不够平台通用 → 按预案降级投递经验仓 build-system/platform-detect 分类（ci-experience-policy），申报位让出、知识不丢失 | 投递位置变化，条目内容不变 |
| forbid | ① 禁改 c_check/hostos 探测逻辑或手改生成的 Makefile.conf 来"消除"CROSS=1；② 禁在真交叉构建（构建机≠目标机）盲目 `CROSS=0` | ① 破坏上游探测语义、污染其他目标；② 可执行在构建机无法运行，同样假结果 |

## 泛化边界（Auditor 修正点 c）

如实划定：本条机理实证于 **GotoBLAS 谱系**（OpenBLAS/lapack-netlib）；`ifneq ($(CROSS),1)` 静默门为该谱系 Makefile 惯例。其他构建体系的 CROSS 类变量语义各异，未实证前不外推。

## 参考

- principles：P-AUTOTOOLS-002（平台探测误判族）、P-BUILD-001
- similar_to：E064（conftest 无法执行被误判为交叉编译）
- 姊妹条：`DRAFT-ohos-flang-driver-link-overlay`（可执行链接打通在前，本条解决就地执行门）
- 证据：run liblapacke-0.3.30（Makefile.conf 实测 CROSS=1；`make -n` 对照 0/1；覆盖后 5,195,617 项真实判定）

---

**草稿状态**：待主编审核后提升为正式条目（最终 Exxx 编号由知识库主编确认）
**最后更新**：2026-09-15
