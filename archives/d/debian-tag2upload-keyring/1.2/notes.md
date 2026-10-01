# debian-tag2upload-keyring 1.2 适配笔记

## 编译环境
- 构建系统: custom（纯数据，无编译）
- 编译日期: 2026-09-10
- 编译器: 无
- 状态: built

## 编译步骤

纯数据包，无编译。打包时仅复制：

1. `debian-tag2upload.pgp` → `share/keyrings/debian-tag2upload.pgp`（tag2upload 服务 OpenPGP 签名公钥环）
2. `README.md` → `share/doc/debian-tag2upload-keyring/`
3. `debian/copyright` → `licenses/`（GPL-3.0-or-later）

## 遇到的问题与解决方案

| # | 问题 | 根源 | 解决方案 |
|---|------|------|----------|
| 1 | 上游 autopkgtest (verify-one) 曾在 OHOS 判为无法执行 | ① 验签步骤依赖 `rsop`，OHOS 工具链与制品仓均无（`perl` 本身可用，见下方「上游测试实测」）；② 早前还误判夹具 `test-tag-object` 内是 dgit 占位签名 | **已解决**：补齐缺失的 `rsop`（纯 Python 等价实现），上游脚本现原样执行并通过。误判根因见「上游测试实测」 |
| 2 | .pgp 为二进制格式，无法按文本检查 | 上游生成二进制 keyring | 校验首字节 0x99（old-format 公钥包标记）+ 全量包流边界解析 |
| 3 | 旧 test_verify.py 硬编码 `PACKAGE_ROOT/share/keyrings/...`，`package_info()` 注入的 `OPENPGP_KEYRING_DIR` 从未被消费 | 定位路径绕开了配方对外发布的契约 | 改为经 runenv 变量定位制品；变量缺失即 FAIL，契约断裂会立刻暴露 |
| 4 | 旧断言止于「首包 tag=6 + 包数≥3」，keyring 被替换成任意 3 包垃圾流也会 PASS | 断言粒度只覆盖包流结构，未覆盖密钥语义 | 追加密钥身份断言：重算指纹与 key id、算法、位数、创建时间戳、user ID 文本 |
| 5 | 无法证明断言本身能失败（PASS 可能是空转） | 缺少反向对照 | 追加变异对照：截断 / 破坏包头 / 夸大长度 / 替换 RSA 模数四种损坏副本必须全部被拒绝 |
| 6 | 无法说明该 keyring 的认证结构由谁建立 | 需区分自签名与第三方背书 | 逐个解析认证签名的 hashed issuer-fingerprint 子包（type 33），区分 2 个自签名（0x13）与 3 个第三方颁发者的 0x10 认证 |
| 7 | `self.run()` 改用 argv 列表后 `conan create` 失败：`/bin/sh: 1: [/usr/bin/python3,: not found` | Conan 2.29.1 在 `shell=True` 下把 list 参数 `str()` 成 `"['/usr/bin/python3', ...]"` 交给 shell | 改回显式引号包裹的命令字符串，并在 `test_package/conanfile.py` 注释中固化该约束 |
| 8 | **v4 指纹算法写错，密钥身份断言实为自证** | 原实现取 `sha1(body[0:6] + body[-2:])`，只对 8 字节求 SHA-1；`body[0:6]` 是 version+创建时间+算法号，`body[-2:]` 对 e=65537 恒为 `0001`，故结果与 RSA 模数无关 | 按 RFC 4880 §12.2 改为 `sha1(0x99 + uint16(len(body)) + body)`；用 `gpg --check-sigs` 独立核对真实指纹 `374D8CE4…E4683C079` / key id `606D084E4683C079`；并新增「替换 RSA 模数」变异对照证明该断言确实覆盖模数 |
| 9 | 连带错误：曾断言「该 keyring 不含自签名」 | 上一条的错误指纹使 `fingerprint != key_fingerprint` 恒真 | 修正指纹后发现本密钥确有 2 个自签名（sigtype 0x13，gpg 校验为 `!` 有效），改为断言「2 个自签名 + 3 个第三方颁发者」 |

## 源码修改

无（纯数据打包）。

## 依赖版本

无编译依赖。

## 验证结果

按仓库 CI 契约脚本原样执行（非模拟）：

```bash
$ CI_PACKAGES=archives/d/debian-tag2upload-keyring/1.2 \
  CI_REPO_ROOT=$PWD zsh ci/conan/build_and_test.sh
L0_RESULT=pass: all checks passed
L1_RESULT=pass: test_package executed
L2_RESULT=skip: no bin/ dir
L4_RESULT=pass: no patches
L5_RESULT=warn: no artifacts found
Success: 1 / Failed: 0 / Pass rate: 100.0% (1/1)
```

`test_package` 在真实 `VirtualRunEnv` 注入的 `OPENPGP_KEYRING_DIR` 下的输出：

```bash
$ CI_PACKAGES=archives/d/debian-tag2upload-keyring/1.2 \
  CI_REPO_ROOT=$PWD zsh ci/conan/build_and_test.sh
L0_RESULT=pass: all checks passed
L1_RESULT=pass: test_package executed
L2_RESULT=skip: no bin/ dir
L4_RESULT=pass: no patches
L5_RESULT=warn: no artifacts found
Success: 1 / Failed: 0 / Pass rate: 100.0% (1/1)
```

三个程序依次执行（上游测试在前）：

```bash
$ OPENPGP_KEYRING_DIR=<package>/share/keyrings \
  python3 run_upstream_tests.py <workdir> /data/service/hnp/bin/bash
TAG2UPLOAD_UPSTREAM_TEST_PASS upstream_test=debian/tests/verify-one ...   # 见「上游测试实测」

$ OPENPGP_KEYRING_DIR=<package>/share/keyrings \
  python3 test_package/test_verify.py <package>
TAG2UPLOAD_KEYRING_VALIDATION_PASS packets=7 assertions=46 \
  keyid=606D084E4683C079 fpr=374D8CE4DB96E9CBD4C0972A606D084E4683C079 \
  bits=4096 created=1741882125 \
  uid='Debian tag2upload service (key 1) <debian-tag2upload@lists.debian.org>' \
  certifications=5 self_certs=2 third_party_certifiers=3 \
  keyring_dir=<package>/share/keyrings
```

独立核对（`gpg --with-colons --check-sigs 606D084E4683C079`）：

```
pub:-:4096:1:606D084E4683C079:1741882125:1801746632::-:::scSC::::::23::0:
fpr:::::::::374D8CE4DB96E9CBD4C0972A606D084E4683C079:
uid:-:...:Debian tag2upload service (key 1) <debian-tag2upload@lists.debian.org>
sig:!::1:606D084E4683C079:...:13x::374D8CE4...E4683C079:::10:   # 自签名，有效
sig:!::1:606D084E4683C079:...:13x::374D8CE4...E4683C079:::10:   # 自签名，有效
sig:?::1:E3E3392348B50D39:...:10x::559AE46C...4B50D39:::10:   # 第三方
sig:?::1:2AE5E34C84B4B055:...:10x::D7A387D9...4B4B055:::10:   # 第三方
sig:?::1:0F56D0553B6D411B:...:10x::8DC2487E...B6D411B:::10:   # 第三方
```

反向对照（全部按预期 FAIL，证明断言非空转）：

| 变异 | 期望 | 实测报错 |
|------|------|----------|
| 删除 `OPENPGP_KEYRING_DIR` | FAIL | `OPENPGP_KEYRING_DIR is not set: package_info() must inject it ...` |
| 变量指向无 keyring 的目录 | FAIL | `missing keyring: .../debian-tag2upload.pgp` |
| 截断末包 100 字节 | FAIL | `packet 7 (tag=2) claims to end at 3240, past end of stream 3140` |
| 首包头 bit7 清零 | FAIL | `offset 0: 0x19 has bit 7 clear, not an old-format packet header` |
| 首包长度夸大 | FAIL | `packet 1 (tag=6) claims to end at 65538, past end of stream 3240` |
| 公钥算法 RSA(1) → DSA(17) | FAIL | `expected RSA public key (algo 1), got 17` |
| 密钥位数 4096 → 2048 | FAIL | `expected 4096-bit RSA key, got 2048` |
| 创建时间戳改动 | FAIL | `expected key creation time 1741882125, got 1734869005` |
| **替换 RSA 模数**（仅改 2 字节，其余结构不变） | FAIL | `derived fingerprint F936C707…A31137B0955D78 does not match expected 374D8CE4…E4683C079` |

前 4 项在 `test_verify.py` 内以变异对照实现（改字节后再解析同一制品），
后 5 项以外部损坏副本执行，均可复现。

其中「替换 RSA 模数」是针对第 8 条问题的直接反证：仅翻转模数的 2 个字节，
version / 创建时间 / 算法号 / 声明位数 / 指数 MPI 全部不变，实测

- 修正后 RFC 4880 算法：key id 由 `606D084E4683C079` 变为 `F6A31137B0955D78` → 被拒
- 原错误算法：指纹仍为 `DD6DA447…5A40AF8A2E8D902`，**对换钥完全无感**

### 端到端消费者用例（test_consumer_e2e.py）

`test_verify.py` 回答「交付的字节是否是结构完整的 keyring」；
`test_consumer_e2e.py` 回答下游真正要问的问题——**拿到本包安装的 keyring，能否
信任 tag2upload 签名密钥**。它在真实制品上跑完整条流水线并给出判决，而不是罗列断言。

真实制品上的输出（`conan create` 内 `VirtualRunEnv` 注入 runenv 后）：

```bash
$ OPENPGP_KEYRING_DIR=<package>/share/keyrings \
  python3 test_package/test_consumer_e2e.py <package>
TAG2UPLOAD_E2E_MUTATION_REJECTED name=rsa-modulus-substituted \
  reason=no public key in keyring has key id 606D084E4683C079
TAG2UPLOAD_E2E_MUTATION_REJECTED name=self-certifications-removed \
  reason=only 0 self-certification(s); a verifier needs at least 1 to bind the key to its user id
TAG2UPLOAD_E2E_MUTATION_REJECTED name=third-party-reduced-to-two \
  reason=third-party roster (...) does not match the pinned (...)
TAG2UPLOAD_E2E_MUTATION_REJECTED name=all-certifications-removed \
  reason=only 0 self-certification(s); a verifier needs at least 1 to bind the key to its user id
TAG2UPLOAD_E2E_MUTATION_REJECTED name=user-id-tampered \
  reason=user id 'Xebian tag2upload service (key 1) <...>' does not match the pinned uid
TAG2UPLOAD_CONSUMER_E2E_REPORT v1
policy identity=exact-keyid binding=min1-self-cert external=min1-third-party
key keyid=606D084E4683C079 fpr=374D8CE4DB96E9CBD4C0972A606D084E4683C079 algo=1 bits=4096 created=1741882125
uid Debian tag2upload service (key 1) <debian-tag2upload@lists.debian.org>
self-cert keyid=606D084E4683C079 sigtype=0x13 created=1741882125
self-cert keyid=606D084E4683C079 sigtype=0x13 created=1770210632
third-party keyid=0F56D0553B6D411B fpr=8DC2487E51ABDD90B5C4753F0F56D0553B6D411B sigtype=0x10 created=1747388867
third-party keyid=2AE5E34C84B4B055 fpr=D7A387D91018536CB330F7772AE5E34C84B4B055 sigtype=0x10 created=1741947022
third-party keyid=E3E3392348B50D39 fpr=559AE46C2D6B6D3265E7CBA1E3E3392348B50D39 sigtype=0x10 created=1741946902
checks identity=ok binding=ok external=ok roster=ok
verdict ACCEPT
TAG2UPLOAD_CONSUMER_E2E_PASS verdict=ACCEPT assertions=24 self_certs=2 \
  third_party=3 delivery_surface=licenses,share
```

三道闸门各自独立生效，缺一即 REJECT：

| 闸门 | 判据 | 挡住什么 |
|------|------|----------|
| identity | 按 RFC 4880 §12.2 重算的 long key id 必须等于待查 key id | 换成另一把结构合法的 RSA 公钥（派生值随模数变） |
| binding | 至少 1 个自签名（0x13，签发者指纹须等于本密钥指纹） | key↔UID 绑定被抹掉 |
| external | 至少 1 个第三方颁发者的认证 | 只剩自签名的「自证式」信任 |
| roster | 认证名册与固定值逐项相等 | 认证被增删（第三方降为 2 个即被拒） |

**参考输出来自独立实现**，不是本程序自输出回填：报告与 `REFERENCE_REPORT`
逐字节比对，该参考值转录自 GnuPG 2.4.5 的 `gpg --with-colons --check-sigs`
（转录见 `reports/report.md`）。

**另外用一把真实的不同密钥环做了外部对照**：用 `gpg` 现场生成一把
`Decoy key <decoy@example.invalid>`（rsa2048，keyid `912C6DFD6A64619A`）导出为
keyring 替换交付物，端到端流水线如期拒绝：

```bash
$ OPENPGP_KEYRING_DIR=<stage>/share/keyrings python3 test_consumer_e2e.py <stage>
TAG2UPLOAD_CONSUMER_E2E_FAIL: no public key in keyring has key id 606D084E4683C079   # exit=1
$ OPENPGP_KEYRING_DIR=<stage>/share/keyrings python3 test_verify.py <stage>
TAG2UPLOAD_KEYRING_VALIDATION_FAIL: expected >=3 certification packets, got 2        # exit=1
```

**确定性**：连跑 3 次，报告与 PASS 行逐字节一致。

**为何不调 `gpg` 做密码学验签**：`gpg`/`gpgv` 不在 OHOS 工具链与制品仓内
（`archives/l/librnp/0.18.1/conanfile.py:278`：「cli_tests need GnuPG gpg/gpgconf
(not available on OHOS workers)」）。故本用例保持纯 Python，在 worker 与开发机
上跑同一份代码。`gpg` 仅作为**离线独立核对**用于标定 `PINNED_*` 常量，
不参与 test_package 运行。**上游测试所需的密码学验签同样不依赖 `gpg`**：
由 `test_package/rsop.py` 纯 Python 实现，其与 GnuPG 的一致性已按
「上游测试实测」的对照表逐例核对过。


## 上游测试实测

上游源码包（sha256 `28649310f9fdf5d8d691931196ed45237215ef543afe7a1f5683bcd3fd08a9b8`，
与 `conandata.yml` 锁定值一致）内含 1 个 autopkgtest：`debian/tests/verify-one`，
其 `debian/tests/control` 声明 `Depends: @, rsop`。脚本本体：

```bash
perl <"$root"/test-tag-object >plaintext -pe '...遇到 armor 头就切出 signature.asc...'
rsop verify <plaintext signature.asc "$root"/debian-tag2upload.pgp
```

注意 `<plaintext` 是 shell 输入重定向：签名数据从 **stdin** 读，`rsop` 收到的是
`<signature.asc> <keyring>` 两个操作数。

### 该测试现已在 OHOS 原样执行并通过

`test_package/run_upstream_tests.py` 逐字节执行上游脚本（副本 sha256
`a00fda89…42bbc3ea`，取自上述锁定 tarball，固定于
`test_package/upstream-test.sha256`，每次运行都比对），cwd 为暂存目录，其中
`debian-tag2upload.pgp` 是**本包交付的** `share/keyrings/debian-tag2upload.pgp`
（经 runenv `OPENPGP_KEYRING_DIR` 定位），故断言落在真实制品上。上游脚本的
`perl` 拆分与 `rsop verify` 都是真实执行：

```
TAG2UPLOAD_UPSTREAM_TEST_PASS upstream_test=debian/tests/verify-one
  script_sha256=a00fda89155ed8657282c799be662fcd2b570b2d84da2e511d05067842bbc3ea
  fixture_sha256=d2e3e4a62cdb8c655b6f6d165245c8fe0b43974b94a5502033d56c905c59c67c
  keyring: <package>/share/keyrings/debian-tag2upload.pgp
  rsop: good signature from key 374D8CE4DB96E9CBD4C0972A606D084E4683C079 using sha512
  mutation controls rejected: tag-object-plaintext-tampered,
    signature-mpi-tampered, keyring-rsa-modulus-replaced, keyring-empty
```

### 唯一替代：`rsop` → `test_package/rsop.py`

`rsop` 确实不在 OHOS 上，但这是**可补齐的依赖，不是不可逾越的阻塞**：
`archives/d/debsig-verify/0.34` 记录了同一缺口（其 `atlocal.in` 依次探测
`sqop/rsop/gosop/pgpainless-cli/sq/gpg`，真机全部缺失）。`rsop.py` 用纯 Python
实现同一 `rsop verify` 契约：RFC 4880 包流解析、RFC 4880 §5.2.4 v4 签名数据
构造、EMSA-PKCS1-v1_5 完整填充校验，并按 hashed issuer-fingerprint 子包
（type 33）解析签发者。构造与仓库内 `archives/d/debsig-verify/0.34/hmbs_gpg_shim.py`
的 `rsa_verify`/`v4_sig_hash` 一致，无需 root、无需联网、无需 GnuPG。

该替代经过交叉核对而非假定：把**同一条未修改的上游脚本**分别接到 GnuPG 2.4.5
支撑的 `rsop` 与 `rsop.py` 上跑同一组输入，判定逐例一致：

| 输入 | GnuPG 支撑的 rsop | `rsop.py` |
|------|------------------|-----------|
| 原始夹具 | accept (exit 0) | accept (exit 0) |
| 篡改 tag object 明文 | reject | reject |
| 篡改签名 MPI | reject | reject |
| 替换 keyring RSA 模数 | reject | reject |
| 空 keyring | reject | reject |

这 4 组变异同时是每次测试运行的断言，因此 PASS 不可能来自「来者不拒」的验签器。

### 更正：早前「夹具是 dgit 占位签名」的结论是错的

早前版本（notes.md / README.md / MANIFEST.yml）称该夹具内是 dgit 自测占位签名，
理由是「签名内记录的 digest 前缀 `0x1621` 与明文 SHA-512 前缀 `0xe9d1` 不符」。
**该理由不成立**，两处数值也算错了：

1. 签名内记录的 digest 前缀实为 `0x0b9f`（`gpg --list-packets` 亦报
   `digest algo 10, begin of digest 0b 9f`），不是 `0x1621`。
2. 更关键的是，**拿签名前缀去和明文的裸 SHA-512 比，本身就是错的比较**。
   OpenPGP v4 签名不直接对文件求哈希，而是按 RFC 4880 §5.2.4 对
   `data ‖ 0x04 sigtype pk_algo hash_algo ‖ uint16(len(hashed)) ‖ hashed
   ‖ 0x04 0xFF ‖ uint32(6+len(hashed))` 求哈希。按此构造重算，摘要与签名内
   记录值**逐字节相同**（`0b9f864a…c375ff3`）。
3. 独立佐证：GnuPG 2.4.5 对同一夹具报 `Good signature from "Debian tag2upload
   service (key 1)"`，exit=0；翻转明文 1 字节 / 截断明文 / 翻转签名 1 字节 /
   换用别的 keyring，GnuPG 一律报 `BAD signature`。

即该夹具是**真实的 tag2upload 签名**（RSA-4096、SHA-512、sigtype 0x00、
签发者指纹 `374D8CE4…E4683C079`、签发时间 1742481458），明文
`dgit-test-dummy release 1.109 for experimental (rc-buggy) [dgit]` 只是
上游用来做自测的**数据内容**，不代表签名是假的。早前把「内容是 dummy」误推为
「签名是占位」，这是本次整改推翻的根因。

保留的环境事实（仍然成立）：`perl` 在 OHOS 可用（5.42.0 @
`/data/service/hnp/bin/perl`），`bash` 可用（`/data/service/hnp/bin/bash`，
上游脚本需要 `set -o pipefail`，toybox ash 不支持），`rsop` 缺失但已由
`rsop.py` 补齐。

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| share/keyrings/debian-tag2upload.pgp | 3240B | Debian tag2upload 服务签名公钥环 |

## 注意事项

- 消费方若需验签，将 OPENPGP_KEYRING_DIR（runenv 注入）指向
  `share/keyrings` 目录即可。
- 密钥身份：v4 RSA-4096，指纹 `374D8CE4DB96E9CBD4C0972A606D084E4683C079`，
  long key id `606D084E4683C079`，创建时间 1741882125，有效期至 1801746632。
- user ID 有 2 个自签名（sigtype 0x13，`gpg --check-sigs` 校验为有效）以及
  3 个第三方颁发者的通用认证（sigtype 0x10）。**验签方需自行确认是否信任这
  3 个第三方颁发者**；自签名只保证 key↔UID 绑定，不等于该密钥被广泛信任。
- 上游源码包内的 `test-tag-object` 属 dgit 自测夹具，无需随包分发（见
  「上游测试实测」）。

## 审查整改记录 (MR #9293)

> 本节只记录本 MR 的整改动作，不改写任何他人评审意见原文。

### 2026-09-26 15:34 轮（CodexBai，VERDICT=FAIL：rule1 / rule4 / rule8 / rule12）

- **根因**：MR 描述在上一轮重建分支时被压缩，丢失了 PR 模板要求的字段名
  （写成「适配包名 / 上游地址 / 主要交付物」而非「三方库名称 / 上游仓库地址 /
  使用知识库」），且缺少「编译状态」「上游/新增测试用例通过率」与
  「适配后测试用例统计」中的「鸿蒙特有测试」行。评审脚本解析不到即全部判为
  `None` → rule1/rule4 报字段缺失，rule8 误判「适配后 M=0」，rule12 报未声明
  鸿蒙特有测试。**配方与测试代码本身未被判失败**。
- **处置 1（rule1/rule4/rule8/rule12）**：按 `.gitcode/PULL_REQUEST_TEMPLATE.md`
  与仓库既有已通过样本（如 `archives/c/cdargs/1.0.0/PR_BODY.md`）的字段写法
  重写 MR 描述，补齐 5 项基本信息 + 编译状态 + 上下游通过率 + 两个复选框 +
  「适配后测试用例统计」含「鸿蒙特有测试」行。
- **处置 2（rule12「不能是纯断言」）**：不只补描述，补真实覆盖。
  test_verify.py 由 17 → 41 项断言，并新增 runenv 契约消费、密钥身份校验、
  认证结构区分与变异对照（见上表）。
- **处置 3（顺带纠正上游测试口径）**：复核上游 tarball 后确认确有 1 个
  autopkgtest（`debian/tests/verify-one`），MR 描述原声明「上游 N=0」与事实
  不符，已在描述中改为据实声明 N=1 并写明无法执行的具体原因（见
  「上游测试实测」），不再以「上游无测试」为由弱化适配。
- **处置 4（AI 检视 High Priority：v4 指纹算法写错）**：AI 检视指出
  `sha1(body[0:6] + body[-2:])` 只对 8 字节求哈希、与 RSA 模数无关，属
  「名为校验、实为自证」。**该意见完全正确**，已按 RFC 4880 §12.2 修正，
  重新标定真实指纹与 key id（经 `gpg --check-sigs` 独立核对），并新增
  「替换 RSA 模数」变异对照。连带纠正了「不含自签名」的错误结论。

### 2026-09-27 16:22 轮（CodexBai，VERDICT=FAIL：rule1 / rule12）

> 触发：该轮评审同时给出「CI 校验通过 #9293」，说明**配方与构建无问题**，
> 两项 FAIL 均指向 MR 描述与鸿蒙特有测试的实质覆盖。

- **rule1 FAIL（PR 模板格式）** — 评审列出的 6 个子项，经逐条核对，**全部属实**：
  | 子项 | 根因 |
  |------|------|
  | 适配路径必须含「路径 A/B/C」之一 | 描述里写的是 `archives/d/debian-tag2upload-keyring/1.2`，未写「路径 A」 |
  | 上游库测试用例统计表「表格不存在」 | 小节标题写成「上游测试用例统计」，缺「库」字，脚本按模板字段名匹配不到 |
  | 适配后测试用例统计表「表格不存在」 | 描述**整节缺失** |
  | 上游测试用例修改说明复选框解析不到 | 写成了「#### 上游测试用例修改说明」下的两条并列项，非模板要求的单行回答 |
  | 补全测试用例说明复选框解析不到 | 同上 |
  | 新增测试用例通过率字段缺失（None） | 描述里没有该字段 |
  **处置**：按 `.gitcode/PULL_REQUEST_TEMPLATE.md` 逐字段重写 MR 描述
  （`## PR 信息` 五项 + 两张统计表含合计行 + 两个复选框 + 验证结果
  含显式 `编译状态：通过` 与上下游通过率），并把「验证结果」段的字段写成
  脚本可解析的字面量（依据 `knowledge/drafts/E544-draft-8A0B.md`：写成
  「配方就绪」「待 CI 验证」「N/A」会被解析成 `None`，同时触发 rule1+rule4；
  通过率禁千分位逗号）。
- **rule12 FAIL（鸿蒙特有测试）** — 评审判定「适配后统计表缺失，无法脚本化核验」，
  并按规则原文指出**不能只是纯断言**（至少要有一个完整消费者用例）。
  **处置**：不只补描述，补真实覆盖 —— 新增独立可执行
  `test_package/test_consumer_e2e.py`，跑「定位制品 → 选键 → 派生身份 →
  归类认证 → 三闸门判决 → 确定性报告」的完整消费者流程，报告与
  **独立实现 GnuPG 2.4.5** 转录来的参考输出逐字节比对，并含 5 组变异对照与
  OHOS 交付面预检。详见上文「端到端消费者用例」。
- **顺带更正**：`perl` 在 OHOS 并非缺失（`knowledge/operations/environment.md`
  记录 5.42.0 可用，`debsigs` 在真机跑通过 `perl/test.pl`）。上游测试当时的
  阻塞点被记为「`rsop` 不存在 + 夹具签名是 dgit 占位签名」。已在
  notes.md / README.md / `test_package/MANIFEST.yml` 三处统一更正口径 ——
  其中「夹具是占位签名」这一条在下一轮被推翻，见下。

### 2026-09-28 11:10 轮（gcw_RIhAOSxD，VERDICT=FAIL：rule4 / rule6）

| 评审条目 | 评审结论 | 本次处置 | 证据 |
|---|---|---|---|
| **rule4 验证结果：上游测试 0/1** | FAIL：「上游有用例 1 个但一个也没测（0/1）,无论任何理由(平台限制/缺依赖/无环境等)均不通过,请解决后真实执行上游测试用例」 | **真实执行上游 `debian/tests/verify-one`**：新增 `test_package/rsop.py`（`rsop` 的纯 Python 等价实现）、`test_package/run_upstream_tests.py`（原样执行上游脚本，指向本包交付的 keyring）、`test_package/upstream/`（逐字节副本 + sha256 固定） | `TAG2UPLOAD_UPSTREAM_TEST_PASS upstream_test=debian/tests/verify-one …`，4 组变异对照全部被拒；上游通过率 0/1 → **1/1** |
| **rule6 AI 检视未覆盖最新提交** | FAIL：最新提交 2026-09-27T17:37:05 晚于最新 AI 检视 2026-09-26T20:12:20 | 本轮整改产生新提交后触发 AI 检视，使检视时间戳晚于最后一条评审意见 | 见本节提交记录与 CI 时间线 |

#### rule4 根因：上一轮的「占位签名」结论是错的

评审要求「解决后真实执行」，因此先复核了上一轮据以拒绝执行的两条理由：

1. **「`rsop` 缺失」——属实，但属可补齐的依赖。** 补一个纯 Python 的
   `rsop verify` 等价实现即可，不需要 root、不需要联网、不需要 GnuPG。
2. **「夹具是 dgit 占位签名」——不成立。** 该结论的论据是「签名 digest 前缀
   `0x1621` ≠ 明文 SHA-512 前缀 `0xe9d1`」，而
   (a) 实测前缀是 `0x0b9f`，不是 `0x1621`；
   (b) **把签名 digest 前缀与明文的裸 SHA-512 比较，这个比较方式本身就是错的**
   ——OpenPGP v4 签名按 RFC 4880 §5.2.4 对
   `data ‖ sig 前缀 ‖ 0x04 0xFF ‖ uint32(len(前缀))` 求哈希，而非直接对文件求哈希。
   按正确构造重算，摘要与签名内记录值逐字节相同。
   (c) GnuPG 2.4.5 对该夹具报 `Good signature`；4 组变异输入 GnuPG 一律报 BAD。

   即该夹具是真实的 tag2upload 签名；明文里的 `dgit-test-dummy` 只是上游自测
   用的**数据内容**，早前把「内容是 dummy」误推为「签名是占位」。

   修正后还发现：`rsop verify <plaintext signature.asc keyring` 里的
   `<plaintext` 是 **shell 输入重定向**，`rsop` 的签名数据来自 stdin，
   操作数只有 `<signature.asc> <keyring>` 两个。`rsop.py` 按此契约实现。

处置原则遵循评审「缺依赖导致测试没跑的，必须解决依赖再测」：不靠改措辞、
不靠声明「受限 N 计数为 0」，而是把缺失的依赖补上，让上游脚本原样跑通。

#### AI 检视的两条 P2（Medium，不阻塞）已一并修正

`atomgit-bot` 12:47 的检视给出 2 条 Medium。经核对**均属实**，已修：

| 意见 | 核对结论 | 修正 |
|---|---|---|
| `rearmor` 传 label=`"PGP SIGNATURE"`，而模板已含 `PGP ` 前缀，实际 armor 头是 `-----BEGIN PGP PGP SIGNATURE-----`，上游 perl 的 `m{^-----BEGIN PGP SIGNATURE-----$}` 匹配不到 → `signature.asc` 根本不生成，该变异对照是**因文件缺失而失败**，并未真正走到「MPI 被篡改后验签失败」 | 属实 | label 改为 `"SIGNATURE"`；并新增 `assert_rejected_by_verification()`，要求每组对照的输出必须出现 `rsop: verification failed` 且**不得**出现 `No such file or directory`，即「必须被验签器拒绝」而非「因别的原因失败」 |
| `test_consumer_e2e.py` 的 `swap_modulus` 写的是 `body[0] ^= 0x01`，但 `_rebuild_first_packet` 传入的是公钥包**体**，`body[0]` 是 version 字节 → 变异后被 `select_key` 的 `body[0] != 4` 提前丢弃，**从未真正检验身份闸门是否依赖 RSA 模数**；而同批 `test_verify.py` 的 `_substitute_modulus` 用的是 `body[8]` | 属实 | 改为 `body[8] ^= 0x01`（v4 公钥包体布局 `[0]=version, [1:5]=created, [5]=algo, [6:8]=位数, [8:]=n 的 MPI`，偏移 8 才是模数首字节），使该对照真正经由模数变更被身份闸门拒绝 |

第 1 条尤其关键：它使文档里「4 组变异对照证明 PASS 非空转」这句话在此之前**名不副实**。
修正后已复验该断言能区分两种情形（回归验证）：

```
label='PGP SIGNATURE'  → missing file: True    → assert_rejected_by_verification: RAISED
label='SIGNATURE'      → missing file: False   → assert_rejected_by_verification: PASSED
```

### 本轮（2026-09-30 16:02 轮评审后）自查发现并修正的两处「计数不可复现」

16:02 轮评审 13 条规则中 12 条 PASS，唯一 FAIL 是 rule6（AI 检视未覆盖最新
提交）。本轮先独立取证再改代码：不采信任何提交说明，改用 GnuPG 2.4.5 与
锁定 tarball 复核，结论如下。

**先取证（独立于本包代码）**

| 核对项 | 方法 | 结果 |
|---|---|---|
| 夹具内是真实 tag2upload 签名 | `gpgv --keyring <交付的 keyring> signature.asc plaintext` | `Good signature from "Debian tag2upload service (key 1)"`，exit=0 |
| 签名内记录的 digest 前缀 | `gpg --list-packets` | `digest algo 10, begin of digest 0b 9f`（即 `0x0b9f`，非旧文档所写 `0x1621`） |
| v4 指纹 | 独立 `sha1(0x99 ‖ uint16(len) ‖ body)` 一行重算 | `374D8CE4…E4683C079` / key id `606D084E4683C079`，与配方常量一致 |
| 名册 | `gpg --with-colons --check-sigs` | 2 个 `13x` 自签名（`!`）+ 3 个 `10x` 第三方（`?`），与报告一致 |
| 上游副本未被改写 | 下载 `conandata.yml` 锁定的 tarball 逐文件比对 sha256 | tarball sha256 与锁定值一致；`verify-one` / `tests/control` / `test-tag-object` 三个副本与 tarball 内文件**逐字节相同** |
| `rsop` 是否真的缺失 | `command -v rsop` | 本机与 OHOS 侧均无，替代属如实降级 |

结论：上游 1/1、夹具真实、指纹与名册无误，rule4 与 rule12 的原有结论成立。

**修正 1：断言总数含手工推算成分**

- 根因：`run_upstream_tests.py` 没有任何计数器，其「5 项断言」是把 4 组变异
  对照折叠成 1 项汇总后手工凑出的；而 `test_verify.py` / `test_consumer_e2e.py`
  各自逐组计数并打印 `assertions=N`。同一粒度规则下上游驱动器应为
  3+1+4=8 而非 5，故此前「合计 70 项」含不可复现的手工成分。
- 改了什么：给上游驱动器补上与另两个程序同构的 `Counter`，把计数打印进
  `TAG2UPLOAD_UPSTREAM_TEST_PASS` 行；每组变异对照各计 1 项（不再折叠），
  且「必须被验签器拒绝而非因缺文件失败」也计为一项。
- 证据：实测 `assertions=20`；并逐项验证该计数器**能失败** —— 篡改被 pin 的
  上游副本 / 清空 `OPENPGP_KEYRING_DIR` / 变量指向无 keyring 目录 /
  换入 `gpg` 现场生成的**另一把真实密钥**，四种破坏下均 exit=1，恢复后仍 exit=0。

**修正 2：文档声称的负向对照有一半并未在流水线内执行**

- 根因：`README.md` 声称 `test_verify.py` 有「9 negative controls」且「must
  all fail」，但 `mutations()` 实际只返回 4 组；runenv 契约断裂、缺失 keyring、
  算法号改写、位数改写、创建时间戳改写这 5 项**只在此前手工跑过**并记在
  `reports/report.md` 的对照表里，代码中并不存在。文档把手工核对说成了自动化。
- 改了什么：不做措辞降级，而是**补成真实自动化** —— `mutations()` 新增
  算法号改写（DSA）/ 位数改写（2048）/ 创建时间戳平移 3 组字节变异，新增
  `runenv_controls()` 覆盖「变量缺失」与「指向无 keyring 目录」2 项。
- 证据：实测 `assertions=46`（原 41），流水线内变异对照 13 → 16 组。逐组确认
  每条新对照都被**它所针对的那条身份断言**拒绝，而非误撞解析错误：
  `expected RSA public key (algo 1), got 17` /
  `expected 4096-bit RSA key, got 2048` /
  `expected key creation time 1741882125, got 1741795725` /
  `derived fingerprint F936C707… does not match expected 374D8CE4…`。

**计数同步**：实测 20 + 46 + 24 = **90 项断言**、16 组流水线内变异对照。
已同步 `test_package/MANIFEST.yml`（`assertion_count: 90`、
新增 `mutation_control_count: 16`）、两级 `manifest.yaml`、`README.md`、
`reports/report.md`（含 `README.md` 原有「65 assertions across the two
programs」这一处更早的漏改）。

### 前序轮次

- **rule11 评审意见未解决**：diff_comment「test_package 需复核」逐条复核后
  标记 resolved；本轮新增的第 3 条同文案 diff_comment 同样在复核后 resolve。
- **rule6 AI 检视未覆盖最新提交**：每次 push 后触发 `/ai review`。