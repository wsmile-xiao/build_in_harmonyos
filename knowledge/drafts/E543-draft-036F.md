# E543（草稿）— 在 find 遍历中改名：OHOS 的 toybox find 会把新名字再匹配一次

> 状态：DRAFT，待主编审核。触发事件：mrename 1.2（PR #11843）CI 构建 #57971。

## 现象

批量改名脚本在桌面 Linux 上测试全绿，到 HarmonyOS PC 的 CI 上断言失败：

```
  FAIL move: renamed file present: expected <1> got <0>
  FAIL spaces: filename preserved: expected <1> got <0>
passed=11 failed=2
```

期望 `c.log` → `pre1c.log`，实际目录里是 `pre2pre1c.log`：**同一个文件被改名了两次**。
copy 模式同理，会出现 `item3item1a.txt` 这种"副本的副本"。脚本不报错，退出码 0。

## 根因

脚本写法：

```sh
find ./ -name "$1" -exec mcpmv {} "$2" "$action" \;   # mcpmv 内部 mv/cp 到 <prefix><n><oldname>
```

改名后的新名字 `pre1c.log` 仍然匹配 `*.log`。它会不会被同一次 `find` 再看到，取决于 find 的实现：

| find 实现 | 目录读取方式 | 遍历期间新增的目录项 |
|---|---|---|
| GNU find（fts） | 进入目录先把全部目录项读进内存，再逐个处理 | 看不到 |
| toybox find（OHOS 自带） | 读一个目录项、处理一个 | **可能看到**，取决于文件系统把新名字写在当前读取位置之前还是之后 |

POSIX 对"遍历过程中新增的目录项是否由后续 `readdir` 返回"不作规定，两种实现都合规——
错的是脚本依赖了 GNU find 的实现细节。

## 为什么本地测不出来

是否暴露取决于目录项布局。同一个修复前的包，只把 `find` 换成 toybox 0.8.14：

| find | 文件系统 | 200 个文件中改名一次 | 改名两次及以上 |
|---|---|---|---|
| GNU find | ext4 | 200 | 0 |
| toybox find | ext4 | 119 | **81** |
| toybox find | tmpfs | 200 | 0 |

本地 ext4 上 ≤60 个文件时一个都不触发，而 OHOS runner 上**单个文件就触发**。
所以"桌面 Linux + 小目录"的测试组合会百分之百漏检。

## 处置

**推荐：先快照，后处理**（纯 POSIX sh）

```sh
matches=$(find ./ -name "$1")
oldifs=$IFS
IFS='
'
set -f
for match in $matches
do
  mcpmv "$match" "$2" "$action"
done
set +f
IFS=$oldifs
```

- `IFS` 只留换行：含空格的文件名不会被拆开；
- `set -f`：含 `* ? [ ]` 的文件名不会被当成通配符展开；
- 局限：文件名本身含换行符时会被拆开（这类文件名在批量改名场景里基本不存在，需要时见回退方案）。

**测试要能抓住它**：

1. 断言"每个文件恰好处理一次"——目录文件总数 + 不存在双前缀名，不要只数符合目标格式的文件
   （只数 `item<N>[ab].txt` 会把 `item3item1a.txt` 漏掉，本次 copy 用例就是这样漏过的）；
2. 放一个上百文件的目录跑一轮，才能在本地文件系统上稳定暴露。

**回退**：先改成不会再次匹配的临时名（或写到另一目录），全部完成后统一改回。适用于必须支持含换行符文件名的场景。

**不要**：

- 改成 `-exec ... {} +`：find 在参数攒满一批时就会中途执行，大目录下照样在遍历途中改名，只是更难复现；
- 在配方/wrapper 里强行换成 GNU findutils：给零依赖脚本包引入额外依赖，且依赖的仍是未被 POSIX 保证的行为。

## 预扫描

`prescan_pattern` 已填 `find\s+\S+.*-exec\s+\S*(mv|cp|rename|mcpmv)\b`，
选型阶段对脚本类源码跑 `prescan` 即可提示风险。

## 相关条目

- `E010` / `E106` / `E188` / `E254` — toybox 各命令的**选项/行为不兼容**（直接报错）；本条目选项合法、不报错，差异在遍历语义
- `E543-draft-EE19` — 同一个包的另一类问题：`#!/bin/sh` 脚本里的 bash 方言
