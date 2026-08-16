# activity-aware-firefox 0.4.2+git20250816.c6082f37 测试报告

## 测试环境

| 项目 | 内容 |
| --- | --- |
| 评估日期 | 2026-08-12 |
| Conan | 2.29.1（仓库 OHOS 适配版） |
| 目标设置 | `os=OHOS`、`os.version=6.0`、`arch=armv8` |
| 构建机 | Windows x86_64 |
| 功能测试 Shell | Git Bash 5.3，直接调用 Conan 缓存中的实际打包脚本 |

## 上游测试审计

上游源码只有 `activityfirefox` 与桌面入口等运行文件，未提供 `test`、
`tests`、CTest、Meson test、Autotools `make check` 或其他自动化测试套件。
因此上游用例数为 `0`，通过率记为 `0/0（N/A）`，不写成 `100%`。

## 构建和打包验证

执行：

```powershell
conan create archives/a/activity-aware-firefox/0.4.2+git20250816.c6082f37 `
  -s:h os=OHOS -s:h os.version=6.0 -s:h arch=armv8 `
  -s:b os=Windows -s:b arch=x86_64
```

结果：

```text
Full package reference:
activity-aware-firefox/0.4.2+git20250816.c6082f37
#9a07cea5fd7bf48a91027b650df0389a
:fc3eeb021243959114a0318489539cad6d087e28
#0519d27386be903d3dcb8ebce0bc7414
```

配方下载并校验上游源码、应用仓库生成的补丁、检查可移植 provider 标记，
并打包 `bin/activityfirefox`、desktop 文件和 MIT-0 许可证。由于 host 为
OHOS/arm64、build 为 Windows/x86_64，Conan 的运行阶段按交叉构建规则跳过，
没有把该跳过计为功能通过。

## 新增功能测试

随后从上述 package revision 的缓存目录取出实际 `bin/activityfirefox`，执行：

```bash
bash test_activity_context.sh /path/to/conan/package/bin/activityfirefox
```

输出终态：

```text
PASS: portable provider and Firefox profile flow assertions=14/14
```

14 项断言覆盖：

1. 显式 provider 解析；
2. 活动 ID 保持；
3. 活动名称保持；
4. profile key 的确定性生成；
5. 只有 ID、没有名称时拒绝；
6. 拒绝 `../escape` 路径穿越 ID；
7. 拒绝含空格的不安全 ID；
8. 首次运行创建 template profile；
9. 首次运行创建活动 profile；
10. 创建命令使用预期 profile 名；
11. Firefox 启动选择预期 profile 路径；
12. Firefox 参数被原样转发；
13. 再次运行复用已有活动 profile，不重复创建；
14. 再次运行继续选择同一 profile，且没有未解析目录错误。

测试使用隔离的临时 `HOME` 和记录调用参数的 Firefox 测试替身；被测对象始终
是 Conan 产生的实际包内脚本，不是源码目录副本，也不是只检查 `--help` 的
空壳测试。

## 统计结果

| 状态 | 数量 |
| --- | ---: |
| 总测试数 | 14 |
| 通过（PASS） | 14 |
| 失败（FAIL） | 0 |
| 跳过（SKIP） | 0 |

- 上游测试用例通过率：`0/0（N/A，上游无自动化测试）`
- 新增测试用例通过率：`14/14（100%）`
- 构建状态：通过

## 已知限制

1. 当前功能测试验证 wrapper 的上下文解析、profile 创建/复用、路径选择和参数转发；没有把真实 Firefox GUI 会话计入通过数。
2. OpenHarmony 调用方仍需提供稳定的 workspace/context ID 和名称，并保证目标环境具有 Bash 与 Firefox。
3. 公开提交后仍须以项目 OHOS runner 的 CI 结果作为最终验收结论。

## 结论

✅ 通过。OHOS/arm64 Conan 包创建成功，新增的 14 项核心流程断言全部通过；
上游无自动化测试的事实与新增测试统计分开记录。
