# wdiff

**GNU wdiff** — 逐词比较两个文件的 diff 前端工具

wdiff 收集两个文件之间的单词差异：对比 GNU diff 的逐行输出，wdiff 输出两个文件在"词"级别的差异，被删除的词用 `[-...-]` 标记，被插入的词用 `{+...+}` 标记。

## 用法

```bash
wdiff [options] file1 file2
```

| 选项 | 说明 |
|------|------|
| `-w string` / `--start-delete=string` | 删除段起始标记（默认 `[-`） |
| `-x string` / `--end-delete=string` | 删除段结束标记（默认 `-]`） |
| `-y string` / `--start-insert=string` | 插入段起始标记（默认 `{+`） |
| `-z string` / `--end-insert=string` | 插入段结束标记（默认 `+}`） |
| `-1` / `-2` / `-3` | 仅显示 file1 / file2 / 两者共有的词 |
| `-a` / `--auto-pager` | 自动进入 pager |
| `-n` / `--avoid-wraps` | 不做长行折行 |

上游文档：https://www.gnu.org/software/wdiff/manual/wdiff.html
