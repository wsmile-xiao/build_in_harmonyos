# tcpflow

[tcpflow](https://github.com/simsong/tcpflow) 是 TCP/IP 报文流重组工具（网络取证），
按 TCP 连接（流）抓取并存储网络数据，支持实时抓包与离线 pcap 解析（`-r`）。
C++ 实现，autotools 构建，GPL-3.0。

## 功能

- `tcpflow -r file.pcap -o outdir`：离线解析 pcap，按流输出文件（每流两个方向各一个文件）
- 实时抓包：`tcpflow -i iface`（需 CAP_NET_RAW / root，CI 环境不可用）
- `-S name=value` 运行时配置（如 `-S enable_report=false` 关闭 DFXML 报告）
- 流文件命名：`ip.port-ip.port`（源-目的），HTTP 体按需拆分 `-HTTPBODY-NNN`

## OpenHarmony 适配要点

| 主题 | 说明 |
|------|------|
| submodule 缺源 | 官方 release tarball 不含 `src/http-parser` submodule 内容，conandata.yml `sources.submodules` 段声明固定 commit 源码并在 source() 合并 |
| autoreconf 自举 | GitHub archive tarball 无 configure，build() 中 `autotools.autoreconf()`（tool_requires automake/1.18 + libtool/2.5.4） |
| 依赖 | zlib/1.3.1、openssl/3.5.6、libpcap/1.10.6、boost/1.84.0（configure.ac 强制检查） |
| DFXML 报告 | 默认 report.xml 生成在 OHOS aarch64/musl 上 SIGSEGV（Signal 11），测试驱动用上游合法配置 `-S enable_report=false` 规避；生产语义不变 |
| 安全边界 | 测试仅用离线 pcap 夹具（test1.pcap），无实时抓包、无 root、无端口绑定、无网络配置修改 |

## 版本

| 版本 | 状态 | 构建系统 | 日期 |
|------|------|----------|------|
| 1.6.1 | built | autotools | 2026-08-14 |

## 测试

- 上游 `make check`：5 个 SH_TESTS，审计后分类 **total=5, passed=1, failed=1,
  skipped=3, errors=0, timeout=0**：
  - test1.sh = 真实 passed（默认 report 离线 pcap 工作流，4 流文件
    md5/size/mtime(2008) 断言实际执行并通过）；
  - test-pdfs.sh = failed（依赖 optional netviz/cairo，configure.ac
    `--enable-cairo=false` 已关闭，属 optional-feature not applicable）；
  - test-multifile.sh / test-iptree.sh / test-chroot.sh = skipped（缺外部
    nitroba.pcap / 2013-httpxfer 大 pcap / root，脚本自身 exit 0，不得视为
    真实 passed；Automake 原始汇总会记为 PASS）。
- 消费者测试（test_package，独立统计）：case_count=4, assertion_count=20,
  passed=20, failed=0（--version/-h 入口 + 默认 report 离线 pcap 工作流，4 流文件
  md5/size/mtime 与上游 tests/test1.sh t=1 分支断言逐字节一致）
- 修复：`patches/0001-src-be13_api-dfxml-src-dfxml_writer.cpp.patch`
  （getpwuid() NULL 保护，消除默认 report.xml SIGSEGV，上游 main 未修复）
