# otpw 1.5 测试报告（test_package 消费者测试）

**HEAD**: 12fbee3c8c8067e62c53332c9cb120c9bf199383（W3 本地 CI 模拟执行版）
**执行方式**: conan create --build=missing + test_package/conanfile.py（conan test，含框架 L1e 破坏性负向二轮）
**执行时间**: 2026-09-26 02:5x–03:0x（设备 A 机，主理-61）

## 测试数字（五维账本）

| 维度 | 数量 |
|---|---|
| 上游测试总数（静态清点） | 0 |
| 总测试数 | 19 |
| 通过 PASS | 19 |
| 失败 FAIL | 0 |
| 跳过 SKIP | 0 |

- 账本不变式: DISCOVERED(19) = PASS(19) + FAIL(0) + SKIP(0)，由 test.sh 末尾自检行实测，不成立即判 FAIL
- 上游清点: `upstream_tests_exist: false`（17 文件无测试目录、裸 Makefile 无 check 目标、
  唯一 `test-login:` 目标是 ssh 回环手工验证指引），证据 `reports/upstream-test-scan.txt`
- 彩排与本轮判决: `=== 汇总 discovered=19 pass=19 fail=0 skip=0 合计=19 ===`、`VERDICT: PASS`、
  `HMBS_TEST_PACKAGE_RESULT={"discovered":19,"passedCount":19,"skipped":0}`（reports/w3-local-ci.log）
- 框架门禁: L1a test_package 已执行 ✅ / L1b 执行证据 ✅ / L1c 上游官方测试入口 ✅ / L1e 破坏性负向二轮 ✅

## 结论

✅ 通过（19/19 实测通过、0 失败、0 跳过——全部断言均真执行打包二进制且环境无关）

## 测试面构成（19 条）

- A 产物面（3）: otpw-gen 存在且可执行、ELF magic、TARGETS 裁剪生效（包内无 pam_otpw.so/demologin）
- B usage/坏参数（4）: `-h` 缺参数、`-s 0`、`-e 8`（熵下限 30）、`-p 99`（未知编码）——均断言 rc=1 与错误文案
- C `-r` 建议路径（3）: rc=0、输出非空、两段式随机密码
- D 正向生成端到端（8）: `-f` 哈希文件 + stdin 喂 prefix password + `-e 30`——页头 "OTPW list generated"、
  三位编号行、`-h 5` 行数、哈希文件非空、两次生成哈希不同（随机性）、`-p 1` 英文单词编码、
  两次密码不一致拒绝生成（not identical，rc=1）
- E `-o` 印刷顺序模式（1）: rc=0 且编号行在

## 已知限制

- 无。19 条断言全部在本轮 W3 模拟中真实执行通过（无环境相关 skip：`-f` 路径绕过
  /etc/passwd 查询，熵走 /dev/urandom，均与主机用户数据库无关）。

## 执行环境

- 设备: 鸿蒙 PC A 机（aarch64，HarmonyOS）
- CONAN_HOME: `~/tmp/ch/home-otpw`
- 依赖: 无 conan 依赖（纯 C 裸 Makefile，零第三方库）
- 日志: `reports/w3-local-ci.log`（正式 W3）、`reports/conan-create.log`（G2 create）、
  `reports/upstream-test-scan.txt`（上游清点）
