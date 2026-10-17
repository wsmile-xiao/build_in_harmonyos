# undbx 0.21 HarmonyOS PC 适配笔记

### 对话 #Codex-4-undbx-0.21

## 任务与基线

- 平台任务：11497；分支：`feat/undbx-0.21`。
- 设备 worktree：`/storage/Users/currentUser/qzy/Codex-4-undbx-0.21`。
- 验证基线：`3e9c9ae2365881355d15792b7c72c519776c26b1`（从 2026-09-17 最新 `upstream/main` 创建）。
- 上游：`https://github.com/ZungBang/undbx`，tag `undbx-0.21`。
- 源码下载使用官方 codeload URL；SHA256：`0c7c3d66aed00133f3889bb449d38c745fb2c757a302c067ace2b65981259422`。

## W0/W0b 与预检

- `bash ci/scripts/preflight_check.sh undbx/0.21`：通过；初始化时无依赖声明，Conan 依赖数为 0。
- 同软件版本历史归档不存在；无历史 `notes.md` 可迁移。
- `recipe-search undbx`：无相似配方，知识配方语料重建为 4992 条。
- R47 `lang-preflight`：task=`c`，detected=`c`；源码统计 5 个 C 源文件（主体 100%），构建系统为 Autotools，匹配通过。

## 探索过程与适配点

1. 官方 GitHub archive URL 的第一次读取超时；同一仓库官方 codeload URL 第二次尝试成功，源码解压为 18 个文件。Conan 配方显式声明 `filename: undbx-0.21.tar.gz`，避免 codeload 无后缀被误判为 ZIP。
2. 源码快照只有 `configure.ac`/`Makefile.am`，没有 `configure`；在源码探索副本和 Conan `build()` 中先执行 `autoreconf`。
3. 首次 `configure` 的第一条错误为共享 HMDFS `$TMPDIR` 无法创建 `config.guess` 的 `dummy.c`。E007 检索确认 `config.guess/config.sub` 缺少 HarmonyOS tuple；探索阶段使用内置 `patch-autotools-ohos.pl`，配方中以等价的可复现步骤补充 `aarch64-unknown-linux-ohos` 识别。
4. 第二次 `configure` 在 `config.status` 创建 `./conf*/subs1.awk` 时触发 E011/E114/E125：当前 uid 为 `20020084`，源码目录属主映射为 `20001006:file_manager`，`umask 077/022` 创建的目录当前用户不可写。`umask 002` 探针成功保留同组写权限；配方在 `autoreconf` 后用 Conan `replace_in_file(..., strict=True)` 将生成 `configure` 中的 `umask 077` 改为 `umask 002`。
5. Conan G2 曾因 profile 的 `CONFIG_SHELL=/data/service/hnp/bin/bash` 触发 E386/getcwd；配方改为在 `conanbuild` 环境中用 `env -u CONFIG_SHELL SHELL=/bin/sh /bin/sh <configure绝对路径> <toolchain args>` 显式路由 configure，make/check 仍使用 Autotools helper。
6. 首次 native 编译在 `-Wall -Werror` 下暴露 `dbxread.c` 两处警告：无效的 `n` 计数变量和三目运算优先级。`patches/0001-dbxread.c.patch` 由设备 `.orig/.work` 的 `diff -u` 生成，只删除无效计数并补全括号，不改变恢复算法。
7. Conan 实际 `export_conandata_patches()` 要求 `patches` 为列表（或版本到列表的映射）；最终 `conandata.yml` 使用列表结构，G2 日志确认补丁被应用。
8. finish 的 G0 clean verify 不执行 build()，而 GitHub 快照没有 configure；`replace_in_file` 作为真实 build() 运行时修复标记，使 G0 将该预期失败透明记录，真实可复现构建由 G2/W3 验证。

配方构建顺序固定为：应用源码补丁 → `autoreconf` → 构建期补充 `config.guess/config.sub` 的 OHOS 识别 → 恢复 helper 执行位 → 修复 HMDFS umask → `/bin/sh` 路由 configure → `make -j1` → `make check -j1`。

## 测试四维账本

| 维度 | 数量 | 证据 |
|---|---:|---|
| 上游静态测试 `N_static` | 0 | 源码无 `TESTS`、`check_PROGRAMS`、`add_test` 或测试源 |
| 上游注册/执行 `N_registered` / `N_executed` | 0 / 0 | `make check -j1` 在配方 `build()` 中真实执行，退出码 0 且无测试输出 |
| 上游跳过/失败 | 0 / 0 | 上游没有测试套件 |
| 新增消费者测试 `N_consumer` | 1 / 1 | `test_package/test_undbx.sh` 真实运行已安装 CLI |

消费者脚本有 4 个可验证断言：版本输出、帮助用法、`--recover` 选项，以及非法选项必须返回非零；Conan create 日志显示全部通过。探索安装基线为：`--version` rc=0、`--help` rc=0、非法选项 rc=1。

## Conan/W3 证据

- `conan-verify undbx 0.21`：G0/G1/G2/G3/G4/L2/L4/L5 全部通过；配置文件为 `ci/conan/profiles/ohos-aarch64`，clang 15、OHOS armv8。
- G2 日志确认 `Apply patch`、OHOS tuple、`make -j1`、`make check -j1`、`make install ... -j1` 和 `Testing the package` 均出现；消费者脚本输出 `PASS: version, help, recovery option, and invalid-option behavior verified`。
- `finish undbx 0.21 built` 第二轮 W3 通过，`.ci-result.json` 已由工具生成并带完整性哈希；W3 使用 `CI_PACKAGES=archives/u/undbx/0.21`，JC6 通过单软件临时 diff 范围。
- 最终定向 W3 使用本任务专属绝对 `BUILD_DIR` 缓存并通过；此前复用旧预下载缓存曾把 `file://` 路径解析为 `/.build-cache/...`，已清理并以官方源重跑，最终日志无该错误。
- finish 的 G0 clean verify 因源码无 configure、build() 负责 autoreconf 而标记 EXPECTED；不是设备编译失败。

## 路径判断

本任务走路径 A。E007/E011/E114/E125/E386/E490 均命中已有知识条目；源码警告修复是 undbx 特定的最小 bugfix，没有形成可跨仓库复用的新知识主题，因此不创建路径 B 草稿或 Issue。也不满足路径 C 的资质条件。

## Codex-5 接班：CI aclocal 缺失修复

- 接手时 PR #10552 的 CI #49390 在 `conan-build-test` 的 `autoreconf` 阶段失败：`Can't exec "aclocal": No such file or directory`。CI worker 的 PATH 只有 HNP/autoconf 入口，没有设备本地 Harmonybrew 的 `aclocal`/`automake`。
- 根因是 GitHub codeload 快照没有预生成 `configure`，配方 `build()` 必须运行 Autotools 自举，但原配方未声明 Automake 构建工具依赖；本机 PATH 的 Harmonybrew 工具掩盖了该缺口。
- 最小修复：增加 `build_requirements()` 的 `automake/1.18`，并在 `generate()` 生成 `VirtualBuildEnv`，让 Conan tool-requires 提供的 `aclocal`、`automake`、`ACLOCAL_PATH`、`PERL5LIB` 注入构建环境；未硬编码设备路径，源码逻辑与运行时测试不变。
- 修复后设备 `conan-verify undbx 0.21` 复验：G0/G1/G2/G3/G4/L2/L4/L5 全部通过，`test_package` 真实消费者测试通过。验证使用已有的 Conan 工具包缓存；新建隔离缓存首次失败仅因未配置 `ohpcd` remote/下载超时，非配方构建错误。

## finish 收尾记录

- 状态：built
- finish 第二轮：G2 通过、W3 通过；Step 6 仅遗留旧版 `packaging/` tar.gz 检查和 SUMMARY 生成器异常，未创建废弃的手工打包产物，也未修改框架文件。
- 交付前需执行：W4 独立审计、当前 HEAD 精确提交/推送、PR 创建后 presubmit、同 SHA CI/AI/未解决意见核验。
- 最终交付状态：built（已通过 Conan verify/W3，尚未上传制品，未声称 published）。
- **最终状态**: built
## CI 修复轮次 2：worker 无裸 `sh`

- 当前 HEAD 的 CI #49610 已通过 L0i 的 `automake/1.18` 依赖检查并成功执行 `autoreconf`，证明第一轮 Automake tool-requires 修复生效。
- 下一条真实错误出现在 `_patch_autotools_scripts()` 的校验命令：CI worker PATH 不包含 `sh`，`subprocess.run(["sh", ...])` 抛出 `FileNotFoundError`；设备环境因 PATH 较完整未暴露该问题。
- 修复为优先使用绝对 `SHELL`，无效时回退 `/bin/sh`；不依赖 worker PATH，不改变 `config.sub` 校验逻辑。
---

**编译结束**: 2026-09-17 20:22
**最终状态**: built
