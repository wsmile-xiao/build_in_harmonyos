# minmea

minmea 是一个用纯 C 编写的轻量级 GPS NMEA 0183 语句解析库，面向资源受限场景（嵌入式、
微控制器），单文件 `minmea.c` + 单头文件 `minmea.h`，无动态内存分配、核心路径不使用浮点。

## 功能概述

- 解析 RMC / GGA / GSA / GST / GSV 五类 NMEA 语句，其他语句返回 `MINMEA_UNKNOWN`。
- 提供校验和验证（`minmea_check`）、语句分类（`minmea_sentence_id`）、字段扫描
  （`minmea_scan`）与各语句的解析函数。
- 定点数 `{value, scale}` 表示坐标与小数，配套 `minmea_rescale` / `minmea_tofloat` /
  `minmea_tocoord` 换算；纯 ISO C99 实现。

## 鸿蒙适配

- 使用 Conan Makefile 配方构建静态库 `libminmea.a`（上游 Makefile 无 install 目标，
  安装动作由 `package()` 完成）。
- 上游测试入口 `make test`（Check 框架，23 个注册用例）在 `build()` 内真实运行；
  `scan-build` 目标因设备/CI 不提供 clang 静态分析包装器而不执行，其余 `all` 目标
  （`test`、`example`）全部构建。
- Check 0.15.2 运行期临时文件目录改指构建目录（`TEMP`/`TMP`/`TMPDIR`），绕开 OHOS 只读 `/tmp`。
- 配方侧以 `-Wno-error=format-security` 消化 clang 15 对 `ck_assert_msg` 非字面量格式串的
  诊断，不修改上游源文件、不生成补丁。
- 在 HarmonyOS PC arm64（os=OHOS, arch=armv8, clang 15）配置下完成 Conan 干净构建与
  消费者测试。

## 依赖关系

- 编译依赖：无（核心库只用 ISO C99 头文件）。
- 运行依赖：无。
- 测试依赖：`check/0.15.2`（仅 `tests.c` 使用，不进安装接口）。

## 参考资料

- 上游仓库：https://github.com/kosma/minmea
- 源码：https://github.com/kosma/minmea/archive/refs/tags/v0.3.0.tar.gz
