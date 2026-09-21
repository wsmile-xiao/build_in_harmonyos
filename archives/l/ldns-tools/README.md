# ldns-tools

`drill` 与 `ldns-*` 系列 —— ldns 自带的 DNS / DNSSEC 命令行工具集。

## Description

- `drill`：dig 风格的 DNS 调试器，支持 DNSSEC 链式验证（`-T`）、trace、反查等。
- `ldns-read-zone` / `ldns-keygen` / `ldns-key2ds` / `ldns-signzone` /
  `ldns-verify-zone` / `ldns-notify` / `ldns-walk` / `ldns-zcat` /
  `ldns-zsplit` / `ldns-gen-zone` / `ldns-test-edns` / `ldns-version` /
  `ldns-zone-digest`：区域文件读写、密钥生成、区域签名与校验等工具。

库本体（`libldns`、`ldns/*.h`、`ldns.pc`）属于 `archives/l/ldns`，本包只交付
`bin/` 下的可执行文件。

## Project URL
https://www.nlnetlabs.nl/projects/ldns/

## License
BSD-3-Clause

## HarmonyOS 适配说明

### 构建信息
- **版本**: 1.9.2（与库包 `archives/l/ldns` 同源）
- **构建系统**: autotools
- **编译器**: clang 15.0.4
- **依赖**: `openssl/3.5.6`（静态链接，drill 与签名/校验类工具需要）
- **链接方式**: `--enable-static --disable-shared`，工具自包含

### 拆包方式：按 install 目标安装
`--with-drill` / `--with-examples` 只决定"编不编这些程序"，真正的库/工具
边界只存在于 Makefile 的安装目标层，所以 `package()` 只调用：

```python
autotools.make(target="install-drill install-examples", args=[f"DESTDIR={self.package_folder}"])
```

**不能**用聚合 `make install`：它会连带 `install-manpages`，其中 470+ 个
`ldns_*.3` man3 页对命令行工具毫无意义，还会把鸿蒙端的构建拖到超时。
装完再防御性删掉 `include/ lib/`，保证同一个文件只有一个属主。

### 平台限制与补丁
| 问题 | 根因 | 处理 |
|------|------|------|
| `configure` 报 `cannot guess build type; you must specify one` | 自带的 `config.guess`（timestamp 2026-05-17）只认 `aarch64:Linux:*`，没有 HarmonyOS 分支 | 补丁 `0001` 补 `aarch64:HarmonyOS:*` 分支并让其 `echo ...; exit 0` 自终止 |
| 补了 config.guess 仍报 `Invalid configuration` | `config.sub` 不认 `aarch64-harmonyos-linux-gnu` 三元组 | 补丁 `0002` 补 3 处 ohos 规则（内核、OS 白名单、内核-OS 组合） |
| `config.status` 报 `can't create ./confXXXXXX/subs1.awk: Permission denied` | HMDFS 下 `umask 077 && mktemp -d` 建的临时目录不可写 | `build()` 里把 `configure` 两处临时目录创建改成 `umask 000 && mkdir -p $TMPDIR/conf$$` |
| L2 冒烟 | `drill` 用 getopt 而非 getopt_long，`--version`/`--help` 会落到未知选项分支 | 同工程的 `examples/ldns-version` 忽略 argv 直接打印版本，L2 由它通过，无需补丁 |
| 新二进制无法执行 | 鸿蒙安全机制要求 ELF 带 `.codesign` | `package()` 内调用 `llvm-objcopy` + `binary-sign-tool` 自签名 |

### 使用方式
```bash
drill www.example.com A
drill -T example.com                 # DNSSEC 链式验证
ldns-read-zone zone.db
ldns-keygen -a ECDSAP256SHA256 example.com
ldns-verify-zone zone.db
ldns-version
```

### 验证结果
- `ohc-run.py conan-verify ldns-tools 1.9.2`: G0-G4 / L2 / L4 / L5 全绿
- `test_package/test.sh`: 全程离线，不依赖任何解析器或网络 ——
  五个工具的存在性、`drill -v` 与 `ldns-version` 的版本输出、
  `ldns-read-zone` 对一份内嵌区域文件的解析（SOA / NS 胶水地址 / `$ORIGIN`
  展开三项断言）、以及"缺失区域文件必须非 0 退出"的反例