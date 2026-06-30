# Net::Domain::TLD

Perl 模块，提供 TLD (Top Level Domain) 查询功能，支持 1906 个顶级域名，包括 gTLD、ccTLD、new gTLD 等。

## 主要功能

- `tld_exists($tld)` — 检查 TLD 是否存在
- `tld_exists($tld, $type)` — 检查指定类型的 TLD 是否存在
- `tlds()` — 获取所有 TLD 列表
- `tlds($type)` — 按类型获取 TLD 列表 (cc/gtld_open/gtld_new/gtld_restricted/new_open/new_restricted/ccidn)

## 编译指导

纯 Perl 模块，使用 Makefile.PL 构建，无需 C 编译器：

```bash
perl Makefile.PL
make
make install DESTDIR=/tmp/destdir
# 复制 .pm 到标准位置
cp /tmp/destdir/.../Net/Domain/TLD.pm lib/perl5/Net/Domain/TLD.pm
```

### HarmonyOS 注意事项

- 纯 Perl 模块，不受 SELinux/HMDFS 限制，可直接安装使用
- 依赖 Storable 和 Carp，均为 Perl 内置模块
- `%tld_profile` 无法导出（上游 bug: 声明为 `my` 而非 `our`），不影响核心功能

## 版本列表

| 版本 | 状态 | 编译日期 |
|------|------|----------|
| [1.75-r0](./1.75-r0/) | published | 2026-06-26 |
