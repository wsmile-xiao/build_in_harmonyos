# debian-tag2upload-keyring 1.2 验证报告

## 结论

**通过** — 已按仓库 CI 契约脚本 `zsh ci/conan/build_and_test.sh` 全量复现，
`conan create` 含 `test_package` 一次通过，L0/L1 门禁均 pass（1/1，100%）。
`test_package` 含三个独立程序：**上游 autopkgtest 原样执行**（`debian/tests/verify-one`，
1/1 通过）+ 结构验证 46 项断言 + 端到端消费者用例 24 项断言 + 上游驱动器 20 项断言
（合计 90 项断言），后者跑完整信任决策流水线并与独立实现 GnuPG 2.4.5
转录的参考输出逐字节比对，另有 1 组外部真实换钥对照证明
判决非空转（三程序合计 16 组流水线内变异对照：上游驱动器 4 + 结构验证 7 +
端到端 5；外部换钥对照仅在开发机执行，不在 CI 流水线内）。三个程序的每项检查
都由各自内部的计数器在运行时统计并打印 `assertions=N`，上列数字取自实测输出而非
手工推算。最终以 AtomGit 新 SHA 的 `## CI 校验通过` 为准。

上游测试此前记为 0/1 未执行，理由是「缺 `rsop`」与「夹具是 dgit 占位签名」。
本轮复核推翻了后一条并补齐了前一条依赖：上游脚本现逐字节原样执行、指向本包
交付的 keyring 并通过（详见下文「上游 autopkgtest 的真实执行」）。

## 本地验证环境（请注意平台）

| 项 | 值 |
|----|-----|
| 脚本 | 仓库 CI 契约脚本 `ci/conan/build_and_test.sh`（zsh 5.9），原样执行，非模拟 |
| profile | `ci/conan/profiles/ohos-aarch64`（`os=OHOS os.version=6.0 arch=armv8 compiler=clang`） |
| conan | 2.29.1（与 `ci/conan/setup.sh` 记录的 OHOS 基线一致） |
| 宿主 | **WSL2 Ubuntu x86_64**，`HOME=/root`，conan 缓存 `/root/.conan2`，解释器 `/usr/bin/python3` |
| 未覆盖 | **不是 OHOS 真机/worker**。`gpg`/`gpgv`/`rsop` 在 OHOS 工具链内不存在，WSL2 上有 `gpg` 2.2.27，故 `gpg` 只能作为**开发机上的离线独立核对**用于标定 `PINNED_*` 常量与交叉核对 `rsop.py`，**不参与 test_package 运行**；三个测试程序本身是纯 Python，在 worker 上跑同一份代码 |

按仓库 CI 契约脚本原样执行：

```bash
CI_PACKAGES=archives/d/debian-tag2upload-keyring/1.2 \
CI_REPO_ROOT=$PWD zsh ci/conan/build_and_test.sh
```

| 门禁 | 结果 |
|------|------|
| L0 质量门禁（L0j 版本冲突 / L0k commands.json / L0m 目录结构） | `L0_RESULT=pass: all checks passed` |
| L1 测试执行验证（L1a 已执行 / L1b 日志证据 / L1e 破坏性负测） | `L1_RESULT=pass: test_package executed` |
| L2 冒烟测试 | `L2_RESULT=skip: no bin/ dir`（纯数据包无二进制） |
| L4 静态安全扫描 | `L4_RESULT=pass: no patches` |
| L5 基线制品检查 | `L5_RESULT=warn: no artifacts found`（纯数据包无 bin/lib） |
| 汇总 | `Success: 1 / Failed: 0 / Pass rate: 100.0% (1/1)` |

`conan create` 全程通过，`test_package` 在真实 `VirtualRunEnv` 注入的
`OPENPGP_KEYRING_DIR` 下定位制品，三个程序依次执行并通过（上游测试在前，
其 PASS 行见下文「上游 autopkgtest 的真实执行」）：

```
RUN: "/usr/bin/python3" ".../test_package/run_upstream_tests.py" "<workdir>" "<bash>"
TAG2UPLOAD_UPSTREAM_TEST_PASS upstream_test=debian/tests/verify-one ...
RUN: "/usr/bin/python3" ".../test_package/test_verify.py" "/root/.conan2/p/.../p"
TAG2UPLOAD_KEYRING_VALIDATION_PASS packets=7 assertions=46 \
  keyid=606D084E4683C079 fpr=374D8CE4DB96E9CBD4C0972A606D084E4683C079 \
  bits=4096 created=1741882125 \
  uid='Debian tag2upload service (key 1) <debian-tag2upload@lists.debian.org>' \
  certifications=5 self_certs=2 third_party_certifiers=3 \
  keyring_dir=/root/.conan2/p/.../p/share/keyrings

RUN: "/usr/bin/python3" ".../test_package/test_consumer_e2e.py" "/root/.conan2/p/.../p"
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

## 端到端消费者用例的参考输出来源（独立实现）

`test_consumer_e2e.py` 的 `REFERENCE_REPORT` **不是**本程序自输出回填的
golden（那属自证），而是转录自 **GnuPG 2.4.5** 的机器可读输出 —— 一个与本测试
完全独立的 OpenPGP 实现。原始转录如下：

```console
$ gpg --batch --with-colons --show-keys --import-options show-only --import debian-tag2upload.pgp
pub:-:4096:1:606D084E4683C079:1741882125:1801746632::-:::scSC::::::23::0:
fpr:::::::::374D8CE4DB96E9CBD4C0972A606D084E4683C079:
uid:-::::1770210632::1EEED9E0BA3FECE8A6AA4135AD32B8F46C16ABFC::Debian tag2upload service (key 1) <debian-tag2upload@lists.debian.org>::::::::::0:

$ gpg --batch --with-colons --check-sigs 606D084E4683C079
pub:-:4096:1:606D084E4683C079:1741882125:1801746632::-:::scSC::::::23::0:
fpr:::::::::374D8CE4DB96E9CBD4C0972A606D084E4683C079:
uid:-::::1770210632::1EEED9E0BA3FECE8A6AA4135AD32B8F46C16ABFC::Debian tag2upload service (key 1) <debian-tag2upload@lists.debian.org>::::::::::0:
sig:!::1:606D084E4683C079:1741882125::::Debian tag2upload service (key 1) <...>:13x::374D8CE4DB96E9CBD4C0972A606D084E4683C079:::10:
sig:?::1:E3E3392348B50D39:1741946902:::::10x::559AE46C2D6B6D3265E7CBA1E3E3392348B50D39:::10:
sig:?::1:2AE5E34C84B4B055:1741947022:::::10x::D7A387D91018536CB330F7772AE5E34C84B4B055:::10:
sig:?::1:0F56D0553B6D411B:1747388867:::::10x::8DC2487E51ABDD90B5C4753F0F56D0553B6D411B:::10:
sig:!::1:606D084E4683C079:1770210632::::Debian tag2upload service (key 1) <...>:13x::374D8CE4DB96E9CBD4C0972A606D084E4683C079:::10:
```

对照关系：`sig:!` + `13x` 即 2 个自签名（`!` = GnuPG 判定签名有效），
`sig:?` + `10x` 即 3 个第三方颁发者的通用认证，issuer key id 均为对应
issuer fingerprint 的后 8 字节。逐项与本测试报告的
`self-cert` / `third-party` 行一致。

### 外部真实换钥对照

用 `gpg` 现场生成一把真实但不同的密钥（`Decoy key <decoy@example.invalid>`，
rsa2048，fpr `C23F2B5BFECFF77741D63DF6912C6DFD6A64619A`）并导出为 keyring
替换交付物，两个测试程序均如期拒绝：

```
TAG2UPLOAD_CONSUMER_E2E_FAIL: no public key in keyring has key id 606D084E4683C079   # exit=1
TAG2UPLOAD_KEYRING_VALIDATION_FAIL: expected >=3 certification packets, got 2         # exit=1
```

### 确定性

连跑 3 次，报告全文与 `TAG2UPLOAD_CONSUMER_E2E_PASS` 行逐字节一致
（自签名按 `created` 排序、第三方按 key id 升序，均为显式排序）。

### 过程中修正的两处问题

1. **自引入回归**：`self.run()` 的参数曾由引号字符串改为 argv 列表，实测在
   Conan 2.29.1 + `shell=True` 下会被 `str()` 成 `"['/usr/bin/python3', ...]"`，
   导致 `/bin/sh: 1: [/usr/bin/python3,: not found`。已改回显式引号字符串并
   在 `test_package/conanfile.py` 中注释说明该约束。
2. **v4 指纹算法错误（AI 检视 High Priority）**：原实现
   `sha1(body[0:6] + body[-2:])` 只覆盖 8 字节，`body[-2:]` 对 e=65537 恒为
   `0001`，故派生值与 RSA 模数无关，密钥身份断言实为自证。已按 RFC 4880 §12.2
   修正为 `sha1(0x99 + uint16(len(body)) + body)`，并新增「替换 RSA 模数」
   变异对照：仅改模数 2 字节，key id 由 `606D084E4683C079` 变为
   `F6A31137B0955D78` 被拒，而旧算法指纹不变（对换钥无感）。连带纠正了
   「该 keyring 不含自签名」的错误结论——实际含 2 个有效自签名。
3. **断言计数为手工推算、且三个程序粒度不一致（本轮自查发现）**：原先
   `run_upstream_tests.py` 没有任何计数器，其「5 项断言」是把 4 组变异对照
   折叠成 1 项汇总后手工凑出的；而 `test_verify.py` / `test_consumer_e2e.py`
   各自逐组计数。同一条规则下应为 3+1+4=8 而非 5，因此此前的「合计 70 项」
   含有不可复现的手工成分。
   已为上游驱动器补上与另两个程序同构的计数器，并把计数打印进
   `TAG2UPLOAD_UPSTREAM_TEST_PASS` 行；每组变异对照各计 1 项，不再折叠。
   实测 20（上游）+ 46（结构验证）+ 24（端到端）= **90 项**，为真实输出。
4. **文档声明的负向对照有一半并未在流水线内自动执行（本轮自查发现）**：
   `README.md` 声称 `test_verify.py` 有「9 negative controls」且「must all
   fail」，但 `mutations()` 实际只返回 4 组；runenv 契约断裂、缺失 keyring、
   算法号改写、位数改写、创建时间戳改写这 5 项只在此前手工执行过并记在
   本报告的对照表里。
   已把这 5 项补成代码内的自动化对照（`mutations()` 新增 3 组字节变异，
   新增 `runenv_controls()` 覆盖 2 项 runenv 契约），使声明成立而非降级措辞。
   实测 46 项断言、7 组字节变异对照 + 2 项 runenv 对照，流水线内变异对照
   总数由 13 增至 16。

### 直接执行的正例与反向对照

对 Conan 产出的真实制品直接运行两个测试程序，正例通过；反向对照全部按预期
失败，证明断言与判决非空转：

| 组 | 变异 | 结果 |
|----|------|------|
| runenv 契约 | 删除 `OPENPGP_KEYRING_DIR` | 按预期 FAIL（两个程序各自报出契约断裂） |
| runenv 契约 | 变量指向无 keyring 的目录 | 按预期 FAIL |
| runenv 契约（`test_verify.py` 进程内自动化） | 删除 `OPENPGP_KEYRING_DIR` | 按预期 FAIL |
| runenv 契约（`test_verify.py` 进程内自动化） | 变量指向无 keyring 的目录 | 按预期 FAIL |
| 变异对照（`test_verify.py` 进程内自动化） | 截断末包 100 字节 | 按预期 FAIL |
| 变异对照（`test_verify.py` 进程内自动化） | 首包头 bit7 清零 | 按预期 FAIL |
| 变异对照（`test_verify.py` 进程内自动化） | 首包长度夸大 | 按预期 FAIL |
| 变异对照（`test_verify.py` 进程内自动化） | 替换 RSA 模数（仅 2 字节，version/创建时间/算法号/声明位数/指数均不变） | 按预期 FAIL |
| 变异对照（`test_verify.py` 进程内自动化） | 公钥算法 RSA(1) → DSA(17) | 按预期 FAIL：`expected RSA public key (algo 1), got 17` |
| 变异对照（`test_verify.py` 进程内自动化） | 密钥位数 4096 → 2048 | 按预期 FAIL：`expected 4096-bit RSA key, got 2048` |
| 变异对照（`test_verify.py` 进程内自动化） | 创建时间戳改动 | 按预期 FAIL：`expected key creation time 1741882125, got 1741795725` |
| 变异对照（`test_consumer_e2e.py` 进程内） | 替换 RSA 模数 → identity 闸门 | 按预期 REJECT |
| 变异对照（`test_consumer_e2e.py` 进程内） | 删除 2 个自签名 → binding 闸门 | 按预期 REJECT |
| 变异对照（`test_consumer_e2e.py` 进程内） | 第三方颁发者降为 2 个 → roster 闸门 | 按预期 REJECT |
| 变异对照（`test_consumer_e2e.py` 进程内） | 删除全部认证 → binding 闸门 | 按预期 REJECT |
| 变异对照（`test_consumer_e2e.py` 进程内） | 篡改 user id → roster 闸门 | 按预期 REJECT |
| 外部真实换钥 | 换成 `gpg` 现场生成的不同密钥环 | 按预期 REJECT（两个程序均拒） |

## CI 验证

- 整改前历史构建：#43384 通过（https://ohpcd.atomgit.com/ci?id=43384）
- 本地已按同一 CI 契约脚本（`zsh ci/conan/build_and_test.sh`）在
  `ohos-aarch64` profile 上全量复现通过（见上表，1/1）。宿主为 WSL2
  x86_64，**非 OHOS worker**，平台差异见「本地验证环境」一节。
- 本轮提交推送后，仍以 AtomGit 新 SHA 的 `## CI 校验通过` 作为最终依据。

## 上游 autopkgtest 的真实执行

上游 `debian/tests/verify-one` 现由 `test_package/run_upstream_tests.py`
**逐字节原样执行**，并指向本包交付的 keyring。上游脚本以 `$PWD` 为 root 解析
keyring，故驱动器把暂存目录的 cwd 设好，并将**包内**
`share/keyrings/debian-tag2upload.pgp` 复制为该目录下的
`debian-tag2upload.pgp`（经 runenv `OPENPGP_KEYRING_DIR` 定位，变量缺失即 FAIL），
于是上游脚本的 `perl` 拆分与 `rsop verify` 都是对真实制品的真实执行：

```
TAG2UPLOAD_UPSTREAM_TEST_PASS upstream_test=debian/tests/verify-one assertions=20
  script_sha256=a00fda89155ed8657282c799be662fcd2b570b2d84da2e511d05067842bbc3ea
  fixture_sha256=d2e3e4a62cdb8c655b6f6d165245c8fe0b43974b94a5502033d56c905c59c67c
  control_sha256=d91db103fc5edc489dbc556c4314d2e4cae78a9152802ea870c10ae44749e033
  keyring: <package>/share/keyrings/debian-tag2upload.pgp
  rsop: good signature from key 374D8CE4DB96E9CBD4C0972A606D084E4683C079 using sha512
  mutation controls rejected: tag-object-plaintext-tampered,
    signature-mpi-tampered, keyring-rsa-modulus-replaced, keyring-empty
```

脚本与夹具是上游 tarball（sha256 在 `conandata.yml` 锁定）的逐字节副本，副本
sha256 固定在 `test_package/upstream-test.sha256` 并在每次运行时比对，防止
副本漂移后测的不再是上游的东西。

### 唯一替代：`rsop` → `test_package/rsop.py`，且与 GnuPG 逐例核对

`rsop` 确实不在 OHOS 工具链与制品仓（`archives/d/debsig-verify/0.34` 的
`atlocal.in` 依次探测 `sqop/rsop/gosop/pgpainless-cli/sq/gpg` 全部缺失），但这是
可补齐的依赖。`rsop.py` 用纯 Python 实现同一 `rsop verify` 契约：RFC 4880
包流解析、RFC 4880 §5.2.4 v4 签名数据构造、EMSA-PKCS1-v1_5 完整填充校验，
按 hashed issuer-fingerprint 子包（type 33）解析签发者。契约细节：上游脚本里
`rsop verify <plaintext signature.asc keyring` 的 `<plaintext` 是 **shell 输入
重定向**，签名数据走 stdin，操作数只有两个。

该替代经交叉核对，而非假定。把**同一条未修改的上游脚本**分别接到 GnuPG 2.4.5
支撑的 `rsop` 与 `rsop.py` 上跑同一组输入：

| 输入 | GnuPG 支撑的 `rsop` | `rsop.py` |
|------|------------------|-----------|
| 原始夹具 | accept (exit 0) | accept (exit 0) |
| 篡改 tag object 明文 | reject | reject |
| 篡改签名 MPI | reject | reject |
| 替换 keyring RSA 模数 | reject | reject |
| 空 keyring | reject | reject |

其中 4 组变异同时是每次测试运行的断言，因此 PASS 不可能来自「来者不拒」的验签器。

### 推翻「夹具是 dgit 占位签名」

早前记 0/1 的两条理由中，第二条不成立：

1. 签名内记录的 digest 前缀实为 `0x0b9f`（`gpg --list-packets` 报
   `digest algo 10, begin of digest 0b 9f`），不是早前所写的 `0x1621`。
2. **把签名前缀与明文的裸 SHA-512 直接比较，这个论据方式本身就不成立**：
   OpenPGP v4 签名按 RFC 4880 §5.2.4 对
   `data ‖ 0x04 sigtype pk_algo hash_algo ‖ uint16(len(hashed)) ‖ hashed
   ‖ 0x04 0xFF ‖ uint32(6+len(hashed))` 求哈希，不对文件裸摘要求哈希。
   按此构造重算，摘要与签名内记录值逐字节相同（`0b9f864a…c375ff3`）。
3. GnuPG 2.4.5 对同一夹具报 `Good signature from "Debian tag2upload service
   (key 1)"`，exit=0；翻转明文 1 字节 / 截断明文 / 翻转签名 1 字节 / 换别的
   keyring，GnuPG 一律 `BAD signature`。

即该夹具是真实的 tag2upload 签名（RSA-4096、SHA-512、sigtype 0x00、签发者指纹
`374D8CE4…E4683C079`、签发时间 1742481458）。明文里的
`dgit-test-dummy release 1.109 …` 只是上游自测用的**数据内容**，早前把
「内容是 dummy」误推为「签名是占位」。

## 测试用例

| 类型 | 用例数 | 结果 |
|------|--------|------|
| 上游 autopkgtest（`debian/tests/verify-one`） | 1 | **1/1 通过**，逐字节原样执行、指向本包交付的 keyring；`rsop: good signature from key 374D8CE4…E4683C079 using sha512`；4 组变异对照全部被拒 |
| 鸿蒙特有测试 · 消费者结构验证（`test_package/test_verify.py`） | 1 | 1/1 通过，46 项断言 |
| 鸿蒙特有测试 · 完整端到端消费者用例（`test_package/test_consumer_e2e.py`） | 1 | 1/1 通过，24 项断言，判决 `ACCEPT` |
| **合计** | **3** | **上游 1/1 + 适配后 2/2 全部通过（90 项断言）** |
