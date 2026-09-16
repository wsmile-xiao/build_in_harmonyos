# `make test` 退出码探针 — 原始输出留档

> 逐字留档：下方 `BEGIN/END VERBATIM CAPTURE` 标记之间的内容即为探针原始输出；
> 属性表对该**块本身**计算（复核命令：`sed -n '/^<!-- BEGIN VERBATIM CAPTURE probe.txt -->$/,/^<!-- END VERBATIM CAPTURE probe.txt -->$/p' reports/make-test-exit-code-probe.md | sed '1d;$d' | sha256sum`）。

| 属性 | 值 |
| --- | --- |
| 原始文件 | `probe.txt` |
| 字节数 | 1569 |
| 行数 | 48 |
| sha256 | `1d3e16668cbca565d55bbebd647d5714376c1c6e9561fff095e9001aeddb65ca` |
| 采集命令 | `make IMAKE_DEFINES=... test` + `echo $?`（见块内第 2 节） |
| 采集时间 | 2026-09-11（设备本地时间） |

<!-- BEGIN VERBATIM CAPTURE probe.txt -->
# make test 退出码探针（原始输出）

> 采集时间：2026-09-11 22:30:00（设备本地时间）
> 树：补丁后的源码树（与 reports/upstream-make-test-evidence.md 同一棵）
> 目的：核实「make test 退出码为 0」这一结论，而不是仅凭规则文本推断。

## 1. 顶层 test 规则原文（Imakefile 经 imake 生成后的 Makefile:316）

```make
test::
	@case '${MFLAGS}' in *[ik]*) set +e;; esac; \
	for i in $(SUBDIRS) ;\
	do \
	(cd $$i ; echo "testing" "in $(CURRENT_DIR)/$$i..."; \
	$(MAKE) $(MFLAGS) DESTDIR='$(DESTDIR)' test); \
	done

test.create::
	@case '${MFLAGS}' in *[ik]*) set +e;; esac; \
	for i in $(SUBDIRS) ;\
	do \
	(cd $$i ; echo "creating tests" "in $(CURRENT_DIR)/$$i..."; \
	$(MAKE) $(MFLAGS) DESTDIR='$(DESTDIR)' test.create); \
```

顶层 recipe 是一个 `for i in $(SUBDIRS)` 循环；**shell 循环的退出状态等于
最后一次迭代的状态**，因此前面子目录的 `*** Error` 不会传递到顶层。
recipe 前的 `@` 只是不回显命令，与退出码无关。

## 2. 实测退出码

```sh
$ make IMAKE_DEFINES="-DStripCmd=true -DAnsiCCmd=clang -DCPlusPlusCmd=clang++" test > /dev/null 2>&1
$ echo $?
0
```

`rc=0` —— 与规则文本推断一致，**实测确认**。

## 3. 同一轮日志内的 `*** Error` 计数（证明 rc=0 不代表没有失败）

```
$ grep -c "\*\*\*.*Error" <本轮日志>
22
```

即：**退出码 0 与 22 条 `*** Error` 并存**。因此 `make test` 的退出码不能作为通过证据，
本 PR 也从未把它记为 PASS（PASS 计为 0）。
<!-- END VERBATIM CAPTURE probe.txt -->
