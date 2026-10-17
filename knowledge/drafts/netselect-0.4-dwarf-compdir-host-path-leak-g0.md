# DRAFT: `-g` DWARF 的 comp_dir 把构建目录绝对路径写进二进制，宿主路径泄漏检查必挂

> 草稿（DRAFT）。与同目录 `netselect-0.4-dwarf-compdir-host-path-leak-g0.kv` 成对。
> 实证来源：netselect 0.4 真机（2026-09-29，r3 后 test_ohos T2 失败）。

## 现象

CI 门禁全绿（L0-L5 pass），但 OHOS 专项检查（test_ohos T2 / 任何
`strings <bin> | grep -E '/storage/|/home/|/Users/'` 类宿主路径泄漏检查）
失败：

```
$ strings bin/netselect | grep -E '/storage/|/home/|/Users/'
/storage/Users/currentUser/ohos-users/codex/netselect-0.4-20260929/conan-home/p/b/.../b
```

泄漏的正是**构建目录本身**，且源码里没有任何该路径字符串。

## 根因

上游 Makefile 默认 `CFLAGS = -O2 -Wall -I. -g`。`-g` 产生的 DWARF 调试信息
（DW_AT_comp_dir / DW_AT_name）会把编译时的工作目录绝对路径嵌入 ELF。
真机构建目录在 `/storage/Users/...`（HMDFS 用户路径），于是路径泄漏检查
必然命中。这与源码硬编码路径（真正的泄漏 bug）机理不同——产物功能无害，
但泄漏检查无法区分二者。

注意区分既有条目：`DRAFT-ci-lowmem-worker-link-oom-mitigation` 里的 `-g0`
是**链接 OOM 削峰**语境；本条是**产物路径泄漏**语境，触发条件和检查点不同。

## 解决方案

配方 `build()` 覆盖 CFLAGS，将 `-g` 改为 `-g0`（禁用调试信息）：

```python
cflags = "-O2 -Wall -g0 ..."   # 原 -g → -g0
self.run(f"make CC={cc} CFLAGS={cflags!r} -j1", cwd=self.source_folder)
```

验证：

```sh
strings <bin> | grep -cE '/storage/|/home/|/Users/'   # 期望 0
```

## 复用要点

- OHOS 上游 Makefile 带 `-g` 的**应用程序类**包（bin/ 产物会被 strings 检查），
  在配方层改 `-g0` 是标准动作；库类若无人 strings 检查可不改。
- 若确需调试信息，可用 `-ffile-prefix-map=<builddir>=.` 重写路径，但 OHOS
  clang 版本支持度需验证，`-g0` 最稳。
- 排查顺序：先 `strings` 命中的内容是否等于 `$PWD`/构建目录 → 是则 DWARF
  comp_dir（改 -g0）；若命中源码逻辑相关路径 → 真泄漏，须查源码。
