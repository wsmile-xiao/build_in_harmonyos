# DRAFT-libdxfrw-0.5.12-absolute-symlink-autotools-helpers：GitHub tag 归档内 automake 辅助脚本为绝对路径符号链接的 Conan 适配

> Contributor: pc2-29 | Status: Draft | Updated: 2026-09-23
> Source: PR (libdxfrw 0.5.12 适配 HarmonyOS PC, task libdxfrw-0.5.12-r01)

## 背景

libdxfrw 0.5.12 是 autotools 老项目（configure 由 autoconf 2.63 时代生成）。官方
GitHub tag 归档（`archive/refs/tags/v0.5.12.tar.gz`）内，7 个 automake/libtool
辅助脚本（`ar-lib`、`config.guess`、`config.sub`、`depcomp`、`install-sh`、
`ltmain.sh`、`missing`）是**指向绝对路径的符号链接**：

```text
lrwxrwxrwx  ar-lib      -> /usr/share/automake-1.12/ar-lib
lrwxrwxrwx  config.guess -> /usr/share/automake-1.12/config.guess
lrwxrwxrwx  ltmain.sh   -> /usr/share/libtool/config/ltmain.sh
...
```

这些路径只存在于上游开发者当年的机器上，本机与 CI 均不存在，即"悬空绝对路径符号链接"。

## 错误现象（两类）

### 1. Python tarfile 解压直接失败（本地 init-build）

```text
❌ 解压失败: 'libdxfrw-0.5.12/ar-lib' is a link to an absolute path
```

Python 3.12 tarfile 的 `filter='data'` 安全过滤拒绝提取链接目标是绝对路径的符号链接
（CVE-2007-4559 防路径逃逸的附带结果）。`ohc-run.py init-build` 内部 `_extract()`
使用该过滤，故首次下载解压即失败。

### 2. conan 解压保留链接但 configure 失败（conan create）

conan `unzip()` 保留符号链接（不做绝对路径拒绝），解压成功，但链接悬空：

```text
configure: error: cannot find install-sh, install.sh, or shtool in "..."
```

（autotools `AC_CONFIG_AUX_DIR` 默认目录找不到可用辅助脚本；后续即使补 install-sh，
config.guess 等仍会以各种方式失败。）

## 根因

上游仓库把 automake 辅助脚本以**符号链接**形式提交进 git（`git archive` 生成的
tag 归档原样保留符号链接），且链接目标是开发者机器的绝对路径。这是上游打包缺陷，
不是本平台问题；但任何从该归档构建的环境都会遇到。Python tarfile 的 `data` 过滤
与 HMDFS/CI 干净环境都放不过它。

## 修复（配方自包含，CI 可复现）

1. **随配方携带真实辅助脚本**：把 7 个辅助脚本的真实文件放入配方目录
   `build-aux/`（config.guess/config.sub 用新版通用脚本；ltmain.sh 必须与
   configure 内嵌的 LT_INIT 宏版本一致，见下），`export_sources()` 里
   `copy(self, "build-aux/*", self.recipe_folder, self.export_sources_folder)`。
2. **source() 解压后替换悬空链接**：检测 `os.path.islink(target)` 或不存在，
   用 `export_sources_folder/build-aux/<name>` 的实体 `os.unlink + shutil.copy2` 替换
   （注意：`os.path.exists()` 对悬空链接返回 False，须用 `os.path.islink()` 先判）。
3. **ltmain.sh 版本一致性**：configure 内嵌 LT_INIT 宏版本
   （`grep macro_version configure` → 2.4.2 / macro_revision 1.3337），替换用的
   ltmain.sh 必须 `VERSION`/`package_revision` 与之完全一致，否则运行时报：

   ```text
   libtool: Version mismatch error. This is libtool 2.6.2, but the
   libtool: definition of this LT_INIT comes from libtool 2.4.2.
   ```
   取官方对应版本 ltmain.sh（如 `libtool-2.4.2/libltdl/config/ltmain.sh`，
   其 `package_revision=1.3337` 与 configure 一致）。

## 验证

- 本地 `ohc-run.py conan-verify libdxfrw 0.5.12`：G0-G4 + L2/L4/L5 全部 PASS；
- `conan create`（干净构建）通过，test_package 读写回环测试 1/1 PASS；
- 无 configure/config.status 失败。

## 适用边界

- 适用于**任何官方 GitHub tag 归档内含绝对路径符号链接**的 autotools 项目
  （老项目常见：辅助脚本以 `ln -s /usr/share/automake-1.12/...` 提交进 git）。
- 若归档内符号链接是**相对路径**或链接目标真实存在，不需要此处理。
- 若链接为**符号链接循环**（资源数据包），参考既有 E255（tarfile filter="data" 手动提取）。
- 辅助脚本的 execute 位注意（相关 E490：chmod +x configure config.guess 等）。

## 反例与限制

- 不要试图在 conandata.yml 改 URL/换镜像来绕（R39：URL 必须官方源）。
- 不要把悬空链接"留空"或删除 install-sh 后期待 configure 用系统 install
  （autotools 检查仍会失败）；必须提供实体脚本。
- `export_sources()` 的 copy 目标不能与源相同（Conan 报
  `copy() 'src' and 'dst' arguments must have different values`）。
