# GNU sed `I` 修饰符在 OHOS toybox sed 报 bad pattern（字符类改写方案）

## 概述
上游测试 harness 常用 GNU sed 扩展 `I` 修饰符做大小写不敏感地址过滤（例如过滤
date/user-agent 等易变响应头后再与期望日志 diff）：
```sh
FILTER='sed -E /(date|user-agent|trying|tcp)|^\*/Id'
```
OHOS 默认 **toybox sed 0.8.12** 不支持地址的 `I` 修饰符（GNU 专有扩展），直接报
`sed: bad pattern '...'@N (d)`，FILTER 管道整段失败（`set -e` 下脚本 rc=1）。
toybox sed 的 `-E`（POSIX 扩展正则）本身可用，仅 `I` 修饰符缺失。

## 错误特征
```
sed: bad pattern '/(date|user-agent|trying|tcp)|^\*/Id'@36 (d)
```

## 根因
1. `I` 是 GNU sed 对地址正则的大小写不敏感修饰符（`/re/I`）。
2. toybox sed 解析到该修饰符即报 bad pattern（不是"行为不同"，是**语法不支持**）。
3. 影响：任何依赖该写法过滤输出后再 diff 的上游测试，在 OHOS 全部失败。

## 方案（免装 GNU sed 的等价改写）
将大小写不敏感匹配展开为显式字符类，并去掉 `I`：
```sh
FILTER='sed -E /[dD][aA][tT][eE]|[uU][sS][eE][rR]-[aA][gG][eE][nN][tT]|[tT][rR][yY][iI][nN][gG]|[tT][cC][pP]|^\*/d'
```
- 语义等价：匹配任意大小写组合（date/Date/DATE…、user-agent/USER-Agent…）。
- toybox 实测通过；GNU sed 同样接受（跨平台兼容）。
- 兜底：cmd-pkgs 安装 GNU sed（`install.sh | sh -s -- sed 4.9`，见 E010）。

## 验证
- iwnet 1.3.1 `server1-tests-run.sh`（plain 与 `--ssl`）：
  改写前 sed bad pattern、脚本 rc=1；改写后 toybox 过滤正确
  （`date:`/`Date:`/`USER-Agent:`/`Trying:`/`tcp:` 均去除，`X-test:` 保留），复跑 rc=0。
- server2/proxy1 脚本同样改写（虽然后续又遇 curl --data-urlencode 大文件限制，
  但 sed 阶段已通过 toybox 语法验证）。

## 适用边界
- 适用于任何上游测试 harness 使用 `sed -E /re/Id`（或 `-r`）过滤的库在 OHOS 构建。
- 仅 `I` 修饰符缺失时适用；若脚本还有 toybox 不支持的其余 GNU 语法
  （嵌套/标签等，E010 域），需装 GNU sed。
- 反例：需要真正 regex 大小写折叠的高级模式（如 Unicode 大小写）不建议手工展开，
  应装 GNU sed。

## 关联条目
- similar_to：E010（toybox sed 通用不兼容——install-gnu-tools 兜底）
- conflicts_with：无