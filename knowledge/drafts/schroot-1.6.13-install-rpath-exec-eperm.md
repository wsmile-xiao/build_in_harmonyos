# 安装期 RPATH 重链产物在 HarmonyOS 上无法执行（execve EPERM）

- **草稿 ID**: DRAFT-SCHROOT-1613-INSTALL-RPATH-EXEC-EPERM
- **条目文件**: `knowledge/drafts/schroot-1.6.13-install-rpath-exec-eperm.kv`
- **来源事件**: schroot 1.6.13 `conan create`（2026-10-01）
- **严重程度**: 🔴 blocking

## 1. 现象

配方编译全部通过、`conan create` 走到 test_package 阶段报：

```
ConanException: Error 126 while executing .../bin/schroot --help
```

即**包内安装出来的可执行文件无法运行**（EPERM / Operation not permitted），
而同一份构建树里的产物 `build/Release/bin/schroot/schroot` 可以直接执行、`--version`/`--help` 正常。

## 2. 根因

`cmake --install`（以及 autotools 的 install 期 relink）为了产物的可重定位性，会在**安装期**
用新的 RPATH 字符串重写 ELF 动态段。当新串比原串长时，只能追加段并改动文件布局——
这一步通常称为 **re-link（重链）**。

- 构建树产物：未经重链 → 可直接 execve ✅
- 包内安装副本：安装期重链 → HarmonyOS 文件安全策略下 execve 返回 **EPERM** ✗
  （conan 侧表现为 `Error 126`）

判据简单可靠：**对比构建树产物与安装副本的 md5**。不同 ⇒ 发生过重链。

schroot 1.6.13 实测：

| 文件 | md5 |
|------|-----|
| 构建树 `.../b/build/Release/bin/schroot/schroot` | `41c15b00…` |
| 包内 `.../p/bin/schroot` | `bc0c7612…` |

工具链缓存中 `CMAKE_SKIP_INSTALL_RPATH:BOOL=NO`，即 install 期允许改写 RPATH——正是触发条件。

## 3. 解决方案（推荐）

**让安装期无串可写**：构造时就令 `CMAKE_BUILD_RPATH == CMAKE_INSTALL_RPATH`（含全部依赖 libdir）。
两者一致 ⇒ 安装期不需要重写 ⇒ 不重链 ⇒ 包内产物与构建树产物一致、可执行。

```cmake
-DCMAKE_BUILD_RPATH="${RPATH}" -DCMAKE_INSTALL_RPATH="${RPATH}"
```

若工具链/上游仍触发重链，补救手段是在 `package()` 中用构建树产物覆盖包内安装副本：

```python
shutil.copyfile(os.path.join(build_tree, "bin", tool),
                os.path.join(self.package_folder, "bin", tool))
```

注意这只是"保证包内产物可用"，不改变上游安装逻辑，须在 notes.md 写明。

## 4. 禁止做法

| 禁止 | 原因 |
|------|------|
| `patchelf --set-rpath` / `chrpath -r` 事后改写 | 同样改写 ELF 动态段，OHOS 上可能再次被拒；且掩盖"安装期重链"根因，让后续包重复踩坑 |
| 把 EPERM 当成"权限不足"去 chmod | 本机 HMDFS/FUSE 挂载下 chmod 无效（见知识库 HMDFS 条目），方向错 |

## 5. 验证

```bash
# 1) 确认是否重链：构建树产物 vs 包内副本
md5sum <conan build folder>/build/Release/bin/<tool> <package_folder>/bin/<tool>

# 2) 直接执行包内产物
<package_folder>/bin/<tool> --version; echo "exit=$?"
```

`exit=0` 且 md5 一致 ⇒ 修复生效。

## 6. 适用范围

- `package_type = "application"`、用 `cmake --install` / `make install` 安装可执行文件；
- 依赖通过 `-L/-l` 或 `find_package` 引入、且不在默认库路径（因此需要 RPATH）的包；
- 同类 autotools 安装期 relink 亦应怀疑同一机制。
