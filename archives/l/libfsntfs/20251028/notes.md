# libfsntfs 20251028 适配笔记

## 当前状态

- 状态：built，真机 shadow CI 通过，制品尚未上传
- 分支：`feat/libfsntfs-20251028`
- worktree：`D:\harmonyos\worktrees\libfsntfs`
- 主仓库未切换分支
- issue：按本轮要求不追踪
- 真机：已通过指定 OHOS aarch64 真机 SSH 执行单包 shadow CI

## W0 依赖检查

上游 `configure.ac` 将以下组件作为本地 libyal 依赖参与构建：

`libbfio libcdata libcerror libcfile libclocale libcnotify libcpath libcsplit libcthreads libfcache libfdata libfdatetime libfguid libfusn libfwnt libhmac libuna`

当前归档中没有这些组件的独立 Conan 包，`ohpcd` 远端也没有对应 recipe。根据“一库一分支”约束，本 PR 不混入这些依赖的适配。

`libfuse` 只用于可选工具支持，本配方显式关闭 `--with-libfuse=no`，因此不把它作为当前构建依赖。

## W1 源码与构建系统

- 上游项目：`https://github.com/libyal/libfsntfs`
- 目标版本：`20251028`
- 已确认对应提交：`f8994835320b989894fe53970c721efed83df220`
- 提交时间：`2025-10-28 17:31:57 UTC`
- 构建系统：Autotools
- 上游官方测试：`make check`
- 上游测试包含 4 个 shell runner 和约 75 个 C 测试程序
- 源包内置的 `config.guess/config.sub` 不识别 HarmonyOS/OHOS；配方在 OHOS profile 下显式传入 `--build=aarch64-unknown-linux-gnu --host=aarch64-unknown-linux-gnu`，绕过平台猜测。

已下载并校验 Debian 镜像中的上游 orig 源码包：

- URL：`https://deb.debian.org/debian/pool/main/libf/libfsntfs/libfsntfs_20251028.orig.tar.gz`
- SHA256：`9edbd1982f8868121391a35696e34c413794a5d88cd91e4ec8b183133eb577f6`
- Debian 源包：`libfsntfs_20251028-1`

该 orig 源码包包含 17 个本地 libyal 依赖目录和发布包生成的 `configure`、`aclocal.m4`、`config.guess`、`config.sub`、`Makefile.in`。其中 `configure.ac`、`Makefile.am`、`libfsntfs/Makefile.am`、`include/libfsntfs.h.in` 与 `f8994835320b989894fe53970c721efed83df220` 提交逐字一致。

上游原始 release URL `https://github.com/libyal/libfsntfs/releases/download/20251028/libfsntfs-experimental-20251028.tar.gz` 当前返回不可用，因此使用 Debian archive 的 orig tarball 镜像；配方保留原始 URL 和 upstream commit 作为溯源信息。

此前也复现过 Conan 对 GitHub codeload 地址的格式误判：未显式传入文件名时把 tar.gz 当成 ZIP，报 `BadZipFile`。当前配方对 Debian 源包同样显式传入 `filename`，避免依赖 URL 推断。

## W2/W3 配方与 test_package

已准备：

- 固定 URL 和 SHA256 的 Conan 配方
- Debian archive 镜像源包的固定 URL、SHA256 和上游 release 溯源
- Autotools HarmonyOS 配置参数
- `make check` 集成位置
- 消费者视角的 `test_package`
- `test_package/MANIFEST.yml` 上游测试清单

配方在 `build()` 开始处主动检查自包含发布包条件；缺失时给出明确阻塞信息，不执行未锁定的 `synclibs.sh`，也不把依赖适配混入本库。

消费者测试覆盖 9 个断言：

- 版本字符串
- 只读访问标志
- codepage 正常路径和错误路径
- `set_codepage(0)`
- NTFS 签名检查错误路径
- volume 初始化与释放

OHOS 专项消费者测试覆盖 5 个断言，仅在 `settings.os=OHOS` 时编译和运行：

- 编译目标必须定义 `__OHOS__`
- libfsntfs 版本必须为 `20251028`
- 真机测试必须使用非 `/tmp` 的 `TMPDIR`
- 在 `TMPDIR` 下创建、写入并读回临时文件
- 临时文件可以删除且删除后不可访问

## W4 本机验证

已完成：

- Debian orig 源码包下载、SHA256 校验和完整目录检查
- `conan inspect`、Python 语法检查、YAML 解析和 `git diff --check`
- 上游目录和构建入口盘点
- `test_package` 源码静态检查
- 改动范围检查

Windows 本机限制：

- `make` / `make check`：Windows 本机无法执行 Unix `configure`，没有可用的 Autotools shell 工具链

## W5 真机 shadow CI

使用真机已有的 `ci/conan/build_and_test.sh` 执行单包构建；设备上未发现工作流文档中的
`ohos-prepare-isolated-conan-job.sh`，因此直接使用现有 runner，并隔离临时目录：

```sh
mkdir -p "$HOME/tmp-zsh" "$HOME/tmp-conan"
export TMPPREFIX="$HOME/tmp-zsh/zsh"
export TMPDIR="$HOME/tmp-conan"
export PATH="/data/service/hnp/bin:$PATH"
CI_PACKAGES="archives/l/libfsntfs/20251028" \
CONAN_PROFILE="ohos-aarch64" \
CONAN_REMOTE_NAME="ohpcd" \
/storage/Users/currentUser/usr/local/bin/zsh -f ci/conan/build_and_test.sh
```

结果：

- L0：通过
- L1：通过；上游 `make check` 执行，Conan `test_package` 执行
- L2：非阻塞 skip；`fsntfsinfo` 和 `fsntfsmount` 的 `--version/--help` smoke probe 未通过
- L4：通过；无独立源码 patch 文件
- L5：通过；`bin/` 有内容
- 上游测试：2 PASS、2 SKIP、0 FAIL
- 消费者测试：9/9 通用断言通过，5/5 OHOS 专项断言通过
- Shadow CI Build Summary：Total 1、Success 1、Failed 0
- 负向测试：移走 `bin/`、`lib/`、`include/` 后，测试正确失败，确认真实链接依赖

## 真机问题与处理

1. 真机 HMDFS 禁止直接执行源码目录中的 shell 脚本。配方用 `CONFIG_SHELL` 显式启动
   `configure`，并让 `make check` 通过 `LOG_COMPILER` 启动 shell 测试。
2. Autoconf 默认的 `umask 077` 会生成不可写的 `confXXXXXX` 目录。OHOS 构建期将
   `configure` 中该处改为 `umask 022`，并在配方中保持整个构建过程使用 `umask 022`。
3. Conan 的 Autotools 默认构建目录与上游源码内 Makefile 位置不一致；配方在源码目录
   显式执行 `make -j1`、`make -j1 check` 和安装。
4. libtool 测试目标是包装脚本，真实 ELF 位于 `.libs`。OHOS 构建期测试运行器解析到
   `.libs`，并注入 `libfsntfs/.libs` 的 `LD_LIBRARY_PATH`。
5. 两个输入驱动测试因发布源包不含 `input` 测试数据而按上游规则 skip；这不是构建失败。
6. 真机仓库的 `build_and_test.sh` 没有可执行权限，使用设备已有的
   `/storage/Users/currentUser/usr/local/bin/zsh -f` 显式解释脚本；该方式不改变脚本内容。

## Path B 知识扩展候选

本轮补充一对与 `libfsntfs` 直接相关的知识草稿：

- `knowledge/drafts/DRAFT-libfsntfs-release-archive-closure.kv`
- `knowledge/drafts/DRAFT-libfsntfs-release-archive-closure.md`

候选主题不是重复申报 HMDFS shell、`umask` 或 libtool `.libs` 运行机制，而是可迁移的
“多组件 libyal Autotools 发布包闭包审计”：

1. 从 `configure.ac`/`Makefile.am` 提取 17 个本地 libyal 组件，构建前确认源码目录和
   `configure`、`aclocal.m4`、`Makefile.in` 等生成文件齐全；
2. 上游 release URL 不可用时，仅接受固定 SHA-256、显式文件名，并以关键源文件与
   上游提交比对作为发行版 orig 镜像的身份依据；
3. 自包含闭包成立时不新增 17 个 Conan 依赖、不调用未锁定的 `synclibs.sh`，保持
   一库一分支边界；
4. 将顶层 runner、可执行测试、input/fixture 能力和 PASS/SKIP/FAIL 分开统计。

去重边界已写入草稿：E277 是缺失 vendored 依赖的 build-time staging，E337/E058 是
缺少生成文件时的 bootstrap，E270/E2147 是外部测试对象或嵌套 fixture 计数；本候选
只主张发布包身份与源码闭包审计的组合方法。该贡献按路径 B（10 分候选）申请，最终
认定以知识库维护者和官方评审为准。

当前没有构建阻塞。AtomGit PR #9922 已创建，源分支为
`feat/libfsntfs-20251028`，目标分支为 `main`。PR 正文按本次自检结果补正；
评审和测试人流程仍以 AtomGit 页面状态为准。
