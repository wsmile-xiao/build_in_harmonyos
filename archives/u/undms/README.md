# undms

`undms` 是 Amiga DMS 软盘镜像解包命令行工具（作者 David Tritscher，Aminet `misc/unix`）。

## 功能概述

- 将 `.dms` 解包为原始磁盘镜像：`undms source.dms destination.img`
- 支持 store / RLE / quick / medium / deep / heavy 压缩轨；不支持加密 DMS

## OHOS 适配

- 上游只发布 Unix compress 压缩的单个 C 文件（`undms-1.3.c.Z`）；配方用纯 Python LZW 解码，不依赖设备 toybox gzip
- 上游无构建系统：配方生成最小 CMake 工程，经 Conan CMakeToolchain 交叉编译为静态 aarch64 CLI，无源码补丁
- `test_package` 用包内 CLI 解包双轨 DMS，解包产物参与消费者编译并运行逐字节核验

## 依赖关系

- 编译：C 编译器、标准 C 库；运行：无

## 参考资料

- Aminet 条目：<https://aminet.net/package/misc/unix/undms-1.3.c>
- 源码：<https://ftp.fau.de/aminet/misc/unix/undms-1.3.c.Z>
- 许可：源码与 Aminet readme 均未声明许可，配方标记 `unknown`
