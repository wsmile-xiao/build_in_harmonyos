# 骨架补丁打错文件：`skel.c` 与 `flex.skl` 内容分叉而 mtime 相同，make 永不重生成

> Draft: `DRAFT-REFLEX-20241231-SKEL-C-FLEX-SKL-MTIME-DIVERGENCE`
> Stem: `reflex-20241231-skel-c-flex-skl-mtime-divergence` — pairs with the same-stem `.kv`

## 基本信息

- **ID**: DRAFT-REFLEX-20241231-SKEL-C-FLEX-SKL-MTIME-DIVERGENCE
- **严重度**: 2
- **类别**: build-system|patch-strategy|determinism
- **触发工具**: make|conan|patch
- **阶段**: patching|compilation

## 错误特征

补丁打在"看起来更像源文件"的 `flex.skl` 上，构建本身还能过，但包自带的
**自举逐字节比对**会失败，diff 恰好落在两文件的写法差异上：

```
$ make check
...
--- scan.c     2026-09-29 ...
+++ initscan.c 2026-09-29 ...
-       yy_c_buf_p = NULL;
+       yy_c_buf_p = (char *) 0;
```

关键取证（同一个发布包内，两文件内容已分叉但时间戳相同）：

```bash
$ ls -la skel.c flex.skl initscan.c
-rw-r--r-- 1 ... 2025-01-01 05:56:16 flex.skl
-rw-r--r-- 1 ... 2025-01-01 05:56:16 skel.c        # ← mtime 与 flex.skl 完全一致
-rw-r--r-- 1 ... 2025-01-01 05:56:16 initscan.c

$ grep -c 'char \*) 0' skel.c initscan.c
skel.c:1
initscan.c:1
$ grep -c '= NULL' flex.skl
# flex.skl 用的是 NULL
```

## 根因

Makefile 用经典的"生成物依赖源"规则：

```make
skel.c: flex.skl mkskel.sh
	sh mkskel.sh flex.skl > skel.c
```

GNU make 的判据是**时间戳**：`flex.skl` 与 `skel.c` mtime 完全相同（tar 打包把整个
发行树归一到同一秒），规则判定"目标已是最新"，于是 **`mkskel.sh` 从不执行**。

结论：**真正生效的构建输入是 dist 包里那个已经存在的 `skel.c`**；`flex.skl` 是陈旧旁支
（它停留在 `NULL` 写法，而 skel.c 与 initscan.c 都已改成 `(char *) 0`）。

因此把骨架补丁打在 `flex.skl` 上会同时踩两个坑：

1. **不生效** —— 构建根本不读它；
2. **误导** —— 一旦某个环境恰好触发了重生成（例如 mtime 因解压顺序改变），补丁内容才
   突然生效，表现为"同一份配方在不同机器上行为不同"。

而 `make check` 的自举比对（重新生成 `scan.c` 与发布版 `initscan.c` 逐字节比）会把这个
不一致直接暴露成 diff —— 极易被误判为"补丁写坏了"。

## 影响范围

- 随包同时附带**生成物 + 生成脚本（或模板）**的源码包：flex/reflex 系生成器、bison 系、
  任何 dist 里 `.c` 与其模板（`.skl`/`.y`/`.l`/`.in`）并存的场景。
- 尤其是 **tar 归档把 mtime 归一到同一秒** 后，本地与 CI 都无法再用时间戳区分新旧；
  `make -j`、增量构建、预下载缓存复用会放大这种不确定性。

## 推荐方案

**方法**: `patch-the-effective-file-and-force-its-mtime`

1. **先判定"谁是真正的构建输入"**：对同一逻辑的候选文件做两件事 ——
   `ls -la`（mtime 是否被归一到同秒）与 `diff -q`（内容是否已分叉）。
   若 **mtime 相等而内容不同**，则 make 不会重生成，生效的是 dist 里已有的生成物。
2. **补丁打在生效文件上**（本例 `skel.c`），不要打模板（`flex.skl`）。
3. **在 recipe 里钉住确定性**：`build()` 内对 source/build 两个目录中的生效文件执行
   `os.utime(path, None)`，使它严格新于模板。这样即便 `mkskel.sh` 有机会运行，也只会
   在补丁生效之后 —— 且不会反向覆盖补丁。**去掉这一步，修复会随构建顺序时有时无。**
4. **用包自带的自举比对验收**：`make check` 的"重新生成 → 逐字节比对"正好验证
   "补丁既生效、又没破坏原有输出一致性"。

## 验证命令

```bash
# 1) 判定生效文件（mtime 相同 + 内容分叉 ⇒ 生成物生效）
ls -la skel.c flex.skl
diff -q <(grep -o 'char \*) 0\|NULL' skel.c | head -1) <(grep -o 'char \*) 0\|NULL' flex.skl | head -1)

# 2) 打补丁后钉 mtime，再跑自举比对
python3 -c "import os; os.utime('skel.c', None)"
make -j1 && make check && echo SELFHOST_OK
```

## 取证记录

- 包: reflex 20241231（`archives/r/reflex/20241231`）
- 环境: OHOS aarch64，clang 15（SDK 26.0.0.18），profile `ci/conan/profiles/ohos-aarch64`
- 逐字证据: `archives/r/reflex/20241231/notes.md`（问题 #2/#3）、
  `reports/w3-local-ci.log`（`Check successful, using COMPRESSION=...` ×7）
