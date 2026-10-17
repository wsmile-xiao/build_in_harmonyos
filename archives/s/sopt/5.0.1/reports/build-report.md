# SOPT 5.0.1 构建

验证框架main：2446216757be20359617ac140c2e103fac6398f0。
按官方标签URL及SHA256获取源码；Conan/CMake完整构建单进程CPU测试与全部示例，未修改上游源码。
此前完整W3使用7200秒本地临时预算（远端默认3600秒）及CMake4.1.2 --debug-find；查找异常深层原因未确证。
配方现通过标准CMake.configure(cli_args)传入--debug-find；原始wrapper干净配置通过，生成的编译/链接命令及39个测试注册与此前完整W3一致，复用该轮测试结果。
官方profile与框架未改。旧G0的Autotools探测未通过，G2超时，完整finish未通过。
实际运行环境及测试结果见test-report.md；正式OHOS6、远端CI、发布、合入及积分待平台验证。详细日志与续跑证据保留本地。
