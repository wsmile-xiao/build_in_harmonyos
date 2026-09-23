# lib1541img

> 处理 Commodore 1541 磁盘镜像（`.d64`）的 C 库。

## 简介

lib1541img 用纯 ISO C（C11）实现，用于创建与修改 Commodore 1541 软驱的 `D64`
磁盘镜像。它采用面向对象的 API，分三层建模：

- `D64`（及 `Track`/`Sector`）：物理层，磁盘的磁道与扇区；
- `CbmdosVfs`（及 `CbmdosFile`）：虚拟文件系统层（磁盘名/ID、目录与文件）；
- `CbmdosFs`："粘合层"，把 VFS 布局到 D64 上并维护 BAM 等。

另含事件机制、日志接口、ZipCode 压缩/解压、LyNX 归档、PC64 容器导入导出等。

## OHOS 适配要点

- 纯 C，无外部依赖。
- 上游用 `zimk` 子模块（GNU make 框架）构建，**发布 tarball 不含该子模块**；
  本仓库直接逐个编译 `src/lib/1541img/*.c` 为静态库 `lib1541img.a`。
- 安装 `include/1541img/*.h` 与 `lib/lib1541img.a`；CMake 目标 `1541img::1541img`。
- 上游无测试套件；本包在 `test_package` 做端到端验证。

## 依赖

| 依赖 | 版本 | 说明 |
| --- | --- | --- |
| （无） | - | 仅标准 C 库（hosted 环境） |

## 功能验证

```c
#include <1541img/d64.h>
#include <1541img/cbmdosfs.h>
#include <1541img/cbmdosvfs.h>
#include <1541img/cbmdosfile.h>
#include <1541img/filedata.h>
/* 新建文件系统 -> 设置盘名/ID -> 添加 CbmdosFile -> 写 D64 -> 读回校验 */
```

## 参考

- [源码仓库](https://github.com/excess-c64/lib1541img)
- [上游 README](https://github.com/excess-c64/lib1541img/blob/master/README.md)
