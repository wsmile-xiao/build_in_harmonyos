# E350 — init-build F068 嵌套源码检测误提升子目录（无顶层构建文件的仓库）

## 错误特征

对 header-only 库（或顶层无任何构建文件的仓库）执行 `ohc-run.py init-build` 时，日志出现：

```
ℹ️   嵌套源码检测: 找到源码在 demos，正在提升到 portablegl-0.100.0.orig ...
✅   嵌套源码提升完成: demos → portablegl-0.100.0.orig
```

随后 `.orig/`/`.work/` 的内容是某个子目录（如 `demos/`）而非仓库根，丢失顶层头文件
（如 `portablegl.h`）。

## 触发条件

- 构建系统: 无（header-only 库典型形态，stb 风格单头文件；或构建文件在深层子目录但非源码根）
- 阶段: init-build（`_create_dual_track` → `_promote_nested_source`）
- 仓库顶层不含 `configure` / `CMakeLists.txt` / `Makefile` / `meson.build` 任何一个，
  而某个子目录（如 PortableGL 的 `demos/`、`testing/`）含 Makefile。

## 根因分析

F068 的 `_promote_nested_source()` 以
`_BUILD_MARKERS = ("configure", "CMakeLists.txt", "Makefile", "meson.build")`
判断"源码根"。设计意图是处理 `pkg-1.0/pkg-1.0/` 双层包装目录，但对顶层本来就没有构建
文件的仓库（header-only 库是典型），它会在 max_depth=3 内找到第一个含 marker 的子目录并
整体提升——PortableGL 0.100.0 的 `demos/` 目录含 Makefile（SDL2 演示程序），被误当成
源码根提升，真正的交付物顶层 `portablegl.h` 反而丢失。

## 解决方案

### 推荐方案（manual-fix-nested-promotion）

1. 手动重建 `.orig`：tarball 解压后把顶层包装目录内容全部移到 `.orig` 根
   （**注意 dotfiles**：shell glob `*` 不匹配 `.github`/`.gitignore` 等，需
   `shopt -s dotglob nullglob`，否则 `mv pkg/* .` 漏掉隐藏文件且 rmdir 报
   `Directory not empty`）
2. 写 `.tarball-sha256`（否则后续无校验标记）
3. 在 `.orig` 顶层放置 `Makefile` 占位文件（注释注明用途），使
   `_create_dual_track` 的 `orig_valid=True`，防止重跑 init-build 时再次解压+误提升
4. `cp -a .orig .work`
5. 带 `--project-dir <repo>` 重跑 `init-build --no-download` 补齐归档骨架

### 验证

```bash
ls $TMPDIR/builds/<name>-<ver>.orig/ | grep <顶层关键头文件>   # portablegl.h
ls $TMPDIR/builds/<name>-<ver>.work/portablegl.h
```

### 禁止做法

- ❌ 直接删除误提升后的 `.orig`/`.work` 后不带任何干预重跑 init-build（会再次误提升）
- ❌ 把 demos/ 里的 Makefile 当成上游构建系统去 conan-init（autotools 模板）——
  header-only 库没有构建产物，配方应为 `package_type="header-library"`

## 关联

- 实证事件: portablegl 0.100.0 HarmonyOS PC 适配（archives/p/portablegl/0.100.0）
- 相邻坑: find_project_dir 误指 skill 安装目录（E351）——两个坑常在同一任务中出现
