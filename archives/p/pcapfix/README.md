# pcapfix — OpenHarmony 编译档案

## 软件简介
pcapfix（Robert Krause / Rup0rt 维护）是一个修复 **损坏 pcap / pcapng 抓包文件** 的
命令行工具：当文件的全局头（magic、版本、snaplen、链路类型）或包头损坏时，它通过
包结构启发式扫描重建头部字段，尽最大可能恢复数据（`pcapfix damaged.pcap`，输出
`fixed_damaged.pcap`，或 `-o` 指定输出）。许可证 GPL-3.0-or-later。本次适配上游
发布版 **1.1.7**（GitHub tag `v1.1.7`）。

## OHOS 适配要点
- 纯 Makefile 单二进制，无 configure/autotools，**零依赖**（全部 include 为 libc
  标准头），`make CC=<OHOS clang>` 即可构建。
- 上游默认 CFLAGS 含 gcc 专属 `--param=ssp-buffer-size=4` 与 `$(shell getconf …)`，
  配方整体显式覆盖 CFLAGS；Makefile 自带的 `LDFLAGS += -Wl,-z,relro` 保持生效。
- 上游 `make install` 使用 GNU-only `install -pDm`，打包由 `package()` 手动复制
  `bin/pcapfix`、`share/man/man1/pcapfix.1`、`licenses/COPYING`。
- pcapfix **无 --version/-h/--help 选项**：无参数调用打印 usage 且返回非零
  （CI L2 smoke 为非阻塞 warn，行为在 test_package 中显式断言）。
- 上游**无测试目标/测试目录**（Makefile 仅 all/pcap/pcap_kuznet/pcapng/install/
  uninstall/clean）；test_package 自带功能测试：对 4 字节 magic 被清零的 pcap 执行
  修复，断言退出码 0、`[+] SUCCESS: 1 Corruption(s) fixed!` 横幅、magic 恢复、
  文件大小不变。

## 依赖关系
- 无编译/运行依赖（仅 C 运行时）
- 被依赖: 无（独立 CLI 工具）

## 参考资料
- [pcapfix 官方主页](https://f00l.de/pcapfix/)
- [pcapfix GitHub 仓库](https://github.com/Rup0rt/pcapfix)
- [v1.1.7 源码归档](https://github.com/Rup0rt/pcapfix/archive/refs/tags/v1.1.7.tar.gz)
