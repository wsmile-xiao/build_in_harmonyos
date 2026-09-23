# ndenv 0.4.0 适配笔记

## 编译环境

- 构建系统: custom（纯 shell 脚本，无 configure/make/cmake）
- 编译日期: 2026-09-12
- 编译器: 无需编译器（纯 shell 脚本，仅打包）
- 状态: built（工作树未提交，待 HMBS 真机预检）

## 编译步骤

ndenv 是 rbenv 风格的纯 shell 项目，上游 tarball 解压后仅含 `bin/`、
`completions/`、`libexec/` 三个目录，无任何构建系统。配方直接打包：

1. 从 GitHub 官方源下载 `v0.4.0.tar.gz`（sha256 见 conandata.yml）。
2. `package()` 中 `shutil.copytree` 复制 `libexec/`（保持软链接）、
   `completions/`，并重建 `bin/ndenv -> ../libexec/ndenv` 软链接
   （与上游形态一致；做法对标已合入的 `archives/n/nodenv/1.6.2`）。
3. `build()` 仅做载荷完整性检查（`libexec/ndenv` 与
   `libexec/ndenv---version` 必须存在），并输出
   `HMBS_UPSTREAM_TEST_RESULT(status=no_tests)` 标记。
4. `test_package` 执行 `test_ndenv.sh` 6 断言冒烟测试，并输出
   `HMBS_TEST_PACKAGE_RESULT` 与复发的 `HMBS_UPSTREAM_TEST_RESULT` 标记。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 上游无测试套件，无法按常规接入 `make check`/ctest | riywo/ndenv 仓库根仅 bin/completions/libexec，无 test 目录、无任何测试运行器配置（GitHub contents API 全量核对，审计见 test_package/MANIFEST.yml） | 按 no_tests 处理：MANIFEST.yml 声明 `upstream_tests_exist: false` + 非空审计；主配方与 test_package 双通道复发 no_tests 标记（包缓存命中时 build() 不执行，靠 test_package 保证标记必现，对标 fancy-cat 0.6.0.1） |
| 2 | 是否需要 nodenv 式的 OHOS 路径补丁（`0001-libexec-nodenv.patch` 改 hook 路径） | ndenv 的 `/usr/local/etc/ndenv.d` 仅为 hook 搜索路径中的一项，不存在的目录无害；且 ndenv 无 nodenv.d/share 私有目录需要重定位 | 不打补丁，保持最小改动。若真机/CI 暴露路径问题再补 |
| 3 | 上游 `bin/ndenv` 本体为软链接，tarball 解压与 Conan `get()` 是否保留 | GitHub tarball 保留软链接；但为结果确定性，配方侧统一重建 `bin/ndenv -> ../libexec/ndenv`（与 nodenv 配方一致） | `package()` 中 `os.symlink` 重建，先删残留再建 |
| 4 | 真机 test_package 功能断言全空失败（`--version`/`commands` 输出为空、`versions` 非零退出），伴随 `getcwd: cannot access parent directories: Not supported` 刷屏；上一轮仅在测试脚本侧 `cd` 到包目录仍无效（HMBS 平台诊断 `[shell_getcwd]`） | HNP `/storage` 沙盒文件系统不支持 getcwd，`pwd` 在包目录本身也失败；上游 `libexec/ndenv` 分发器（`set -e` + `cwd=$(pwd)`/`NDENV_DIR=$(pwd)`）与 `libexec/ndenv-which` 的 `expand_path` 遇到 `pwd` 失败即 abort，且与测试脚本侧的 `cd` 无关 | 新增 OHOS 可移植补丁 `recipe-side _patch_ohos_getcwd_fallback in conanfile.py build() (pure-Python replace_in_file, no .patch files)`（conandata 已声明）：所有 `pwd` 调用失败时回退到 POSIX 的 `$PWD`，`cd` 失败加 `|| true`/`|| return 1` 保护；不引入平台宏，`getcwd` 正常时行为与上游一致 |

## 源码修改

`recipe-side _patch_ohos_getcwd_fallback in conanfile.py build() (pure-Python replace_in_file, no .patch files)`（conandata 已声明，portability）：`libexec/ndenv` 分发器与 `libexec/ndenv-which` 的 `expand_path` 在 `pwd`/`cd` 失败时回退（`$PWD` 兜底），适配 HNP 沙盒不支持 getcwd 的情况；其余 payload 无改动。

## 依赖版本

无构建依赖。运行时 `install` 子命令需 node-build 插件配合（可选运行时插件，
非构建依赖，不在配方中声明）。

## 验证结果

待 HMBS 真机预检回填（`conan create` + 双 JSON 标记）。本地 Windows 环境不运行 conan，
按任务守则等待 hmbs 后台预检。

预期命令与标记：

```bash
conan create . -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
# build() 输出 HMBS_UPSTREAM_TEST_RESULT(status=no_tests)
# test_package 输出 HMBS_TEST_PACKAGE_RESULT(discovered=6) + HMBS_UPSTREAM_TEST_RESULT(no_tests 复发)
```

冒烟断言（`test_package/test_ndenv.sh`，共 6 个）：

1. `bin/ndenv` 存在且可执行
2. shebang 声明 bash
3. `libexec/` 全脚本 `bash -n` 通过
4. `ndenv --version` 输出含 `0.4.0`
5. `ndenv commands` 列出子命令（含 `versions`）
6. 空 `NDENV_ROOT` 下 `ndenv versions` 退出 0

## 交付物

| 文件 | 说明 |
|------|------|
| `archives/n/ndenv/0.4.0/conanfile.py` | 主配方（application，settings 四项） |
| `archives/n/ndenv/0.4.0/conandata.yml` | 官方源 URL + sha256 |
| `archives/n/ndenv/0.4.0/manifest.yaml` | 版本级 manifest（status: built） |
| `archives/n/ndenv/0.4.0/notes.md` | 本文件 |
| `archives/n/ndenv/0.4.0/test_package/` | conanfile.py + test_ndenv.sh + MANIFEST.yml |
| `archives/n/ndenv/commands.json` | 软件级工具声明（R38） |
| `archives/n/ndenv/manifest.yaml` | 软件级 manifest |
| `archives/n/ndenv/README.md` | 软件级说明 |

## 注意事项

1. 上游 riywo/ndenv 已归档并声明 deprecated（推荐 nodenv），但 0.4.0 仍为本次任务需求版本，配方如实适配。
2. 本轮仅完成未提交工作树；任何改动后须经 HMBS 真机全部门禁通过后才可提交推送。
3. `settings` 取 `os/arch/compiler/build_type` 四项（PF8 配方静态闸要求四项齐全），
   纯脚本包中 compiler/build_type 仅作占位。

## 2026-09-12 patch-parser fix

Conan apply_conandata_patches failed twice with `invalid hunk no.1 at 25` on libexec/ndenv even though hunk line numbers match upstream (single-file split did not help). Switched strategy: removed patches/ and conandata patches section; build() now applies the identical HNP getcwd fallback via replace_in_file with strict match (6 patterns verified against official v0.4.0 tarball). No .patch files remain, so the parser is bypassed entirely.
