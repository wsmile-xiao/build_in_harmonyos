# DRAFT-conan-copy-keep-path-nesting：conan copy 工具 pattern+keep_path 目录嵌套陷阱

> Contributor: alexjs-11.0.1 适配 | Status: Draft | Updated: 2026-08-19
> Source: archives/a/alexjs/11.0.1

## 现象

alexjs 11.0.1 配方中两次踩到 conan.tools.files.copy 的路径语义坑：

1. **export_sources 双重嵌套**：`copy(self, "upstream-tests/*", src=recipe_root,
   dst=export_sources_folder/upstream-tests)` 实际产出
   `upstream-tests/upstream-tests/...` 双重嵌套，build() 里 `node test/index.js`
   找不到测试文件（`Cannot find module .../test/index.js`）。
2. **node_modules 静默空目录**：`copy(self, "node_modules/*", src=<...>/node_modules,
   dst=app_dir/node_modules)` 匹配不到任何文件（pattern 基于 src 解析，src 已指向
   node_modules 内部），打包产物 node_modules 为空 → 运行期
   `ERR_MODULE_NOT_FOUND: Cannot find package 'update-notifier'`。

## 根因分析

- conan copy 的 pattern 是相对 src 的匹配表达式，keep_path=True 保留匹配到的
  相对路径（含 pattern 中的目录前缀）。
- `'dir/*'` + src 指向 dir 的上级 → 相对路径含 `dir/` 前缀 → 双重嵌套。
- `'dir/*'` + src 指向 dir 本身 → 匹配不到（src 下没有 dir/ 子目录）→ 静默空。

## 解决方案

1. **src 指向目录内部 + pattern `'*'`**：
   ```python
   copy(self, "*", src=os.path.join(self.recipe_folder, "upstream-tests"),
        dst=os.path.join(self.export_sources_folder, "upstream-tests"))
   ```
2. **整目录树复制用 `shutil.copytree`**（确定性，无 pattern 语义歧义）：
   ```python
   shutil.copytree(tests_src, tests_dst)
   ```

## 验证证据

- 修正后 conan create G2 PASS：上游测试 47/47 PASS，test_package 3/3 PASS。

## 禁止做法

- 不要 `copy(self, "dir/*", src=dir 的上级, ...)`（双重嵌套）。
- 不要 `copy(self, "node_modules/*", src=node_modules, ...)`（静默空目录）。
