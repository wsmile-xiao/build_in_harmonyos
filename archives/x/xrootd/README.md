# XRootD

XRootD（eXtended Root Daemon）是 SLAC/CERN 开发的高性能、容错、可扩展的
数据访问服务框架，是高能物理数据基础设施（WLCG）的核心组件之一。

## 功能概述

- **客户端库 XrdCl**：C++ 客户端 API（文件读写、目录列举、第三方复制、
  zip 支持、重定向/故障切换、TLS 加密）
- **服务器**：xrootd 数据服务器 + cmsd 集群管理器（负载均衡、重定向、
  缓存与代理）
- **协议插件**：HTTP/HTTPS 服务器（含 TPC 三方复制，经 libcurl）
- **安全框架**：unix/gsi/pwd/sss/ztn 认证插件，共享密钥与代理凭证管理
- **POSIX 前端**：libXrdPosix + LD_PRELOAD 拦截层，将 POSIX 调用透明转发
  到 xroot 集群
- **工具集**：xrdcp（复制）、xrdfs（远程 shell）、xrdadler32/xrdcrc32c
  （校验和）、xrdmapc（集群映射）、frm_*（文件回收管理）等 24 个工具

## OHOS 适配（5.8.1）

- OHOS musl 缺失 API 适配：rindex→strrchr、innetgr（上游 musl stub 扩展）、
  getpass（termios 本地实现）、getspnam（CMake 探针）、POSIX AIO（上游同步
  回退路径）、pthread_cancel 系列（SIGUSR2 信号重建 deferred 取消语义）
- FIFO/unix-socket 文件创建被内核禁止：ofsEvents/admin 辅助管理通道优雅
  降级（核心文件服务不受影响，已端到端验证）
- SONAME flag 注入（CMake 无 Platform/HarmonyOS 模块）、readline 路径注入
- 共 114 个补丁，详见 `5.8.1/notes.md` 平台适配点与 `5.8.1/patches/`

## 验证

- 上游 gtest 单元测试 30/30 通过（真机，配方 build() 内 ctest）
- 端到端：xrootd 服务器 + xrdcp 上传/下载（含 10MB 二进制）逐字节校验一致；
  xrdfs ls/stat 正常；进程干净退出
- 详见 `5.8.1/reports/test-report.md`

## 依赖关系

- 构建期（制品仓静态包，静态链入 Xrd*.so）：zlib 1.3.1.1、openssl 3.5.6.1.2、
  libuuid 2.40.4、readline 8.3、ncurses 6.6、libxml2 2.15.3.1、libcurl 8.5.0
- 测试期：gtest 1.17.0.1（上游单元测试）
- 消费者：链接 XrdCl/XrdUtils/XrdServer 等共享库即可，依赖已静态链入

## 未启用组件（对应三方库未发布，上游 if-possible 自动关闭）

Kerberos5、VOMS、Macaroons、SciTokens、XrdEc（isal）、XrdClHttp（Davix）、
Ceph、systemd、FUSE（上游限 Linux|kFreeBSD 且 OHOS 无 /dev/fuse）、
Python 绑定（交叉无目标 Python）

## 参考资料

- 上游: https://github.com/xrootd/xrootd
- 官网: https://xrootd.slac.stanford.edu/
- 文档: https://xrootd.readthedocs.io/
