# libservicelog

IBM Power 平台服务事件日志库（C + sqlite3）。为 Power 固件/平台事件提供统一的
记录、查询、打印接口（v1 API `servicelog.h`）并保留 v0.2.9 兼容层，配套
PPC64 平台专属的 RTAS 事件打印（librtasevent 解析）。本身为纯 C + sqlite3，
可在鸿蒙 PC 上直接构建运行。

- 上游：https://github.com/power-ras/libservicelog
- 构建：autotools（本配方手写 clang 直编，上游 `-release 1.1 -version-info 1`
  命名语义由配方复刻：libservicelog-1.1.so.1.1.19 / SONAME .so.1）
- 依赖：制品仓 `sqlite3/3.53.4`（静态库内联进共享库）；librtas 整包不依赖
- 测试：上游 6 场景（BASIC/OS/RTAS/ENCL/BMC 五类事件 log→dump 往返 + 截断
  语义），test_package 以消费者方式全量跑通

## OHOS 适配

- 上游 `configure.ac` 对 librtas/librtasevent 做 AC_CHECK_LIB 硬校验，但 v1
  主打印路径不调用它们（已审计：仅 v29 兼容层引用 parse_rtas_event 等符号）。
  配方从官方 librtas 2.0.4 源码包提取 `librtasevent_src/` 14 个纯解析 .c
  文件（零 librtas 依赖）内联编译进 libservicelog，闭合链接且无需适配 librtas
  整包。
- `SERVICELOG_PATH` 硬编码 `/var/lib/servicelog/servicelog.db`，鸿蒙无此路径：
  补丁 0001 增加 `SERVICELOG_DB` 环境变量覆盖（默认行为不变，与上游
  repair_action.c 的 `SERVICELOG_TEST` 惯例一致）。
- HMDFS 禁符号链接：soname/开发名/无版本名（pkg-config 广告的
  `-lservicelog`）以真实文件拷贝物化，非 ln -s。
- 上游测试器为 bash + GNU `diff -y`，设备不可用：test_package 以 POSIX 移植
  驱动同一组 6 场景 + python 容差比较器（复刻上游 timestamp 容差语义）。

## References

- https://github.com/power-ras/libservicelog
- https://github.com/ibm-power-utilities/librtas（librtasevent_src 来源）
