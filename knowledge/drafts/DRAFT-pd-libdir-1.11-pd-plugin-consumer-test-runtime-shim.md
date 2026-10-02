# draft-pd-libdir-1.11-pd-plugin-consumer-test-runtime-shim

> Status: **Draft**（待审核 promote）| severity: `3` | category: `testing|toolchain` | Updated: 2026-10-01
> 对应: `knowledge/drafts/DRAFT-pd-libdir-1.11-pd-plugin-consumer-test-runtime-shim.kv`

---

**匹配关键词**：pd, puredata, pd_linux, externals, dlopen, dlsym, -rdynamic, export-dynamic,
sys_register_loader, sys_trytoopenone, namelist_append, gensym, class_new, t_symbol, t_atom, m_pd.h, libdir

## 症状

想给 Pd externals（`*.pd_linux`）写**真实**的消费者测试时，会撞上三件事：

```text
# 一、根本无法链接
undefined reference to `class_new' / `sys_register_loader' / `gensym'
# 仓库里没有 libpd.so：Pd 是 application 可执行文件，靠 -rdynamic 导出符号

# 二、shim 用单槽位 gensym → 断言读到错误的值
  FAIL the added path is encoded as "+<library-dir>" (got "add-to-path", want "+/tmp/.../demolib")

# 三、shim 把 sys_trytoopenone 的 dir 原样回显 → 插件登记了错的目录
  FAIL the added path is encoded as "+<library-dir>" (got "+/tmp/pdld/scratch", want "+/tmp/pdld/scratch/demolib")
```

## 根因

Pd（`puredata` 包）是 `application` 可执行文件，用 `-rdynamic` 链接把 Pd API 符号导出到
**自己的动态符号表**；Pd externals 因此**不链接任何库**，全部 Pd 符号在 dlopen 时从 Pd
进程映像解析。所以制品仓里没有可供消费者链接的 `libpd.so`（本仓 `archives/l/libpd/0.16.1`
是另一条路线——它自己构建 `libpd.so`）。

要测 Pd 插件，只能走 Pd 本人的路数：**导出同名符号 + dlopen**。而 shim 一旦与 Pd 真实
ABI 语义有细微差异，就会出现上面三个症状：

1. **`gensym` 必须驻留**：Pd 对每个不同的名字返回一个固定的 `t_symbol`。libdir 的代码先
   `SETSYMBOL(at, gensym("+<dir>"))` 把符号存进 atom，**之后**才求值
   `gensym("add-to-path")`。shim 若复用同一个静态槽位，后一次 `gensym` 会覆盖已存的 atom
   → 断言读到 `"add-to-path"`（症状二）。
2. **`sys_trytoopenone` 的 `dirresult` 是「找到的文件的目录」，不是传入的搜索条目**
   （对齐 Pd `src/s_path.c:265`）：先把 `dir + "/" + name + ext` 拼进 `dirresult`，
   `open()` 成功后在**最后一个 `/`** 处截断，`*nameresult` 指向 basename。
   libdir 登记的是 `dirresult`，shim 原样回显 `dir` 就会让插件登记错目录（症状三）。
3. **`t_class` / `t_pd` 在公开头文件里只有前置声明**：`static t_class cls;` 编译报
   `variable has incomplete type 'struct _class'`，要用 `max_align_t[]` 静态存储冒充。

## 推荐方案（`dlopen-rtldnow-with-exported-pd-symbol-shim + interning-gensym + faithful-sys-trytoopenone + opaque-storage-for-incomplete-types`）

1. `readelf --dyn-syms <plugin>` 列出 GLOBAL UND，逐个提供定义。pd-libdir 1.11 共 15 个：
   `sys_getversion` `sys_register_loader` `logpost` `gensym` `class_new` `pd_new`
   `pd_typedmess` `namelist_append` `sys_isabsolutepath` `sys_trytoopenone` `sys_close`
   `sys_searchpath` + `canvas_open` `open_via_path` `canvas_getenv`。
   签名一律取自 `m_pd.h` / `s_stuff.h` / `g_canvas.h`，不要手写，避免类型不匹配。
2. 消费者程序用 `-rdynamic` 编译（CMake 里是 `ENABLE_EXPORTS ON`）以导出自己的动态符号表。
3. `dlopen(plugin, RTLD_NOW|RTLD_LOCAL)` → `dlsym("setup")` → 调用真实 `setup()` →
   取回注册的 loader → 用真实磁盘上的 `<lib>/<lib>-meta.pd` 驱动它，断言
   `pd_typedmess("pd", "add-to-path", "+<library-dir>")`。
4. 把不该走的旧版/画布路径（`canvas_open` / `open_via_path` / `canvas_getenv`）实现成
   一旦被调用即 `exit(1)`，顺带钉住插件的调用图。

## 验证

`pd-libdir/1.11` conan create 全绿，test_package **22/22** 断言通过，且 CI **L1e 破坏性
反向验证**通过（移走 `lib/` 后测试确实失败 → 证明测试真依赖被测包，不是 echo 空壳）。
上述两个语义坑在开发中各复现一次并逐一修正。

---

*本文件由 `knowledge/drafts/DRAFT-pd-libdir-1.11-pd-plugin-consumer-test-runtime-shim.kv` 字段派生；内容与 kv 一致，待主编审核 promote 后转入 `knowledge/doc/`。*
