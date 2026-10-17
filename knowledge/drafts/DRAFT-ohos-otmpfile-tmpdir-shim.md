# DRAFT-ohos-otmpfile-tmpdir-shim — 库硬编码 P_tmpdir/O_TMPFILE 无视 TMPDIR 的 LD_PRELOAD 重定向

> **Contributor**: ohpcd | **Status**: DRAFT | **Updated**: 2026-09-02
> **Severity**: 🟡 medium | **Category**: testing / tmpdir / filesystem / ld-preload

## 相关既有条目（同族差异化定位）

本技能与既有条目共享"/tmp 只读、临时文件失败"背景，但问题类与拦截面不同，
**非重复条目**；申报路径 B 时以此差异化定位为准。

| 既有条目 | 收录状态 | 同族点 | 本 skill 的增量（差异化） |
|---------|---------|--------|--------------------------|
| **E002** | 正式收录 | /tmp 只读 erofs、TMPDIR 根因 | 非本题——本条目以其为根因上下文；E002 解决"脚本遵守 TMPDIR"的场景，本条目处理"库根本不查 TMPDIR"的场景 |
| **E272**（arm-none-eabi-binutils） | 正式收录 | LD_PRELOAD tmpfile shim、OHOS libc tmpfile() 忽略 TMPDIR 报 EACCES | ①E272 只拦 `tmpfile()`（mkstemp+unlink+fdopen）；本 shim 新增 **open() O_TMPFILE 旗标改写**（O_CREAT\|O_EXCL+立即 unlink，保持无名语义）——O_TMPFILE 路径 E272 完全未覆盖；②问题类不同：E272 是 **libc tmpfile() 忽略 TMPDIR**，本条目是**库硬编码 P_tmpdir("/tmp") 且从不查询 $TMPDIR**（连 tmpfile() 回退都救不了 open(O_TMPFILE) 主路径）；③四级可写目录回退链（$TMPDIR→$TMP→$TEMP→$HOME/tmp） |

> index.tsv 查证（2026-09-02）：`O_TMPFILE` 命中 0 条、`P_tmpdir` 命中 0 条、
> `TMPFILE` 仅 E272——无正面撞车，本条目为 E272 同族的 open(O_TMPFILE) 增量。

## Scope（何时用）

在 HarmonyOS PC 上运行任何 C 库的上游测试/消费者测试时，若出现：

- 库在运行时（非构建期）创建临时文件失败，且堆栈指向 `open(..., O_TMPFILE)`
  或 `tmpfile()`；
- 源码中临时目录来自 `P_tmpdir` 宏（stdio.h 默认 `"/tmp"`）或硬编码路径，
  **不读取 `$TMPDIR`**；
- 已确认 `/tmp` 只读（erofs，E002）、环境已注入可写 `TMPDIR` 但仍失败。

典型实例：cairo `_cairo_ps_surface_create_internal -> _cairo_tmpfile()`
（cairo-misc.c）——每个 `cairo.PSSurface(...)` 失败。纯 Python/脚本类临时文件
问题（mkstemp 遵守 TMPDIR）不适用本条目。

## Symptom

```text
cairo.PSSurface(...)
→ CAIRO_STATUS_TEMP_FILE_ERROR: error creating or writing to a temporary file
# /tmp 只读（erofs）；注入 TMPDIR 无效——库从不查询 TMPDIR
```

## Root Cause

1. POSIX `tmpfile()`/`O_TMPFILE` 的目录来源是实现定义的：glibc/musl 的
   `tmpfile()` 用 `P_tmpdir`，cairo 的 `_cairo_tmpfile()` 直接 `open(P_tmpdir,
   O_TMPFILE)` 再回退 `tmpfile()`——**两级都绕开 `$TMPDIR`**；
2. HarmonyOS `/tmp` 挂载为只读 erofs（E002），`P_tmpdir` 指向的目录必然不可写；
3. 这类失败发生在测试进程运行时，改配方环境变量、换构建目录均无效——
   拦截面只能在 libc 调用层。

## Recommended Solution

LD_PRELOAD shim（`ohos_tmpdir_shim.c`，随配方在 build() 编译，**仅注入测试
进程，不进生产 package**）：

1. **拦截面最小化**：只拦 `open()` 中带 `O_TMPFILE` 旗标的调用与 `tmpfile()`；
   其余 open/dlopen 等全部透传。OHOS musl 上 `open64` 是 `open` 的宏别名，
   无需单独拦截；
2. **目录解析**：依次探测 `$TMPDIR → $TMP → $TEMP → $HOME/tmp`，取首个可写
   目录（`access(W_OK)`）；
3. **语义保持**：`O_TMPFILE` 调用改写为
   `(flags & ~(O_TMPFILE|O_DIRECTORY)) | O_CREAT | O_EXCL`，创建后立即
   `unlink()`——对进程而言文件无名，与 O_TMPFILE/tmpfile() 语义一致，
   不会留下垃圾文件；
4. **签名**：产物 `.so` 经 `/data/service/hnp/bin/binary-sign-tool` 签名，
   否则 AppSpawn/hmmac 拦截加载（E212）；若仍被拦截，走 fallback
   （capability-scoped 豁免 + excluded_cases 如实声明）；
5. **注入点**：conanfile.py 在 `build()` 运行上游 pytest 前设置
   `LD_PRELOAD=<abs>/ohos_tmpdir_shim.so`。

## 双库实证

| 库 | 角色 | 结果 |
|----|------|------|
| **pycairo/1.29.0** | 主验证（main 已含同款 `ohos_tmpdir_shim.c`） | ✅ PSSurface 相关 pytest 用例真实执行通过，上游 287/287 |
| **python3-cairo/1.29.1** | 二次验证（PR !7647） | ✅ 同款 shim 复用，上游 287/287（100%），3 个 numpy/pygame 门控用例按硬门禁排除并声明 |

## 测试覆盖边界

- shim 是**测试环境兼容层**：只影响测试进程的临时文件落点，不进入
  package 产物，不改变库本身行为；上游 PS surface 的临时文件语义
  （无名、自动回收）在 shim 下保持不变；
- 声明通过率时：shim 救回的用例计入真实执行；确因 E212 无法注入的场景
  走 fallback 逐个豁免并说明，不整体填 N/A（rule 4）。
