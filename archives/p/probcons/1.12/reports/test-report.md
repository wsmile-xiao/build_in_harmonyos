# probcons 1.12 测试报告（R51 上游测试三步法 + 五维账本）

日期: 2026-09-25  执行: 主理-30（A 机原生 OHOS aarch64，clang 15.0.4）

## 一、上游测试清点
- 源码包 16 个文件全部为 .cc/.h/Makefile/README，**无 tests/ 目录**
- Makefile 无 check/test 目标（`make -n check` → No rule to make target 'check'）
- 结论: **上游自动化测试面 = 0**

## 二、可执行测试面（本适配提供）
test_package 消费者测试（test_probcons.py，conan create 内自动执行）:
1. `probcons --version` → rc=0，输出含 "1.12"（K0，2 断言）
2. `probcons --help` → rc=0，输出含 "Usage"（K0，2 断言）
3. 3 条蛋白质序列真实比对 → rc=0，3 记录头 + 3 残基行 + 残基字符合法
   （含 U，硒代半胱氨酸）+ 行等长（5 断言）

## 三、五维账本
| 维度 | 数值 |
|---|---|
| 静态测试总数（上游声明） | 0 |
| 可执行数（断言） | 9 |
| 实测通过 | 9 |
| 跳过 | 0 |
| 失败 | 0 |

## 四、W3 本地 CI 模拟判决（reports/w3-local-ci.log）
```
L0_RESULT=pass: all checks passed
L1_RESULT=pass: test_package executed
L2_RESULT=pass: compare version/help failed, makegnuplot failed, probcons --version OK, project failed
L4_RESULT=pass: patches clean
L5_RESULT=pass: bin/ has content
Build Summary: Success: 1, Failed: 0, Pass rate: 100.0% (1/1)
```
说明: compare/project/makegnuplot 为上游辅助工具，上游本身不支持 --version
（exit 1 属上游行为，未改动）；K0 只约束主命令 probcons（主命令名=包名，
--version/--help 均 rc=0）。

## 五、人工冒烟（探索期，~/builds/probcons-1.12.work）
- clang++ 直编 4 目标零错误（仅 -Wdeprecated-copy 警告，上游代码风格所致）
- FASTA 功能比对输出与上游语义一致（MFA 格式，rc=0）
