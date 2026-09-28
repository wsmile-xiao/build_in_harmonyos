# nuvie 0.5 — patch_ng 的 hunk 区间重叠会让 `apply_conandata_patches` 抛 IndexError（草稿）

**Category**: conan, build, patch, ohos, ci · **Severity**: 3 · **Tool**: conan

## 症状

`conan create` 在 `build()` 里 `apply_conandata_patches(self)` 一行炸掉，报
`IndexError: list index out of range`，**栈里没有用户代码**：

```
nuvie/0.5: Apply patch (portability): configure 用 umask 022 建临时目录，规避 HMDFS 0700 目录不可写
nuvie/0.5: ERROR:
ERROR: nuvie/0.5: Error in build() method, line 81
	apply_conandata_patches(self)
	IndexError: list index out of range
```

迷惑点有三条：

1. `Apply patch (...)` 那行**已经打印出来了** —— 说明 conandata 解析成功、补丁文件
   也读到了，不像"文件不存在/格式错"；
2. 同一个 `.patch` 手工用 GNU `patch -p0 < x.patch` 打**完全成功**；
3. 报错类型是 `IndexError` 而不是 `ConanException` —— 它不是 conan 的校验报错，
   而是 conan **内部调用的第三方库 `patch_ng`** 崩了。

## 根因

Conan 2 的 `conan.tools.files.patch()` 用内置的 `patch_ng`（纯 Python）打补丁，
**不是** GNU `patch(1)`。`patch_ng.PatchSet.apply()` 校验 hunk 的循环
（`patch_ng.py` 的 `apply()`）对源文件**只扫一遍**，并且：

- `hunkfind`（当前 hunk 的源侧期望行）**只在 `行号 == hunk.startsrc` 那一刻**才
  重算（`patch_ng.py:1132-1134`）；
- 当前 hunk 的最后一行源侧行被消费掉时，它把 `hunkno` 推进到下一个 hunk
  （`patch_ng.py:1168-1173`），**但不会重算 `hunkfind`**。

两者相安无事的**前提是 hunk 在源文件里按区间递增且互不重叠**。一旦后一个 hunk 的
`startsrc` 落在前一个 hunk 覆盖的区间**之内**：

1. 校验到前一个 hunk 末行时 `hunkno` 被推进；
2. 下一个 hunk 的 `startsrc` 是**已经走过**的行号，`行号 == hunk.startsrc` 再也不会
   成立 → `hunkfind` 永远停留在前一个 hunk 的列表上；
3. 而校验条件 `行号 < hunk.startsrc + len(hunkfind)` 仍然成立，于是
   `hunkfind[hunklineno]` 的 `hunklineno` 一路自增到越界 → `IndexError`
   （实测崩在 `patch_ng.py:1142`）。

nuvie 的实例：两处 `umask 077→022` 被写成了两个 hunk，`@@ -5651,7` 覆盖
5651..5657，`@@ -5656,7` 又从 5656 起 —— 后者的起点落在前者区间内，于是必炸。
GNU `patch(1)` 对此**没问题**（它按 hunk 逐段在源文件里重新定位），所以"手工能打"
完全不能作为"Conan 能打"的证据。

> 判据：**Conan 下 hunk 必须按源文件区间严格递增且首尾不重叠。**
> 注意判的是**源侧区间**（`-` 那半），与 `+` 那半无关；hunk 头里的行数
> （`len(hunkfind)` = 该 hunk 里 `' '` 与 `-` 开头的行数）才是有效长度，
> 而不是 hunk 头声明的 `,n`。

## 处置（可复用）

**把重叠的 hunk 合并成一个。** 两处改动通常本来就挨得很近（同一个代码块），
合并后 hunk 头行数 = 合并区间内的源侧行数，`@@ -5651,12 +5651,12` 一次覆盖
5651..5662，全部上下文都在同一个 hunk 里就没问题。合并时注意：

- 两处 `-`/`+` 对都要保留，顺序按源文件里的先后；
- 落在两段之间的上下文行只写一次（不要重复，否则源侧计数与 hunk 头不符）；
- 合并后**重新核对 hunk 头的源/目标行数**：源侧 = 上下文 + `-` 行数，目标侧 =
  上下文 + `+` 行数（本实例 12 / 12）。

不能合并时（两处相隔很远，硬合并会拖进大段无关上下文）的等价改法：**把后一个
hunk 的上下文整体下移，使它的 `startsrc` 严格大于前一个 hunk 的
`startsrc + len(hunkfind) - 1`**；或干脆**拆成两个 patch 文件**，各自只有一个 hunk，
由 conandata 依次列出（conan 会按顺序分别调用 `patch()`，各扫一遍，互不影响）。

### 怎么提前发现

写补丁后别只看 `git apply` / `patch(1)` 能不能打。按下面规则扫一遍：

- 把一个 `.patch` 按 `--- `/`+++ ` 行切分成若干 item（**不同文件之间的 hunk 不
  相互约束**，误报全部来自跨文件的假阳性）；
- 每个 item 内，对相邻 hunk 检查
  `next.startsrc <= prev.startsrc + (prev 中 ' ' 与 - 开头的行数) - 1`；
- 命中即为必炸（或至少必判 `premature end of source file`）。

本地复现（定位到真因的最快路径）：

```python
import patch_ng
ps = patch_ng.fromfile("<the>.patch")
ps.apply(strip=0, root="<源文件所在目录>")   # 抛 IndexError 时栈帧局部变量里
                                            # hunkfind 的长度 = 上一个 hunk 的
                                            # 长度、hunklineno 已越界 —— 一眼定罪
```

## 退路

- **hunk 太多、合并后不可读**：拆成多个 `.patch` 文件，每个文件一个 hunk，
  conandata 里按顺序列出，`patch_description` 分别写。
- **确实无法避免顺序倒错**（后一个 hunk 的源位置在前一个之前）：这也是
  `patch_ng` 的硬限制（它是单遍扫描），唯一出路是把它们排成递增顺序，或拆文件。
- **不要在 conandata 里加 `strip` 试图绕过**：`strip` 只影响源/目标文件名的层级
  解析（`a/`、`b/` 前缀剥离），与 hunk 定位完全无关。nuvie 这个补丁的
  `strip` 无论取 0 还是 1 都会走到同一个崩溃点。

## 验证

- 用 GNU `patch -p0` 能打 **且** 用 `patch_ng` 复现 `IndexError`（两者都做一遍，
  才能确认是"补丁写法"而不是"环境/路径"问题）；
- 合并成单 hunk 后，用 `patch_ng.fromfile(...).apply(strip=0, root=<源目录>)`
  对**源文件副本**实跑，返回 `True`、两处替换都落到目标行、且不留 `.orig` 备份；
- 提交后由 CI 实跑 `conan create` 验证（`Apply patch` 行之后不再有 `ERROR:`）。

nuvie 0.5 实测：合并前 `IndexError`，合并后 `patch_ng` 返回 `True`，
5654 / 5659 两行均替换为 `umask 022`、源文件里 `umask 077` 归零。

## 关联

- `archives/n/nuvie/0.5/patches/0001-configure-umask.patch`
- `archives/n/nuvie/0.5/notes.md`（"补丁"一节记录了这次改写）
- 同类先例（单 hunk、无重叠，可直接对照）：
  `archives/s/sdl_image/1.2.12/patches/0001-configure.patch`、
  `archives/b/ballandpaddle/0.8.1/patches/0001-configure-umask.patch`
- 知识库条目 **E011**（HMDFS umask 0700 那条；本例是它的"补丁怎么写"补丁包）
