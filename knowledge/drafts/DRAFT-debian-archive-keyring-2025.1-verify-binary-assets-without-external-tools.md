# DRAFT: 数据包里的二进制资产不要靠外部工具校验 —— 自己按格式解析头部，并注意 ASCII armor 的两个坑

> Contributor: username- | Status: DRAFT | Created: 2026-09-19
> 来源: debian-archive-keyring 2025.1 适配（9 份 ASCII-armored OpenPGP 公钥）

## 症状 / 场景

纯数据包常要交付"二进制/编码过的资产"：OpenPGP 公钥（`.asc`）、密钥环、
证书、序列化的 registry 数据……把它们装进包之后，最容易写出的断言是
"文件存在且非空"。但那证明不了资产**没被截断、没被换成占位文本**。

直觉做法是调用 `gpg --list-packets` 之类的外部工具去验，但在 OHOS 与 CI worker
上 `gpg` 并不保证存在（本包的上游 `Makefile` 正是用 `gpg` + `jetring-build`
合成 keyring，所以源包交付里根本没有现成的 keyring 文件）。

## 两个真实的坑

**坑 1：ASCII armor 不是"去掉 `-----` 行就是 base64"。**
armor 体末尾有一行校验和，形如：

```
NlB2T6bKGcYGqL7L
=UUyy
-----END PGP PUBLIC KEY BLOCK-----
```

把这行 `=UUyy` 拼进 base64 会直接报
`binascii.Error: Excess padding not allowed`；若 armor 里带
`Version:` / `Comment:` 这类头，也会一起破坏解码。正确切法：

```python
m = re.search(r"-----BEGIN PGP PUBLIC KEY BLOCK-----\r?\n(.*?)\r?\n"
              r"-----END PGP PUBLIC KEY BLOCK-----", text, re.S)
body = "".join(l.strip() for l in m.group(1).splitlines()
               if l.strip() and ":" not in l and not l.strip().startswith("="))
raw = base64.b64decode(body)
```

**坑 2：OpenPGP 包头的长度字段有四种类型，版本号位置随之变化。**
同样是公钥包，`bookworm-stable` 用 `0x98`（老格式 tag=6 + **1 字节**长度），
`bookworm-automatic` 用 `0x99`（老格式 + **2 字节**长度）。写死 `raw[3]` 或
`raw[4]` 都会误判版本号。按 RFC 4880 解析：

```python
first = raw[0]
if first & 0x40:                      # 新格式头
    tag = first & 0x3F; i = 1; l = raw[i]; i += 1
    if 192 <= l < 224: i += 1
    elif l == 255: i += 4
else:                                 # 老格式头：长度类型在最低两位
    tag = (first >> 2) & 0x0F
    i = 1 + {0: 1, 1: 2, 2: 4}.get(first & 0x03, 0)
version = raw[i]
```

断言 `tag == 6 and version == 4` 就足以证明"这是一份结构完整的 v4 公钥"，
零外部依赖、可在纯 Python 的 test_package 里跑。

## 可复用的模式

对"二进制/编码资产"类数据包：

1. **格式自解析**：自己按格式规范解析头部/魔数（PNG `\x89PNG`、XPM `/* XPM */`、
   CUR `00 00 02 00`、OpenPGP tag+version、BMP `BM`+位图头…），不调用外部工具；
2. **集合与关系断言**：文件名集合精确相等 + 资产两两不同（防复制粘贴错文件）
   + 尺寸分布表；
3. **反向断言**：安装目录里不得出现上游的构建系统与"构建期才生成"的空目录
   （本包 `keyrings/` 在源包里就是空目录，说明它必须由 gpg 生成 —— 我们不生成它，
   所以要显式断言它没被当成内容装进来）。

## 与现有条目的边界

`DRAFT-ieee-data-20260625-conan-copy-star-skips-dotfiles` 讲的是 `copy()` 丢点文件，
属于"打包阶段漏文件"；本条讲的是"**内容阶段的校验强度**"——文件都在，但要用
自解析证明内容完整。两者互补，不重叠。

## 上游测试情况

Debian 原生包，上游 N=0；本包 test_package 16 条断言（含上面两个坑的回归），
本地 `ohc-run.py conan-verify` G0–G4 全绿。
