# nftables

nftables 是 Netfilter 的用户态包过滤管理工具与 libnftables 库（iptables 的后继者），基于 nf_tables 内核子系统。

## OHOS 适配

- Autotools 构建；`libmnl/1.0.5` 来自制品仓，`libnftnl 1.3.1` 官方源码在配方内私有静态编译（制品仓暂无该包，保持单 PR 原子性）。
- 最小依赖：`--with-mini-gmp --without-cli --disable-python --disable-man-doc --disable-debug`。
- 静态交付；`nft --version` 与 `nft --check` 解析器自检验证。

## 依赖

- libmnl 1.0.5（制品仓已发布）
- libnftnl 1.3.1（官方源码配方内私有编译，不发布）

## 功能验证

```bash
nft --version  # 期望输出: nftables v1.1.6
nft --check -f minimal.nft  # 解析器自检，无需内核
```

## 参考

- 官网: https://www.netfilter.org/projects/nftables/
- 源码: https://www.netfilter.org/pub/nftables/
- 仓库: https://git.netfilter.org/nftables/
