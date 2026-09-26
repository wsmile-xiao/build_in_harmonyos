# E585 — refresh-patch 幻影补丁：.orig 基线损坏导致零修改包产出补丁

- **状态**: DRAFT（待审）
- **严重度**: 2
- **触发工具**: `refresh-patch` / `clean-verify` / `conan`
- **阶段**: 补丁生成（configuration/packaging）
- **来源任务**: ld2410-ble 0.2.0 纯 Python 适配

## 现象

`finish` 在 Step 1「补丁生成」后产出 9 个补丁，全部形如 `+N/-0`（新增文件）、
hunk 头为 `--- /dev/null`：

```
0001-CHANGELOG.md.patch    (+28)   0006-commitlint.config.js.patch (+8)
0002-CONTRIBUTING.md.patch (+117)  0007-poetry.lock.patch         (+1028)
0003-README.md.patch       (+59)   0008-pyproject.toml.patch      (+97)
0004-setup.py.patch        (+9)    0009-renovate.json.patch       (+3)
0005-LICENSE.patch         (+202)
```

紧接着 G0 干净构建验证失败：

```
❌ G0: 补丁 0001-CHANGELOG.md.patch 应用失败
```

但该包**上游源码零修改**——`conandata.yml` 声明 `patches: {}`，配方里没有任何
`replace_in_file` / patch 逻辑。

## 根因

`refresh-patch --auto` 在「无编辑追踪器」时会回退到**排除规则扫描**，即比对
`.work`（工作源码树）与 `.orig`（原始解压树）两个目录。

本例中 `.orig` 已被 `init-build` 的嵌套源码目录探测缺陷（F068：把 `docs/` 下的
`Makefile` 误判为源码根）破坏：`.orig` 顶层只剩被误判目录的内容，缺少 `src/`、
`tests/` 等真实源码树。手工修复工作目录后 `.work` 恢复完整，于是两个目录树比对时，
**上游原本就存在的顶层文件全部被判为「新增」**，生成一串 add-file 补丁。

这些补丁在 G0 阶段应用时，目标文件早已存在于归档解压结果中，patch 立即
`FAILED`（或 `Reversed (or previously applied) patch detected`）。

## 判据（关键）

> **`.work` 与上游归档逐字节一致，却仍然产出补丁 —— 即基线污染，而非真实改动。**

```bash
diff -rq <orig_dir> <work_dir>     # 无输出 ⇒ 上游零修改，正确结论是"零补丁"
```

## 处置

不要逐条调试补丁的 hunk 上下文（那是症状）。正确动作是**证伪补丁的必要性**：

1. 从官方归档重新解压出干净的 `.orig` 基线；
2. 与 `.work` 做全树比对；
3. 逐字节一致 ⇒ 清空 `patches/`，在 `manifest.yaml` 记录 `patches_count: 0` 与
   `method: none`，并把污染经过写入 `note`（供后续审计追溯）；
4. 重跑 `finish`。

```bash
cd $HOME/builds && rm -rf .orig-pristine && mkdir .orig-pristine
tar xzf <pkg>-<ver>.tar.gz -C .orig-pristine
mv .orig-pristine/<top-dir> <pkg>-<ver>.orig-pristine
mv <pkg>-<ver>.orig <pkg>-<ver>.orig-broken      # 保留脏基线以便追溯
mv <pkg>-<ver>.orig-pristine <pkg>-<ver>.orig
diff -rq <pkg>-<ver>.orig <pkg>-<ver>.work       # 期望：无输出
rm -rf <repo>/archives/<l>/<pkg>/<ver>/patches
```

## 禁忌

- **禁止手改 `patches/*.patch` 的 hunk 上下文**：补丁内容不是根因，改 hunk 只是
  掩盖基线污染；且 `patches/` 是 CI 输入，手改会引入不可复现差异。下一轮
  `refresh-patch` 会重新生成同类幻影补丁，G0 继续失败，进入调参螺旋（R43）。
- 判定 `+N/-0` + `--- /dev/null` 的补丁为幻影之前，**必须先确认归档中确有同名文件**
  （避免把真正的新增文件误删）：
  ```bash
  grep -l '^--- /dev/null' <ver_dir>/patches/*.patch
  ```

## 影响面

任何走了 `init-build`（模式 A/B）且 `.orig` 基线被嵌套目录探测、部分解压或手工
修复过工作目录的任务。**纯 Python / 单层 `src` 布局的包最易触发**——因为它们的
`docs/` 常自带 `Makefile`，正好命中 F068 的误判条件。

## 验证

修复后重跑 `finish`，Step 1 输出：

```
⚠️ 无编辑追踪器，使用排除规则扫描差异...
✅ 无差异，保留现有补丁
```

G0 阶段输出 `G0: 无补丁`，补丁相关失败消失（余下诊断见 E586）。
