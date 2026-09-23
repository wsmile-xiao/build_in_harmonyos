# librtmp 2.4_git20190330 适配笔记

> 适配日期: 2026-09-19 · 执行: macOS 协调 + 设备验证(HarmonyOS PC, arm64)

## 1. 版本与来源

- 任务版本 `2.4_git20190330` = rtmpdump git master 快照 `c5f04a58fc2aeea6296ca7c44ee4734c18401aa3`
  (Howard Chu "Reject Content-Length over 2^31", 2019-03-30; RHEL/Rocky 8 的
  `rtmpdump-2.4-15.20190330.gitc5f04a5` 即此快照)。上游 `VERSION=v2.4`。
- 官方仓库 `git.ffmpeg.org/rtmpdump.git` 的 cgit snapshot 端点对非浏览器客户端
  返回 Anubis 反爬 HTML 页(2026-09-19 实测: `curl` 下载得到 7437 字节 HTML,
  而非 tar.gz),无法作为 CI 自动下载源。故 conandata.yml 采用权威镜像
  `mstorsjo/rtmpdump`(Martin Storsjö 维护,提交历史与上游一致,目标 commit
  c5f04a58 由上游作者 Howard Chu 提交)的 GitHub 归档:
  - url: https://github.com/mstorsjo/rtmpdump/archive/c5f04a58fc2aeea6296ca7c44ee4734c18401aa3.tar.gz
  - sha256: e6f1b4f024a7711801b7f2d57728158f5acfc97f3281219cf957ad6c51c1e93a
- 归档内无 librtmp/rtmpdump 同名或历史条目(archives/{l,r} 均无),无 W0b 历史
  notes 可核验;知识图谱 grep "librtmp" 无命中。

## 2. 上游构建系统

- 纯 Makefile(无 configure/autoconf): 根 Makefile 构建工具链程序,`librtmp/Makefile`
  构建 `librtmp.a` 与 `librtmp.so.1`(SO_VERSION=1),对象: rtmp.o log.o amf.o
  hashswf.o parseurl.o。CRYPTO=OPENSSL 默认(`-DUSE_OPENSSL`, `-lssl -lcrypto -lz`)。
- Makefile 显式赋值 `CC=$(CROSS_COMPILE)gcc`、`AR=...`、`SHARED=yes` —— 会覆盖
  环境变量,因此配方以 **make 命令行变量** 传 CC/AR/SHARED;依赖 include/lib 与
  fPIC 通过 Makefile 预留的 `XCFLAGS`/`XLDFLAGS` 追加通道注入(R33: 值全部来自
  Conan conf 与依赖图,不读 shell 环境)。
- 本配方仅打包库(不含 rtmpdump/rtmpgw/rtmpsrv/rtmpsuck 工具),故无需
  commands.json(R38,纯库包必须无)。
- 共享版 soname 为 `librtmp.so.1`(`-Wl,-soname`),OHOS lld 支持;macOS ld 不支持
  该选项,本地演练时共享链接失败属平台差异,非 OHOS 问题。

## 3. 依赖 (W0)

- W0 检查(2026-09-19, 私有 CONAN_HOME, ohpcd remote, ohos-aarch64 profile):
  - `openssl/3.5.6`: available(conan download 成功, recipe revision 748fc4de…)
  - `zlib/1.3.1`: available(recipe revision 2ee7c0ee…)
  - `librtmp/2.4_git20190330`: 远端无占用(version_occupancy=missing),status=pass
- 用途: OpenSSL 用于 RTMPE/RTMPS 握手(DH 密钥交换、RC4、HMAC-SHA256);
  zlib 用于 hashswf.c 的 SWF 解压。

## 4. 平台适配 (补丁)

`patches/0001-openssl-1.1-3.x-compat.patch`(唯一补丁, portability):

1. **HMAC 兼容**: 上游 hashswf.c 与 handshake.h 使用栈上 `HMAC_CTX ctx;` +
   `HMAC_CTX_init/HMAC_CTX_cleanup` —— OpenSSL 1.1.0 起结构体不透明、这两个
   函数已删除,对 openssl/3.5.6 直接编译失败。按
   `OPENSSL_VERSION_NUMBER < 0x10100000L` 分支保留旧 API,新 API 改用
   `HMAC_CTX_new/HMAC_CTX_free`(语义与 Debian/Fedora/Arch 发行版补丁一致)。
2. **DH 访问器**: dh.h 的 OpenSSL 分支直接访问 `dh->p/g/pub_key/priv_key/length`,
   OpenSSL 1.1 起 DH 结构体不透明。改用 `DH_set0_pqg`(DHInit, 含所有权转移与
   失败释放)、`DH_get0_pqg`/`DH_get0_key`(DHGenerateKey/DHGetPublicKey/
   DHComputeSharedSecretKey)、`DH_set_length`(DHInit)。密钥校验循环中不再手工
   清零 pub/priv —— `DH_generate_key` 每次调用内部重新生成。
3. RC4(`RC4_set_key`/`RC4`)、`DH_new/DH_generate_key/DH_compute_key`、
   `SSLv23_method` 等低层 API 在 OpenSSL 3.x 仍导出(仅 deprecated 警告,
   -Wall 无 -Werror),未改动 —— 上游 master 自 2019 年后未再更新,无官方修复可
   backport(已核对 mstorsjo 镜像 master 与 handshake.h 提交历史)。

## 5. 上游测试与消费者测试 (R51)

- **上游测试 N=0**: 无 tests/、无 check/test 目标、无测试框架(清点证据见
  test_package/MANIFEST.yml)。通过率按 0/0 披露。
- **消费者测试**: test_package/test_librtmp.c 实调公开 API,34 处断言
  (RTMP_ParseURL 规范/rtmpe/非法 URL、AMF Int16/24/32/Number/Boolean/String
  编解码回环、RTMP_LogSetLevel/GetLevel 往返、RTMP_Init/Close 生命周期断言),
  无网络依赖。macOS 侧对同一补丁源码先行验证: 34 checks, 0 failures
  (探索性证据,权威验证以设备 W3 为准)。

## 6. 已知警告(非阻塞)

- OpenSSL 3.x 对 RC4/DH 低层 API 的 deprecated 警告(上游代码现状,-Wall 仅警告)。
- bytes.h 对 `__FLOAT_WORD_ORDER` 未定义时的 #warning(字节序假设,与上游一致)。

## 7. 备忘

- 静态库消费者经 cpp_info.requires 继承 openssl/zlib;OHOS socket 系统调用在
  libc,无需额外 system_libs。
- 公开头文件与上游 install_base 一致: amf.h http.h log.h rtmp.h(安装至
  include/librtmp/,消费者 `#include "rtmp.h"`)。
- L5 产物基线重立说明(2026-09-19): ar 归档(.a)内嵌成员时间戳与构建目录路径
  (每轮验证使用随机命名的私有 CONAN_HOME)逐轮变化,同源码重验时 lib/librtmp.a
  字节必变;conan-verify 报告自带指引允许删除 reports/baseline.json 重立基线
  (语义等同首轮)。已按该指引重立,库内容物(对象码)与 W3 通过轮一致,非源码或
  配方变化。
