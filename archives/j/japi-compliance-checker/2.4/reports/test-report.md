# japi-compliance-checker 2.4 测试报告（HarmonyOS PC 适配）

- 任务: 平台积分赛 #12626 · 分支 feat/japi-compliance-checker-2.4
- 日期: 2026-10-06
- 设备: HarmonyOS PC 真机（HAD-W32 / ARM64 / HarmonyOS 6.1.0）
- 工具链: Perl 5.44.0（Harmonybrew）+ BiSheng OpenJDK 17.0.13（~/bishengjdk17）
- 源码: lvc/japi-compliance-checker tag 2.4
  sha256 `0fd8ff8539a6f4a2c30379999befc1f9003fbb513f778b018a722360ab8c2229`
  （gh-proxy.com 与 ghproxy.net 双镜像交叉校验一致）

## 1. 上游测试（R51 三步法）

### 1.1 清点

上游无独立 tests/ 目录；回归套件内嵌于 `modules/Internals/RegTests.pm`
（入口 `-test`）：现场生成 libsample_java v1/v2 源码 → javac 编译、jar 打包 →
编译并运行 30 个 Test_*.java 运行时用例 → 以"检出 API break 数 ≥ 100"为
最终断言（README 声明 "about 100 basic tests in the test suite"）。

### 1.2 实测（真机）

```
$ PATH=~/bishengjdk17/bin:$PATH japi-compliance-checker -test
Using Java 17.0.13
...
Binary compatibility: 64%
Source compatibility: 58.1%
Total binary compatibility problems: 72, warnings: 27
Total source compatibility problems: 92, warnings: 6
Test result: SUCCESS (164 breaks found)      # 164 >= 100 → PASS
$ echo $?
0
```

Journal（libsample_java/Tests/Journal.txt）记录 30 个运行时用例：
16 个干净通过；14 个为设计内的不兼容触发用例（运行期抛
NoSuchFieldError / NoSuchMethodError 等，用以证明被检出的 break 真实存在，
属套件预期行为——最终判定以 ≥100 breaks 断言为准，实测 164，SUCCESS）。

该套件已内置入配方 build()（conan create 即实测，见 reports/conan-create.log
中 `Test result: SUCCESS (164 breaks found)` 与
`upstream -test tail` 日志段）。

### 1.3 结论

| 项 | 数值 |
|---|---|
| 上游测试套件 | 1 套（-test 内嵌回归套件） |
| 最终断言 | 检出 break 数 ≥ 100（实测 164）→ SUCCESS |
| 运行时用例 | 30（16 干净通过 + 14 设计内预期失败） |
| 真机退出码 | 0 |

## 2. conan-verify（G0–G4 + L2/L4/L5）

`ohc-run.py conan-verify japi-compliance-checker 2.4 --profile ohos-aarch64-device`

| 门禁 | 结果 |
|---|---|
| G1 配方完整性 | PASS |
| G2 conan create 干净构建 | PASS（含 build() 内上游 -test + test_package） |
| G3 系统同名库隔离 (R26) | PASS（包内无 .so） |
| G4 产物完整性 | PASS（bin/ + share/ + licenses/） |
| L2 smoke（--version） | PASS |
| L4 checksec | PASS（脚本工具，无 ELF 攻击面） |
| L5 产物基线 | PASS |

完整日志: `reports/conan-create.log`、`reports/conan-verify-report.md`（本地留档，不入仓）。

## 3. test_package 消费者测试（8/8 PASS）

test.sh 以真实 jar 对比验证已安装 CLI（R34；conanrun 环境 + JDK17）：

| # | 断言 | 结果 |
|---|---|---|
| A1 | --version 输出 "Java API Compliance Checker (JAPICC) 2.4" | PASS |
| A2 | JDK 工具链可达（javac/jar/java/javap） | PASS |
| A3 | 现场编译打包 v1/v2 测试 jar（v2 删除公有方法 removeMe） | PASS |
| A4 | 对比完成且生成 compat_reports/v/1_to_2/compat_report.html | PASS |
| A5 | 检出破坏："Binary compatibility: 66.7%"、"problems: 1"、退出码 1（上游契约） | PASS |
| A6 | 报告 HTML 包含被删方法名 removeMe | PASS |
| A7 | 负向对照 v1-vs-v1：100% 兼容、0 问题、退出码 0 | PASS |
| A8 | -dump 生成含 API_DUMP_VERSION 2.4 的 API dump | PASS |

（首次运行 A4 曾按"退出码必须为 0"断言而失败——上游契约是检出 break 时
退出码非 0（实测 1），已按上游语义修正断言；修正后 8/8。）

## 4. 真机手动验证证据

```
$ japi-compliance-checker --version
Java API Compliance Checker (JAPICC) 2.4
$ japi-compliance-checker v1.jar v2.jar
Binary compatibility: 66.7% / problems: 1 / Report: compat_reports/v/1_to_2/compat_report.html
$ japi-compliance-checker v1.jar v1.jar
Binary compatibility: 100% / problems: 0
$ japi-compliance-checker -dump v1.jar -dump-path api.dump
Dump path: api.dump   （含 API_DUMP_VERSION => '2.4'）
```

## 5. 本地 W3 CI（finish Step5 内置 build_and_test.sh）

- W2 原子性: PASS（12 文件=11 归档文件+本报告，仅配方变更，无框架文件）
- L0 质量门禁（含 L0p settings 四项 / junk check 增量模式）: PASS
- L1 test_package: PASS（8/8 断言）
- `.ci-result.json`: exit_code=0，integrity_hash=122cfb444e86db84，
  log_sha256=f2aeeadfb848455e3f3aec0fa1c50fb10dcc1ff0d32199b02a38b148e9e0fe8c
- 完整日志: reports/w3-local-ci.log（本地留档，不入仓）

注: 本地验证期间 conandata.yml 曾临时指向设备本地 HTTP 镜像（设备/本机
无法直连 GitHub，ghfast.top 注入已失效）；提交版为官方 GitHub URL
（sha256 双镜像交叉校验一致），远端 CI 由其 predl 镜像机制自行下载。

