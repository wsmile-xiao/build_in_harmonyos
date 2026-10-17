# E635 — init_build._promote_nested_source 误提升 projects/ 子目录为源码根

## 错误特征

`ohc-run.py init-build` 后源码根目录只剩 `projects/` 内容（如 `projects/makefile/`），
顶层的真实源码目录（`src/`、`lib/`、测试图等）被删除；日志出现
"嵌套源码检测: 找到源码在 projects|提升完成: projects"。

## 触发条件

- 构建系统: makefile（构建文件位于 `projects/` 等子目录，源码在顶层）
- 阶段: init-build 嵌套源码检测（F068 `_promote_nested_source`）
- 实测案例: libsoil 1.07.20080707.dfsg（`projects/makefile/makefile` + 顶层 `src/`）
- 放大器: HMDFS 大小写不敏感文件系统上 `projects/Makefile` 与 `projects/makefile` 目录同名匹配

## 根因分析

`_find_source_subdir` 仅按 `configure`/`CMakeLists.txt`/`Makefile`/`meson.build` 标记识别
源码子目录。libsoil 这类"构建文件放 `projects/` 子目录、源码在顶层"的 C 包，顶层无构建
标记，递归扫描命中 `projects/makefile`，于是把 `projects/` 提升为源码根，并删除真正的
顶层文件（`src/`、`lib/`、测试图）。这是检测规则的假阳性，不是源码本身的问题。

## 解决方案

### 推荐方案

手动修复源树（绕过 F068，保留顶层布局）：
1. `rm -rf` 误提升的 `.orig` / `.work`
2. `mkdir .orig && tar xzf --strip-components=1 -C .orig <tarball>`（不触发嵌套提升）
3. `cp -a .orig/. .work/`
4. 写 `.orig/.tarball-sha256`
5. 重建 edit-tracker 基线（`python -c "from ohc.edit_tracker import snapshot; snapshot('<work>')"`）
6. conanfile 的 build() 直接 cd 到 `projects/makefile`（绝对路径
   `cwd=os.path.join(self.source_folder, "projects", "makefile")`）用 `make CXX=clang` 构建

### 禁止做法

- ❌ 直接改 scripts/ 的检测逻辑（框架文件，协作者只读）
- ❌ 在误提升的源树上继续编译（真实源码已丢失）

## 验证

```bash
ls .work/ | grep -E 'src|lib' && test -f .work/src/SOIL.c   # 修复后应有顶层 src/ 与 lib/
```

## 关联条目

- 相关: E466（同族误提升的 Python sdist 变体）
