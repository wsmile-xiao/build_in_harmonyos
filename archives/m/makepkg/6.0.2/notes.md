# makepkg 6.0.2 适配笔记

## 范围

- 本包只适配 pacman 上游中的 `makepkg` Bash 脚本及其 `libmakepkg` helper。
- 不适配 pacman/libalpm C 程序，不引入 pacman 的 libarchive/curl/gpgme 编译链。
- 关联 issue: #1422。

## 版本选择

- 曾检查 pacman 官方 GitLab tag，最新稳定 tag 可见 `v7.1.0`。
- GitLab release/archive HTTP 下载在本机返回 bot challenge HTML，无法作为 Conan `get()` 的稳定源码 URL。
- 官方 `sources.archlinux.org/other/pacman/` 可稳定下载的较新源码为 `pacman-6.0.2.tar.xz`，因此本轮选择 `6.0.2`。

源码:

- URL: `https://sources.archlinux.org/other/pacman/pacman-6.0.2.tar.xz`
- SHA256: `7d8e3e8c5121aec0965df71f59bedf46052c6cf14f96365c4411ec3de0a4c1a5`

## W0 依赖检查

- `makepkg` 脚本注释列出的运行工具: awk, bsdtar/libarchive, bzip2, coreutils, fakeroot, file, findutils, gettext, gpg, grep, gzip, sed, tput/ncurses, xz。
- 本配方不声明 Conan `requirements()`，避免把上述系统工具或尚未确认发布的依赖混入当前 PR。
- 曾尝试查询 `bash/5.3`:
  - `conan download "bash/5.3" -r=ohpcd --only-recipe` 返回 `system acceleration policy not enabled`。
  - `conan list "bash/5.3" -r=ohpcd` 返回 `Recipe 'bash/5.3' not found`。
- 因此本轮将 GNU bash 视为 OHOS/DevBox 运行环境前提，后续如评审要求 Conan 化依赖，应单独确认/补齐 bash 发布，不混入 makepkg PR。

## 构建系统分析

- 上游 pacman 使用 Meson。
- `makepkg` 相关文件是模板脚本:
  - `scripts/makepkg.sh.in`
  - `scripts/libmakepkg/**/*.sh.in`
  - `etc/makepkg.conf.in`
- 当前配方用自定义 Python 渲染替代完整 Meson 构建，仅做占位符替换和 Bash 语法检查。
- `makepkg` 主脚本中的 `LIBRARY` 改为相对 `bin/makepkg` 定位 `../share/makepkg`，避免硬编码 `/usr/share/makepkg`。

## 测试策略

- build 阶段:
  - `bash -n generated/bin/makepkg`
  - `bash -n generated/share/makepkg/**/*.sh`
  - 上游 `test/scripts/parseopts_test.sh`，通过 `PMTEST_LIBMAKEPKG_DIR` 指向渲染后的 `libmakepkg`，共 56 条 TAP。
- test_package:
  - 执行 `makepkg --version`，确认脚本可运行且版本为 6.0.2。
  - 生成最小 `PKGBUILD`，使用临时 `makepkg.conf` 执行 `makepkg --printsrcinfo`，确认能加载 `libmakepkg` 并输出 `.SRCINFO`。
  - `--printsrcinfo` smoke 中设置 `PACMAN=sh`，避免测试环境缺少 pacman 命令导致早期 `type -P pacman` 失败。
  - `--printsrcinfo` smoke 中覆盖 `OPTIONS=(!strip ...)`，避免该路径依赖外部 `strip` 命令。
- 未运行 `test/scripts/makepkg-template_test.sh`：该测试覆盖上游另一个 `makepkg-template` Perl 工具，当前包未打包该工具，且当前真机无 Perl 运行时。

## 本机前置验证

- 已确认源码 URL 可下载，sha256 与官方 `.sha256sum` 一致。
- Windows tar 解包 pacman 6.0.2 时对少量硬链接文件报 `Invalid argument`，但 `scripts/` 和 `etc/makepkg.conf.in` 已完整用于分析；OHOS/Linux tar 环境预期可正常解包。
- 本机已执行:
  - `python -m py_compile conanfile.py test_package/conanfile.py`
  - `conan inspect archives/m/makepkg/6.0.2`
  - `conan export archives/m/makepkg/6.0.2 --user=ohpcd --channel=stable`
  - `git diff --check -- archives/m/makepkg/6.0.2`

## 真机验证

执行环境:

- 真机: HarmonyOS / HongMeng Kernel 1.12.0 / aarch64
- 验证仓库: `/storage/Users/currentUser/validation/build_in_harmonyos`
- 日志: `/storage/Users/currentUser/validation/build_in_harmonyos/logs/conan_makepkg_6.0.2_build_20260725-130743.log`

命令:

```sh
CI_PACKAGES="archives/m/makepkg/6.0.2" zsh ci/conan/build_and_test.sh
```

结果:

- Build Summary: `Total: 1`, `Success: 1`, `Failed: 0`
- L0: pass。已补充软件级 `archives/m/makepkg/commands.json`，满足 CLI 工具 R38 元数据要求。
- L1: pass。`test_package` 执行，破坏性反向验证确认测试依赖 `makepkg`。
- L2: pass。`makepkg --version` OK。
- L4: pass。无 patches。
- L5: pass。`bin/` 有产物。

真机迭代修复:

- OHOS 上 `/usr/bin/env` 作为 shebang 解释器会报 `Permission denied`，改为在 OHOS 构建时使用 `shutil.which("bash")` 找到的真实 bash 路径。
- 当前真机无 `/data/service/hnp/bin/bash`，实际 bash 为 `/storage/Users/currentUser/usr/local/bin/bash`。
- `makepkg --printsrcinfo` 会先解析 `PACMAN` 可执行路径；测试环境无 pacman，smoke 中用 `PACMAN=sh` 避开非本轮依赖。
- 默认 `makepkg.conf` 启用 `strip`，测试环境无 strip，smoke 临时覆盖为 `!strip`。

补充真机上游测试:

- 命令: `CI_PACKAGES="archives/m/makepkg/6.0.2" zsh ci/conan/build_and_test.sh`
- 日志: `/storage/Users/currentUser/validation/build_in_harmonyos/logs/conan_makepkg_6.0.2_upstream_parseopts_rerun_20260725-134150.log`
- 上游 makepkg 相关测试: `test/scripts/parseopts_test.sh`
- 结果: TAP `1..56`，`All 56 tests successfully run.`
- Build Summary: `Total: 1`, `Success: 1`, `Failed: 0`
- L0/L1/L2/L4/L5: pass
- 后续根据 AI 审核建议补充 `archives/m/makepkg/commands.json`，用于消除 L0k 对 CLI 工具元数据的提示。

commands.json 补充后复验:

- 命令: `CI_PACKAGES="archives/m/makepkg/6.0.2" zsh ci/conan/build_and_test.sh`
- 日志: `/storage/Users/currentUser/validation/build_in_harmonyos/logs/conan_makepkg_6.0.2_commands_json_20260725-134756.log`
- L0k: `commands.json valid (type=tool)`
- Build Summary: `Total: 1`, `Success: 1`, `Failed: 0`
- L0/L1/L2/L4/L5: pass

P3 审查建议修复后复验:

- 修复项: 简化 `_chost()` 无效分支、`assertion_count` 修正为 59、`test.sh` 启用 `set -euo pipefail`。
- 命令: `CI_PACKAGES="archives/m/makepkg/6.0.2" zsh ci/conan/build_and_test.sh`
- 日志: `/storage/Users/currentUser/validation/build_in_harmonyos/logs/conan_makepkg_6.0.2_review_p3_20260725-140352.log`
- 结果: 上游 `parseopts_test.sh` TAP `1..56` 全部通过；test_package smoke 3 条断言通过。
- Build Summary: `Total: 1`, `Success: 1`, `Failed: 0`
- L0/L1/L2/L4/L5: pass

## 下一步 shadow CI / PR

如需复刻干净提交快照，建议在提交后执行:

```sh
CI_PACKAGES="archives/m/makepkg/6.0.2" zsh ci/conan/build_and_test.sh
```

如使用影子 CI:

```sh
/path/to/run-ohos-shadow-ci.sh archives/m/makepkg/6.0.2
```

重点核对:

- `Build Summary` 中 `Total: 1`。
- L0/L1 pass。
- L2 对 `makepkg --version`/`--help` 应为 pass。
- L5 应确认 `bin/makepkg` 与 `share/makepkg/*.sh` 存在。
