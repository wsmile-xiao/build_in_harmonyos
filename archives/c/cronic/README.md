# cronic

cronic 是一个 cron 任务输出包装脚本（bash 实现）。它把一条命令包起来执行，
只有当该命令**失败**或产生**非空 stderr 输出**时才输出一份报告（命令行、结果码、
错误输出、标准输出），否则完全静默。这样 cron 只在真正出错时发邮件，避免
cron 把每次运行的正常输出都当成"有事发生"而反复发送邮件。

- 上游：http://habilis.net/cronic/ ；源码镜像：https://github.com/justincase/cronic
- 许可证：Public Domain / CC0-1.0

## 交付内容

- `bin/cronic`：上游 bash 脚本原样安装（854 字节，未修改）。
- `share/doc/cronic/README.md`：上游说明文档。
- `licenses/LICENSE`：上游 CC0-1.0 许可证正文。

上游归档为扁平结构（仅 `LICENSE`、`README.md`、`cronic` 三个文件），**没有构建系统、
没有编译单元、没有上游测试套件**，因此本包没有编译步骤。

## 使用

把命令交给 cronic 执行即可：

```sh
cronic backup
# 等价于在 crontab 中：
# 0 1 * * * cronic backup
```

cronic 自身始终以 0 退出（它是报告包装器，不转发被包装命令的退出码）；判断是否
出错请看它是否产生了报告。

## 运行时依赖

`bash`、`grep`、`mktemp` 三个系统工具，**不是 Conan 包**，因此配方没有
`requires`/`tool_requires`。在 HarmonyOS PC 上 bash 位于 `/data/service/hnp/bin/bash`
（已在 PATH 中），系统没有 `/bin/bash`，所以调用时应显式使用
`bash <pkg>/bin/cronic ...`，不要依赖 shebang 与执行位。

## HarmonyOS 适配

- 纯脚本包，与 CPU 架构/编译器无关，`package_id` 已清空。
- HMDFS 上 chmod 可能被忽略、执行位不可靠，因此配方虽尽力 `chmod 0755`，但**不依赖**
  执行位：test_package 与调用方都通过 `bash <脚本>` 显式解释执行。
- 鸿蒙专项测试：`test_package/test_cronic_ohos.sh` 覆盖 6 类鸿蒙运行时约束（无 `/bin/bash`
  时的 shebang 基线、HMDFS 执行位归一化、只读 `/tmp` 的 TMPDIR 依赖与 `mktemp` 清理、
  UTF-8 与含空格路径、HNP bash 兼容、只读 `/tmp` 陷阱），共 14 条断言；连同通用语义
  6 条断言，test_package 合计 **9 用例 / 20 断言**（详见版本目录 `notes.md` 与
  `reports/test-report.md`）。
- 版本：上游将该版本标注为 "Cronic v3"，且无点分版本、无 git tag。Conan 2.x 的
  RecipeReference 校验要求版本 ≥2 字符，单字符 `cronic/3` 会在 export 阶段被拒
  （`Invalid package version '3'`）。按仓库既有先例（`archives/c/cutmp3/4`、
  `archives/r/rapidhash/3`），归档目录保留任务卡的 `3`，制品版本由 `set_version()`
  取上游标签 `v3`。

## 版本

| 版本 | 制品引用 | 上游版本 | 状态 |
|------|----------|----------|------|
| 3 | `cronic/v3` | v3 | built |

## 参考资料

- 官网：http://habilis.net/cronic/
- 源码：https://github.com/justincase/cronic
- 许可证：http://creativecommons.org/publicdomain/zero/1.0/
