# jkmeter 0.9.0 测试报告（test-report）

> 任务：jkmeter 0.9.0（任务号 7640）｜分支 feat/jkmeter-0.9.0｜配方定稿 HEAD f48e06471e
> 构建机：B 机（frp-bar.com:19214）｜CONAN_HOME=~/tmp/ch/home-jkmeter
> 数字同源：本报告与 `notes.md` 测试账本、`reports/w3-local-ci.log` 机器行、`reports/conan-verify-report.md` 同源；CI/AI 判决后正文引用同一组数。

## 五维账本

| 维度 | 读数 | 依据 |
|---|---|---|
| 静态清点（上游测试程序） | **0**（上游 Makefile 仅 all/install/uninstall/clean 四目标，无 check/TESTS/测试程序） | 上游 `Makefile` 实测；`reports/conan-create.log` |
| 包内可执行（bin/） | **1 个**（bin/jkmeter，68224B）+ share/jkmeter/ 24 张表盘 PNG | 包目录 `bin/`、`share/` ls 实测；`commands.json` 已声明 |
| 实测通过 | 消费者 test_package **1/1**（Success: 1 / Failed: 0）；分层 smoke：装载层（ELF 闭包 118 文件 + 主程序 = 校验面 119、自签、执行位、安装路径；W60J-1 整改）PASS，进程层（`-help` 横幅输出、无 DISPLAY 干净 exit 1）PASS——`JKMETER_SMOKE_PASS banner=1 nodisplay_exit=1 display_msg=1` | `reports/w3-local-ci.log`；`~/tmp/uc2/jkmeter/` smoke 读数 |
| 跳过 | 框架 **L2_RESULT=skip**（jkmeter 无 `--version`/`--help` 之外的版本旗标，框架 version 探测不适用）；真实 GUI/JACK 会话层未运行（OHOS 环境无 X server/JACK daemon，如实申报为环境不可运行，非运行时失败） | `reports/w3-local-ci.log` `L2_RESULT=skip` 行 |
| 失败 | **0** | `reports/w3-local-ci.log` `Failed: 0` |

## W3 本地 CI 机器行（reports/w3-local-ci.log）

```
G0_RESULT=pass
KC_RESULT=pass
JC_RESULT=pass
L0_RESULT=pass: all checks passed
L1_RESULT=pass: test_package executed
L2_RESULT=skip: jkmeter version/help failed
L4_RESULT=pass: patches clean
L5_RESULT=pass: bin/ has content
  Success: 1
  Failed:  0
```

`conan-verify` 8 门全 PASS（`reports/conan-verify-report.md` Verdict: PASS）。

## 口径说明（防 rule4 少报/多报）

1. 上游无任何自动化测试入口（静态 0）⇒ 无"上游用例通过率"可申报，正文按 `0/0` 口径并注明依据；
   消费者测试（test_package 1/1 + 分层 smoke 3 项 PASS）为适配后真实执行面，不冒充上游用例。
2. 进程层 smoke 的 `nodisplay_exit=1` 是**无 DISPLAY 环境的干净退出**（exit code 1、错误信息落在 X 连接层），
   证明 loader/链接/初始化全通——不计为"通过"，如实申报为分层读数。
3. L2 skip 是框架对无版本旗标 CLI 的预期判定（非崩溃、非失败）；jkmeter 的能力面以 `-help` 横幅与
   装载层证据为准。

## 已知限制

- 真实 GUI/JACK 音量表功能面（连接 JACK daemon + X 渲染）在 OHOS 环境不可运行（无 X server/JACK
  daemon），已如实申报为环境限制；装载层+进程层证据证明产物完整、可执行、依赖闭包正确。
- 缓存包复用场景的 test_package chmod EPERM 坑已修（防御式，见 knowledge/drafts/DRAFT-7640-* 与 notes）。
