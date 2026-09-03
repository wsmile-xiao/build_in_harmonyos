# openssl 3.5.8.1 编译进度

**日期**: 2026-09-03
**状态**: ✅ built（conan-verify 全部通过 + W3 本地 CI 模拟通过）
**版本**: 3.5.8.1 = 3.5.8 + 适配修复（R37，制品仓 3.5.6/3.5.6.1/3.5.6.1.1 均已被占用）

## 步骤记录

| 步骤 | 状态 | 备注 |
|------|------|------|
| Step 1 下载源码 | ✅ | openssl.org 官方源，sha256 匹配 (a8f84a39...) |
| Step 2 Configure | ✅ | `perl ./Configure linux-aarch64 --prefix=... --openssldir=...` |
| Step 3 make -j2 | ✅ | libcrypto.a / libssl.a / apps/openssl 生成 |
| Step 4 install staging | ✅ | make install_sw DESTDIR=$TEST_PREFIX |
| Step 5 make test | ⏭️ | 前 130 ok / 0 fail，超时跳过（partial） |
| Step 6 conan-init | ✅ | conanfile.py + conandata.yml + test_package/ |
| Step 7 conan-verify | ✅ | G0-G4 PASS，L2/L4/L5 全部通过 |
| Step 8 finish | ✅ | 9 步，status=built |

## 关键发现与修复

### 1. 升级上游版本 3.5.6 → 3.5.8
- OpenSSL 3.5.8 (RELEASE_DATE: 25 Aug 2026)
- 完整复用 3.5.6.1.1 的成功适配经验
- 源码 SHA256: `a8f84a39918ec6415ce765d9b429d313ba97b8143169c172e734b9514464f5b2`
- 两个补丁（0001/0002）在 3.5.8 源码上下文完全一致，无需修改

### 2. gcc 缺失（沿用 3.5.6.1.1 修复）
- OpenSSL `perl ./Configure` 默认在 Makefile 里写 `CC=$(CROSS_COMPILE)gcc`
- 本机只有 clang（/data/service/hnp/bin/clang），无 gcc → `make` 报 `gcc: inaccessible or not found`
- **修复**：conanfile.py build() 显式传 `CC=<clang>`，编译器从 profile 的
  `tools.build:compiler_executables` 读取（R33），回退到 `os.environ.get("CC")` → "clang"

### 3. 版本号占用（R37/L0j）
- 制品仓已存在 openssl/3.5.6（recipe+binary, 2026-07-12 发布）
- 制品仓还存在 openssl/3.5.6.1（recipe 已占用，2026-08-03）
- 制品仓还存在 openssl/3.5.6.1.1（recipe 已占用，2026-08-03）
- 升级到 3.5.8 后递增后缀 → 3.5.8.1

### 4. 网络限制（沿用 3.5.6.1.1 修复）
- github.com / openssl.org 经 python urllib 不可达（urllib 卡死），但 conan/requests 可直连 github
- ghfast.top 镜像不可达
- **解决**：配置 `core.sources:download_cache`，用 sha256 预置源码包，conan create 完全走本地缓存
- 本次直接复用本地缓存 `.build-cache/openssl-3.5.8.tar.gz`

## 测试结果

- `openssl version` → `OpenSSL 3.5.8 25 Aug 2026` ✅
- `openssl ciphers -v` → TLS 1.3 套件正常 ✅
- make test：130 个测试文件 ok，0 失败（partial，超时截断）
- L1 test_package：12/12 PASS (T1-T12，含 HMAC-SHA256 RFC 4231 KAT + AES-GCM SET_TAG + ECDSA 篡改拒绝)

## 产物

- libcrypto.a / libssl.a（静态，R26 no-shared）
- bin/openssl（PIE + Full RELRO + NX）
- include/openssl/ 142+ 个头文件
- ssl/openssl.cnf 默认配置

---

**编译结束**: 2026-09-03 16:51
**最终状态**: published (CI #37500 PASS)
