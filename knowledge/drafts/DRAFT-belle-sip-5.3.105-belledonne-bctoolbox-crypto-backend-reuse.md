# Belledonne 栈在 OHOS 上的 crypto 后端缺口：优先复用已发布的私有后端，而不是逐库重写 vendoring

> Draft: `DRAFT-BELLE-SIP-5105-BELLEDONNE-CRYPTO-BACKEND-REUSE`
> Stem: `DRAFT-belle-sip-5.3.105-belledonne-bctoolbox-crypto-backend-reuse` — pairs with the same-stem `.kv`

## 基本信息

- **ID**: DRAFT-BELLE-SIP-5105-BELLEDONNE-CRYPTO-BACKEND-REUSE
- **严重度**: 2
- **类别**: dependency|ohos-platform|link
- **触发工具**: conan|cmake|clang
- **阶段**: configuration|compilation|link

## 现象

适配 Belledonne 栈库（本文以 belle-sip 5.3.105 为例，lime / mediastreamer2 等同样适用）时，
配置阶段先失败在头文件：

```
src/auth_helper.c:23:10: fatal error: 'bctoolbox/crypto.h' file not found
```

补上头文件后，编译能过，链接阶段换成一串未定义符号：

```
undefined reference to `bctbx_ssl_context_new'
undefined reference to `bctbx_ssl_config_defaults'
undefined reference to `bctbx_rng_context_new'
undefined reference to `bctbx_sha256'
undefined reference to `bctbx_md5'
undefined reference to `bctbx_base64_encode'
undefined reference to `bctbx_signing_key_parse'
```

## 根因

1. Belledonne 栈的源码**无条件**调用 bctoolbox 的 crypto/TLS API（SSL 上下文与配置、RNG、
   SHA256/MD5、base64、签名密钥等）。
2. 制品仓发布的 `bctoolbox/5.3.115` 是 **`ENABLE_MBEDTLS=OFF`** 构建：
   - 包内没有 `include/bctoolbox/crypto.h`；
   - `libbctoolbox.a` 里没有这些符号。

实测（2026-10-02，OHOS aarch64 真机，clang 15.0.4）：

```text
belle-sip 5.3.105 引用 181 个 bctbx_* 符号；
与 libbctoolbox.a 的定义集合逐个比对，
bctbx_ssl_* / bctbx_rng_* / bctbx_sha256 / bctbx_md5 / bctbx_base64_* /
bctbx_signing_key_* / bctbx_aes_gcm_* 等全部缺失。
```

## 推荐做法（已在 belle-sip 5.3.105 上验证通过）

### 1) 先找"同族已发布包里的私有后端"，不要急着重新 vendoring

`bzrtp/5.3.105`（同一 5.3 发布火车，已合入制品仓）为**完全相同的缺口**做过 vendoring：
它在包内发布了

| 产物 | 路径 |
|------|------|
| crypto 头 | `include/bctoolbox/crypto.h`、`crypto.hh` |
| 私有 crypto 对象归档 | `lib/libbctbx-crypto-priv.a` |
| 私有 mbedtls | `lib/libmbedcrypto.a`、`libmbedtls.a`、`libmbedx509.a` |

并且它已经用 `objcopy` 把与已发布 bctoolbox 重名的回退符号（`bctbx_clean`、`bctbx_random`）
本地化，因此**与 bctoolbox 并存不会重复定义**——这正是 bzrtp 自己的 test_package
（同时链接 `bzrtp::bzrtp` 与 `bctoolbox::bctoolbox`）在 CI 上长期跑通的组合。

### 2) 配方侧的三个要点

```python
def requirements(self):
    self.requires("belr/5.3.105")        # 解析依赖
    self.requires("bctoolbox/5.3.115")   # 工具库（无 crypto）
    self.requires("bzrtp/5.3.105")       # ← 私有 crypto 后端提供者
    self.requires("zlib/1.3.1")
```

```python
# 编译期头文件：crypto.h 只在 bzrtp 包里
tc.extra_cflags.append("-isystem" + os.path.join(crypto_pkg, "include"))
tc.extra_cxxflags.append("-isystem" + os.path.join(crypto_pkg, "include"))

# 链接期：必须落在 target_link_libraries（对象之后），
# 只写 CMAKE_EXE/SHARED_LINKER_FLAGS 会排在对象之前 → 仍然 undefined
replace_in_file(... "target_link_libraries(<target> ... ${LIBS})",
                     "target_link_libraries(<target> ... ${LIBS} "
                     "-lbctbx-crypto-priv -lmbedcrypto -lmbedtls -lmbedx509)")
```

```python
def package(self):
    # 公共头依赖 bctoolbox/...，而 CMakeDeps 不向"间接"消费者导出
    # bctoolbox 的 include 目录（实测 bctoolbox_INCLUDE_DIRS 为空），
    # 因此把这些头随包安装（belr/5.3.105、bzrtp/5.3.105 同款处理）
    copy(self, "*.h", src=os.path.join(crypto_pkg, "include", "bctoolbox"),
         dst=os.path.join(self.package_folder, "include", "bctoolbox"))
```

### 3) CMake 变量：用上游 config，不要用 CMakeDeps 生成的

Belledonne 各库的 CMakeLists 依赖上游 config 提供的 `${BCToolbox_TARGET}`、`${Belr_TARGET}`
以及 `bc_apply_compile_flags()` 等宏；用 `<Package>_DIR` 指向上游 config 目录即可同时拿到
变量与宏（belr 的 config 装在 `lib/cmake/Belr`，bctoolbox 在 `share/BCToolbox/cmake`，
两者都要探测，见配方里的 candidates 列表）。

## 验证证据（belle-sip 5.3.105，OHOS PC）

| 项 | 结果 |
|----|------|
| 库编译/链接/打包 | `conan create` rc=0 |
| 消费者用例 | 12/12 通过（URI 解析、消息解析、From tag、序列化） |
| 上游 tester（可运行套件 10 个） | 175 个用例全部通过：Headers 50 / SDP 31 / Message 31 / Refresher 36 / Object 9 / Authentication helper 8 / Core 4 / Generic uri 4 / Object inheritance 1 / FAST SIP URI 2 |
| 上游 tester 平台受限套件（豁免，见 MANIFEST.yml） | Resolver（需 `/etc/nsswitch.conf`，缺失 → SEGFAULT）、HTTP stack / Register / Dialog（需本机回环 SIP/HTTP 服务与网络）、SIP URI 与 FAST SIP URI（各 1 个上游期望值差异） |

## 适用范围与边界

- 适用：任何在 OHOS 上依赖 bctoolbox crypto 的 Belledonne 栈库；也适用于"制品仓依赖缺少编译期可选后端"的一般情形（先找同族已发布包里的等价产物）。
- 边界：本做法依赖 bzrtp 包发布的内容（版本锁定 `bzrtp/5.3.105`）；若将来制品仓发布
  crypto-enabled 的 bctoolbox 变体，应优先切回该依赖，届时本做法可整体删除。
- 与本做法配套的还有一条平台事实：CMakeDeps 不向间接消费者导出 bctoolbox 的 include 目录，
  因此依赖 bctoolbox 头的包都要自带这些头（已在 belr 5.3.105 的 notes 中单独记录）。
