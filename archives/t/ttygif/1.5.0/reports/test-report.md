# ttygif 1.5.0 测试报告（test_package 消费者测试）

**HEAD**: 0f85c0282de8f2a14f5272108e5841e3dd178635（W3 本地 CI 模拟执行版）
**执行方式**: conan create --build=missing + test_package/conanfile.py（conan test，含框架 L1e 破坏性负向二轮）
**执行时间**: 2026-09-26 01:49（设备 A 机，主理-61）

## 测试数字（五维账本）

| 维度 | 数量 |
|---|---|
| 上游测试总数（静态清点） | 0 |
| 总测试数 | 51 |
| 通过 PASS | 49 |
| 失败 FAIL | 0 |
| 跳过 SKIP | 2 |

- 账本不变式: DISCOVERED(51) = PASS(49) + FAIL(0) + SKIP(2)，由 test.sh 末尾自检行实测，不成立即判 FAIL
- 上游清点: `status=no_tests`（13 个文件无测试目录、`make -np` 无 check 目标、六类标记仅许可证
  文案与 2 处 libc assert），证据 `reports/upstream-test-scan.txt`
- 正式判决（reports/w3-local-ci.log）: `=== 汇总 discovered=51 pass=49 fail=0 skip=2 合计=51 ===`、
  `VERDICT: PASS`、`HMBS_TEST_PACKAGE_RESULT={"executed":true,"passed":true,"discovered":51,"passedCount":49,"skipped":2}`
- 上游侧: `HMBS_UPSTREAM_TEST_RESULT={"status":"no_tests","discovered":0,...}`
- 框架门禁: L1a test_package 已执行 ✅ / L1b 执行证据 ✅ / L1c 上游官方测试入口 ✅ / L1e 破坏性负向二轮 ✅

## 结论

✅ 通过（49/51 实测通过、0 失败、2 条带一手取证依据的 skip）

## 已知限制（skip 明细）

1. **E01 端到端 xwd 抓屏 ⇒ tty.gif**：需要活的 X display 与真实窗口 id——DISPLAY 实测为空，
   且 xwd 不在制品仓（`conan search xwd` → Recipe 'xwd' not found；`archives/x/xwd/1.0.9` 只有
   manifest/notes/patches，无 conanfile.py）。按 R36/PF4 不在本 PR 里补依赖，整条抓屏链如实
   登记为未执行，不伪造 GIF 断言。
2. **D06 XWD 帧写入与解码**：`identify -list format` 全表 XWD 行命中 0；convert 写 .xwd 聚合
   rc=1、把 .xwd 喂回 convert 解码 rc=1（NoDecodeDelegateForThisImageFormat）——已发布的
   imagemagick/7.1.2.29 不带 XWD coder，属依赖能力缺口，按红线不在本 PR 改别的包。

## 执行环境

- 设备: 鸿蒙 PC A 机（aarch64，HarmonyOS）
- CONAN_HOME: `~/tmp/ch/home-ttygif`
- 依赖: imagemagick/7.1.2.29（`requires(..., headers=False, libs=False, run=True)`）
- 日志: `reports/w3-local-ci.log`（正式 W3）、`reports/conan-create.log`（G2 create）、
  `reports/upstream-test-scan.txt`（上游清点）
