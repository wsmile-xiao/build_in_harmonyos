# xli 1.17.0:OHOS musl 缺 BSD 遗留函数 rindex——逐函数最小替换,别开 -DSYSV

> 草稿(DRAFT)— 来自 xli 1.17.0-20061110 HarmonyOS PC (aarch64) 适配的真实实践。
> 与 `.kv` 同 stem 配对。

## 问题

xli 的 `ddxli.h` 把 `rindex` 的可用性推给上游特性宏：

```c
#ifdef SYSV
# define rindex strrchr
...
#endif
```

不启用 `SYSV` 时既没有声明、也没有符号；musl（OHOS libc）**不提供 rindex**。
实测（OHOS SDK 26.0.0.18，`sysroot/usr/lib/aarch64-linux-ohos/libc.so`）：

```
$ nm -D --defined-only libc.so | grep -cw rindex
0
$ nm -D --defined-only libc.so | grep -cw index      # 1
$ ...  bcopy -> 1    bzero -> 1    bcmp -> 1
```

即：**同族五个 BSD 遗留接口里,只缺 rindex**——这正是不能一把梭的理由。

## 最小解

编译期等价替换，一行搞定：

```python
# conanfile.py build flags
self._cflags += ["-Drindex=strrchr"]
```

`rindex(s, c)` 与 `strrchr(s, c)` 语义一致（返回最后一个匹配指针，未命中回 NULL），
因此这是**语义等价**的替换，不是打补丁绕过。

## 为什么禁 -DSYSV

启用 `-DSYSV` 会连带打开上游的 System V 分支：`stropts.h`（musl 无）、
`F_FREESP`（musl 无）、`poll` 相关路径等——样本代码 `window.c` 里就有一串
`#ifdef SYSV / #ifdef SVR4` 的 streams 逻辑。修一个符号问题换来一片缺口：

| 方案 | 缺口数 | 修复面 |
|------|--------|--------|
| `-Drindex=strrchr` | 1 | 一行编译 flag |
| `-DSYSV` | ≥3（头文件/结构/轮询语义） | 逐个补丁，且互相牵连 |

**口径**：老代码里的 `SYSV`/`SVR4`/`__svr4__` 总开关一律不上；同族函数逐函数探针
（`nm -D --defined-only`）确认后逐个替换，缺一个补一个。

## 验证与反向证据

- 修复后：`conan create archives/x/xli/1.17.0-20061110` 全绿；免显示 CLI `xlito`
  往返转换冒烟通过（`test_package/test_xli_consumer.sh` 输出 PASS）。
- 反向：去掉 `-Drindex=strrchr` 即回到 `implicit declaration of function 'rindex'`
  / undefined symbol 的失败态——证明该 flag 是必要且充分的。

## 检测与复现

```sh
python3 knowledge/drafts/imake-legacy-x11/detect_imake_legacy.py --src <源码目录> \
    --libc <ohos-sdk>/.../aarch64-linux-ohos/libc.so
sh knowledge/drafts/imake-legacy-x11/reproduce.sh --src <源码目录>
```

## 覆盖判断

- 与 E051/P008（未实现 syscall 需调用前拦截）不同：那是**运行时**系统调用缺口，
  本条是**编译/链接期**符号缺口，且已通过编译期等价替换解决，无需源码补丁。
- 与 gnulib/libtool 类替代（`gnulib` 提供 rindex 兼容实现）相比，本方案不引入新依赖。
