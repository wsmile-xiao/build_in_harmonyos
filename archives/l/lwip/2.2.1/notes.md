# lwip 2.2.1 适配笔记

## 编译环境
- 构建系统: custom（lwIP 官方无 configure/make 库目标，src/Filelists.cmake 组装模式，配方直接编译 src 源文件）
- 编译日期: 2026-09-16
- 编译器: clang/clang++ (15.0.4, aarch64-linux-ohos)
- 状态: published

## 编译步骤

1. 官方源码: https://download.savannah.nongnu.org/releases/lwip/lwip-2.2.1.zip
   SHA-256: 7b622662dba2383d71f874f2e494b54ae948531559c17acbe75797966d646878
   （Savannah 官方 release 区 2025-02-06 发布；官方 git tag STABLE-2_2_1_RELEASE 交叉核验一致）
2. lang-preflight: 工具误判 mixed（官方 zip 自带 doc/doxygen/html/*.js 620 个计入 nodejs 主体），
   按 R47 排除文档目录后主体为纯 C（201 .c + 274 .h），与任务默认 cpp 属兼容族 → lang_checked 通过
3. conanfile.py: 直接编译 src/core + src/netif（NO_SYS=1 模式，无 RTOS 依赖），排除 src/api（netconn/socket 需要 OS）、
   makefsdata（独立 host 工具自带 main）；生成默认 lwipopts.h（NO_SYS/LWIP_NETCONN=0/LWIP_SOCKET=0/LWIP_NETIF_API=0）；
   port_shim.c 提供 lwip_port_rand/sys_now/sys_arch_protect 等 NO_SYS 模式必需符号；安装 unix port arch/cc.h
4. conan create + test_package: 通过（test.c 调用 lwip_init + tcp_new 真实 API；ctest 1/1 passed）

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | lang-preflight 判定 mixed → env_unsupported | lang_detect 统计未排除 doc/doxygen 目录，官方 zip 自带 620 个文档 .js 被当 nodejs 主体 | 按 R47 边界规则复核主体（C），覆盖终态为 lang_checked |
| 2 | lwipopts.h 缺失 | opt.h 无条件 include lwipopts.h，官方 zip 顶层无此文件 | 配方 build() 生成默认 lwipopts.h（NO_SYS 模式）并安装到 include/ |
| 3 | arch/cc.h 缺失（consumer 编译失败） | package() 未安装 unix port arch 头 | package() 补装 contrib/ports/unix/port/include |
| 4 | src/api 编译失败（tcpip_callback_fn 未定义） | NO_SYS=1 时 netconn/socket（src/api）需要 OS 线程 | 配方排除 src/api 目录，仅编译 core+netif（raw API 语义） |
| 5 | 上游测试 test_ip6_reass 断言 abort | test/unit/lwipopts.h 的 PTR64 判定不识别 __aarch64__，IPV6_FRAG_COPYHEADER 未启用 | 最小补丁追加 `|| defined(__aarch64__)`；137/137 通过 |
| 6 | /tmp 只读导致 check 库无法创建临时文件 | /tmp 为只读文件系统（erofs） | 专用临时目录 chmod 700 + TMPDIR/TMP/TEMP 后重跑成功 |
| 7 | sys_arch_protect/sys_now 未定义（NO_SYS 链接） | NO_SYS 模式仍需 port 提供保护与时钟符号 | port_shim.c 提供（rand 用 libc rand，时钟用 clock_gettime） |

## 源码修改

无正式配方补丁（patches/ 为空）；仅上游测试最小验证补丁记录于知识草稿：
- test/unit/lwipopts.h PTR64 判定追加 __aarch64__（见 DRAFT-lwip-2.2.1-ptr64-aarch64-lwipopts）

## 依赖版本

- check/0.15.2（上游测试框架，ohpcd 制品仓）
- 运行时: 无第三方依赖（lwIP 自包含）

## 验证结果

- conan create + test_package: PASS（1/1 ctest）
- 上游单元测试: 137/137 (100%)，0 失败 0 错误（源码声明 138，1 个 #else 互斥分支未实例化）
- 鸿蒙专项测试（tests/ohos_platform_test.c）: ALL PASSED
- 消费者验证（tests/consumer_test.c，仅用包安装产物）: PASSED
- W3 本地 CI: PASS；W2 PR 原子性: PASS；基线隔离审计: PASS（E219/E253/E305 为既有基线噪声）

## 知识沉淀

- DRAFT-lwip-2.2.1-lang-preflight-doxygen-js-misdetect（lang-preflight 对官方包自带 doxygen 文档 .js 的误判）
- DRAFT-lwip-2.2.1-ptr64-aarch64-lwipopts（上游测试 PTR64 判定不识别 __aarch64__）
- 路径决定: path B（知识库扩展）
---

**编译结束**: 2026-09-16 10:53
**最终状态**: published
