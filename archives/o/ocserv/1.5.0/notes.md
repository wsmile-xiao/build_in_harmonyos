# ocserv 1.5.0 适配笔记

## 构建信息
- 构建系统：meson（上游 1.3.0 起 autotools → meson 迁移，1.5.0 tarball 只有 meson.build）
- 交叉编译：clang 15.0.4，--target=aarch64-linux-ohos，musl libc
- 上游源：https://gitlab.com/ocserv/ocserv/-/archive/1.5.0/ocserv-1.5.0.tar.gz（sha256 e7e7073f...）
- gitlab.com 直连被 Cloudflare 拦截时 curl -sL 重试可成功（tar.gz 端点可用）

## W0 依赖实测（conan download -r=ohpcd --only-recipe）
- gnutls/3.8.10 EXISTS（传递 nettle/3.10.2.1、libtasn1、libgcrypt、libgpg-error、gmp、libunistring）
- libev/4.33 EXISTS
- readline/8.3 EXISTS（传递 ncursesw）
- protobuf-c：registry 无任何版本（conan list 显示 0 recipes）→ 用上游 bundled protobuf-c 源码（src/protobuf/），meson -Dlocal-protobuf=true
- talloc/llhttp/pcl/ccan/inih：上游源码树自带 bundled，-Dlocal-*=true（上游 CI 同款做法）
- 可选依赖（pam/radius/gssapi/liboath/libnl/maxmind/geoip/lz4/seccomp/systemd/utmp/libwrap/sock-diag/oidc）：全部 -D*=disabled

## 踩坑记录
1. **ev.pc 命名**：conan PkgConfigDeps 生成 `libev.pc`，ocserv 的 `cc.find_library('ev')` 不走 pkg-config；
   必须把 libev 的 include/lib 路径注入 c_args/c_link_args（否则 ev.h 找不到 / -lev 链接失败）
2. **readline 链接**：`cc.find_library('readline', has_headers:['readline/readline.h'])` 需要 include+lib 路径注入；
   且静态 readline 需要 -lncursesw（tputs 符号）
3. **protoc-c 生成**：meson 找不到 protoc 时 fallback 到 `fs.exists('ipc.pb-c.c')` 分支；OHOS 主机用
   protobuf 21.12 + protobuf-c 1.5.2 源码构建主机版 protoc/protoc-gen-c（注意 LD_LIBRARY_PATH 需带
   protobuf 构建目录和 OHOS llvm libc++ 路径），生成 pb-c 后打进 patch
4. **getpass 缺失**：OHOS musl 无 getpass(3)（链接 undefined symbol）→ ocpasswd.c 加 __OHOS__ 兼容实现
5. **tests gnutls 依赖**：上游 tests/meson.build 的 test_base_deps 不含 gnutls_dep（Linux CI 假设系统头文件路径），
   conan prefix 构建下 str.c → main.h → vpn.h → gnutls/gnutls.h 编译失败 → patch 显式加 gnutls_dep
6. **config-inherit /tmp**：测试硬编码 /tmp（OHOS 只读 E002）→ patch 尊重 TMPDIR 环境变量
7. **ELF 签名**：构建出的 ocserv/ocserv-worker/occtl/ocpasswd 需 binary-sign-tool sign -selfSign 1 后才能执行
   （否则 Operation not permitted，HMDFS security.isolate 属性）
8. **meson wrapper**：设备无 meson 可执行文件，pip install meson 后用 python3 -m mesonbuild.mesonmain 或
   自建 wrapper 脚本；conan 配方内采用 vendored meson（astroterm 先例）

## 上游测试
- C 单元测试 16 个：15 PASS + 1 SKIP（kkdcp-parsing 需要 GSSAPI，编译期禁用，exit 77 预期跳过）
- meson test 的 SKIP 全是 wrapper 问题：meson 用 /bin/sh 执行测试二进制，OHOS mksh 无法直接执行 ELF
  （需签名），直接运行测试二进制则通过——测试结论以直接运行为准
- shell 脚本测试：ocpasswd-test PASS、test-fw-normalize-route PASS；其余 ~100 个脚本测试需要
  openconnect 客户端/root/namespace/cwrap 环境，OHOS 无法运行
- 运行验证：ocserv --version = "OpenConnect VPN Server 1.5.0, GnuTLS 3.8.10"

## 产物
- bin/ocserv、bin/ocserv-worker、bin/occtl、bin/ocpasswd、libexec/ocserv-fw、share/doc/ocserv/sample.config
---

**编译结束**: 2026-09-02 03:57
**最终状态**: published

### 上游测试可运行性矩阵（2026-09-02 补充，回应 PR #7645 Septest 审查 rule4）

上游测试全集 ~123 项分类实测（源码 tests/meson.build 解析 + 真机逐项执行）：

**一、可运行且全部通过（18 项）**
- C unit_tests 14 项：str-test / str-test2 / kkdcp-parsing / json-escape / ban-ips / port-parsing / human_addr / valid-hostname / url-escape / html-escape / ipv4-prefix / ipv6-prefix / proxyproto-v1 / proxyproto-v2 —— 真机执行全部 rc=0（含 kkdcp-parsing：直跑通过，先前 conan create 内嵌因 GSSAPI 头缺失判 skip 系误判，实测通过）
- C 条件测试 2 项：config-inherit（TMPDIR 尊重 patch 后通过）、cstp-recv（真机 rc=0 通过）
- always shell 2 项：ocpasswd-test（12 子断言全过）、test-fw-normalize-route

**二、不可运行（~105 项，逐类原因）**
- always shell 4 项（test-owasp-headers/test-http-limits/test-http-smuggling/test-cookie-sid-overflow）：common.sh 第 26-31 行硬性检查 openconnect 二进制（OHOS 无，上游姊妹软件未移植）；另需 libsocket_wrapper.so LD_PRELOAD（cwrap 未移植）
- always shell 1 项（test-replay）：直接调用 openconnect 客户端
- cwrap_scripts 31 项：需 socket_wrapper/uid_wrapper/nss_wrapper/pam_wrapper LD_PRELOAD 全套 cwrap 基础设施（OHOS 均未移植；实测 test-owasp-headers 在无 openconnect 时 common.sh 即 exit 1）
- root_scripts 56 项：需真 root + Linux netns + /dev/net/tun + nftables（OHOS 用户态终端无特权，unshare(CLONE_NEWNET) SIGSYS）
- gssapi 3 项 / radius 7 项 / oidc 2 项 / pam 4 项 + pam-guard-page / gen_oidc_test_data（C）：对应功能编译期 disabled（-Dgssapi=disabled 等，依赖 krb5/radiusclient/oidc/pam 均未鸿蒙化）

**三、结论与解锁路径**
- 按比赛 FAQ #18（"依赖测试框架，未鸿蒙化 → 申请路径 B"）：测试基础设施依赖（openconnect 客户端、cwrap 全家桶）属测试框架未鸿蒙化范畴
- 解锁路径：openconnect 与 socket_wrapper 可作为独立依赖项任务适配（每个 0.5 分），完成后 35 项测试（5 always + 31 cwrap - 1 重复）可运行；root/netns/tun 56 项属 OHOS 特权模型平台边界（路径 B 无法适配范畴）
