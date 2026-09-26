# zrc 2.7 测试报告

## 上游测试情况

上游 zrc 仓库（tag v2.7）**无测试套件**：Makefile 仅含 release / debug /
clean / install / help 目标，无 check / test 目标，源码树无 tests/ 目录。
上游验证由消费者 test_package 承担（与 jpnevulator 2.3.6 同模式）。

## conan create 台账

- 命令：`conan create archives/z/zrc/2.7 -pr:h=ohos-aarch64
  -pr:b=ohos-aarch64 --build=missing --user=ohpcd --channel=stable`
- 结果：RC=0，`Packaged 2 files: zrc, LICENSE`
- 明细日志：`reports/conan-create.log`

## W3 本地 CI 模拟（reports/w3-local-ci.log）

| 门禁 | 结果 | 说明 |
|------|------|------|
| G0 | pass | 干净构建风险评估 |
| KC / JC | pass | 知识/junk 检查 |
| L0 | pass | 全部检查通过 |
| L1 | pass | test_package 执行 |
| L2 | skip | 平台功能矩阵探测：zrc `--version` 按上游语义恒以退出码 1 结束（脚本路径 return stonum($status)，status 未更新时为 1），非产物缺陷 |
| L4 | pass | 无补丁，静态安全扫描干净 |
| L5 | pass | bin/ 有产物 |

## test_package 消费者测试（test_zrc.sh，8 项断言，8/8 PASS）

| # | 断言 | 结果 |
|---|------|------|
| 1 | --version 以 ≤1 容差退出（上游恒 1） | ok |
| 2 | --version stderr 输出横幅 `zrc v2.7` | ok |
| 3 | -c 单行 echo 内建输出正确 | ok |
| 4 | -c 命令替换 + expr 算术输出 42 | ok |
| 5 | 真实脚本执行（exit 0 收尾）退出码 0 | ok |
| 6 | 脚本输出含首节 `3 bottles of beer on the wall,` | ok |
| 7 | 脚本 do/while 递减至末节 `1 bottles of beer on the wall!` | ok |
| 8 | 脚本结束行 `done` | ok |

脚本改编自上游 examples/99bottles.zrc，覆盖 set 赋值、变量展开、
[inc] 算术、do/while 控制流与退出码语义。

## 通过率

- 上游测试用例通过率：0/0（上游无测试套件，如实申报）
- 新增测试用例通过率：8/8（100%）

## staging 验证

- verify-build：PASS（G1-G4 全过，`.verify-passed` 已写入 staging）
- `.staging-verified`: `verified=1 failed=0`（bin/zrc 可正常执行并输出
  `zrc v2.7` 横幅；--version 退出码 1 为上游定义语义，非运行缺陷，
  证据见上表第 1/2 项断言）
