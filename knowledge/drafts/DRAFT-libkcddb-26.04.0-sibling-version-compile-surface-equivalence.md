# E644: 同族小版本任务的「编译面等价性」判定法（复用既有配方前的机械判据）

> 草稿状态：pending-editor-review（最终编号由主编确认）
> 交付实例：libkcddb 26.04.0（任务 #8241，PR !11783）——判定与 26.04.3 编译面等价
> 反例对照：xz 5.8.1 vs 5.8.3（编译面有真实差异，不能仅凭"同族"复用）

## 错误特征（要防的两种事故）

```
# 事故 1：补丁"成功"但带 fuzz/offset 应用
Hunk #3 succeeded at 41 (offset 2 lines).
Hunk #5 succeeded at 118 with fuzz 2.
```

```
# 事故 2：判定为可复用但实际不可用 —— 只在 CI 才暴露
Job ... FAILED: cmake ... error: ...      # 本地"照搬既有配方"看起来没问题
```

触发场景：任务要求的目标版本与制品仓中已有归档版本属于**同族小版本**
（如已有 `libkcddb/26.04.3`，任务要 `libkcddb/26.04.0`）。

## 根因

同族小版本"看起来一样"是很强的先验，但版本之间可能有：

1. **补丁上下文漂移**：上游在版本间改动了补丁命中位置，`patch` 仍能"成功"（offset/fuzz），
   落点却可能与预期不同；
2. **编译面真实改动**：源码 / `CMakeLists.txt` / `tests/` 变了，沿用配方会留下未适配面；
3. **过度保守**：明明等价却重做一遍完整适配，浪费工时。

而 KDE Gear / KDE Frameworks 的小版本差异**常常只落在 `po/` 翻译与配方关闭的子目录**里
（翻译与不参与编译的模块），对产物没有任何影响——这正是判据可以利用的结构。

## 推荐方案：三步机械判定（可复核、可重跑）

对两版本各解包一份，**应用同一个补丁**，然后：

**① 补丁一致性**：`patch -p1 --dry-run --forward` 对目标版本**全部文件**返回 0，
输出无 `with fuzz` / `offset`；应用的文件数应与既有归档 `patches/` 声明一致。

**② 全树差异枚举**：`diff -rq <new> <sibling>` 列出差异文件清单（不要只看源码目录）。

**③ 差异归属判定**：差异文件必须**全部**落进白名单，才判定「编译面等价、配方可整体沿用」：

| 白名单类别 | 例 |
|---|---|
| 配方已关闭的子目录 | `kcmcddb/`（`BUILD_KCM=OFF`，不参与编译） |
| 非编译面 | `po/`（翻译）、`doc/`、`*.md`、测试数据 |

差异若落在 **源码 / CMakeLists.txt / tests/** 上 → **判定不等价**，按正常适配流程重新处理差异，
并在 `notes.md` 中逐项说明改了什么。

**④ 留证**：把判定结论（命令 + 差异清单 + 归属理由）写进版本级 `manifest.yaml` / `notes.md`
与 PR 正文，使复核者可直接重跑。

```bash
for v in $VER $SIBLING; do
  tar -xf $PKG-$v.tar.* && ( cd $PKG-$v && patch -p1 --forward --dry-run < ../$PATCH ) || exit 1
  ( cd $PKG-$v && patch -p1 --forward < ../$PATCH )
done
diff -rq $PKG-$VER $PKG-$SIBLING | tee /tmp/diff.list
grep -vE '/(po|doc)/|\.md$|kcmcddb/' /tmp/diff.list \
  && echo "⚠️ 编译面有差异 → 需重新适配" || echo "✅ 编译面等价"
```

## 实测证据（libkcddb 26.04.0 ← 26.04.3）

| 检查项 | 结果 |
|---|---|
| 补丁 dry-run（15 个文件） | exit 0，无 fuzz / 无 offset |
| `diff -r libkcddb-26.04.0/libkcddb libkcddb-26.04.3/libkcddb` | 完全相同 |
| `diff -r …/tests …/tests` | 完全相同 |
| `diff -u …/CMakeLists.txt …/CMakeLists.txt` | 完全相同 |
| `diff -rq`（全树） | 仅 9 个文件不同：`po/{lt,nb,nn,se}/{libkcddb,kcmcddb}.po`（8 个，翻译）+ `kcmcddb/kcm_cddb.json`（`BUILD_KCM=OFF`，不编译） |

结论：**参与编译的文件集合逐字节相同** ⇒ 配方与补丁可整体沿用；
同族 26.04.3 已由 CI 构建并合入 ⇒ 新版本的构建结论可由 CI 承接（这也是 E643 场景下
本地验证的合法上限）。

## 反例（说明判据必须实测）

xz 5.8.1 与 5.8.3 同属一个上游仓库的小版本序列，但编译面存在真实差异，
配方必须做两处实质改动（交叉编译时用 libtool `-all-static` 让上游测试可真实执行；
`test_package` 按 `cross_building` 从 profile 取交叉编译器），
不能仅凭"同族"照搬既有配方。

## 红线

- **禁止**未做 ①②③ 就宣称"同族可直接复用/照搬既有配方"。
- **禁止**只给结论不给差异清单与可复现命令（等价性结论必须可复核，否则等同未验证）。
