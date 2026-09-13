# E573 — raw Makefile 配方手工拼接 GnuToolchain 的 CFLAGS 时，defines 是裸宏名（缺 -D 前缀）

> Contributor: Awstme <awstme@qq.com> | Status: Draft | Updated: 2026-09-11
> Source: dbview 1.0.4 适配（G2 首轮 conan create 失败 → 修正后 PASS）

## 编号说明（原号 E570 → 现号 E573）

本条目初选编号为 **E570**，经 W4 独立审计指出与已占用编号撞号，故改用 **E573**。
原号 E570 有**两个**独立占用者（后者为并发撞号，与本条目的关系更典型）：

- **占用者 1（文本引用形态）**：上游主线 `archives/l/libmobi/0.12/conanfile.py:248` 的注释
  `# E570：上游 make check 自动化（不可手工 sed）`——该编号已被用于**另一主题**。
  该引用只存在于代码注释中，没有 `E570.kv`/`E570.md`，按 workflow 第 9.1 节的四类文件命名形态
  扫描全部落空，属"悬空但已被引用"的占用，**只有叠加主线文本引用扫描才能发现**。
- **占用者 2（并发真实草稿）**：`wt-dazzdb-1.0-git20250217.a3eefd4/knowledge/drafts/`
  下的 `E570-draft-EB2A.kv`（`id: E570`，另一主题），创建时间 2026-09-11 01:16，
  **晚于本条目取号（00:23）、早于本说明撰写**。这是 workflow 第 9.1 节描述的
  "并发适配任务共享同一 drafts 池、无事务性占用"导致的典型并发撞号
  （同节登记的 E561/E565 先例同型）：`graph add` 只按落盘文件名查重，两个任务在同一时间窗
  各自取到 E570 并静默共存。
- **换号口径**：核查改为「跨 worktree 文件形态扫描」+「主线文本引用扫描」两口径取并集
  （后者必须用整词边界，否则 `13DE5726FA…` 这类 sha256 子串会造成假占用）。
  并集后 E543–E572 全部已占用，首个空号即 E573。按占用形态分两类：
  1. **已被上游主线追踪**（`git ls-tree -r upstream/main -- knowledge/drafts` 可见，
     因此存在于每个 worktree 的检出中）：`E543`–`E567`；
  2. **其他任务尚未合入的本地草稿**（仅存在于各自 worktree，主线不可见）：
     `E568`/`E569` → `wt-crashmail-1.7/knowledge/drafts/`（`E568-draft-5818.*`、`E569-draft-EDF5.*`）、
     `E570` → `wt-dazzdb-1.0-git20250217.a3eefd4/knowledge/drafts/E570-draft-EB2A.kv`、
     `E571` → `wt-libtsm-4.3.0/knowledge/drafts/DRAFT-E571-ohos-libcheck-temp-env-first-probe.*`、
     `E572` → `wt-cube2font-1.5.1/knowledge/drafts/DRAFT-E572-removed-config-script-pkgconfig-migration.*`。
  这说明**只扫主线或只扫本 worktree 都不足以完成全池核查**：第 2 类占用在主线里完全不可见。
- 记录该冲突与口径的原因：这两个漏检点（只扫文件形态会漏注释引用；全池核查必须跨 worktree
  且覆盖 `DRAFT-<ID>-*` 形态）已作为工具侧反馈提交。

## 错误特征

`conan create` 在 `build()` 的 `self.run(...)` 处失败，日志形态：

```text
dbview/1.0.4: RUN: make -j1 CC="/data/service/hnp/bin/clang" CFLAGS="-O3 NDEBUG"
/data/service/hnp/bin/clang -O3 NDEBUG -c db_dump.c
clang-15: error: no such file or directory: 'NDEBUG'
make: *** [Makefile:36: db_dump.o] Error 1

dbview/1.0.4: ERROR:
ERROR: dbview/1.0.4: Error in build() method, line 68
	ConanException: Error 2 while executing
```

关键判据是 `CFLAGS="-O3 NDEBUG"` 里那个**裸 `NDEBUG`**：它没有 `-D` 前缀，于是被 clang
当作输入文件而不是宏定义。错误文本只提 clang 与文件名，完全不指向配方里拼 flags 的那一行。

## 触发条件

- 构建系统：raw Makefile（无 `configure`、无 `CMakeLists.txt`，即 Conan 里没有
  Autotools/CMake/Meson 助手代拼编译参数的工程）
- 配方在 `build()` 里手工拼 CFLAGS，且写成 `tc.cflags + tc.defines`
- `build_type=Release`（或 `RelWithDebInfo`/`MinSizeRel`，此时 `GnuToolchain.ndebug` 非空）

## 根因分析

`GnuToolchain.defines`（`conan/tools/gnu/gnutoolchain.py`）返回的是**裸宏名列表**：

```python
@property
def defines(self):
    conf_flags = self._conanfile.conf.get("tools.build:defines", default=[], check_type=list)
    ret = [self.ndebug, self.gcc_cxx11_abi] + self.extra_defines + conf_flags
    return self._filter_list_empty_fields(ret)
```

`Release` 下 `self.ndebug == "NDEBUG"`，返回值就是 `['NDEBUG']`，**不带 `-D`**。前缀由消费方补：
`AutotoolsToolchain`/`CMakeToolchain` 在生成 `CPPFLAGS`/`DEFINES` 时自行拼 `-D`（MSVC 下 `/D`），
所以按「cflags 那样的裸 flag 列表」直觉使用 `defines` 就会踩空。

raw Makefile 工程没有这层助手：配方自己就是那个「消费方」，必须显式补前缀。

## 解决方案

### 推荐方案

拼接时逐项补 `-D`：

```python
tc = GnuToolchain(self)
# GnuToolchain.defines yields bare macro names (no "-D" prefix), the
# Autotools helpers add the prefix themselves — do the same here.
cflags = " ".join(tc.cflags + [f"-D{define}" for define in tc.defines])
self.run(f'make -j1 CC="{cc}" CFLAGS="{cflags}"', cwd=self.source_folder)
```

修复后同一日志中的编译行变为 `CFLAGS="-O3 -DNDEBUG"`，构建继续走完。

### 禁止做法

- ❌ `" ".join(tc.cflags + tc.defines)` —— 产生 `NDEBUG` 裸参数
- ❌ 用 `os.environ["CFLAGS"] = ...` 绕开（R33：release worker 上环境变量为空会静默降级）
- ❌ 直接丢掉 `defines` —— `Release` 下断言语义会随之改变（与 E259 的 NDEBUG 面相关）

## 验证

```bash
# 失败态：CFLAGS 中出现裸宏名，紧随其后是 clang 的 no such file or directory
grep -m1 'RUN: make' "$LOG"
# 修复态：应打印 CFLAGS="-O3 -DNDEBUG"
grep -m1 'RUN: make' "$LOG"
```

dbview 1.0.4 实测：修复后 `conan create` exit 0，`test_package` 22/22 通过。

## 关联条目

- 相关: E259（Conan Release 注入 -DNDEBUG 导致 assert 副作用不求值——同一 `defines` 来源的下游后果）
