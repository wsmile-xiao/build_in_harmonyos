# nettle 3.10.2.1 编译进度

**日期**: 2026-04-17
**状态**: ✅ 已完成编译与归档 (built + conan-verified)

## 步骤记录

| 步骤 | 状态 | 备注 |
|------|------|------|
| Step 1 init (init-build) | ✅ | 源码: https://ftp.gnu.org/gnu/nettle/nettle-3.10.2.tar.gz, sha256=fe9ff51c... |
| Step 2 patches | ✅ | 2 个平台补丁: 0001-config.guess (HarmonyOS 三元组), 0002-configure (umask 077→022) |
| Step 3 configure | ✅ | CC=clang, CXX=clang++, --with-include-path/--with-lib-path=gmp, 启用 Public key crypto (hogweed) |
| Step 4 make | ✅ | -j2, 无错误 |
| Step 5 install (DESTDIR staging) | ✅ | /tmp/test-install-nettle-3.10.2, 静态+动态产物齐全 |
| Step 6 safety | ✅ | 签名检查通过 (checksec L4) |
| Step 7 check | ✅ | **上游 make check: All 117 tests passed** (含 cxx/symbols/dlopen) |
| Step 8 staging | ✅ | .staging-verified |
| Step 9 package | ✅ | packaging/nettle-3.10.2-ohos-aarch64.tar.gz + -debug.tar.gz |
| Step 10 deploy | ⏸️ | 待 PR 合入后发布至 ohpcd 制品仓 |
| Step 11 finish | ✅ | build-closed, W3 本地 CI 模拟, W4 知识图谱完整性通过 |

## 发现与知识

- **E007**: GNU config.guess 不含 HarmonyOS 检测分支。`uname -s` 返回 `HarmonyOS`，
  configure 在第一阶段 `cannot guess build type` 即退出。
  方案: 在 nettle/config.guess 中补 `*:HarmonyOS:*:*` case 分支, 映射 aarch64→`aarch64-unknown-linux-ohos`。
  config.sub 已支持 `ohos*`，无需改。
- **hmdfs umask 077 陷阱**: autotools configure/config.status 用 `umask 077 && mktemp -d` 创建
  临时目录，在 hmdfs 上权限不足导致 `Permission denied`。
  方案: 将 configure 与 config.status 中 2×2=4 处 `umask 077` 改为 `umask 022`。
  与 E007 一并作为平台补丁 0001/0002 提交。
- **E001**: HarmonyOS PATH 中无 `cc` 软链接，仅 clang 可用。
  方案: AutotoolsToolchain 显式 `update_configure_args({"CC":"clang","CXX":"clang++"})`。
- **依赖传递路径问题**: nettle 需要 gmp 启用 Public key crypto（否则 libhogweed 不构建）。
  Conan 构建时，仅 `self.requires("gmp/6.3.0")` 不够——nettle 的 autotools configure
  不读 CMakeDeps，需把 gmp 的 include/lib 显式传给 `--with-include-path` / `--with-lib-path`。
- **E005**: 静态库链接到共享库时需 `-fPIC`（autotools 默认不带 -fPIC，由 CFLAGS 传入）。
- **test_package 消费者测试**: 用真实 API 调用验证：SHA256('abc') 断言已知 digest
  0xba7816bf..., AES-128 块加密 (key=00..0f, in=00,11,...ff) 断言已知密文 0x69c4e0d8...。
  失败即非 0 退出。

## 上游测试

- make check: All 117 tests passed (覆盖 AES/DES/ChaCha/SM4/GCM/CCM/SIV,
  SHA1/SHA2/SHA3/MD5, HMAC, PBKDF2, Ed25519/Ed448, ECDSA, GOSTDSA, RSA,
  balloon, cxx, symbols, dlopen 等)。
- test_package (L1): SHA256 + AES-128 消费者断言 PASS。

## 编译对话要点

- 用户决策: gnutls 链缺包时先适配 nettle → gnutls → 再恢复 gnustep-base（不降级 TLS）。
- 每个依赖项独立分支、独立 PR，合入并 Conan 发布后才进入下一个。
- 补丁必须真实、可复现；补丁分类标记为 platform_only。

---

**编译结束**: 2026-08-21 02:20
**最终状态**: built (conan-verified: G0-G4 PASS, finish PASS, W4 知识图谱完整)

### 对话 #1: 用户确认 gnutls 链适配路线

Q: gnutls 依赖缺失，怎么办？
A: 建议两条路：(1) 先适配 nettle→libgcrypt→gnutls 并发布，再恢复 gnustep-base；
   (2) `--disable-tls` 降级（影响 NSStream/NSURL/NSURLHandle）。
用户决策: 走路线 (1)，保持完整功能，先适配 gnutls 链。

### 对话 #2: 拓扑图补全要求

Q: 前面的拓扑图是不是不全？
A: 确认遗漏了 gnustep-base 的系统级第三方依赖层（libffi/libxml2/gnutls/icu 等）
   和 gnutls 依赖链（nettle/libgcrypt/libtasn1/libgpg-error）。补全并给出完整拓扑图。
用户要求: 全部依赖项的依赖项也检测。

### 对话 #3: configure 阶段 E007 + hmdfs umask

Q: nettle configure 报 `cannot guess build type`。
A: 与 gnustep-make 同问题，E007。config.guess 不含 HarmonyOS 分支，补 `*:HarmonyOS:*:*`。
随后 `config.status Permission denied`：umask 077 在 hmdfs 上不可写，改 022。
用户要求: 严格按 SKILL 走补丁流程，不得用 --build/--host 绕过。

### 对话 #4: make check 117 全通过 + Conan G0-G4 通过

Q: 上游 make check 结果？
A: All 117 tests passed（覆盖对称/公钥/哈希/签名/曲线等）。
Q: Conan 配方验证？
A: G0(知识图谱预查询)+G1(完整性)+G2(conan create 干净构建)+G3(系统同名库隔离)+G4 全部 PASS。
   G2 中修了 4 个问题：config.guess 补丁、umask、E001 CC=clang、gmp include/lib 路径传递。
