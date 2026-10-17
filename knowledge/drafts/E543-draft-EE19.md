# E543（草稿）— 声明 `#!/bin/sh` 却使用 bash 方言的脚本，在 OHOS 上静默失效

> 状态：DRAFT，待主编审核。触发事件：mrename 1.2 适配（`feat/mrename-1.2`）。

## 现象

脚本工具在 Linux 桌面上工作正常，打包到 HarmonyOS PC 后运行，终端出现：

```
mrename: 93: [: ==: unexpected operator
mrename: 96: [: ==: unexpected operator
```

更棘手的是**没有崩溃**：脚本继续往下跑，打印 "Done"，退出码 0，
但文件一个都没被重命名。用户看到的是"命令跑完了却什么都没发生"。

## 根因

三类 bash 专有语法藏在声明 `#!/bin/sh` 的脚本里：

| 写法 | 性质 | 在严格 POSIX shell 下的行为 |
|---|---|---|
| `[ $x == "y" ]` | bash 的 test 扩展 | 报 `[: ==: unexpected operator`，test 返回非 0 |
| `n=$[$i+1]` | bash 早期废弃的算术展开 | 不展开，变量取到空串，编号全为空 |
| `echo -n "..."` | 非 POSIX 的 echo 行为 | 原样打印 `-n `，提示串错乱 |

大多数 Linux 发行版把 `/bin/sh` 链到 bash，所以这些写法能存活二十年不被发现；
HarmonyOS PC 的基础 shell 是严格 POSIX 实现，一进去就暴露。

**静默失效的机制**：`[` 报错时退出码非 0，脚本的 `if/elif` 顺势走到 `else`
分支或跳过整段逻辑，控制流照常走到结尾并 `exit 0`。所以 CI 里只看退出码
的冒烟测试会判"通过"。

## 处置

**推荐：POSIX 化，保留 `#!/bin/sh`**

```sh
-	if [ $1 == "-h" ]          +	if [ "$1" = "-h" ]
-	if [ ! $3 ]                +	if [ -z "$3" ]
-nnumber=$[$number+1]          +nnumber=$((number + 1))
-echo -n "type yes: "          +printf '%s' "type yes: "
-cp $mfile $2$n$mfile          +cp -- "$mfile" "$2$n$mfile"
-find ./ -name "$1" -exec helper {} $2 $act \;
+find ./ -name "$1" -exec helper {} "$2" "$act" \;
```

给变量加引号不是顺手美化：`[ $x = "y" ]` 在 `$x` 为空时会退化成
`[ = "y" ]` 而报参数错误，加引号后才真正健壮。

**验证必须用严格 POSIX shell**。在 `/bin/sh -> bash` 的机器上跑测试证明不了
任何事。可用的最低成本做法是显式用 `dash` 跑一轮，再用 `bash` 跑一轮确认没回退：

```bash
dash ./test_suite.sh <script>     # 打补丁前: passed=5 failed=6
dash ./test_suite.sh <script>     # 打补丁后: passed=11 failed=0
bash ./test_suite.sh <script>     # 打补丁后: passed=11 failed=0
```

把这三行结果写进 test-report 与 PR，比一句"已修复 bashism"有用得多。

**不推荐：把 shebang 改成 bash**（Debian 对 mrename 的处置是
`debian/patches/20-shebang-patch.patch` 改 `#!/bin/bash`）。
改动量确实最小，但等于给一个零依赖脚本工具引入 bash 运行期依赖；
OHOS PC 基础环境不保证有 bash 时，包在目标机上直接跑不起来。
只有当脚本大量使用数组、关联数组、`[[ ]]` 正则匹配等无法平价 POSIX 化的
特性时，才值得选这条路——而且要在 notes 里写清为什么无法 POSIX 化。

**禁止**把 shebang 写成设备绝对路径（如构建机软链 `/data/service/hnp/bin/bash`）：
那是构建机准备，不是交付产物的一部分，换台机器就 `bad interpreter`。

## 附带一条：`find -exec <helper>` 的 PATH 语义

这类老脚本常把功能拆成主脚本 + 辅助脚本，并用
`find ./ -name "$1" -exec helper {} ... \;` 调用同伴。`find -exec` 走 `execvp`，
**按 PATH 查找**。上游假定两个脚本都装在 `/usr/bin`，而 Conan 包可以安装到任意前缀。

修法不在补丁里，而在打包侧：把真实脚本放 `libexec/<pkg>/`，`bin/<pkg>` 放一个
解析自身真实路径、把 `libexec` 前置进 `PATH` 后再 `exec` 的 wrapper
（`archives/a/acme.sh/3.1.3` 是同形态先例）。这样上游脚本逻辑一行不用改，
包也保持可重定位。

## 预扫描

`prescan_pattern` 已填 `\[\s+[^]]*==\s|\$\[[^]]*\]|echo\s+-n\s`，
选型阶段对脚本类源码跑 `prescan` 即可提前暴露，不必等打包后在设备上踩。

## 相关条目

- `E043` — `${BASH_SOURCE}` 在 toybox ash 下取空（bash **变量**，本条目是 bash **语法**）
- `E165` / `E037` / `E049` — shebang **路径**不存在（本条目的 shebang 路径正确）
- `DRAFT-script-hardcoded-fhs-paths-need-patch-to-selflocate` — 脚本写死 FHS 绝对路径
