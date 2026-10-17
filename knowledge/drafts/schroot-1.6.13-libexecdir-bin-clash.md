# conan 工具链把 `CMAKE_INSTALL_LIBEXECDIR` 设为 `bin`：helper 安装目录冲突

- **草稿 ID**: DRAFT-SCHROOT-1613-LIBEXECDIR-BIN-CLASH
- **条目文件**: `knowledge/drafts/schroot-1.6.13-libexecdir-bin-clash.kv`
- **来源事件**: schroot 1.6.13 安装阶段（2026-10-01）
- **严重程度**: 🟡 medium（不改则安装直接失败）

## 1. 现象

`cmake --install` 阶段报目标目录冲突（helper 程序与 `bin/` 下主程序争用同一目录），
例如 `file INSTALL cannot ... destination is not a directory`。

## 2. 根因

conan 的 **CMakeToolchain** 为适配 conan 包布局，会把一批 GNUInstallDirs 变量改成
conan 风格，其中：

```
CMAKE_INSTALL_LIBEXECDIR = bin     # 工具链既定行为
```

上游若把 helper/daemon 程序装到 `${CMAKE_INSTALL_LIBEXECDIR}`，这些 helper 就会
落到 `bin/`，与主程序同目录；当上游同时 `install(DIRECTORY ...)` 该目录本身时，
目录与文件相互冲突 → 安装报错。

schroot 实测：主程序 `schroot` 在 `bin/`，helper `schroot-mount`、`schroot-listmounts`
本应在 `libexec/schroot/`。

## 3. 解决方案

**用上游自己的 CACHE 变量覆盖**（不改 conan 工具链、不改上游 CMakeLists）：

```python
tc.cache_variables["SCHROOT_LIBEXEC_DIR"] = os.path.join(self.package_folder, "libexec", "schroot")
```

安装后布局恢复为上游预期：

```
libexec/schroot/schroot-mount
libexec/schroot/schroot-listmounts
```

若上游只认 `CMAKE_INSTALL_LIBEXECDIR`，则直接覆盖该变量本身，但需确认包内 helper
与主程序不再同目录。

## 4. 备选与禁止

- 备选：`package()` 中把被装进 `bin/` 的 helper 移到 `libexec/<pkg>/`（须同步修正配置里
  对 helper 路径的引用），并在 notes.md 说明与上游布局的差异。
- ❌ 禁止 `rm -f bin/<helper>` 或直接 `sed` 改写安装结果——helper 路径常被上层脚本/配置引用，
  删改会让运行时找不到 helper，问题延后到用户侧。

## 5. 验证

```bash
grep -n "CMAKE_INSTALL_LIBEXECDIR" <build tree>/CMakeCache.txt   # 看 conan 给了什么
ls <package_folder>/libexec                                       # 期望看到 helper 目录与程序
```
