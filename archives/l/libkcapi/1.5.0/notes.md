# libkcapi 1.5.0 适配笔记

## 编译环境
- 构建系统: autotools (tarball 无 configure，需自举)
- 编译日期: 2026-09-16
- 编译器: clang/clang++ (鸿蒙工具链)
- 状态: built

## 编译步骤

```bash
conan create . -pr:h=ohos-aarch64 -pr:b=ohos-aarch64 --build=missing
```

配方要点：
- tool_requires automake/1.18 + libtool/2.5.4（hnp/bin 只有 autoconf 家族，
  无 automake/libtool；同 abiword-plugin-* 先例）
- 直跑自举链 aclocal → libtoolize → autoconf → automake（autoreconf 链在
  OHOS HMDFS 下有 autoconf.m4f 宏冲突先例）
- configure 内 mktemp -d 恒 0700，HMDFS setgid 目录下 config.status 写
  subs1.awk EPERM（DRAFT-6507 cln 同型）：替换为唯一名 + umask 000 mkdir
- --enable-kcapi-test：构建上游主测试程序 bin/kcapi（test/kcapi-main.c）

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | sockaddr_storage 重定义 | OHOS 内核 linux/socket.h 与 musl sys/socket.h 冲突（E091） | 0001 补丁：include 前后 #define/#undef 宏守卫 |
| 2 | bool/true/false 重定义 | OHOS clang 自带 stdbool.h 宏定义与上游手写 enum+_Bool typedef 冲突 | 0002 补丁：改用 #include <stdbool.h> |
| 3 | config.status: could not setup config files machinery | mktemp -d 恒 0700 + HMDFS setgid（DRAFT-6507） | bootstrap 后 patch configure 临时目录创建 |
| 4 | aclocal: not found | hnp/bin 无 automake/libtool | tool_requires automake/1.18 + libtool/2.5.4 |

## 上游测试实跑结果（2026-09-16 本机）

上游测试套件 test/test.sh（225 个用例：hash/hmac/hkdf/skcipher/aead/rng）
已实际执行：

```
$ KCAPI_TEST_BIN_DIR=<build>/bin bash test.sh
exit=194; FAILED=225; PASSED=0
```

- **通过率 0/225（0%）**，全部用例在同一处失败：
  `libkcapi - Error: AF_ALG: bind failed (errno: -13)`
- 根因（平台内核层，非库代码缺陷）：
  1. SELinux（hishell_hap 域）拒绝非特权进程 bind(AF_ALG)（EPERM）；
     hash/skcipher/rng/aead 全类型实测均被拒；
  2. 鉴别试验（2026-09-16）：`socket(AF_ALG)` 本身成功（协议族已注册），
     但 `socket(AF_NETLINK, SOCK_RAW, NETLINK_CRYPTO)` 直接 EPERM，
     `/proc/crypto` 不存在（/proc/net 其余项可读，属针对性隐藏）——
     两条内核 crypto 用户态接口均被 SELinux 策略封锁，确认为策略层
     全面封锁而非内核子系统缺失；设备无 su/setenforce，环境内无法修复
     （知识库草稿 E6400）。
- 属 E237 compile-verify-with-runtime-degradation 同型平台能力缺失；
  无法在环境内修复（需内核/SELinux 策略支持）。

test_package 消费者冒烟测试（不依赖 AF_ALG 的纯用户态 API：
kcapi_versionstring/kcapi_version）1/1 通过（100%）。

## 验证结果

```bash
$ ./test_libkcapi
libkcapi version: libkcapi 1.5.0 (0x00100590)
PASS
```

- conan create（含 test_package）：通过
- 上游测试：0/225（0%，AF_ALG 被内核/SELinux 拒绝，见上）
- test_package 冒烟测试：1/1（100%）

## 依赖

- 无外部 C 库依赖（仅 C 编译器 + autotools）
- 运行时功能依赖内核 AF_ALG（鸿蒙非特权应用不可用，见上）

## 产物

- `lib/libkcapi.a` — 静态库
- `include/kcapi.h` — 公共头文件
- `bin/kcapi` — 上游主测试程序/命令行工具
- `bin/kcapi-hasher` / `kcapi-rng` / `kcapi-enc` / `kcapi-dgst` — 应用工具

---

**编译结束**: 2026-09-16
**最终状态**: built
