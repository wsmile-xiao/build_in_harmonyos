# init-build 把 CMake 便捷包装 `./configure` 误判成 autotools（E707 草稿）

> 状态：草稿（DRAFT，待人工审核）｜来源：paraglob 0.6.0 OHOS aarch64 适配（2026-09-24）
> 同型先例：zint 2.16.0 `notes.md` 问题表 #2

## 问题

paraglob 是纯 CMake 工程（`cmake_minimum_required(VERSION 3.5)` +
`add_subdirectory(src/tools)`），但 `init-build` 判成了 autotools：

```
⚠️   conandata.yml 模板不可用，跳过
⚠️   conanfile.py 模板不可用（autotools），跳过
⚠️   test_package 模板不可用（test_package-conanfile-autotools.py），跳过
⚠️   test_package/MANIFEST.yml 模板不可用，跳过
```

同时 `manifest.yaml` 被写成 `build_system: autotools`、
`.build-context-paraglob-0.6.0` 被写成 `export BUILD_SYSTEM="autotools"`。

## 根因（两层）

1. **探测层**：上游根目录的 `./configure` 不是 autoconf 脚本，而是 CMake
   便捷包装（首行 `# Convenience wrapper for easily viewing/setting options
   that the project's CMake scripts will recognize`，内部只 `mkdir build` +
   调 `cmake`）。init-build 的探测**见 `configure` 即判 autotools**。
2. **优先级层（真正的坑）**：`scripts/ohc/conan_recipe.py` 的
   `_detect_build_system()` 顺序是

   ```
   BUILD_SYSTEM env（init-build 写入 .build-context）
     > manifest.build.system
     > manifest 顶层 build_system
     > 源码扫描（CMakeLists.txt / meson.build / configure / Makefile）
     > 默认 autotools
   ```

   所以**只改 manifest 不够**：一旦 source 过 `.build-context`，env 里的
   `"autotools"` 会把 manifest 的正确值盖回去，conan-init 照样选
   `conanfile-autotools.py.tmpl`。源码扫描那条 `CMakeLists.txt` 分支根本轮不到。

## 方案（两处一起改）

```sh
PKG="$HOME/ws/worktrees/paraglob-0.6.0/archives/p/paraglob/0.6.0"
# ① manifest 顶层 build_system 与 build.system 都改成 cmake
#    （改完 yaml.safe_load 回读自检，避免双引号串里出现 \$ 之类的非法转义）
# ② conan-init 用显式 env，且不要 source .build-context
cd "$HOME/ws/worktrees/paraglob-0.6.0"
export BUILD_SYSTEM=cmake
unset BUILD_SRC_DIR
python3 scripts/ohc-run.py conan-init paraglob 0.6.0
```

**通过判据**：`manifest.build.system == "cmake"` **且** `conanfile.py` 含
`cmake_layout`（只看 manifest 会被 env 优先级骗过——这是本条目最容易复发的点）。

## 为什么值得单独记一条

- 三个症状会同时出现，但**只有 env 优先级这一条是根**；按「manifest 没改好」
  反复改 manifest 会一直不生效（同错误类别多轮不收敛，踩 R43 调参螺旋）。
- 出错形态（`模板不可用（autotools）`）看起来像「仓库缺模板」，极易被误读成
  框架缺陷而去改 `templates/`——那是框架改动，必须单独 PR，不该混进软件 PR。

## 复现命令（设备可直接执行）

```sh
. "$HOME/tmp/paraglob-0.6.0/env.sh"
head -5 "$HOME/ws/tmp/builds/paraglob-0.6.0.work/configure"
grep -n -A6 "def _detect_build_system" "$HOME/ws/worktrees/paraglob-0.6.0/scripts/ohc/conan_recipe.py"
```

## 关联

- 后续影响面：build.system 错了会连带 W3 走错构建链，与 E706（测试侧装置）
  一前一后分别污染「构建」与「测量」两个环节。
