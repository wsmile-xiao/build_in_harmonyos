# pyroute2

纯 Python **netlink** 库，提供 RTNL、nfnetlink、ipset、nftables、ethtool、nl80211 等接口，以及配套 CLI（`pyroute2-cli`、`pyroute2-decoder`、`pyroute2-dhcp-client`、`pyroute2-test-platform`、`ss2`）。

## 功能概述

- IP 地址 / 路由 / 链路等 RTNL 操作（`IPRoute`、`NDB`）
- ipset、nftables、ethtool、无线（nl80211）等 netlink 协议族
- 纯 Python 实现，Linux/OHOS 无额外 pip 运行时依赖
- 提供多个 console_scripts 入口

## OHOS 适配

- 构建：setuptools / pip `--prefix` 安装后归一化为 `lib/pythonX.Y/site-packages` + `bin/`
- `platform.uname().release` 在 OHOS 容器常为 `HongMeng Kernel …`（不以 `[0-9.]+` 开头），会使 `config.kernel` 解析为空；版本级补丁回退为 `[99, 0, 0]`，避免消费者索引 `kernel[0]` 时 `IndexError`
- 上游 `test_exceptions` 需真实 `AF_NETLINK`（`CAP_NET_ADMIN`）；OHOS worker 无权限，构建中 `--deselect` 豁免；`NetlinkError` 别名类同一性由 `test_package` 覆盖
- 本适配未验证真机 netlink 写操作

## 依赖关系

| 类型 | 依赖 |
|------|------|
| 编译 | setuptools、wheel（构建时 pip 安装）；pytest（上游 unit） |
| 运行 | 无（Windows 才需 `win_inet_pton`） |
| Conan | 无 |

## 版本

| 版本 | 状态 | 说明 |
|------|------|------|
| 0.8.1 | built | PyPI sdist；含 kernel 空值补丁与 test_exceptions 豁免 |

## 参考资料

- 官网 / 源码：https://github.com/svinota/pyroute2
- PyPI：https://pypi.org/project/pyroute2/
- 文档：https://docs.pyroute2.org/
