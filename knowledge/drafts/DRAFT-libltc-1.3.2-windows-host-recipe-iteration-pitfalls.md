# Windows 主机配方迭代五坑：PowerShell 文本管道毁补丁、本地源码自我污染、补丁上下文保真、byte-exact 恢复

- **软件**: libltc 1.3.2（泛化到所有 Windows 主机写 Conan 配方/补丁的适配）
- **阶段**: 配方与补丁编写/验证（W2-W4）
- **severity**: 2
- **状态**: DRAFT

## 坑 1：PowerShell 重定向把补丁写成 UTF-16

`git show <commit>:<path> > x.patch` 在 PowerShell 中默认以 UTF-16 编码落盘，
`git diff --stat` 显示 `Bin xxx -> 0 bytes`，`git apply --check` 报
`No valid patches in input`。与"PowerShell 文本管道破坏 tar"（真机指南 §2.3）
同根：**PowerShell 重定向不是字节流**。

修复：恢复单个历史文件一律用 `git checkout <commit> -- <path>`（byte-exact，
不经文本层）；确需导出时用 `cmd /c "git show ... > file"` 或 `git cat-file`。

## 坑 2：本地验证源码被自己污染，补丁"假性不应用"

为生成 diff 先在本地工作副本上做过替换（umask 077→022），随后再
`git apply --check` 同一补丁必然失败且报错行号极具误导性（`patch failed: configure:13573`）。
**apply --check 前必须先从原始 tarball 重新解出目标文件**
（`tar -xzf src.tar.gz pkg/configure`），排除自我污染变量。

## 坑 3：手写补丁的上下文必须逐字节保真

autoconf 生成的 configure 中"空行"实际是 `" "`（一个空格的行），手写补丁时
写成真空行即 apply 失败；漏写上下文空行同样失败（hunk 行数标注与实际不符）。
由此产生的 `git diff --check` trailing whitespace 警告**源自上游文件本身**，
保真优先于消警告——删掉"多余空格行"补丁就不再应用。
正确姿势：小改动优先 `cp 原文件 → 修改 → git diff --no-prefix` 生成，
只有能逐字节核对上下文时才手写。

## 坑 4：远端设备执行复杂命令的转义地狱

toybox sh（无进程替换、sed 分号受限）+ PowerShell 双引号插值 + ssh 三层叠加时，
内联命令几乎必炸（`sed: bad pattern`、`syntax error: unexpected '('`、`$?` 被本地
shell 吞成 True）。统一模式：

```
本地 write 工具写 .py 补丁脚本
  -> scp 到设备 job 目录（/tmp 只读 E002，HOME 下 job 目录可写）
  -> ssh "python3 ~/ohos-users/codex/<job>/patch.py"
```

## 坑 5：PowerShell `&&` 与 `$?`

Windows PowerShell 5.x 不支持 `&&`/`||`；内联 `\"$?\"` 会被本地解析为
True/False。用 `if($?){...}` 分句；退出码用 `$LASTEXITCODE`。

## 证据

libltc 1.3.2（atomgit PR #13721）迭代实录：
- `git show > patch` 产生 928 字节"二进制"补丁 → `git checkout <c> -- path` 恢复后
  `git apply --check` APPLIES_CLEAN；
- 补丁上下文含上游空格行，截断/净化后两次 apply 失败，恢复保真版后通过；
- 远端 umask 替换 sed 三连炸，改 python3+scp 模式一次成功；
- 该补丁随后在真机 r5 全绿（exit 0）验证有效。

## 复用价值

Windows 本机是本仓库并行适配的主力环境，以上五坑每个都会浪费一轮真机窗口
（错误信息全部具有误导性），本条把它们的"识别→规避"收敛为固定操作模式。
