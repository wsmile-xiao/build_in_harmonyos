# E546 — OHOS /tmp 只读 + zsh 脚本 heredoc 临时文件失败（TMPPREFIX）

## 错误特征

本地 `finish`（W3 本地 CI 模拟）跑 `ci/conan/build_and_test.sh`（`#!/usr/bin/zsh`）
时，脚本内的 here-document 全线失败：

```
[fail] L0i: conanfile.py AST 解析失败, 无法提取依赖:
       /…/ci/conan/build_and_test.sh:439: can't create temp file for here document: read-only file system
[hint] 常见原因: conanfile.py 带 UTF-8 BOM 或语法错误。请以 UTF-8（无 BOM）重新保存

/…/ci/conan/build_and_test.sh:787: can't create temp file for here document: read-only file system
```

命令系统里同样可见：

```
$ echo hi > /tmp/t_w
zsh:3: read-only file system: /tmp/t_w
$ zsh -c 'cat <<EOF
hello
EOF'
zsh:1: can't create temp file for here document: read-only file system
```

## 触发条件

- 平台：HarmonyOS / OHOS（`/tmp` 只读，HMDFS）
- 脚本解释器：**zsh**（`#!/usr/bin/zsh`）
- 阶段：任何含 heredoc 的脚本步骤（W3/CI 脚本里的内嵌 python/shell 片段）

## 根因分析

1. zsh 的 here-document **不像 bash 那样走匿名管道**，而是落一个临时文件；
   其路径前缀取变量 `TMPPREFIX`，**默认 `/tmp/zsh`**。
2. zsh 不使用 `TMPDIR` 来决定该前缀（实测 `TMPDIR=$HOME/tmp zsh -c 'cat <<EOF…'`
   仍报 read-only）。
3. OHOS 的 `/tmp` 不可写 → heredoc 建临时文件失败 → 依赖 heredoc 的门禁
   （`build_and_test.sh:439` L0i 依赖提取、`:787` 目录结构检查）整体失效，
   并把错误以「AST 解析失败 / 可能是 BOM」这类**误导性 hint** 抛出。

> 注：`build_and_test.sh` 内部其它临时目录用法都写了 `${TMPDIR:-$HOME/tmp}`
> 回退，只有 zsh 自身的 heredoc 临时文件不走 TMPDIR。

## 解决方案

### 推荐方案

在执行侧导出 `TMPPREFIX`（并同时给出 `TMPDIR`）：

```bash
export TMPDIR=$HOME/tmp
export TMPPREFIX=$HOME/tmp/zsh      # zsh heredoc 临时文件前缀
python3 scripts/ohc-run.py finish vgabios 0.8a built < /dev/null
```

实测：设置后 heredoc 正常（`got=hello`，rc=0），W3 得以继续推进到后续门禁。

### 回退方案

把脚本 shebang 改为 bash（bash heredoc 用管道，不落 /tmp）：

```bash
sed -i '1s|#!/usr/bin/zsh|#!/usr/bin/env bash|' ci/conan/build_and_test.sh
```

（属框架文件改动，需单独 PR，且 CI worker 上原本正常 —— 仅作本地临时手段。）

## 关联

- 同平台另一静默失败点见 E545（conan 子进程 stdin 为 socket → SDK clang 静默 exit 1）
