# 测试报告 — fixed-point-fundamentals 1.0.0

## 上游测试
- 上游无独立测试框架（无 tests/、src/tests/、ctest 注册；make test 扫描的 lessons/<lesson>/src/tests 全仓库不存在，实例化 0 用例）
- 17 个示例程序（examples）作为可运行入口，全部编译并逐一运行验证：17/17 exit=0、输出非空
- 全量枚举台账见 reports/knowledge-candidate-ledger.md（17 项逐条列出）

## test_package（消费者验证）
- test.sh：运行安装产物 q16_16_basics（51 行输出）、format_selector（164 行输出），exit=0 ✓
- ohos_test.sh（OHOS 专项）：4 项确定性断言（重复运行输出 SHA256 逐位一致）+ 4 项关键数值断言
  （Q16.16 +1→raw 65536、Q16_16_HALF、格式清单 Q16.16、浮点累加漂移演示）全部通过 ✓

## 门禁
- conan-verify：G0-G4 + L2/L4/L5 全过（可标记 published）
- W3 本地 CI：L0-L5 全过（.ci-result.json exit_code=0）
- W4 Pre-PR 审计：verdict=pass（P0=0/P1=0）
