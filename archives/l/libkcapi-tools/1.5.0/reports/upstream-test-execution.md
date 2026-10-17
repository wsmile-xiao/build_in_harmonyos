# libkcapi-tools 1.5.0 — 上游测试套件真机实跑报告（rule4 复审回应）

- 日期：2026-09-26
- 环境：HarmonyOS PC aarch64 真机（HongMeng Kernel 1.12.0，SELinux 域 `u:r:hishell_hap:s0`）
- 源码：上游 v1.5.0 官方 tag tarball（sha256 `f1d8277…aa566ba0`，与 conandata.yml 一致）
- 构建：`--enable-kcapi-test --enable-kcapi-hasher --enable-kcapi-rngapp
  --enable-kcapi-encapp --enable-kcapi-dgstapp --disable-kcapi-speed`
  自举链 aclocal→libtoolize→autoconf→automake 全通，产出上游完整测试程序
  `bin/kcapi` 与全部工具（含发布配方不含的测试二进制）
- 测试驱动：上游 test/ 目录脚本原样执行（未修改任何上游测试文件），
  `KCAPI_TEST_BIN_DIR=<build>/bin`

## 一、实跑结果总表（按上游 `[PASSED]/[FAILED]` 标记逐条计数）

| 脚本 | 实跑标记 | PASS | FAIL | 退出码 | 日志 |
|------|---------|------|------|--------|------|
| test/sh test.sh | 225 | 0 | 225 | 194 | test-run.log |
| test/hasher-test.sh | 182 | 18 | 164 | 164 | hasher-test.sh.log |
| test/kcapi-dgst-test.sh | 384 | 64 | 320 | 64 | kcapi-dgst-test.sh.log |
| test/kcapi-enc-test.sh | 483 | 120 | 363 | 107 | kcapi-enc-test.sh.log |
| test/kcapi-enc-test-large.sh | 1 | 0 | 0 | 0（DEACTIVATED） | kcapi-enc-test-large.sh.log |
| **合计** | **1275** | **202** | **1072** | | |

- 上游 284 个"清点口径"用例（脚本调用点计数，见 test_package/MANIFEST.yml）
  全部被覆盖执行；shell 脚本内部按字节数/密钥长度循环展开，
  故实际标记数（1275）大于清点口径（284）。
- `kcapi-enc-test-large.sh` 被上游自身逻辑停用：
  `libtest.sh` wordsize 检测在本机输出 `[DEACTIVATED: unknown wordsize]`
  （上游 `[: too many arguments` 检测缺陷，与 OHOS 无关）。

## 二、202 个 PASS 的性质（如实声明）

逐条核对 PASS 用例内容，**全部为退化通过**：

- hasher-test.sh 18 例：负路径用例（"Failure on empty checker file"
  等——测试预期工具失败，工具确实失败 → PASS）；
- kcapi-dgst-test.sh 64 例 / kcapi-enc-test.sh 120 例：密码测试与
  openssl 生成明文对照用例中，期望输出文件与实际输出文件**同时为空**
  （cipher 分配失败 → 两侧均为空文件 sha256 `e3b0c442…`）→ 形式 PASS。

**正向密码学功能用例 0 通过**——没有任何一个用例验证了真实的
hash/hmac/skcipher 计算结果。全部正向用例失败于同一处：

```
libkcapi - Error: AF_ALG: bind failed (errno: -13)
```

## 三、根因取证（本机 2026-09-26 复验）

1. `socket(AF_ALG, SOCK_SEQPACKET)` 成功（协议族已注册）；
   `bind(("hash"/"skcipher"/"rng"/"aead", …))` 四类全部 `EACCES (13)`。
2. `/proc/crypto` 不存在（/proc 其余项可读，属针对性隐藏）；
   `socket(AF_NETLINK, SOCK_RAW, NETLINK_CRYPTO)` EPERM
   （2026-09-16 基线鉴别，见 archives/l/libkcapi/1.5.0/notes.md）。
3. SELinux 域 `u:r:hishell_hap:s0`；`param get/set selinux.enforce`
   被拒（errNum 106/114，无特权）；无 su/setenforce。
4. 设备无 /dev/kvm、无 qemu/docker——不存在可提供 AF_ALG 的替代内核环境。
5. 结论：内核 crypto 用户态接口（AF_ALG + NETLINK_CRYPTO）被平台
   SELinux 策略层全面封锁，非本包适配缺陷，环境内无法修复。
   与已合入 base 包 libkcapi 1.5.0（同样 0/225，知识 E6400 同型）结论一致。

## 四、test_package（鸿蒙特有）15 项断言

不依赖 AF_ALG 的用户态契约（版本查询/参数解析/自包含/加载性）
15/15 通过——由 conan create + 本机 CI 验证（见 .ci-result.json）。
