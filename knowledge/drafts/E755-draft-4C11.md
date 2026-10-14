# E755 — clang 把裸 `-export-dynamic` 当成 `-e xport-dynamic`：ELF 入口点丢失，程序启动即 SIGSEGV

- **草稿 ID**: DRAFT-E755（本地取号，`knowledge/drafts/E755-draft-4C11.kv`）
- **来源**: ptask 1.0.0 HarmonyOS PC 适配（autotools + OHOS clang 15）
- **分类**: portability / autotools / build-system / clang / ohos
- **严重度**: 3（🔴 blocking）
- **状态**: 本地草稿（待官方主编流程合入）

## 错误特征

构建**成功**，`conan create` / `make` 退出码 0，产物存在且 `NEEDED` 齐全（`.codesign` 正常、`readelf -d` 能列出 `libgtk-3` 等），但**每次执行都在打印任何输出之前崩溃**：

```
$ <bin> --version
Segmentation fault (core dumped)        # rc=139
```

构建日志里唯一相关的一行是**警告**（极易被忽略，且不在失败路径上）：

```
ld.lld: warning: cannot find entry symbol xport-dynamic; not setting start address
```

`readelf -h <bin>` 的 `Entry point` 字段为 0 —— 加载器因此跳到非法地址。

## 触发条件

- 构建系统：autotools（automake 生成的 `Makefile.in`；CMake/meson 若把裸 `-export-dynamic` 直接放进链接命令行同理）
- 阶段：linking；现象暴露在 runtime
- 编译器：本设备 `clang 15.0.4`（`/data/service/hnp/bin/clang`）+ `ld.lld`。GCC 驱动不会复现

## 根因分析

ptask 1.0.0 发行包里的 `src/Makefile.in`（源自上游 `src/Makefile.am`）：

```make
# -export-dynamic is need for defining handlers in the glade file.
AM_LDFLAGS = -Wl,--as-needed  -export-dynamic
```

- `-Wl,--as-needed` 写法正确，但 `-export-dynamic` **漏了 `-Wl,` 前缀**。
- **GCC 驱动**自带 `-export-dynamic` 这个选项（等价 `-rdynamic`），会把它翻译成 `--export-dynamic` 传给链接器，所以在 Debian/Fedora 上这套 Makefile 一直能正常工作。
- **clang 驱动不识别** `-export-dynamic`，按「未知参数原样转发给链接器」处理；链接器按自己的语法把 `-export-dynamic` 拆成 **`-e xport-dynamic`**（`-e` 指定入口符号，值是 `xport-dynamic`）。该符号不存在 ⇒ lld 只打一行 warning、`e_entry` 留空 ⇒ 内核把控制权交给非法地址 ⇒ `SIGSEGV`，发生在 `main()` 之前。
- 因为构建全程 rc=0、产物齐全，症状看起来像「配方 / GTK / 自签名 / 运行时依赖」问题，而真正的证据（`Entry point` 为 0 或那行 warning）都极易被漏读。

### 定位过程（可复用）

设备 `ptrace` 被拒（`gdb` 报 `Could not trace the inferior process`），ASan 的 fake-stack 在本设备上自身不可靠（报 `asan_fake_stack.h:133` 的 wild jump）。可用的组合是：**自写 `LD_PRELOAD` SIGSEGV handler**（`SA_SIGINFO`，读 `ucontext_t->uc_mcontext.pc`，`_Unwind_Backtrace` 走栈）——本设备 `sigaction` + 同步 SIGSEGV 投递**可用**（与 valgrind 内部信号链路的结论不同）。但本例最快的判据不是栈，而是**直接读构建日志里的那一行 warning 和 `readelf -h` 的 `Entry point`**。

## 解决方案

### 推荐方案

补丁**生成物** `src/Makefile.in`（不要同时改 `Makefile.am`，否则会触发 automake 重新生成 `Makefile.in`，而设备/worker 上通常没有 automake）：

```diff
--- a/src/Makefile.in
+++ b/src/Makefile.in
@@
 # -export-dynamic is need for defining handlers in the glade file.
-AM_LDFLAGS = -Wl,--as-needed  -export-dynamic
+AM_LDFLAGS = -Wl,--as-needed  -Wl,--export-dynamic
```

复核：

```sh
readelf -h <bin> | grep 'Entry point'      # 必须是非 0 的可执行地址
<bin> --version                            # rc=0，且有正常输出
```

诊断命令（判「是不是这个坑」）：

```sh
# 1) 构建日志里找这一行——有它基本就确诊
grep -n 'cannot find entry symbol' <build log>
# 2) 入口点为空
readelf -h <bin> | grep -i 'entry point'
```

### 回退方案

若不方便补丁生成物：在 `LDFLAGS` 里追加 `-Wl,-e,main` 之类强制入口符号，或在配方里覆盖 `AM_LDFLAGS`（`make AM_LDFLAGS=...`）。两种都属绕行，推荐方案才是把上游写法本身修正。

### 禁止做法

- ❌ 不要看到 `rc=139` 就去改 GTK / 自签名 / 运行时依赖；先读 `readelf -h` 的 `Entry point` 和链接期 warning，否则会在错误方向上耗掉数小时。
- ❌ 不要把 `-export-dynamic` 整个删掉当「修复」：ptask 靠 `--export-dynamic` 让 glade 里的信号处理函数可被动态解析，删掉会破坏 GUI 回调绑定。

## 验证

```sh
# 修复前
readelf -h <bin> | grep 'Entry point'          # 0x0
<bin> --version                                # rc=139
# 修复后（ptask 1.0.0 实测）
readelf -h <bin> | grep 'Entry point'          # 非 0
<bin> --version                                # rc=0，输出 'ptask 1.0.0'
```

ptask 1.0.0 上修复后 `test_package` 14/14 条断言通过、`--selftest` 23/23 条检查通过。

## 关联条目

- 相似主题：`-Wl,` 前缀缺失 / 驱动与链接器参数语义不一致（clang 转发 GCC 专有选项）
- 本包另有一条非链接期缺陷（`pstr.c` 的 `trim()` 漏拷 NUL：`memmove(str, p, strlen(p))`），无日志签名，登记在 ptask 的 `notes.md` 与本 PR 正文，不单独建条目
