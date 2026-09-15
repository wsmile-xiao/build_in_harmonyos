# plenv 2.3.1 适配笔记

## 编译环境
- 构建系统: custom（纯 Bash 工具，无原生编译）
- 上游: https://github.com/tokuhirom/plenv，tag 2.3.1
- 归档: https://github.com/tokuhirom/plenv/archive/refs/tags/2.3.1.tar.gz（25764 字节，sha256 见 conandata.yml）
- 状态: built（待真机预检 evidence 回填后按实测更新）

## 打包步骤

1. `source()` 解包上游 tarball（strip_root）。
2. `build()` 运行上游测试的离线等效验证（见下节），无编译动作。
3. `package()` 复制 `libexec/`、`completions/`、`plenv.d/` 与 `LICENSE`/`Changes`/`README.md`，
   重建 `bin/plenv -> ../libexec/plenv` 相对符号链接，并给 `libexec/` 下文件加可执行位。

## 上游测试审计

- 上游测试入口: `Makefile` 的 `test` 目标，实际执行 `prove -v test/`。
- 上游测试用例: `test/shim.t`，共 1 个断言（plan 1）：shim 能透传 `-E` 且能观察到 `PLENV_DIR`。
- 前置依赖: `ext/test-simple-bash`（`make test` 时现场 `git clone`，需网络）+ `prove` + 真实 perl。
- 在 HarmonyOS aarch64 实测环境下复刻该断言的低成本离线方案：
  用只打印 `$PLENV_DIR` 的 stub perl 充当 `versions/dummy/bin/perl`，
  `PLENV_VERSION=dummy`，跑 `plenv rehash` 后断言 `shims/perl` 非空、
  且 `shims/perl -E 1` 的输出恰等于隔离 `PLENV_ROOT`。
  该镜像同时在 `conanfile.py build()` 与 `test_package` 中执行，
  前者在构建日志留痕并输出 `HMBS_UPSTREAM_TEST_RESULT`，
  后者重跑后输出同一标记（详见 `test_package/MANIFEST.yml`）。
- 未改动上游任何测试文件。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 生成的 shim 通过 PATH 回调 `plenv`，直接跑会找不到命令 | shim 模板内嵌 `exec "$(command -v plenv)" exec ...` | 测试先把指向被测 plenv 的 wrapper 目录前置到 PATH |
| 2 | 真机可能没有系统 perl，`plenv exec perl` 会报 command not found | `system` 版本走 PATH 找真实 perl | 用 `PLENV_VERSION=dummy` + stub perl，使断言不依赖真实 perl |
| 3 | `make test` 现场 git clone，不适合 CI | 上游 Makefile 在 test 目标内 clone 外部仓库 | 离线镜像替代，并在 PR 补充说明中如实声明 |
| 4 | 真机 HNP bash 在 HMFS/HMDFS 工作目录下 getcwd 失败（shell-init 报错），plenv 主流程 `cd "$OLDPWD"` 报 null directory 导致 build() 失败；且旧 check.sh 用 shell printf 生成 wrapper/stub，转义后文件内容损坏 | 构建目录对 HNP bash 不可见，printf 多层转义易错 | 驱动改用注入的 SHELL/CONFIG_SHELL（/bin/sh），check 与 test_package 工作目录改到 TMPDIR，脚本开头先 cd 到 getcwd 安全目录；plenv/shim 执行器经 shopt 探测后首选 SHELL，不支持 bash 语法才回退 PATH bash；wrapper/stub 改用 heredoc 生成 |
| 6 | true-machine rehash fails: ln cannot create hard link .plenv-shim to perl, Operation not permitted (HMBS_CAPABILITIES hardlink=0) | upstream libexec/plenv-rehash install_registered_shims hardcodes ln -f | build() edits libexec/plenv-rehash in place: ln -f failure falls back to cp -f; symlink rejected because EXIT trap removes prototype leaving dangling links, cp keeps diff-identical content. In-place Python replace chosen after .patch hunk-count parse failure (extra lines for hunk no.1). Edit persists to package() via source_folder |
| 7 | conandata .patch fails to parse (extra lines for hunk no.1 at 16, Failed to parse patch) | hunk header @@ -66,7 +66,11 @@ miscounted old/new line counts | drop patch-file mechanism entirely: revert conandata to patches {}, delete patches dir, do idempotent Python string replace in build() before check.sh; no unified-diff parsing involved |
| 5 | 上一轮改用 TMPDIR 工作目录后真机仍报相同 getcwd/shell-init 错误；另源码下载出现 github 连接超时 | TMPDIR 同在 /storage（HMFS）下，对 HNP bash 同样不可 getcwd；下载超时需按守则加镜像 | 改为运行时探测 getcwd 安全启动目录（候选 /tmp、/、HOME、TMPDIR：逐个用所选 bash 起 pwd，有 shell-init 字样即弃选），数据目录仍放 TMPDIR；conandata.yml 按仓库映射加 gh-proxy 镜像在前、官方 URL 回退在后的有序列表，sha256 不变 |

## 依赖版本

无运行时依赖（bash + readlink 由系统提供）。无 conan requires。

## 验证结果

- 本地已验证：上游归档可下载、sha256 可复现、配方文件齐备。
- 真机 `conan create` 实测（编译状态、上游 1/1、消费者 N/N）以 HMBS 预检日志为准，
  本轮不预填数字，待 evidence 轮回填。

## 注意事项

- 消费者测试必须使用隔离 `PLENV_ROOT`（`test_package` 内 `plenv-root` 目录），
  禁止写入用户 HOME。
- 工具包按 R38 在软件级目录提供 `commands.json`。
