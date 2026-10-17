# pmount

以普通用户身份挂载可移动设备的 `mount(8)` 包装器（无需匹配的 fstab 条目），
含配套卸载工具 `pumount`。上游是 Kay Sievers 的 pmount，发布位在 Debian
alioth-archive。

- 上游主页：<https://alioth-archive.debian.org/releases/pmount/pmount>
- 已适配版本：0.9.23（Autotools，包内自带 configure/Makefile.in，不做 autoreconf）
- 直接依赖：libblkid（探测文件系统类型）、gettext 运行库 libintl（消息目录）；
  构建期工具依赖 intltool
- 产物：`bin/pmount`、`bin/pumount`，样例白名单 `res/pmount.allow`
- OHOS 侧已知限制：上游依赖 setuid-root 提权，OHOS 打包件不具备该语义，
  因此打包件不能替用户完成挂载；无参枚举路径另受 `/sys/block` 不可读限制。
  详见 `0.9.23/notes.md` 的"注意事项"。
