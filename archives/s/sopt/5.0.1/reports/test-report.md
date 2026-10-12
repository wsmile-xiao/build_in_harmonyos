# SOPT 5.0.1 测试报告

2026-10-04；实际运行：OHOS 7.0.0.32 Beta/API26/AArch64 QEMU。
工具：SDK26.0.0.18/Clang15.0.4、Conan2.29.1、CMake4.1.2、Ninja。
Conan6.0仅为包/依赖元数据，不是OHOS6真机证据。

此前官方 conan-verify：exit=0；最终W3强制重构建：exit=0。统计按最终W3，不累计重复运行。CTest注册JSON与执行XML对应39/39，无失败或跳过。
核心22入口覆盖55个Catch测试用例（961次断言）；自动示例17/17，按上游退出码判定。
另3个上游NOTEST示例照常构建；上游测试源码未改。
全源码69个TEST_CASE；MPI5入口、ONNX4入口及OpenMP宏保护路径不在本配置。

安装包消费者4/4：共轭梯度残差、DB2小波往返、灰度TIFF往返、编译后logger状态。
显式host/build profile反向检查：移走私有cache的lib后因缺sopt库失败，恢复后所有74个文件/链接摘要一致。
许可证与16个原始测试数据文件逐字节核对通过；ELF为AArch64，SONAME保留libsopt.so.5.0。
动态加载器检查exit=0；Conan库及系统运行库的实际路径记录于本地runtime-closure.json，未宣称脱离系统运行库的独立闭包。

v5.0.1标签内SOPT_VERSION=5.0.0原样保留。正式OHOS6、远端CI、发布、合入及积分待平台验证。

最终W3时间：2026-10-04T04:52:13.077668；安装包与运行路径已按该轮精确引用重新核对。
后续将--debug-find固化到公开配方；原始wrapper干净配置通过，编译/链接命令及39个测试注册不变。仅补配置验证，复用上述完整W3结果，未新增测试运行统计或W3标记。
