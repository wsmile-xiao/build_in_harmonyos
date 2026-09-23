# abuild-rootbld 3.18.0_rc3 适配笔记

## 编译环境
- 构建系统: custom（noarch 元包，无 C/C++ 编译）
- 编译日期: 2026-09-02
- 编译器: N/A
- 状态: built
- 配方底稿: archives/a/abuild-rootbld/3.17.0（同模式换版本，mkz--mkz 先例）

## 软件形态与适配思路

abuild-rootbld 是 Alpine abuild 的 **noarch 元包子包**（`_rootbld()` split 函数，APKBUILD 中仅声明依赖）：
- 运行时依赖：`abuild`（主包，提供 `abuild rootbld` 命令）+ `bubblewrap`（bwrap，chroot 沙箱）+ `cmd:envsubst`（gettext 提供，模板变量替换）
- `rootbld` 命令本体是 `abuild.in` 内的 shell 函数（`rootbld()` / `rootbld_actions()`），由 abuild 主包安装

因此本配方：
1. `requirements()` 声明 abuild/3.17.0.1 + bubblewrap/0.11.0 + gettext/0.22.5.1（依赖契约）
2. `package()` 安装 `bin/rootbld` 薄包装脚本（`exec abuild rootbld "$@"`），使入口在 PATH 可用；附带打包 abuild.in 源码摘录（share/abuild-rootbld/abuild.in）供参考
3. 无编译（build_system: custom）

## 依赖就绪情况（W0，实测）

| 依赖 | 版本 | 状态（conan download + conan install 双实测） |
|------|------|------|
| abuild | 3.17.0.1 | ✅ 已发布 ohpcd 制品仓（rrev 46572ba3b10927a688638f9d9f997d3b） |
| bubblewrap | 0.11.0 | ✅ 已发布 ohpcd 制品仓（rrev 22ecf24481ad1d6046bea5c847100c8e） |
| gettext | 0.22.5.1 | ✅ 已发布 ohpcd 制品仓（rrev e9e42b021f66183017dd3e4222f708a2） |

注：上游 abuild 无 3.18.x 的 abuild 主包发布到制品仓（3.18.0_rc3 仅为源码 tag，制品仓 abuild 主包最新为 3.17.0.1），故 requirements 引用 abuild/3.17.0.1（制品仓实际可用的最新修复版，3.17.0.1 为 3.17.0 的适配修复版，先例 3.17.0 配方引用 3.17.0，本配方升级为最新修复版）。

## 上游 diff 要点（3.17.0 → 3.18.0_rc3）

对比两版本 abuild.in 的 `rootbld_actions()`（3.17.0: 2482-2508 行 / 3.18.0_rc3: 2444-2470 行）与 `rootbld()`（3.17.0: 2510-2687 行 / 3.18.0_rc3: 2472-2669 行）：

**依赖契约不变（关键结论）**：
- 两版本 rootbld() 开头的依赖检查完全一致：`if ! command -v bwrap >/dev/null || ! command -v envsubst >/dev/null; then die "rootbld: requires bubblewrap and envsubst (try installing abuild-rootbld)"`
- bwrap 沙箱调用（`bwrap --new-session --unshare-ipc --unshare-uts ...`）参数结构不变

**rootbld() 内部改进（不依赖契约，不影响配方结构）**：
1. chroot 目录创建加固：`mktemp -d` 包裹 `umask 0077` + `chmod g-s "$BUILD_ROOT"`
2. git 调用改进：`$git` → `$git -C "$startdir"`（symbolic-ref / config --list / config --get 三处）
3. apk 初始化改进：`$SUDO_APK add` → `ROOTBLD_APK`（`$APK --no-interactive`，非 root 加 `--usermode`）
4. 包缓存改进：删除 `/etc/apk/cache` cachedir 探测，改用 `ABUILD_PACKAGE_CACHE`（默认 `${XDG_CACHE_HOME:-$HOME/.cache}/apk`）
5. abuild.conf 源：`cat - /etc/abuild.conf` → `cat - "$ABUILD_CONF"`
6. repositories 生成：新增 `echo "$REPODEST/$repo"` 首行

**结论**：rootbld 的外部依赖契约（abuild + bubblewrap + envsubst）与命令入口（`abuild rootbld`）在 3.18.0_rc3 中完全不变，先例 3.17.0 配方结构完全沿用，仅换版本号与源码 URL/sha256，abuild 依赖引用升级为制品仓最新修复版 3.17.0.1。

**其他 diff（不影响本元包）**：abuild-rmtemp.c 被移除（重命名为 abuild-rm.c）、Makefile/abuild-keygen/abuild-sign 等文件更新——这些属于 abuild 主包范畴。

## 上游测试情况（如实记录）

- `abuild-rootbld` 无独立上游测试套件：rootbld 是 abuild.in 内的 shell 函数，abuild 自身的 ATF/Kyua 测试（tests/*_test）不涉及 rootbld（3.17.0 与 3.18.0_rc3 两版本均无 tests/rootbld* 测试文件）
- 本配方 test_package 验证依赖契约（与先例 3.17.0 同款 5 项断言）：
  1. `rootbld --version`（wrapper 可执行，输出版本）
  2. `bwrap --version`（bubblewrap 依赖在位）
  3. `envsubst --version`（gettext 依赖在位）
  4. `abuild` 存在性（abuild 依赖在位）
  5. test.sh 整体冒烟（rootbld/bwrap/envsubst/abuild 命令存在性）

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 主工作树被并行任务占用（boost 分支） | 多任务共享仓库 | git worktree 隔离（wt-abuild-rootbld-3.18.0_rc3），基于最新 main 73c2b47a25 |
| 2 | conan CLI shebang 权限问题 | 环境限制 | 用 `python3 -c "from conans.conan import run"` 直调 |
| 3 | noarch 元包 G4 产物检查 | G4 要求 bin/ 产物 | package() 安装 bin/rootbld 委托包装脚本（非空产物），沿用先例方案 |

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py | noarch 元包配方（requirements 三依赖 + rootbld wrapper） |
| conandata.yml | abuild 3.18.0_rc3 tarball 源（sha256 校验） |
| test_package/ | 依赖契约冒烟测试（conanfile.py + test.sh + MANIFEST.yml） |
| manifest.yaml | 版本级（status=built） |
| 软件级 manifest.yaml | 版本索引新增 3.18.0_rc3 |
| commands.json | 软件级 tool 声明（commands: rootbld，新增 3.18.0_rc3 版本条目） |

## 注意事项

- rootbld 实际沙箱构建需要 bwrap user namespaces / setuid，OHOS 上受限（与 bubblewrap 相同），不影响本元包编译与依赖契约验证
- 上游 tag 为 3.18.0_rc3（rc 版本），版本号按任务指定使用，不跟进上游后续 rc
---

**编译结束**: 2026-09-02 22:54
**最终状态**: built
