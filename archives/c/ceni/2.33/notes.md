# ceni 2.33 适配笔记

## 编译环境

- 构建系统: perl-makefile（ExtUtils::MakeMaker）
- 编译日期: 2026-09-09
- 编译器: clang/clang++（OHOS aarch64 预检环境；纯 Perl 包无 C 编译）
- Perl: 真机系统 perl（`shutil.which("perl")` 优先，缺失时回退 `/data/service/hnp/bin/perl` 与 `~/usr/local/bin/perl`）
- 状态: built（首轮工作树，真机预检待 HMBS 回传后更新）

## 上游审计

- 上游仓库: https://github.com/fullstory/ceni（Debian control 的 Homepage；`fullstory/ceni` 与 `fullstory-morgue/ceni` 同对象，已验证两地址的 `debian/2.33` 归档 sha256 一致）
- 源码归档: https://github.com/fullstory/ceni/archive/refs/tags/debian/2.33.tar.gz
- sha256: `5eb268f78b3a38c5a888da1ad3afc615610e0aa0b033e71fff75f2b3ec0aa335`（Windows curl 实测，`fullstory/ceni` 规范地址与实际下载地址同哈希）
- 归档结构: `Makefile.PL`、`lib/Ceni/Backend.pm`、`bin/Ceni`、`bin/nicinfo`、`bin/Ceni_read_config`、`bin/Ceni_write_config`、`bin/wpa_cli_scan.pl`、`t/Ceni-Backend.t`、`icons/`、`ceni.desktop`、`debian/`
- 构建入口: `Makefile.PL`（`NAME => Ceni::Backend`，`VERSION_FROM => lib/Ceni/Backend.pm`，`EXE_FILES => [bin/Ceni, bin/nicinfo]`）
- 上游测试: `t/Ceni-Backend.t`，`Test::More tests => 2`（`use_ok('Ceni::Backend')` + `Ceni::Backend->new({file => '/dev/null'})` 成对象），经 `make test`（prove）执行
- 依赖盘点: `Carp` / `Data::Dumper` / `Fcntl` / `Tie::File` / `Getopt::Long` / `File::Spec` / `File::Copy` 均为 perl 核心；`Expect` 仅 `wireless_scan` 的 wpa_cli 交互需要（非核心，Conan 制品仓无 `perl-expect`）；`Curses::UI` / `Term::ReadKey` 仅交互主程序 `bin/Ceni` 需要，解析器不需要
- 许可证: GPL-2.0-or-later（README 声明 GPL v2+）

## 编译步骤

```bash
perl Makefile.PL PREFIX=/
make -j1
make test
make install DESTDIR=<package_folder>
```

- `PREFIX=/` 使 `make install DESTDIR` 产物落到规范的包内 `bin/`、`lib/`、`share/man` 下，对齐 autotools `--prefix=/` 惯例
- `build()` 内真实执行 `make test`，通过后输出 `HMBS_UPSTREAM_TEST_RESULT`（perl-prove，discovered=2/executed=2/passed=2）
- `package()` 内除 `EXE_FILES` 的 `Ceni`、`nicinfo` 外，把 `bin/` 下的 `Ceni_read_config`、`Ceni_write_config`、`wpa_cli_scan.pl` 一并复制到包内 `bin/` 并统一 `chmod 755`（非交互解析场景可用；桌面文件与图标与 OHOS 无关，未打包）

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `Ceni::Backend` 顶层 `use Expect` 导致缺 `libexpect-perl` 时模块加载与上游单测整体失败 | `Expect` 仅无线扫描路径使用，却被写成编译期硬依赖；制品仓无 `perl-expect` 可供声明 | 补丁 `patches/0001-lib-Ceni-Backend-pm.patch` 改为 `eval { require Expect }` 懒加载，仅 `wireless_scan` 在缺模块时 croak 明示；解析器与单测恢复可用，有模块时行为不变；补丁无平台宏，属 POSIX 兼容的特性探测 |
| 2 | `Makefile.PL` 只安装 2 个可执行文件，解析辅助脚本会丢失 | `EXE_FILES` 仅声明 `Ceni`、`nicinfo` | `package()` 内把 `bin/` 余下 3 个脚本显式复制到包内 `bin/` |
| 3 | MakeMaker 安装的 `Backend.pm` 子路径随 perl 配置而变，测试硬编码路径易碎 | 不同 perl 的 sitelib/vendor 路径不一致 | `test_package` 在包内按 `Ceni/Backend.pm` 反查 `-I` 目录，不硬编码 `lib/perl5` |
| 4 | 真机 `apply_conandata_patches` 先后报 hunk1 行数不符、hunk2 在 463 行失配（手写 hunk 行号/计数错误；conan 打补丁器不做模糊偏移，git 宽容则掩盖了问题） | 手写 unified diff 的 `@@` 起始行与计数与 `debian/2.33` 真实源码逐行不对齐 | 改用机器生成策略：本地解包归档→改副本→`git diff --no-index` 生成补丁并规范为 `a|b/lib/Ceni/Backend.pm` 路径；hunk2 纠正为 `@@ -466,6 +471,8 @@`；校验：`git apply --check` 零偏移通过，且补丁应用后与预期修改副本逐字节一致 |

## 源码修改

- `patches/0001-lib-Ceni-Backend-pm.patch`（portability）：顶层 `use Expect;` 改为 `my $HAVE_EXPECT = eval { require Expect; 1; };`，`wireless_scan` 在创建 `Expect` 对象前缺模块时 `croak`；其余逻辑未动

## 依赖版本

- 构建期 Conan 依赖：无
- 运行期系统 perl 模块：核心模块（随 perl）；可选 `Expect`（无线扫描）、`Curses::UI` + `Term::ReadKey`（交互界面）

## 验证结果

- 上游测试：`make test`（`t/Ceni-Backend.t`，2 断言）已接入 `build()`，结果待真机预检回填
- 消费者测试：`test_package/test_ceni.pl`（6 个 `Test::More` 断言：模块加载、对象构造、`parse_eni`、eth0 方法、eth0 地址、接口已配置），经 `perl -I<packaged-lib> test_ceni.pl` 真实执行，结果待真机预检回填
- 证伪预案：若预检报告 0 执行或全跳过，按序核查 TAP 输出非空、临时 interfaces 文件非空、`make test` 的 `Files/Tests` 计数，必要时用桩二进制确认 harness 能捕获失败

## 交付物

| 文件 | 说明 |
|------|------|
| Ceni/Backend.pm | 解析器模块（包内 perl 库目录） |
| bin/Ceni | 交互主程序（需终端与 Curses::UI） |
| bin/nicinfo | 网卡信息脚本 |
| bin/Ceni_read_config | 按接口读配置节 |
| bin/Ceni_write_config | 按接口写配置节 |
| bin/wpa_cli_scan.pl | 无线扫描辅助脚本（需 Expect 与 wpa 工具链） |

## 注意事项

1. 本轮为未提交工作树，真机预检通过前不 commit、不 push、不建 PR
2. OHOS 无 ifupdown/`/sys/class/net` 语义保证：`ifup`/`ifdown`/`nic_info`/`wireless_scan` 的执行级行为依赖目标系统，配方保证的是解析、配置读写与安装可用，执行级差异在 PR 补充说明中如实声明
3. `bin/Ceni` 的完整交互验证需终端，本轮消费者测试覆盖解析器 API；若真机缺 `Curses::UI`，主程序的 `--help` 级验证与解析器测试互为补充，不伪造通过
