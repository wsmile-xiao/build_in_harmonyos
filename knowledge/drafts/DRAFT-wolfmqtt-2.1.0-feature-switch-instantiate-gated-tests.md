# DRAFT-wolfmqtt-2.1.0-feature-switch-instantiate-gated-tests：用无依赖库特性开关实例化 AM_CONDITIONAL 门控的上游测试，并把特性宏同步进 consumer defines

> Contributor: pc1-15 | Status: Draft | Updated: 2026-09-19（r03 统计口径对齐同步）
> Source: wolfmqtt 2.1.0 适配（任务 wolfmqtt-2.1.0-r01/r02/r03-pc1-15）；触发场景：上游 2.1.0 引入真实测试套件，默认配置只实例化部分用例
> 对应：`knowledge/drafts/DRAFT-wolfmqtt-2.1.0-feature-switch-instantiate-gated-tests.kv`

## 现象

自动工具（autotools）上游把部分测试二进制挂在**库特性开关**的 AM_CONDITIONAL 条件块下：

```makefile
# tests/include.am（wolfmqtt 2.1.0）
check_PROGRAMS += tests/unit_tests              # 恒构建（307 声明）
if BUILD_SN
check_PROGRAMS += tests/test_mqtt_sn            # 98 用例
check_PROGRAMS += tests/test_mqtt_sn_client     # 26 用例
endif
if BUILD_BROKER
check_PROGRAMS += tests/test_broker_connect     # 54 用例
endif
```

默认 configure（上游默认 `ENABLED_SN=no`、`ENABLED_V5=no`、`ENABLED_BROKER=no`）只实例化
`unit_tests`。若配方照抄默认，双口径台账里大量源码声明用例会落在
`uninstantiated`，且本可直接运行的测试白白损失覆盖率。

区分两种门控语义（关键）：

| 门控来源 | 机制 | 处置 |
|---|---|---|
| **库特性开关**（--enable-sn / --enable-v5 / --enable-nonblock / --enable-mt / --enable-broker） | 门控的是库真实功能；测试目标与库功能 1:1 对应 | **开开关实例化**（无额外依赖、交付形态合规时）；开不了的如实 uninstantiated |
| **可选测试框架 autodetect**（AC_CHECK_CUTTER / PKG_CHECK_MODULES + AM_CONDITIONAL） | 门控的是第三方测试框架存在性 | 走 DRAFT-10251-libnfc-tools-autotools-test-framework-guard（补框架），不是开特性 |

## 根因

1. autotools 的 `if BUILD_X` / AM_CONDITIONAL 是"优雅降级"设计：特性关 → 对应测试目标
   根本不生成（`make check` 的 TOTAL 计数随之减少），configure/make 都不报错，退出码 0。
2. 默认配置 ≠ 最优配置：对**库型交付**，SN/V5/NONBLOCK/MT 这类特性开关无额外依赖、
   不产生 bin_PROGRAM（不翻转交付形态），照搬上游默认是"宁可少测"的保守选择，
   不是技术必需。
3. 特性开关一旦开启，库的公开头文件结构可能随特性宏变化（#ifdef 包住字段/枚举/
   函数）——若只开开关而不同步 `cpp_info.defines`，consumer 编译期拿不到宏，
   头文件布局与库 ABI 错位。
4. 同一 AM_CONDITIONAL 可能同时门控"库功能 + 测试二进制 + bin_PROGRAM（CLI）"，
   需逐一评估交付形态影响（见 broker 案例，r02 实证）。

## 方案（r01→r02 演进）

1. **判别门控语义**：读 `tests/include.am`/`configure.ac`，确认 `check_PROGRAMS +=`
   挂在 `if BUILD_SN` 这种**库特性 AM_CONDITIONAL**（而非测试框架 autodetect）下；
   用 `grep -nE 'if BUILD_' tests/include.am` 与 `grep -nE 'AM_CONDITIONAL' configure.ac`
   取证。
2. **只开无依赖、交付形态合规的库特性**：
   ```python
   tc.configure_args.append("--enable-sn")
   tc.configure_args.append("--enable-v5")
   tc.configure_args.append("--enable-nonblock")
   tc.configure_args.append("--enable-mt")          # r02 新增：无依赖（AX_PTHREAD 无条件探测）
   tc.configure_args.append("--enable-broker")      # r02 新增：见 broker 判定
   ```
   - 判据 A：该特性不需要新增 `self.requires()`/libevent 等外部依赖；
   - 判据 B：不产生 `bin_PROGRAMS`（否则库变 CLI，需 commands.json/签名链——R38/E424）；
   - r02 实证（broker 判定）：`--enable-broker` 虽产生 bin_PROGRAM src/mqtt_broker
     （CLI 型），但 ①libevent 配方在 ohpcd 可消费（`conan download --only-recipe`
     证据在案）；②上游 configure.ac **从不设置 $(LTLIBEVENT)**（无 AX_CHECK_LIBRARY/
     AC_CHECK_LIB 探测），src/mqtt_broker.c 无 event_* 引用 → **实际无硬链接依赖**；
     ③按 CLI 交付规则补 `archives/w/wolfmqtt/commands.json`（R38/L0k）即合规。
     → broker 可安全纳入，test_broker_connect 54 项中 50 项实例化。
3. **特性宏同步 consumer defines**（ABI 一致性）：
   ```python
   self.cpp_info.defines = ["ENABLE_MQTT_TLS", "WOLFMQTT_SN",
                            "WOLFMQTT_V5", "WOLFMQTT_NONBLOCK",
                            "WOLFMQTT_MULTITHREAD", "WOLFMQTT_BROKER"]
   ```
   验证：enable 后 `grep -nE '#ifdef (WOLFMQTT_V5|WOLFMQTT_SN|WOLFMQTT_MULTITHREAD|WOLFMQTT_BROKER)' <安装头>`，
   确认公开结构/枚举受宏影响；consumer 测试必须带同一组宏编译（test_package CMakeLists
   `target_compile_definitions`）。`cpp_info.bindirs=["bin"]` 声明 CLI 目录。
4. **重跑** conan create（`make check` 需在 build() 内执行以被 CI 记录），对比
   r-before/r-after 实例化数，回填双口径台账。
5. **集成脚本排除**（r02 新增）：`--enable-broker` 会连带注册 `scripts/broker.test`
   集成脚本（非用户 TEST() 用例，需 --enable-examples 示例二进制 + /bin/bash，OHOS 无），
   `make check` 用 `TESTS="tests/unit_tests tests/test_mqtt_sn tests/test_mqtt_sn_client
   tests/test_broker_connect"` 显式限定四 check_PROGRAMS（automake TESTS 覆盖），
   集成脚本列入台账但不计用户用例（R51 口径）。

## 验证（wolfmqtt 2.1.0 实证，r02 终值）

- 关闭 v5/nonblock（仅 --enable-sn）：unit_tests 193（packet 140 + client 44 + framework 9）+
  sn 98 + sn_client 13 = **304 例**；
- 开启 --enable-v5 --enable-nonblock：unit_tests 235（packet 170 + client 56 + framework 9）+
  sn 98 + sn_client 25 = **358 例**（多实例化 **54 例**）；
- r02 再开 --enable-mt --enable-broker：unit_tests 313（packet 245 + client 59 + framework 9）+
  sn 98 + sn_client 26 + broker_connect 50 = **487 例注册**（含 framework 9）；
- 最终双口径（r03 口径对齐）：source_declared_total=494（485 用户 + framework 自测 9，审查端全量口径）、
  configured_executable_total=487、executed_passed_total=487（用户 478 + framework 9）、失败 0、
  uninstantiated=7（用户用例互斥分支）；
  全量 487/494=98.58%，当前配置可执行集 487/487=100%（台账 reports/test-ledger.md）；
- r02e/finish_r02e conan create 全绿：make check 四 check_PROGRAMS 全 PASS，test_package 2/2
  （消费者 + 鸿蒙专项 test_ohos）；W3 本地 CI PASS（.ci-result.json exit_code=0）；
- 日志：adaptation_validation_r02e.log、finish_r02e.log、w3_build_and_test_r02d.log，
  上游用例日志在 `<conan build>/tests/{unit_tests,test_mqtt_sn,test_mqtt_sn_client,test_broker_connect}.log`。

## 剩余 uninstantiated（7 项，全部为真实互斥编译分支，非可纳入）

| 归属 | 数量 | 门控条件 | 原因 |
|---|---|---|---|
| test_mqtt_packet.c | 3 | `defined(WOLFMQTT_BROKER) && !defined(WOLFMQTT_V5)` | v3.1.1 专属 disconnect 解码用例；V5 已启用 → 互斥 |
| test_broker_connect.c | 3 | `#ifndef WOLFMQTT_BROKER_WILDCARDS` | no-wildcards 配置专属；上游默认 wildcards on → 互斥 |
| test_broker_connect.c | 1 | `!defined(WOLFMQTT_V5)` | v3.1.1 disconnect will 用例；V5 已启用 → 互斥 |

恢复条件：构建 WOLFMQTT_V5=off + wildcards=off 的第二配置可实例化这 7 项；当前单配置下
与已启用特性互斥，属上游互斥编译分支如实记录，非跳过（不修改分母、不伪写通过）。

## 适用边界

- autotools 库型包；上游测试目标挂在**库特性开关** AM_CONDITIONAL 下；被门控特性
  无额外依赖、或依赖可消费且交付形态合规（CLI 时按 R38 补 commands.json）。
- 头文件随特性宏变化时，cpp_info.defines 必须同步（本条目直接要求）。

## 反例与限制

- 特性引入外部依赖且不可消费、或交付形态合规性无法满足（如 broker 若真需 libevent
  且制品缺失）→ 不得为测而开，记 uninstantiated + 依赖证据，等待分析端绑定；
- 门控是测试框架 autodetect（cutter/check/cmocka）→ 不是本条目场景，走 libnfc 草稿
  （补框架），不得伪造 WITH_CUTTER=yes（R8）；
- 禁止改上游 tests/*.c / 禁止绕过 configure 守卫强行置真；
- 特性开关影响公开头/ABI 时，consumer 测试必须用同一宏集编译；
- 集成脚本（非用户用例）不得混入 TESTS 默认执行路径（automake TESTS 覆盖限定）；
- r02 调优教训：本地 W3 300s 窗口内完成全量 build_and_test.sh，需预热远端
  revisions 元数据（conan download 首次 67s → 缓存后 1s）与并行度 -j8，
  否则 L0i 探针 + 强制重建超出窗口（属环境调优，非知识本体）。

## 查重差异

- DRAFT-10251-libnfc-tools-autotools-test-framework-guard：同属"AM_CONDITIONAL 门控
  测试被静默排除"语义域 —— 但根因不同（可选测试框架 autodetect 缺失 vs 库特性默认关）、
  方案不同（补第三方框架 vs 开库特性开关+宏传播）、边界不同（框架补齐 vs 交付形态判定）。
- DRAFT-fast-cdr-2.3.5-upstream-test-enablement：CMake BUILD_TESTING FORCE OFF 形态
  （-D 注入 + GTest_DIR），构建系统与门控源不同。
- E231（discover-tests-from-verified-archive）：来源绑定与校验，非实例化策略。
- 其余（E007/E011/E490 等）为本轮复用的正式条目，不属本条。