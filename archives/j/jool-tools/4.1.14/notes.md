# jool-tools 4.1.14

## 范围

本配方构建并交付上游用户态程序 `jool`、`jool_siit` 和 `joold`、对应 man8 手册及许可证。不构建或交付 `src/mod` 内核模块，也禁用可选 xtables 扩展和 bash completion。

## 依赖与构建

- 上游 `configure.ac` 检查 `libnl-genl-3.0 >= 3.2.22`；使用仓库 `libnl/3.11.0`。
- 上游含 `AC_CHECK_LIB(argp, argp_parse)`；OHOS musl 不提供 argp，使用已发布的 `argp-standalone/1.5.0`。
- 使用官方 v4.1.14 release tarball（含 `configure`），不需 autoreconf。
- 源码 SHA-256 由官方 release URL 下载后实测：`Get-FileHash jool-4.1.14.tar.gz -Algorithm SHA256` → `ECCD5517C575FB043C1C55C8CF24ECB03E2D0878B4F7901877DC6359B2BA284F`；与 `conandata.yml` 一致。
- 复用 libnl/3.11.0 的静态 `.a` 并把 PkgConfigDeps 生成的 `.pc` 搜索目录指向不含 `.la` 的目录，避开上游 libnl `.la` 中 `libdir='//lib'` 对嵌套 libtool 链接的干扰。
- `--with-xtables=no` 将 iptables 扩展排除在交付范围外。
- 上游发行包没有 `TESTS`、`check_PROGRAMS` 或 `test/` 测试套件；仍执行 `make check` 并由 `test_package` 验证三个实际交付 CLI。
- release 自带的旧 `config.sub` 实测拒绝 `aarch64-linux-ohos`（`OS 'ohos' not recognized`）。`patches/0001-config.sub-ohos-triplet.patch` 为其补充 OHOS OS/kernel 组合白名单，并实测使 `aarch64-unknown-linux-ohos` 可规范化。OHOS 配置使用该明确目标 triplet；Conan 有真实交叉 build profile 时保留其 `--build`，同为 OHOS AArch64 的 CI build/host 配置则显式指定匹配的实际构建 triplet。E119 两个 CPPFLAGS 宏仅在 OHOS 注入。
- GitCode CI 首次完成配置探测后，Autoconf 因 `umask 077` 在 HarmonyOS HMDFS 临时目录权限策略下创建不可写的 `confXXXXXX`，报 `subs1.awk: Permission denied`。`patches/0002-configure-temp-umask.patch` 只把 `configure` 的临时目录 umask 调整为 `022`，保留当前用户对临时脚本的读写权限。

## HarmonyOS PC 测试

`test_package/test_cli.sh` 对三个程序核验存在性、ELF 魔数和 AArch64 `e_machine`，并检查 CLI 版本/帮助及 `joold` 无参错误契约。OHOS 上另执行 `jool instance display` 与 `jool_siit instance display`，验证真实 netlink 请求在缺少 Jool 内核模块时 fail-closed、输出可操作提示且不崩溃；不声明内核模块构建、加载或转发功能通过。
