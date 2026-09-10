# systemd 261 适配笔记

## 编译环境
- **构建系统**: meson
- **编译日期**: 2026-09-03
- **平台**: arm64-ohos（OpenHarmony PC）
- **状态**: built（Conan 配方验证通过）
- **补丁数量**: 0

## 编译步骤（conan create 全流程）

```bash
conan create archives/s/systemd/261 --build=missing -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
```

### 1. 源码获取（source()）
`get()` 从 conandata 声明的 GitHub gh-proxy tarball 下载（v261 tag）。

### 2. 依赖注入（generate()）
- libcap/2.69、liblzma/5.8.1、libzstd/1.5.7、zlib/1.3.1、libcrypt/4.5.2、
  libucontext/1.5.2——均 ohpcd 已发布
- 复制各依赖包 pkgconfig 目录的 .pc 到 generators_folder 并改写 prefix，
  保证 meson 的 dependency() 可解析
- build() 里把各依赖 pkgconfig 目录注入 os.environ PKG_CONFIG_PATH

### 3. 构建（build()）
- meson configure + build
- 只打 libsystemd 客户端库：关闭 daemon（core/journald/udevd/networkd/logind
  等）与缺依赖组件（libmount/blkid/acl/pcre2/kmod/cryptsetup/audit/gnutls/
  bpf/selinux/apparmor/polkit 全部 -Dxxx=disabled）
- 关闭 man/html/tests（沙箱无 makeinfo）
- 上游测试：meson test 依赖运行中的 systemd 环境（pid1/udev/cgroup），
  OHOS 无——rule 1.2 平台限制声明

### 4. 打包（package()）
- meson install；产物：libsystemd.so（sd-bus/sd-event/sd-daemon 客户端 API）
  + 头文件

## 依赖
- libcap/2.69、liblzma/5.8.1、libzstd/1.5.7、zlib/1.3.1、libcrypt/4.5.2、
  libucontext/1.5.2（均 ohpcd 已发布）

## 上游测试（rule 4 逐类归因）
- systemd 上游 src/test/ 下有 **252 个 test-*.c 纯单元测试**（GitHub Contents API +
  本地 pristine 源码双重核验 = 252，与评审口径一致）；DEFINE_TEST 宏注册，理论
  不依赖运行中的 systemd 守护进程（pid1/udev/cgroup）。
- **编译归因**（tests=true 下实际编译全部 252 个测试目标，2026-09-05 实测）：
  - 可编译 235 个（实际 ninja 生成可执行二进制，含 test-hexdecoct/test-escape/
    test-set/test-hashmap/test-parse-util/test-alloc-util 等核心纯单测）；
  - 编译失败/未注册 17 个（依赖被禁 feature 致 meson 未注册该目标）：
    test-acl-util/test-bpf-token/test-crypto-util/test-curl-util/test-hashmap-plain/
    test-libmount/test-mount-util/test-netlink-manual/test-nss-hosts/test-nss-users/
    test-pkcs7-util/test-pressure/test-qmp-client-qemu/test-sbat/test-seccomp/
    test-socket-bind/test-utmp——均为 acl/bpf/crypto/curl/libmount/nss/pkcs7/
    seccomp/utmp 等 feature 被配方禁用（OHOS 无对应依赖）。
- **运行归因**（累计实测 172 项，含此前完整构建链 + 本次专项纯单测实测）：
  - **运行通过 120 个**（核心纯单测 + 专项纯单测 test-af-list/test-architecture/
    test-parse-argument/test-set/test-hashmap/test-hexdecoct/test-escape 等
    字符串/解析/工具类全部通过）；
  - **跳过 14 个**（exit=77，平台条件不满足，如 test-barrier/bpf-*/btrfs/
    test-boot-timestamps/test-ipcrm）；
  - **失败 38 个**——全部为 OHOS 沙箱平台限制（rule 1.2 如实声明，非跳过）：
    /tmp 只读导致硬编码 mkdtemp 断言失败（test-bootspec/chase/clock/
    conf-files/conf-parser）、EROFS（test-async）、无 bpf/capability
    （test-bpf-devices/test-capability-util）、memfd/install/umask 等沙箱受限。
  - 已实测小计 172 项（占全量 68.3%）；其余 63 项可编译未逐项运行（因 build()
    不跑 meson test 避免触发全量 1281 测试目标构建超时），编译可用性已由编译
    归因验证，运行受沙箱平台限制按 rule 1.2 声明。
- **通过率口径**：按全量 252 填报 = **120/252 ≈ 47.6%**（此前 12.3% 仅 57 项
  实测，已通过专项纯单测实测提升：新增 89 通过，详见 PR 描述）。
- 1281 vs 252：1281 是 meson 注册的全部测试目标（含各组件测试 + check-*/dlopen-*/
  fuzz-* 等），252 是 src/test/ 纯单测文件数——口径不同不矛盾。
- 本地验证：conan create 通过，libsystemd 客户端库与头文件编译链接成功
- 适配后：test_package R34 真实产物校验——libsystemd.so 存在 + ELF
  shared object，1/1 = 100%

## 已知限制
- systemd 是 Linux init 系统，OHOS 不运行其守护进程——daemon 运行类功能按
  平台限制声明；libsystemd 客户端库编译可用
