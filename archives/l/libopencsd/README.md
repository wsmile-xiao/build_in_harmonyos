# libopencsd (OpenCSD)

## 是什么

OpenCSD（Open CoreSight Decode）是 ARM 官方的 CoreSight 追踪数据解码库，
支持 ETMv3 / ETMv4 / ETE / PTM / STM 协议解码，输出通用追踪元素
（generic trace elements），并提供稳定的 C API（`opencsd/c_api/opencsd_c_api.h`）。
Linux 内核 perf 子系统与 OpenCSD 解码头对接即基于该库。

## 功能概述

- ETMv3 / PTM / ETMv4 / ETE / STM 追踪流解码；
- 帧解格式化（TPIU deformatter）；
- 内存访问抽象（文件/缓冲区/回调三种内存访问器）；
- 快照解析与包列表工具（`trc_pkt_lister` 等测试工具）；
- C API 与 C++ API 双接口。

## OHOS 适配

- 纯 C++11/POSIX 实现，无外部第三方依赖，源码零补丁；
- 自定义 Makefile 构建（`decoder/build/linux/makefile` + `unix_common/makefile.common`），
  无 configure 步骤；工具链经 make 变量 `MASTER_CC/MASTER_CXX/MASTER_LINKER/MASTER_LIB` 注入
  （R33：取值自 Conan conf `tools.build:compiler_executables`，禁止裸用 shell `${CC}`）；
- OHOS 上测试可执行文件（`trc_pkt_lister` 等）需用 HNP `binary-sign-tool` 签名后才能 exec；
  库文件（.so）无需签名即可作为 DT_NEEDED 在 exec 时加载（CI worker 对用户目录 .so 的
  dlopen 存在平台限制，详见 E502）；
- macOS 本地验证：ld64 不支持 `-soname`/`-z defs`，本地构建以 `-install_name` 替代
  `-soname` 并去掉 `-Wl,-z,defs`（仅影响本地验证，OHOS/CI 保持上游链接参数）；
- 上游测试为 3 个 bash 脚本（`run_pkt_decode_tests.bash` / `run_pkt_decode_tests-ete.bash` /
  `run_capi_test.bash`）声明的 61 个命令行测试场景，无正式测试框架；适配中用驱动器
  逐场景执行并检查 rc==0。

## 依赖关系

- 编译依赖：无（C++11 标准库 + libc/libm）
- 运行依赖：libc++（OHOS SDK 自带）

## 参考资料

- 上游仓库：https://github.com/Linaro/OpenCSD
- 上游文档：decoder/docs（HOWTO.md / doxygen）
