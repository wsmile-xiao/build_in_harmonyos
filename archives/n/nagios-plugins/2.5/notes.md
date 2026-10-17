# nagios-plugins 2.5 HarmonyOS 前置适配记录

## 结论

- 适配类型：C/Autotools 命令行工具集合，Conan `package_type` 为 `application`。
- 上游版本：2.5，源码包来自官方站点。
- issue：本轮按用户要求不再依赖 issue 编号。
- 当前状态：W0-W4 已完成，设备 shadow `conan create`、消费者 `test_package` 和 Shadow CI `#44395` 均通过；已复用 PR #9536，未创建重复 PR。

## W0 依赖检查

- 直接构建依赖：`openssl/3.5.6`。
- 未将数据库、LDAP、RADIUS、DBI 等可选依赖混入本库；对应插件通过上游正式 configure 选项关闭。
- Perl 仅用于上游 `plugins/t/check_dummy.t` 测试。配方在构建环境有 Perl 时运行该测试，没有 Perl 时给出 warning 并跳过，不新增未经适配的 Conan 依赖。
- `openssl/3.5.6` 已存在于仓库的独立归档目录，依赖适配不混入本 PR。

## W1 源码与构建系统分析

- 上游源码为官方 `tar.gz` 发布包，包含生成好的 `configure`、`Makefile.in` 和 `release`。
- 核心插件位于 `plugins/`，Perl/shell 插件位于 `plugins-scripts/`，root-only 插件位于 `plugins-root/`。
- `check_tcp` 的 FTP、IMAP、NNTP、POP、UDP、CLAMD 等命令名由安装 hook 创建别名；HarmonyOS 设备文件系统拒绝该处的符号链接，因此改为复制 `check_tcp` 实体文件。
- 上游 `check_dummy.t` 有 20 个确定性断言，适合作为本机或 shadow CI 的首个官方测试。
- 发布包中的 `build-aux/config.guess` 和 `config.sub` 未识别设备环境；通过显式 `aarch64-unknown-linux-gnu` build/host triplet 完成 configure，无需改动上游判断脚本。
- 设备 `/bin/ps` 输出为 `STAT UID PID PPID VSZ RSS %CPU COMM ARGS`，配方固定对应的 9 列格式和变量映射，保证 `check_procs` 等插件使用正确。
- 配方设置 `CONFIG_SHELL`、`SHELL`，并将 `TMPDIR/TMP/TEMP` 指向构建目录；同时修正 configure 临时目录的 restrictive umask，规避 HarmonyOS 文件权限限制。

## W2/W3 配方与消费者测试

- 配方使用 `AutotoolsToolchain`、`AutotoolsDeps`、`VirtualBuildEnv`，串行 `make -j1`。
- 安装前缀为包根，插件安装到包内 `bin/`；root-only 插件使用上游 `install-packager`，不写入 setuid 位。
- `test_package` 检查包内 `check_dummy` 的退出码和输出，并检查 `check_tcp`、`check_udp`、`check_disk`、`check_http` 及 TLS 别名 `check_simap` 的版本字符串。
- 上游测试命令（构建目录内）：
  `perl -I <build-folder> -I <source-folder> <build-folder>/test.pl <source-folder>/plugins/t/check_dummy.t`
- HarmonyOS libc 兼容项：`pthread_cancel` 映射到 `pthread_self`，utmpx API 映射到设备提供的 utmp API，`rindex` 映射到标准 `strrchr`；配方显式预包含 `utmp.h`，避免 CI profile 未提供声明时 `getutent` 被 Clang 当作隐式 `int` 返回。
- `test_package` 使用 `self.recipe_folder` 定位 `test.sh`，兼容 Conan 2 的 test package 对象模型。

## 验证结果

- 已下载并校验官方源码包。
- SHA256：`44d1510b5e17055fd9aa4a1d9662a234fc5d5c1b96548852c8e78701584b2684`
- Windows 主机缺少 `conan`、`clang`、`clang++`、`make`、`bash` 和 `perl`，因此 W4 在 OHOS aarch64 设备上完成。
- 设备 `conan create`：通过；OpenSSL 使用设备缓存中的独立 `openssl/3.5.6` 包。
- Shadow CI `#44395`：通过；Conan `test_package`、L0、L1 及构建流程全部通过。
- 上游 `plugins/t/check_dummy.t`：20/20 通过。
- 消费者 `test_package`：通过 `check_dummy` 正负退出码与输出、5 个插件版本检查。
- 设备包中 61 个文件成功打包，`check_tcp` 别名在构建和安装阶段均以普通文件复制完成。
- 额外设备烟测：`check_dummy`、`check_tcp`、`check_udp`、`check_disk`、`check_http`、`check_simap`、`check_users`、`check_load`、`check_procs`、`check_dns`、`check_ftp`、`check_imap`、`check_nntp`、`check_pop` 的 `--version` 均通过，并确认 `check_ftp`、`check_udp` 不是符号链接。
- 观察性警告：ICMP ping 语法未探测到可用形式；PostgreSQL、MySQL、LDAP、RADIUS、DBI、SNMP、fping 等可选插件因依赖缺失按 configure 预期跳过；OpenSSL SHA1 API 产生弃用警告。这些不影响本轮已启用插件的构建和测试。

## 复现命令

在具备 OHOS Conan profile、编译器和 shell 的 shadow CI 或真机环境执行：

```sh
conan create archives/n/nagios-plugins/2.5 \
  -pr:h=ohos-aarch64-fixed -pr:b=default --build=missing \
  -c tools.build:jobs=1

conan test archives/n/nagios-plugins/2.5/test_package \
  nagios-plugins/2.5 -pr:h=ohos-aarch64-fixed -pr:b=default
```

## 门禁兼容说明

- 仓库提交逻辑允许当前包的软件级 `commands.json` 和 `manifest.yaml`；两者已补齐，用于注册 CLI 工具及版本引用。
- 版本配方、源码校验、版本级 manifest、notes 和 `test_package` 仍集中在 `archives/n/nagios-plugins/2.5/`。
- 当前 `preflight.py` 的 PF9 路径检查要求所有 `archives/` 变更都带版本层，但同一仓库的 PF8 又要求软件级 `commands.json`；若 PF9 报软件级元数据路径错误，这是门禁实现自身的规则矛盾，不是包内容缺失。
