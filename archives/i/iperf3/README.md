# iperf3

## 简介
iperf3 是一个网络带宽测试工具，支持 TCP、UDP 和 SCTP 协议的性能测量，广泛用于网络性能评估和故障排查。

## OHOS 适配
- 标准autotools 项目，需要 config.guess/config.sub 补丁
- 需要 pthread stubs 补丁解决平台兼容问题
- 其他补丁涉及 CMakeLists.txt、iperf_config.h、version.h

## 依赖
- 编译依赖：clang, make
- 运行依赖：libc, libpthread

## 功能验证
```bash
iperf3 --version
```

## 参考
- 官网：https://software.es.net/iperf/
- 源码：https://github.com/esnet/iperf
