# DRAFT-ctags-6.2.1.1-ohos-tmain-suite-adaptation：OHOS 上上游 Tmain 测试套件的四类环境适配

> Contributor: OpenDesk | Status: Draft | Updated: 2026-09-26
> Source: ctags 6.2.1.1 适配（目标库任务）；首轮 `make check` 假绿 + tmain 16 例失败
> 对应：`knowledge/drafts/DRAFT-ctags-6.2.1.1-ohos-tmain-suite-adaptation.kv`

## 使用说明（怎么用这条知识）

1. 在 OHOS 上跑某项目的上游测试（`make check` / `ctest` / shell 测试驱动）后，先**判断结果是否可信**：
   ```bash
   grep -c '^Traceback' <测试日志>      # >0 说明有异常被吞掉，统计不可信
   ```
   若 >0，先按"第 0 步"消除假绿，再看失败清单。
2. 按"四类差异"对照失败现象定位，逐类修复（均为语义等价的小改，Linux 上行为不变）。
3. 修复后重跑，确认 `tmain/shell 驱动` 段 `failed = 0`。

## 适用范围

| 条件 | 说明 |
|------|------|
| 平台 | OpenHarmony / HarmonyOS（`/bin/sh` 是 toybox sh；`/tmp` 只读） |
| 对象 | 由 **shell 脚本驱动**的上游测试套件（GNU autotools 的 `make check`、`misc/units`、自定义 `run.sh`） |
| 典型现象 | `Read-only file system`、`fc: history functions not available`、grep 匹配为空、单个用例耗时异常 |
| 不适用 | 纯二进制单元测试（无 shell/tmp 依赖）；已有 `$TMPDIR` 规范的上游脚本 |

## 输入 / 输出定义

| 项 | 定义 |
|----|------|
| 输入 | 上游测试脚本（`Tmain/*/run.sh` 等）与测试驱动（`misc/units.py`）；OHOS 的 `/bin/sh`、`$TMPDIR` |
| 输出 | 适配后的测试脚本 + `patches/0003-*.patch`；`make check` 中该段失败数为 0 |
| 成功判据 | `PYTHONPATH=<pyfix> make -k check` 后：`grep -c '^Traceback'`=0 且失败段 `failed(diff:)`=0 |
| 失败信号 | 仍出现 `/tmp` 写入失败、`fc: history functions not available`、grep 输出为空、用例超时 |

## 第 0 步：先消除"假绿"（否则失败会被吞掉）

`misc/units.py` 的 `tmain_compare()` 只有在**比对失败**时才调用 `diff` 生成诊断文件：

```python
else:
    with open(generated, 'wb') as f:
        subprocess.run(['diff', '-U', ...], stdout=f, ...)   # ← 本机此处抛 FileNotFoundError
    run_result('error', msg, None, 'diff: ' + generated, file=f)   # ← 未执行
    return False
```

本机 CPython 走 `os.posix_spawn` 快路径时**不按 PATH 解析裸命令名**（`executable='diff'`），
于是 `diff` 抛 `FileNotFoundError` → **失败既不计入 FAILED 也不计入总数** → `make check` 报 exit 0。

**消除办法**（不改上游源码，仅本地/验证环境）：

```bash
mkdir -p /path/pyfix
cat > /path/pyfix/sitecustomize.py <<'EOF'
import subprocess
subprocess._USE_POSIX_SPAWN = False   # 回退到 fork_exec（带 PATH 查找）
EOF
PYTHONPATH=/path/pyfix make -k check
```

> 复现验证：注入前 `grep -c '^Traceback'` = 43（43 处失败被吞）；注入后 = 0，失败正常上报。
> 本包实测：修复前 units 总数为 1574，修复后为 1602（28 项此前被吞）。

## 四类差异与修复

### ① `/tmp` 只读（E002）—— 21 个 `run.sh`

```diff
-} > /tmp/ctags-tmain-$$.stdout 2>/tmp/ctags-tmain-$$.stderr
+} > ${TMPDIR:-/tmp}/ctags-tmain-$$.stdout 2>${TMPDIR:-/tmp}/ctags-tmain-$$.stderr
```
`${TMPDIR:-/tmp}` 在 Linux 上仍解析为 `/tmp`（行为不变）。

### ② toybox sh 吞掉 grep BRE 交替里的反斜杠 —— 5 个 `run.sh`

```diff
-$CTAGS --list-map-extensions=all | grep '^#\|LdScript'
+$CTAGS --list-map-extensions=all | grep -E '^#|LdScript'
```
实测：同一命令在 zsh 下正常，在 `/bin/sh -c` 下 `grep '^#\|LdScript'` 返回 rc=1、0 行（`\|` 被吞成 `|`）。

> 注意：同一文件中的 `sed -e 's|\||/|g'` **不是** grep，不要误改。

### ③ `r` 与 toybox sh 的 fc(history) 内建冲突 —— 1 个 `run.sh`

```diff
-r()
+run_query()
 {
 	echo ';; ' "$1"
 	${READTAGS} -e -t output.tags -Q "$1" -l
 }
```
现象：`run.sh[21]: fc: history functions not available`（`unalias r` 无效，必须改名）。

### ④ toybox sh 的 `printf` 是外部命令 —— `c-large-enum.d/run.sh`

```diff
-i=0
 {
 	echo "enum E {"
-	while [ $i -lt 32770 ]; do
-		printf "X%x," $i
-		i=$(($i + 1))
-	done
+	awk 'BEGIN { for (i = 0; i < 32770; i++) printf "X%x,", i }'
 	echo "};"
 } > $input
```
实测：原循环在测试环境下 90 s 只完成 ~3400 次迭代（约 0.026 s/次，32770 次需 ~14 分钟）；改为 awk 后整体 0.3 s 完成。

## 示例（ctags 6.2.1 实测结果）

| 阶段 | 修复前（首轮，假绿） | 修复前（注入 pyfix 后） | 修复后 |
|------|--------------------|----------------------|--------|
| tmain 段失败 | 未上报（假绿） | 15 个用例 / 26 判定 | **0** |
| units 段 `#FAILED (unexpected-output)` | 0（假绿） | 4 | 4（**待定性，见 notes.md**） |
| `grep -c '^Traceback'` | 43 | 0 | 0 |

补丁文件：`archives/c/ctags/6.2.1.1/patches/0003-tmain-ohos-tmpdir-shell-compat.patch`（28 文件 / 392 行，`patch -p1` 可干净应用）。

## 相关平台知识

- E002：`/tmp` 只读，应使用 `$TMPDIR`。
- `DRAFT-ctags-6.2.1.1-hmdfs-mktemp-AS_TMPDIR-unwritable`：HMDFS 上 `mktemp -d` 目录不可写（姊妹条目）。
- R51 上游测试三步法：清点 → 真实运行 → 如实回填；本条目解决"真实运行"阶段的平台适配。
