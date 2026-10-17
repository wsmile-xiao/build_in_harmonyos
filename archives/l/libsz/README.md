# libsz

一句话说明：libsz 是 SZIP 兼容的无损压缩库，与 libaec 同源发布，
专为空间成像与数值模式等低熵整型数据设计。

## 功能概述

- 1～32 位有符号/无符号整数的快速无损压缩（自适应 Golomb-Rice 编码，
  CCSDS 121.0-B-3）。
- 提供两套 API：SZIP 兼容接口（`szlib.h`，`libsz`）与原生 AEC 接口
  （`libaec.h`，`libaec`），同一份上游源码同时构建两个库。
- 无第三方依赖，纯 C99。

## OHOS 适配

- 适配要点：标准 CMake 构建即可；`BUILD_TESTING=ON` 跑全 7 个上游
  CTest 用例；`test_package` 用两个安装包消费者验证 `sz`/`aec` 回环。
- 已知问题：无。上游 `graec` 工具不在安装目标中，本包为纯库包。
- 与 Linux 的差异：无，行为一致。

## 依赖关系

- 编译依赖：无。
- 运行依赖：无。

## 参考资料

- 上游仓库：https://github.com/Deutsches-Klimarechenzentrum/libaec
- 主仓（GitLab）：https://gitlab.dkrz.de/k202009/libaec
- 标准文档：CCSDS 121.0-B-3
