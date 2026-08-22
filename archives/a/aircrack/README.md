# aircrack-ng

WiFi 网络安全评估工具套件，支持 WEP/WPA/WPA2 密码破解、抓包（airodump-ng）、
注入（aireplay-ng）、数据包解密（airdecap-ng）等。

## 功能概述

- `aircrack-ng` — WEP/WPA/WPA2 密钥破解
- `airodump-ng` — 802.11 数据包捕获
- `aireplay-ng` — 数据包注入
- `airbase-ng` — 流氓 AP 模拟
- `airdecap-ng` — 抓包文件解密
- `airolib-ng` — 密码字典数据库（需 sqlite3）
- `wpaclean` / `packetforge-ng` 等辅助工具

## OHOS 适配

- 官方 tarball 不含 configure，构建前需运行 `./autogen.sh`。
- OHOS 无 libnl，configure 需 `--disable-libnl`。
- 无线注入/监听类工具依赖网卡驱动与 root 权限，在 HarmonyOS PC 上功能受限；
  离线破解/解密类功能（aircrack-ng、airdecap-ng、wpaclean）可用。

## 依赖关系

- 编译依赖：无（可选依赖 libnl 已禁用）
- 运行依赖：无

## 参考资料

- 官网: https://www.aircrack-ng.org/
- 源码: https://github.com/aircrack-ng/aircrack-ng
