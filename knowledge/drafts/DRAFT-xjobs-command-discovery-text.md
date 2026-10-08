# 命令发现描述被当命令执行并掩盖依赖失败：xjobs 20241010

## 错误特征与触发条件

Shell helper 捕获 `command -v` 的标准输出，再把该文本放入命令位置。xjobs 原 `testdummy` 使用：

```sh
S=$(command -v gsleep||command -v sleep)
$S $1
expr "$1" \> "4" > /dev/null
```

OpenHarmony PC aarch64 上的 H1-011 原上游运行出现 `9.24046 alias not found` 等十条错误，最长等待输入为 9.24046 秒，业务摘要却为 `3 failed, 7 succeeded, executed in 0.147s`；外层 elapsed=0.224s、make rc2。七成功/三失败是后续业务结果，不能证明 sleep 执行成功。

H1-020 实际 `/system/bin/sh -c 'command -v sleep'` 返回 rc0、`alias sleep=sleep`；原选择表达式返回同一文本。该批按条件停止，未运行旧 helper，也未识别此 sh 的具体实现。

## 根因

`command -v` 报告 shell 如何解析命令，输出可能是路径、命令名或 alias 定义；正常 alias 描述本身不是错误。[POSIX.1-2024 command](https://pubs.opengroup.org/onlinepubs/9799919799.2024edition/utilities/command.html)规定 alias 按定义命令行的形式输出。

旧 helper 将描述作为未加引号的 `$S $1` 执行，展开为 `alias sleep=sleep 9.24046` 这种 alias 调用，数值被当作查询的 alias 名。脚本还忽略依赖调用的退出状态，继续由 expr 决定业务退出码。源码结构、实际 lookup 输出与旧错误日志共同支持这一根因；不能将旧 make rc2 全部归于 lookup，也不能把正常 alias 输出单独作为错误签名。

## 最小修法与使用说明

对于按名称选择工具的 helper，只使用 lookup 的退出状态选名称，按名称实际调用，引用参数并在依赖失败时停止：

```sh
if command -v gsleep >/dev/null 2>&1; then
    gsleep "$1" || exit 2
else
    sleep "$1" || exit 2
fi
```

后面的 expr 业务判断保持不变。`exit 2` 是本 helper 明确的依赖失败分支，并不承诺保留依赖工具的原始数值退出码。不要用 eval 执行 lookup 描述。该修法只对应 `0006-testdummy-sleep-command.patch`，不修改上游随机输入、种子或预期负向任务；也不将其他五个适配补丁合并申报为本知识。

## 输入、输出与验证

复用既有固定输入的目标机证据，本知识补交新增软件/H1/构建运行为 0：

| 原件 | 实际结果与覆盖边界 |
|---|---|
| H1-011 原 helper | 十项数值 `alias not found`、总时长0.147s、make rc2；原失败保留。 |
| H1-020 lookup | 实际 `/system/bin/sh` rc0、输出 `alias sleep=sleep`；这是正常反例，不是 helper 成功结果。 |
| H1-021 修后 0.05 | trace 先 sleep 后 expr，rc1、0.117964687s；进入业务负向分支。 |
| H1-021 修后 4.5 | trace 先 sleep 后 expr，rc0、4.572179063s；真实等待后进入业务成功分支。 |
| H1-021 非法时长 | sleep 报 Invalid argument，rc2、0.048958593s，无 expr；依赖失败不再被业务判定掩盖。该批上游 make test 的60s超时仍为UNKNOWN。 |
| H1-025 真实上游 | 使用真实 gawk 生成未改的十项输入；十项完成、max_running=8，七业务成功/三预期负向与真实 expr 参考一致，make rc0、11.362298594s。有采集包装和DEVNULL stdin，不能说运行条件与021完全相同。 |
| v2 本地 W3 | setup/build_and_test/worker rc0、step35=true；1个Conan消费者程序内8项检查通过（8/8）。这是本地软件阶段PASS；外层capture=UNKNOWN_OR_FAILED_STOP、ownership_complete=false仍保留，不是官方托管CI。 |

上游源码包 `xjobs-20241010.tgz` SHA256：`985666fede9346abe034a0074d8ab03f19f518802eaa744dd339c4028e639f38`。修法0006 SHA256：`bb9e1ca277224e74ea0841442986e78d7631d73170762e6f259982477baf7f61`。来源为[原适配PR !13828](https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos/merge_requests/13828)，固定[来源提交8fabbbe952f76ae0ae7027608a3f9071f4383774](https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos/commit/8fabbbe952f76ae0ae7027608a3f9071f4383774)；原A已于2026-10-04 06:03:12（Asia/Shanghai）合入。本知识的接受、合入及计分另行核验，不继承原A的完成结论。

原件以软件证据目录中的 `h1-011/xjobs-h1-011-complete.tar.gz :: logs/upstream-make-test.*`、`h1-020/raw/A2.json/A4.json`、`h1-021/raw/logs/probe-{0.05,4.5,not-a-duration}.json`、`h1-025-real-gawk-upstream-v1/device-originals/` 与 `h1-current-w3-20261003-v2/device-originals/` 为索引。关键摘要：011包 `9c5a1d035b28fbd2dcb3d99a265938b764115e960f3b332412ba0d3890a90f8a`；020 A2 `696d400c51c826716ab990e56423049f9acac23ef1ae92b2bea8b4d9357fcfbf`；021非法时长JSON `0c6a5a69a4029f77d66f515828f7d41470451f74287dc3428a9d68d3059b08c9`；025原始归档 `5161e0d1907a5f9e4a00544d44114e658fa0a9307731b24a6d3a6b6e0de99b8c`。

## 适用范围与匹配边界

其他 Shell wrapper 或构建/测试 helper 若采用 `T=$(command -v preferred || command -v fallback)` 后 `$T args`，且受测 shell 将命令报告为 alias 描述，会有同机制需求。复核时必须同时查看源码结构、原错误、真实依赖调用和错误传播。未取得第二库实测，不宣称跨库验证。

仅用 `command -v tool >/dev/null` 做存在性分支的脚本、正常打印 alias 描述、单纯缺工具/PATH、或契约要求直接执行外部ELF/绝对路径的调用者，不直接套用本名称选择方案。lookup成功也不保证工具实际运行成功，应保留实际调用与失败检查。

KV以真实下游字面 `alias not found` 匹配，并要求人工确认上述源码条件；`rec_auto_fix=false`。正常人工 alias 查询也可能报同一句，应据上下文分流。正常 `alias sleep=sleep`、修后sleep/expr trace及sleep非法参数错误均不作为本条错误签名。

## 与近邻的增量

E010覆盖toybox sed/expr功能不足；E386覆盖真实cwd能力及shell/ELF选择性派发；E404覆盖zsh autoload文件缺失；Issue2161覆盖解释器/CLI依赖识别及Conan运行闭包。本条只补“正常lookup描述 → 变量命令误执行 → 忽略依赖错误”的链条，不重复这些机制，不推断受测shell为zsh。

最近的[mk草稿DRAFT-13686](https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos/blob/2446216757be20359617ac140c2e103fac6398f0/knowledge/drafts/DRAFT-13686-mk-ohos-shell-alias-breaks-exec-probe.md)已解释正常alias描述不能证明命令实际可执行：其失败链为存在性假阳性、按原名称调用chown返回127、set-e中断安装；修法针对可选属主变更，用外部可执行路径检查决定是否降级。本项的新增链为把lookup描述放在变量命令位置、误调用alias、忽略依赖错误而由expr继续判定。两者共享alias背景，但调用契约与错误传播不同。本名称选择方案继续检查真实调用失败，不将lookup状态写成可执行性保证，不代替mk的外部路径/可选操作契约；不修改或重复提交该作者草稿。

当前主线的[libsir草稿](https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos/blob/39f112dccc41b35e440632532afce2e17a2ff3e9/knowledge/drafts/DRAFT-libsir-2.2.6-makefile-command-v-sh-alias-sh.md)已覆盖command-v的alias描述被用于Makefile SHELL、recipe以非法前缀执行并显式报Error127，修法为调用层覆盖SHELL=/bin/sh。两者共享描述误执行的根因。xjobs的独立增量限定为sleep依赖失败被后续expr掩盖、业务7/3不能证明真实等待，以及按名称调用后失败exit2、真实延时与非法时长分别验收；这组错误传播与验收边界未由libsir条目覆盖。
