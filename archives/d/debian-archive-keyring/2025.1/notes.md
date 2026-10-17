# debian-archive-keyring 2025.1 适配笔记

## 概述

把 `debian-archive-keyring`（Debian 归档签名公钥）适配为 HarmonyOS PC 的 Conan
纯数据包。它交付的是**验证 Debian 发布文件（Release/InRelease）真实性的 OpenPGP
公钥**，是"离线/自建仓库、签名校验、可信源固定"这类场景的基础数据。

## 上游形态

```
debian-archive-keyring-2025.1/            (Debian 原生包)
├── apt-trusted-asc/                       9 份 ASCII-armored 公钥（本包交付物）
│   └── debian-archive-{bookworm,bullseye,trixie}-{automatic,security-automatic,stable}.asc
├── active-keys/                           jetring 密钥源：9 份 add-* + index（sha256 清单）
├── removed-keys/                          历史（已撤销）密钥源
├── keyrings/                              **空目录** —— 由 Makefile 的 build 目标生成
├── trusted.pgp/                           likewise（per-suite keyring，构建期生成）
├── Makefile                               build 用 jetring-build + gpg 合成 keyring
├── README / README.maintainer
└── debian/                                changelog/control/copyright/install/rules
```

## 安装内容

```
share/keyrings/debian-archive-<suite>-<kind>.asc     9 份公钥（3 套发行版 × 3 种用途）
share/keyrings/active-keys/{index,add-*}             jetring 密钥源与 sha256 清单
share/doc/debian-archive-keyring/{README,README.maintainer}
licenses/copyright
```

## 为什么没有编译，也没有 gpg

上游 `Makefile` 的 `build:` 目标用 `jetring-build` + `gpg` 把 `active-keys/` 与
`removed-keys/` 合成 `keyrings/debian-archive-keyring.pgp` 和 `trusted.pgp/` 下 9 份
per-suite keyring。**这些合成结果在源包里本来就不存在**（`keyrings/` 是空目录），
而 OpenHarmony 上也没有 `gpg`/`jetring`。

关键在于：**真正随源包发布、开箱即用的形态是 `apt-trusted-asc/*.asc`**（Debian 从
2023 年起就改用这种 ASCII-armored trusted key 目录），它已经是可以直接给
`apt` 的 `trusted.gpg.d/` 使用的最终产物。因此本包交付 `.asc` 这一形态，
不执行需要 gpg 的合成步骤 —— 这是有意的技术取舍，不是漏做。

## 上游测试情况

Debian 原生包，没有测试目录、没有测试框架、`debian/rules` 只有 `dh`、也没有
autopkgtest。**上游用例数 N = 0。**

## 新增自检（test_package/test_keyring.py，16 条断言）

关键点是**不依赖 gpg 也能证明"密钥是真的"**：

| 断言组 | 条数 | 内容 |
|--------|------|------|
| 文件集合 | 1 | 9 份 `.asc` 文件名严格等于 `{bookworm,bullseye,trixie} × {automatic,security-automatic,stable}` 的笛卡尔积 |
| armor 解码 | 1 | 9 份都能按 ASCII armor 解码（**必须跳过 armor 头与末尾 `=校验和` 行**，否则 base64 解不出来） |
| OpenPGP 包头 | 3 | 首个 packet 的 tag = 6（public key）、包内版本号 = 4、解码后 ≥ 200 字节 —— 按 RFC 4880 自己解析老/新格式头，不需要 gpg |
| 内容关系 | 3 | 9 份公钥两两不同；每套发行版内部三把互不相同；输出 9 份尺寸分布（bookworm 8700/8709/280、bullseye 8700/8709/2453、trixie 8698/8707/962） |
| jetring 密钥源 | 3 | `active-keys/` 随包发布、含 9 份 `add-*`、`index` 是 9 行 `sha256-<64hex> <name>` 清单 |
| 文档/许可/纯净性 | 5 | `share/doc/debian-archive-keyring` 两份文档；`licenses/copyright` 写明"公钥不受版权保护"；未混入 `Makefile`/`debian/`/`removed-keys/`/`trusted.pgp/`/空的 `keyrings/`；`share/keyrings` 下只有 `.asc` 与 `active-keys/` |

## 两个踩过的点

1. **ASCII armor 不是"去掉 `-----` 行就是 base64"**：armor 体末尾有一行 `=校验和`
   （形如 `=UUyy`），直接拼进去会 base64 报 `Excess padding not allowed`；
   若存在 `Key: value` 形式的 armor 头也要跳过。正确做法是用正则取出
   BEGIN/END 之间的块，再过滤空行、含 `:` 的行、以 `=` 开头的行。
2. **OpenPGP 包头的长度字段要按老/新格式分别解析**：同样是公钥，`bookworm-stable`
   用的是 `0x98`（老格式 + 1 字节长度），`bookworm-automatic` 用的是 `0x99`
   （老格式 + 2 字节长度）。版本号在第 3 或第 2 个字节上取决于长度类型 ——
   写死 `raw[4]` 或 `raw[3]` 都会误判。

## 构建与验证

纯数据包，本机即可跑完整门禁（不需要设备）：

```bash
source /home/silhouette/conanenv/bin/activate
export CONAN_HOME=/home/silhouette/.conan2-ohos
python3 scripts/ohc-run.py conan-verify debian-archive-keyring 2025.1
```

## 来源

- Source URL: `https://mirrors.tuna.tsinghua.edu.cn/debian/pool/main/d/debian-archive-keyring/debian-archive-keyring_2025.1.tar.xz`
  （官方路径 `https://deb.debian.org/debian/pool/main/d/debian-archive-keyring/debian-archive-keyring_2025.1.tar.xz`）
- SHA256: `2d019c3fa19c42da4d37571e473c296286dad0214cb3bd5cafd99f04a8bf5471`
  （与 `debian-archive-keyring_2025.1.dsc` 的 `Checksums-Sha256` 一致）
- License: 公钥不受版权保护；其余部分 GPL（见 `debian/copyright`）

---

**编译结束**: 2026-09-19
**最终状态**: built
