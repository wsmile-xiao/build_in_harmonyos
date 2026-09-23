# ceni (Curses network interface configurator)

## 简介

Ceni 是面向 ifupdown 的 Curses 网络接口配置工具，提供交互式界面与一批可脚本化的解析辅助脚本。核心解析逻辑位于纯 Perl 模块 `Ceni::Backend`（interfaces 文件解析、接口配置读写），交互界面由 `bin/Ceni`（依赖 `Curses::UI`）承载。

### 主要特性

- 解析与写回 `/etc/network/interfaces` 风格的 ifupdown 配置
- `Ceni_read_config` / `Ceni_write_config` 支持按接口读写配置节
- `nicinfo` 输出网卡连接类型、驱动、总线、MAC 与描述
- 上游自带 `t/Ceni-Backend.t` 单测（模块加载与对象构造）

## 版本历史

| 版本 | 状态 | 编译日期 | 说明 |
|------|------|----------|------|
| 2.33 | built | 2026-09-09 | 首个适配 OHOS 的版本，纯 Perl 打包 |

## OHOS 适配说明

### 编译环境

- **构建系统**: perl-makefile（ExtUtils::MakeMaker）
- **流程**: `perl Makefile.PL PREFIX=/`、`make -j1`、`make test`、`make install DESTDIR`
- **依赖**: 构建期无 Conan 依赖；运行期 `Curses::UI`、`Term::ReadKey` 仅交互主程序需要，解析器仅可选依赖 `Expect`

### 关键适配点

1. **Expect 懒加载**：`lib/Ceni/Backend.pm` 顶层 `use Expect` 改为 `eval { require Expect }` 懒加载，仅 `wireless_scan` 在真正调用且缺模块时 croak。解析器（`parse_eni`）与上游单测不再硬依赖 `libexpect-perl`，有模块时无线扫描行为保持不变。
2. **可执行脚本全量安装**：除 `Makefile.PL` 声明的 `Ceni`、`nicinfo` 外，`make install` 后把 `bin/` 下的 `Ceni_read_config`、`Ceni_write_config`、`wpa_cli_scan.pl` 一并复制到包内 `bin/`，方便非交互场景调用解析器。
3. **上游测试内建**：`build()` 内真实执行 `make test`（2 个断言），并输出 `HMBS_UPSTREAM_TEST_RESULT` 证据标记。

### 已知限制

| 事项 | 说明 |
|------|------|
| 交互界面 | `bin/Ceni` 需要终端与 `Curses::UI`，OHOS 上仅保证安装与 `--help` 级别可用性，核心验证走解析器 API |
| 无线扫描 | 需 `Expect`、`wpa_supplicant`、`wpa_cli` 与 `/sys/class/net`，缺失时 `wireless_scan` 明确报错而非静默跳过 |
| 网络管理 | OHOS 无 ifupdown，`ifup`/`ifdown` 相关能力仅保留解析与配置生成，实际生效依赖目标系统网络栈 |

## 使用说明

```bash
# 解析接口配置（示例）
perl -I<package>/lib/perl5 -MCeni::Backend -e 'print "ok"'
bin/Ceni_read_config --iface eth0 --input ./interfaces
bin/nicinfo --help
```

## 参考资料

- 上游: https://github.com/fullstory/ceni
- Debian 源码: https://packages.debian.org/source/bookworm/ceni
