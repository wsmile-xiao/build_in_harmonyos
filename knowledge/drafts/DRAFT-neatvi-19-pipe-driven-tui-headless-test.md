# neatvi 19：管道驱动 TUI 编辑器无头测试可行性审查 + /tmp 硬编码改写

## 场景

neatvi 上游 test.sh 用管道驱动 vi 二进制跑 67 个用例
（`sh 用例 期望输出 | ./vi -s -e` ex 模式 26 个 / `-v` visual 模式
41 个，cmp 逐字节比对）。TUI 编辑器能否在无头 CI（无 tty）这样跑，
取决于终端初始化代码的容错性。

## 无头实跑可行性三查

1. **isatty 门控**：`grep -rn 'isatty\|/dev/tty' *.c` 应为空。
   有 isatty 门控的编辑器（管道 stdin 直接拒跑）只能上 pty 包装，
   成本翻倍。neatvi 全仓无 isatty、不开 /dev/tty。
2. **tcgetattr 返回值**：neatvi `term.c:21` 为
   `tcgetattr(0, &termios);`——返回值不检查，非 tty stdin 不致命。
   若上游检查返回值并 fatal，则管道驱动走不通。
3. **终端尺寸回退**：`term.c:27-30` 支持 `LINES`/`COLUMNS` 环境变量，
   不依赖 ioctl(TIOCGWINSZ)（非 tty 上 ioctl 会失败）。

三查全过 → 上游 harness 可全量实跑，包括 visual 模式用例
（占 61%，跳过即 rule4 少报）。

## /tmp 硬编码改写（HMFS 只读约束）

test.sh 硬编码 `/tmp/.neatvi[12]`（4 处 + cmp）。HMFS /tmp 只读 →
build() 运行时 sed 改写 + TMPDIR 重定向：

```python
t = open(test_sh).read().replace("/tmp/.neatvi", "${TMPDIR:-/tmp}/.neatvi")
open(test_sh, "w").write(t)
self.run(f'TMPDIR="{bf}" sh test.sh', cwd=src, env="conanbuild")
```

语义等价、非源码补丁（conandata.yml 注释披露）。与 ctemplate CI #44037
（here-doc /tmp）、libmatheval CI #42548（tmpfile()）同属"HMFS 临时
文件原语"一族。

## 环境污染

`ex.c:1498-1503` 启动时读 `EXINIT` 环境变量或 `~/.neatvi` 配置——CI
环境残留会污染测试输入流。上游 test.sh 已 `unset EXINIT HOME`，运行
时保持该行为，勿画蛇添足 export HOME。
