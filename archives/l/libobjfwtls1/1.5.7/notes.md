# libobjfwtls1 1.5.7 适配笔记

## 编译环境
- 构建系统: autotools
- 适配日期: 2026-09-19
- 编译器: clang 15 (Objective-C) / clang++
- 目标平台: OpenHarmony / HarmonyOS PC (aarch64), OS=OHOS
- 状态: 首轮工作树（待真机预检验证后回填实测数据）

## 背景
- 上游: ObjFW (https://objfw.nil.im/) 整体源码树，Autotools 构建。
  一次构建产出 libobjfw、libobjfwrt、libobjfwtls 等库。
- 本包名 libobjfwtls1，聚焦 TLS 库 libobjfwtls（OpenSSL 后端）。
- 与已合入的姐妹包 libobjfwhid1/1.5.7 同源同树（同一 objfw-1.5.7.tar.gz，
  同一 sha256），复用其验证过的 3 个补丁与构建惯例；唯一本质差异是
  TLS 开关：姐妹包 `--without-tls`，本包 `--with-tls=openssl`。
- 上游源码已独立下载验证：大小 1034864 字节，与官方目录一致，
  sha256 e637c32731dc07396b812c4019f34d1417a3f7aa39d450b7f27c9bcdc23b3e12。

## 上游测试审计（R51 第一步：清点）
- 上游测试框架：ObjFW 自研 OFTests 框架，tests/ 目录 88 个 `*Tests.m`
  用例文件编译进单一 `tests` 二进制，顶层 `make check` 驱动
  （tests/run 目标，先建版本软链接再执行）。
- 88 个用例文件无一引用 TLS/X509：TLS 开关不改变上游用例集合。
- 离线安全：OFHTTPClientTests 只打本地 127.0.0.1 回环服务器
  （源码中唯一的 https 外链是文件头 License 注释里的 gnu.org 地址文本，
  非测试目标），无在线数据集依赖。
- 同树姐妹包（--without-tls）在真机实测 1238 通过 / 0 失败 / 4 跳过
  （4 跳过均为平台能力缺失：UNIX stream/datagram/sequenced socket 与硬链接）。
  本包启用 TLS 后的实测数以真机预检为准，不照抄。

## 编译步骤

```bash
# 1. 平台识别打补丁（config.guess/config.sub，E007 规程；与姐妹包相同）
#    - config.guess: __OHOS__ LIBC 检测 + HarmonyOS 系统识别 → aarch64-unknown-linux-ohos
#    - config.sub: ohos-linux triplet + ohos* OS 列表 + kernel-OS 校验表追加 linux-ohos*-
# 2. configure（显式 OpenSSL 后端；OpenSSL 由 conan openssl/3.5.8.1 提供）
./configure --prefix=$PREFIX --with-tls=openssl --enable-static --disable-shared
# 3. make（-j1：HMDFS 上 make -jN 的 jobserver mkfifo 报 Operation not permitted）
make -j1
# 4. make check（上游测试，见「验证结果」）
make check -j1
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | config.guess 不识别 HarmonyOS | GNU config.guess 无 __OHOS__/HarmonyOS 分支 (E007) | 复用姐妹包 0001 补丁 |
| 2 | config.sub 报 Kernel 'linux' not known to work with OS 'ohos' | 新版 config.sub kernel-OS 校验表未含 linux-ohos (E122/E268) | 复用姐妹包 0002 补丁 |
| 3 | configure 临时目录不可写（umask 077） | HMDFS UID 映射 + umask 077 (E011) | 复用姐妹包 0003 补丁 |
| 4 | TLS 后端选择 | OHOS 上 GnuTLS/mbedTLS 不可用；openssl/3.5.8.1 已发布 | `--with-tls=openssl` + `requires openssl/3.5.8.1` + AutotoolsDeps 注入 -I/-L（configure 只用裸 -lssl/-lcrypto 探测，无 pkg-config） |

## 源码修改

- build-aux/config.guess：__OHOS__ LIBC 检测 + HarmonyOS 系统识别（与姐妹包相同内容）
- build-aux/config.sub：ohos-linux triplet + ohos* OS 列表 + kernel-OS 校验表追加 linux-ohos*-（与姐妹包相同内容）
- configure：umask 077→022（与姐妹包相同内容）
- 本包无新增源码补丁；patches/ 3 个文件与姐妹包逐字节一致。

## 依赖版本

- openssl/3.5.8.1（已发布，conan requires；提供 libssl/libcrypto 静态库）
- 无其他外部依赖。

## 验证结果（待真机预检回填）

### 上游测试（make check）
- 命令已接入 conanfile.py build()（`make check -j1`），真机 conan create 时真实执行。
- 通过数/跳过数以真机预检日志为准。

### 消费者测试（test_package）
- conan create 自动编译 test_package：
  - test_tls.m（Objective-C）：真实调用 `+[OFX509Certificate supportsPEMFiles]`
    （OpenSSL 后端编入时为 true）并用非法 PEM 文件验证真实 X.509 解析器
    抛异常；纯离线。
  - test_runtime.c（C）：验证 libobjfwrt 运行时链接与类注册。
- 通过数以真机预检日志为准。

## 产物说明

conan create 产出（package 目录，剔除 bin/sbin 使包保持纯库类型，R38）：
- include/ObjFWTLS/ 与 include/ObjFW/ 等头文件
- lib/libobjfwtls.{a,so} / lib/libobjfw.{a,so} / lib/libobjfwrt.{a,so}
- 配方 cpp_info.libs = ["objfwtls", "objfw", "objfwrt"]，
  cpp_info.requires = ["openssl::openssl"]（静态消费方自动带上 -lssl -lcrypto，
  与包内 lib/objfw-config/ObjFWTLS.oc 记录的链接一致）

## 注意事项

- ObjFW 是 Objective-C 库，需要 clang 的 ObjC 支持。
- 消费者编译需 ObjFW 运行时 flags（`-fconstant-string-class=OFConstantString`、
  `-Xclang -fobjc-runtime=objfw-1.5`），见 test_package/CMakeLists.txt。
- **in-source 构建**：ObjFW 的 Makefile 为 tarball 静态文件（非 automake 生成），
  conan 配方必须 `folders.build = "."`（in-source），否则 out-of-tree 无 Makefile。
- 静态默认（shared=False）：与姐妹包一致；openssl 依赖本身也是静态（R26）。
- HMBS_TEST_PACKAGE_RESULT / HMBS_UPSTREAM_TEST_RESULT 两行 JSON 标记由真机
  实际测试命令产生，本轮不手写。
