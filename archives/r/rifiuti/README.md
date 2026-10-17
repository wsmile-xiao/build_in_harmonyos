# rifiuti

Windows 回收站元数据（`INFO2` 文件）解析工具。

rifiuti 读取 Windows 回收站目录里的 `INFO2` 索引文件，按记录逐条输出：

```
INDEX	DELETED TIME	DRIVE NUMBER	PATH	SIZE
```

即被删除文件在 `INFO2` 中的索引号、删除时间（Windows `FILETIME` 换算成
`MM/DD/YYYY HH:MM:SS`）、所在盘符、原始完整路径与文件大小，字段间默认用 TAB
分隔（`-t` 可改分隔符）。它是纯格式解析工具：只读文件，不访问任何设备、
不联网、不需要特权。

- 上游：Keith J. Jones（Foundstone），2004-05-05 版
- 许可证：BSD-3-Clause（许可文本在源码文件头部注释里，包内无独立 LICENSE）
- 构建系统：仅 `src/Makefile`（实测 215 字节、4 个目标），内有**两条**硬编码 `gcc` 的编译命令：
  `src/Makefile:4`（`install` → `rifiuti`）与 `:7`（`installwin` → `-DCYGWIN` 的 `rifiuti.exe`，CYGWIN 专用）；
  默认 `all: install` 只走第一条，本配方复刻的就是第一条（详见版本级 notes.md）
