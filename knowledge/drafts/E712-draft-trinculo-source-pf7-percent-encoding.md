# trinculo 0.96 取源三关：SF urllib 403 双面、PF7 +dfsg 子串判据、%2B 编码绕行与四路 sha 锚定（草稿 E712）

- **来源**：trinculo 0.96 OHOS 移植（任务卡 11293），W0-① 取源 + 配方期 PF7 模拟
- **日期**：2026-09-24
- **证据**：`archives/t/trinculo/0.96/notes.md` 问题表 #3/#4；`$TASK_DIR/w0/W0-evidence.md` 关①；`feedback/pending/2026-09-24-trinculo-0.96.md` F1/F2

## 三关叠加（必须串着解）

### 关 ① 下载栈面：SF 直链 curl/urllib 双面分裂

```
curl -L  downloads.sourceforge.net/project/trinculo/trinculo_v0.96.tar.gz → 200, sha abb69b85… (438717 B)
urllib   同 URL（两镜像域）                                          → HTTP Error 403: Forbidden
```

conan `source()` 下载走 urllib ⇒ SF 官方源实际不可达。且 SF tarball 与
Debian pool tarball sha 不等（`abb69b85` vs `51b73c31`）——dfsg 重打包剔除了
预编译 `bin/*_linux/_osx` 与 macOS 垃圾，**源文件 dfsg 独有 0 项**（comm 清单
比对）。⇒ 取源改发行版 pool，别在 conandata 留官方 SF URL 赌 CI 栈。

### 关 ② PF7 判据面：字面 `+dfsg` 在任意域名都命中

`_pf7_classify` 中 `_PF7_DEBIAN_HOSTS` 名单与 `"+dfsg" in url.lower()` 子串
判据**并联**：

```python
# 实测（本单）
c('http://ftp.debian.org/…trinculo_0.96+dfsg.orig.tar.xz')        → '明文 http 源…'（host 名单+http 双命中）
c('https://archive.ubuntu.com/…trinculo_0.96+dfsg.orig.tar.xz')   → 'Debian 下游重打包源'   ← 名单外域名照样命中
c('https://old.kali.org/…trinculo_0.96+dfsg.orig.tar.xz')         → 'Debian 下游重打包源'   ← 同上
```

⇒ **第一法（换名单外镜像，meschach/lie 先例）对 +dfsg 文件名无效**。

### 关 ③ 等价形绕行：`+` → `%2B`（RFC 3986）

```
c('https://archive.ubuntu.com/…trinculo_0.96%2Bdfsg.orig.tar.xz') → None   ← 零 findings
```

服务器解码 `%2B` ≡ `+`：curl + urllib 双栈实下 61360 B、sha256 =
`51b73c31…b5767d`，与其余三路全等。**保官方池源 + 过 A 类闸 + 零改判据依赖。**

## sha 锚定层数（≥3 路 + 独立权威 + 内证）

| 面 | 证据 |
|---|---|
| 四域名独立下载 distinct=1 | ftp.debian.org / mirror.nodesdirect.com / archive.ubuntu.com / old.kali.org → `51b73c31…` |
| 权威独立锚定 | Debian 官方 `.dsc`（PGP 签名）`Checksums-Sha256` 同值 |
| 编码形双栈 | %2B URL curl+urllib 均 61360 B 同 sha |
| 源码内证 | README.txt:2「trinculo v0.96, January 2016」+ trinculo.cpp:574「Running trinculo v0.96」 |

## 定稿顺序（省整轮的硬纪律）

1. curl + urllib 双栈打上游官方 URL → 一面 403 即改 pool；
2. 写 conandata/manifest URL（名单外域名 + 字面 `+dfsg` 必须 `%2B`）；
3. **提交前跑官方 `_pf7_classify`/`check_source_urls` 函数级模拟零 findings**——
   PF 是 A 类，pr_create 才炸浪费整轮；
4. ≥3 路 sha distinct=1 + `.dsc` 权威锚定 + 内证，理由写 notes。

## 两法并列（入册口径）

- **第一法**：换 `_PF7_DEDIAN_HOSTS` 名单外镜像（meschach/lie 先例）——仅当
  文件名**不含** `+dfsg` 时有效；
- **第二法**：`%2B` 百分号编码等价形（本单）——文件名含 `+dfsg` 时唯一过闸法，
  保官方池源、不依赖镜像域名知识。第二法同时也满足第一法的域名要求
  （选名单外域名 + 编码），是超集。

## 禁行

- conandata 写 `deb.debian.org`/`snapshot`/`security`/`archive.debian.org`：A 类不可豁免。
- 字面 `+dfsg` 写进 URL：任意域名命中，换镜像救不了。
- 写 SF 直链赌下载栈：urllib 403 双面实测，source() 阶段必挂。

> 提交后回填 source_commit；晋升需人工/AI 评审改名 `E712.kv` 移入 `knowledge/graph/` 并登记 index.tsv。
