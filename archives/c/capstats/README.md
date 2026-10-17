# capstats

capstats 是一个基于 libpcap 收集网络接口流量统计信息的命令行工具。

## 功能

- 按时间间隔输出抓包数量、吞吐率、协议统计和网卡丢包计数。
- 支持 BPF 过滤、snaplen、包大小和 payload 校验。
- 支持将抓到的包写入 pcap 文件，并提供 `--version` 版本查询。

## HarmonyOS PC 适配

- 0.31 使用 CMake 构建，目标平台为 OHOS aarch64。
- 上游的自定义 `FindPCAP.cmake` 不直接消费 Conan 生成的包配置；配方显式传入已发布 `libpcap/1.10.6` 的包目录。
- 该版本没有上游自动化测试或 CTest 注册；配方仍运行 CTest，并由 test_package 真实运行 `capstats --version` 验证产物。

## 依赖

- 构建和运行依赖：`libpcap/1.10.6`。

## 参考资料

- 上游仓库：https://github.com/zeek/capstats
- 版本源码：https://download.zeek.org/capstats-0.31.tar.gz
