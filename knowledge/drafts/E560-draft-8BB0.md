# E560 — finish 的 refresh-patch --auto 重命名补丁导致 conandata.yml 引用失效

## 错误特征

conan create 在 `export_sources()` 阶段报错：

```
ERROR: <pkg>/<ver>: Error in export_sources() method, line N
	export_conandata_patches(self)
	ConanException: Patch file does not exist: '.../patches/0001-use-env-bash.patch'
```

W3 本地 CI / conan-verify 的 G2 门禁直接 FAIL，hint 提示 "patch 文件路径或格式错误"。

## 触发条件

- 构建系统: CMake（任何带 patches/ 目录的 Conan 配方）
- 阶段: conan create 的 export_sources()（配方导出）
- 前置：conandata.yml 的 patch_file 使用**手工命名**（如 `0001-use-env-bash-for-...-tests.patch`），
  而非 refresh-patch 的 per-file 自动命名

## 根因分析

`finish` 管线的 step [1/10] 会自动调用 `refresh-patch --auto`。该工具从工作目录
（`.work`）与原始目录（`.orig`）的 diff 按 **per-file** 重新生成补丁，命名为
`0001-<file路径>.patch`（如 `0001-compile_fail.sh.patch`），并把旧的 `*.patch`
移动到 `.patch-backup-<timestamp>/`。若 conandata.yml 仍引用旧手工补丁名，
`export_conandata_patches()` 在导出时找不到文件 → conan create 失败。

另一个隐藏坑：refresh-patch 只基于工作目录与 orig 的 diff。若某源文件改动**未真正
落盘**（如 `patch` 应用时 hunk 失败被忽略），该改动会被静默遗漏，生成的补丁不完整，
导致上游测试与配方行为不一致。

## 解决方案

### 推荐方案

1. 在 `finish` 之前**主动**运行 `refresh-patch --auto`，观察重命名结果：
   ```bash
   python3 scripts/ohc-run.py refresh-patch --auto <软件> <版本>
   ```
2. 把 conandata.yml 的 `patch_file` 条目**同步**为新生成的 per-file 补丁名，
   patch_description/patch_type 保持合理语义。
3. 核验每个预期改动文件都出现在 patches/ 中：
   ```bash
   diff -rq <orig>/<file> <work>/<file>   # 确认改动已落盘
   ls <ver_dir>/patches/                   # 确认补丁齐全
   ```
4. 重跑 conan-verify 确认 G2 PASS。

### 禁止做法

- ❌ 在 conandata.yml 引用 `.patch-backup-*` 目录中的旧补丁名。
- ❌ 直接跳过 refresh-patch（finish 会强制执行，跳过只是延迟问题）。
- ❌ 手工向 patches/ 写回旧命名补丁而不回写 conandata.yml。

## 验证

```bash
grep -n "patch_file" archives/c/chrono/3.0.4/conandata.yml
ls archives/c/chrono/3.0.4/patches/
python3 scripts/ohc-run.py conan-verify chrono 3.0.4   # G2 PASS, 108/108 测试
```

## 关联条目

- 相关: E276（codeload URL basename 误判 BadZipFile，同为 Conan 配方导出阶段坑）
- 相关: E515（Patch file does not exist 模板，本条目补充 refresh-patch 重命名根因）
