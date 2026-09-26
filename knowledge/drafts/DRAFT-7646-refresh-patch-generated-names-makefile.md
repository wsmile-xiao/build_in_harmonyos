# DRAFT — refresh-patch 的「生成物名单」吞掉你改过的 Makefile，报「无差异，保留现有补丁」

> Status: DRAFT (contributor 主理-64) | Source: jmeters/0.4.5 adaptation, task #7646
> Environment: HarmonyOS PC aarch64（B 机）, Conan 2.29.1 (OHOS), ohc `refresh-patch --auto` / `finish`
> 关联 Issue：#3445（https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos/issues/3445）

## 1. 症状（一手读数，逐字）

本包唯一的补丁目标就是**被修改过的上游 `source/Makefile`**（去 `-march=native`、
`install` → `$(INSTALL)`）。在手工准备的 `.orig` / `.work` 两棵树上跑 `refresh-patch --auto`，
工具连续多轮输出成功并声称"无需新补丁"：

```
  ℹ️ refresh-patch --auto jmeters 0.4.5
  ❌ 无法定位源码目录: orig=None, work=None
  ℹ️   ⚠️ 无编辑追踪器，使用排除规则扫描差异...
  ℹ️   扫描差异文件...
  ✅   无差异，保留现有补丁
```

同一时刻 `diff -u` 两棵树的 `source/Makefile` 实证差 5 行（`+5/-5`）。也就是说：
**改动是真的、`git diff` 看得见、`diff -u` 看得见，只有补丁生成器"看不见"**，并且它以
rc=0 退出、把旧补丁原样留在 `patches/`，看起来像"已经生成过了"。

日志位置（设备 `~/tmp/uc2/z64-jmeters/`）：

| 读数 | 文件:行 |
|---|---|
| `⚠️ 无编辑追踪器，使用排除规则扫描差异...` | `round2-refreshpatch.log:3`、`round2-e.log:41`、`round2-g.log:28`、`round2-h.log:70`、`round2-k.log:89`、`round2-l.log:22`、`round2-rp3.log:2`、`round2-rp4.log:2`、`round2-rp5.log:2` |
| `✅ 无差异，保留现有补丁` | 同上各文件的下一处（`round2-refreshpatch.log:5`、`round2-e.log:43`、`round2-g.log:30`、`round2-h.log:72`、`round2-k.log:91`、`round2-l.log:24`、`round2-rp{3,4,5}.log:4`） |
| 反例（有基线但无变更）`ℹ️ 无追踪到的变更` | `round2-l.log:19` |

第 2 棒复跑 `finish` 时同一条链再次出现（`w3-r1.log` 第 20-23 行：
`❌ 无法定位源码目录: orig=None, work=None` → `⚠️ 无编辑追踪器...` → `✅ 无差异，保留现有补丁`），
⇒ 该机制**每次重跑都会重新触发**，不是历史一次性事故。

## 2. 根因（行号已在 HEAD `1bdd1b0` 逐行复核）

`scripts/ohc/refresh_patch.py`：

- `:22` 注释自己写着名单的适用面——`# Known build-system generated file names (only used for NEW files in right_only)`；
- `:23-26` `_GENERATED_NAMES = frozenset({"Makefile", "config.h", "libtool", "stamp-h1", "stamp-h", "config.cache", "config.h.in~", "configure.lineno"})`；
- `:46` `def _is_likely_generated(...)` → `:59-60` `if name in _GENERATED_NAMES: return True`；
- `:184` `def _classify(mod_file)`，`:186-188` 把 `_is_likely_generated` 的 `True`（生成物）翻成 `False`（不要这个文件）；
- **关键错配**：`:215` `for f in dcmp.diff_files:` 是"**两边都存在但内容不同**"= 被修改的源文件分支，
  `:220` 却同样执行 `verdict = _classify(mod_file)`，`:221-222` `if verdict is False: continue`
  ——被改过的 `Makefile` 在这一步就被 `continue` 掉了，既不进 `diff_pairs` 也不进 `uncertain_pairs`；
- `:370` `auto_mode()` → `:386` `use_tracker = has_tracker(work_dir)` → 无追踪器时 `:416` 打印
  「⚠️ 无编辑追踪器，使用排除规则扫描差异...」、`:418` `_find_differences(orig_dir, work_dir)`；
- `:430-432` `if not diff_pairs:` → `log_ok("  无差异，保留现有补丁")` → `return 0`（**成功退出码**）。

对照分支：`:390-413` 的**精准模式**（有 `.edit-tracker.json`）只按追踪器列表
`diff_pairs.append(...)`，**全程不调用 `_classify`** ⇒ 同一个被改过的 `Makefile` 在这条路上会被正常打进补丁。
注释里的"only for NEW files"与 `diff_files` 分支的实际调用相互矛盾，就是本条知识的全部内容。

## 3. 判据（写进配方笔记的一句话）

> **`git diff`（或 `diff -u .orig .work`）看得见改动，而 `refresh-patch` 报「无差异，保留现有补丁」
> ⇒ 立即怀疑此机制**，第一动作是查改动文件名是否命中 `_GENERATED_NAMES`
> （`Makefile` / `config.h` / `libtool` / `stamp-h*` / `config.cache` / `configure.lineno`），
> 而不是去怀疑自己的补丁写坏了。

自检两条读数：命中时 `refresh-patch` 的输出里必然同时有「无编辑追踪器」（走了规则回退分支）
与「无差异」两行；若输出是「追踪到 N 个文件变更 / 精准模式: 只对 N 个追踪文件生成补丁」，则与本机制无关。

## 4. 绕行（本包实测有效，且不改框架）

追踪器基线**只能**由模块级 API 建立，CLI 没有重置基线的入口：

- `scripts/ohc/edit_tracker.py:256-280` 的 `track-edit` 子命令只有 `scan`（:263）/ `add`（:269）/ `list`（:275），
  **没有** `snapshot`；`track-edit add` 在无基线时报「`.edit-tracker.json` 不存在，先运行 snapshot」；
- 唯一的建基线函数是 `scripts/ohc/edit_tracker.py:73` `def snapshot(work_dir, software="", version="")`，
  框架内部只有 `scripts/ohc/init_build.py:337` `edit_tracker_snapshot(work_dir, software="", version="")` 调它
  ——也就是说 `init-build` 建过基线的包才天然走精准模式，绕开 `init-build` 手搭两棵树的包必须自己补这一步。

因此本包的做法（驱动脚本 `r2m.sh`）：手工构造纯净 `.orig` 与改过的 `.work` 两棵树 →
用小驱动调用 `edit_tracker.snapshot()` 建基线 → `refresh-patch --auto`。转绿读数：

```
  ℹ️   追踪到 1 个文件变更:
  ℹ️   精准模式: 只对 1 个追踪文件生成补丁（无需排除规则）
```

（`round2-m.log:76,78` 与 `round2-rp6.log:5,7`；随后 `✅ 生成 1 个补丁`，
产物即入库的 `patches/0001-source-Makefile.patch`，正文 `+5/-5`。）

生成后**必须**逐行核对补丁正文再入库：`grep -n "^[-+]" archives/j/jmeters/0.4.5/patches/0001-source-Makefile.patch`。

## 5. 适用范围与边界

- 适用：补丁目标文件名命中名单的包——**裸 Makefile 上游**（kokkinizita 系、suckless 系、
  一切"改一行 Makefile 就要出补丁"的家族）最典型；改 `config.h` / `libtool` 的包同理中招。
- 不适用：只新增文件（`right_only` 分支）或改的是 `.c/.cc/.h` 等源码扩展名的包——
  那些文件名单不认识，会正常进 diff。
- ⛔ 不要为了"让规则路径认出 Makefile"去删 `_GENERATED_NAMES` 里的条目：那是框架文件（要单独 PR），
  而且 configure 生成的 `Makefile` 确实需要被排除；本条给的是不改框架的绕行路径。
- ⚠ 与 `finish` 的幂等性叠加时后果更糟：`finish` Step 1 每次都会重跑 refresh-patch，
  本包第 2 棒 `finish` 又打印了一次「无差异」（见 §1 末），此时若上一轮用的是**手工补丁**，
  重跑不会纠正它，只会维持现状——分类回填要放在最后一次 `finish` 之后。

## 6. 查重与新增价值

| 检索面 | 关键词 | 读数 |
|---|---|---|
| `knowledge/graph/*.kv` | `edit-tracker` / `_GENERATED_NAMES` / `无差异` | **0 命中** |
| `knowledge/graph/*.kv` | `refresh-patch` | 只命中 `E066.kv:2,6,8,13,16,19`（讲补丁管线只认 `.tar.gz`，**异机制**） |
| `knowledge/graph/*.kv` | `track-edit` | `E090.kv:31`、`E095.kv:45`、`E249.kv:19`、`E503.kv:34`——只给推荐命令，无本症状 |
| `knowledge/drafts/` | 同题条目 | `DRAFT-8543-refresh-patch-rename-conandata-desync.kv:17`（补丁改名致 conandata 失配）、`:32`（"`snapshot` 不是合法子命令…无官方基线重置入口"） |
| `经验文档/B草稿库/` + `手册/07` | `refresh-patch` / `track-edit` / `edit-tracker` / `_GENERATED_NAMES` | **0 命中** |

与 `DRAFT-8543` 是**同题的相反面**：那条讲"工具把补丁改名/重置分类"（改动**被带走**），
本条讲"工具把改动**判成不存在**"；那条的 `:32` 断言"没有官方基线重置入口"，
本条的一手读数是"**模块级 API `edit_tracker.snapshot()` 就是入口**，CLI 只是没暴露"，
并据此给出了可复现的绕行动作（§4）。两条互不覆盖，引用方向为本条指向它、而非重复它。
