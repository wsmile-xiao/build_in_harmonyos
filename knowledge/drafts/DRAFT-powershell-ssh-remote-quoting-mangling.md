# DRAFT：PowerShell→OHOS 设备 ssh 远端命令被三层引号解析拆散（"sh: FAIL: inaccessible"）

> Draft（未 promote）— 来源于 xfpt 1.00 真机 shadow CI 调试（2026-09-29）
> 对应 `.kv` 文件同 stem：`DRAFT-powershell-ssh-remote-quoting-mangling.kv`

## 症状

从 Windows 工作站 ssh 到设备执行带管道/`$()` 的复合命令：

```powershell
ssh ... currentUser@<真机IP> 'R=$(ls -dt ~/ohos-test-runs/*xfpt* | head -1);
  grep -E "PASS|FAIL|RESULT" $R/logs/stdout.log'
```

远端返回一堆"工具不存在"式报错，但报错的"命令"是字面词：

```
sh: FAIL: inaccessible or not found
sh: RESULT: inaccessible or not found
sh: -dt: inaccessible or not found
sh: syntax error: unexpected '('
```

误导性极强——看起来像设备缺 grep/ls，实际命令根本没被完整送达。

## 根因

三层解析链，每层都可能剥引号：

1. **PowerShell** 解析本地命令行（`$` 在双引号内会本地展开成空）；
2. **Windows OpenSSH 客户端** 把参数重新拼接成远端命令字符串（空格分词
   时双引号丢失）；
3. **远端 sh** 对收到的残缺字符串再解析——`"PASS|FAIL|RESULT"` 的引号
   没了，`|` 被当管道，`PASS`/`FAIL` 被当成独立命令执行。

## 方案（按复杂度分级）

1. **简单命令**：双引号包裹 + 所有远端 `$` 写成 `` `$ ``（反引号转义）：
   ```powershell
   ssh ... "R=`$(ls -dt ~/ohos-test-runs/*xfpt* | head -1); tail -70 `$R/logs/stdout.log"
   ```
2. **复杂命令（监控循环、多步调试、heredoc）**：**不要拼远端命令**——
   本地写脚本 → `scp` 上去 → `ssh ... "sh /path/to/script.sh"`，
   彻底绕开三层解析；
3. **判别口诀**：`sh: <词>: inaccessible or not found` 里的 `<词>` 若是
   命令片段中的**字面词**（如 `FAIL`、`-dt`），先怀疑引号被拆；真缺工具
   时报错的是完整命令名，且可用 `command -v <工具>` 验证。

## 本轮实证

xfpt r4 排障时两次触发：读 run 日志的 grep 命令被拆（`sh: FAIL:`）、
`$(ls ...)` 被本地展开（`PKGDIR=` 为空、列出家目录）。改用 `` `$ ``
转义后一次成功；test_package 调试改 scp 完整脚本 + `bash -x` 后稳定。

## 复用面

所有从 Windows 工作站 ssh 驱动真机 shadow CI（建 job、传包、读日志、
手动调试 test_package）的协作者。
