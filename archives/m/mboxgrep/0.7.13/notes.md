# mboxgrep 0.7.13 — HarmonyOS PC 原生适配

- 看板任务：`@tank_you` 已认领 `mboxgrep/0.7.13`，指定分支 `feat/mboxgrep-0.7.13`，活动「开源鸿蒙 PC 专项积分赛」，10 火种。路径 B（知识库扩展）候选；最终定级由维护者评定。
- 上游：官方 [0.7.13 发布包](https://github.com/dspiljar/mboxgrep/releases/tag/0.7.13)，归档 SHA-256 `be2c9d65bbdaa97a860313e394938cf4bdcbca6e5f84d5fb98434ec38b8d65b4`。发布包自带 `configure`/`Makefile.in`，无自动化上游测试入口，故上游测试数为 0，不虚构通过率。
- 真机：`10.62.210.132:2222` 经已登记 ED25519 指纹验证，`uname` 为 HarmonyOS/aarch64，Conan 2.29.1、Clang 15.0.4。源码与配方归档均经过上传、目标 SHA-256、独立回读 SHA-256 三方一致。验证运行根目录 `/data/storage/el2/base/haps/entry/files/mboxgrep-conan-0.7.13-20260929T125256`。
- 初始失败：未设置 `TMPDIR` 时，Autoconf 向只读 `/tmp` 写临时文件失败；改用应用私有目录后，原样源码 `configure` 显示 `cross compiling... no`、`make -j1` 返回 0。其 `-E -c foo` 却退出 2，误报缺少 Perl 正则：`src/misc.c` 在 `if (regextype == REGEX_PERL)` 后多一个分号，禁用 PCRE2 时会无条件进入报错块。
- 最小修复：仅删去该分号，不改上游测试；配置显式 `--without-pcre2 --without-z`，POSIX 正则保留，Perl 正则与压缩 mbox 支持不在本包能力范围。因未启用可选依赖，最终 ELF64 AArch64 可执行文件 `NEEDED` 仅 `libc.so`。
- W0：隔离 Conan home 的 `conan create --build=never` 返回缺少 `mboxgrep/0.7.13` 二进制；这只证明此次配置没有预编译包，不代表公共仓库不存在任何版本。
- W3：提交版官方 HTTPS 下载在目标机 Conan Python 连接 GitHub 时超时，`create-v1.log` SHA-256 `e617ddc3a3cd84947b1214dfa1a90b02d69a8078bae6c8c2faef0f12237756af`。同一运行根中，验证副本的 `conandata.yml` **只将 URL 改为同 SHA-256 的本地 `file://` 归档**；未修改源码、补丁、构建或测试逻辑。隔离 Conan home 的 `conan create` 返回 0，完整 `create-v2.log` SHA-256 `a10f160ea974a010c1ad1d6bab5b117c2bbe2e52ac128a84d9bfb6e24542f477`。CI 官方 URL 下载及其构建结果仍须单独验证，不据本地成功宣称 CI 通过。
- 消费者测试：最终安装包外部运行 `test_package/test_mailbox.py`，一项场景含 5 个断言：版本、默认 POSIX 匹配计数、`-E` 扩展正则、仅头部匹配、禁用 PCRE2 时 `-P` 拒绝。真机输出 `PASS: installed mboxgrep 0.7.13, POSIX patterns and PCRE2 boundary`，1/1 项、5/5 断言通过。未测试压缩邮箱、Maildir/MH、删除/写入/管道等功能。
- HD1–HD4：未见私有 OHOS 接口、私有工具链、复杂架构或大型依赖/测试成本；单一 C CLI、标准 Clang/Autotools、可选依赖关闭，因此不申报高难度路径 C。
