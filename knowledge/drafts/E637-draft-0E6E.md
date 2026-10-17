# E637 — dfsg 后缀版本的源取法：上游官网死链时用 Debian/Ubuntu pool 的 .orig.tar.xz

## 错误特征

适配 Debian 衍生版本（版本串带 `dfsg`/`+dfsg.N`）时，conandata.yml 里的上游
官网地址已不可用：

```text
# 官网路径 302 重定向到门户页，跟着走拿到的是 HTML 而不是 tarball
$ curl -sIL http://www.davidhbailey.com/dbpapers/qd-2.3.23.tar.gz
https://www.davidhbailey.com/dhbpapers/qd-2.3.23.tar.gz → 404
$ curl -sL https://crd-legacy.lbl.gov/~dhbailey/mpdist/qd-2.3.23.tar.gz | file -
/dev/stdin: ASCII text          # 实际是 cs.lbl.gov 的 SEO 门户页
```

放进 conandata.yml 的表现是 conan 侧 `ERROR: Error downloading file`、
`The requested URL returned error: 404`，或下载到门户页后
`sha256 signature failed for file`（HTML 的哈希当然对不上）。

## 触发条件

- 任务版本串含 Debian 重打包标记（`2.3.23-dfsg.1`、`1.2.3+dfsg` 等）
- 上游是小众学术/政府站点（LBNL、NERSC 等），多年后改版或下线历史归档
- 构建系统: 任意（本条只关心源获取）；阶段: source()/下载

## 根因分析

Debian 对上游源码做 DFSG 重打包（剥离不可再分发的文档、字体等）后，正式
版本串变成 `<上游版本>+dfsg.N`，重打包产物以
`<包名>_<上游版本>+dfsg.N.orig.tar.*` 存放在发行版源码 pool 里。多年后上游
站点改版（qd 的两个历史地址 `crd-legacy.lbl.gov/~dhbailey/mpdist` 与
`davidhbailey.com/dhbpapers` 都已失效），这份重打包 tarball 往往就是全网
唯一还讲得清出处的副本。

## 解决方案

### 推荐方案

1. 在 pool 里定位文件（`<首字母>/<包名>/` 两级目录）：

```bash
curl -s "https://deb.debian.org/debian/pool/main/q/qd/" | grep -o 'href="qd[^"]*"'
```

2. **实际下载并计算 sha256**（写进 conandata.yml 的值必须来自本机对
   deb.debian.org 这份文件自己的实测，不同镜像字节应一致但要以本机实测为准）：

```bash
curl -sL -o src.tar.xz "https://deb.debian.org/debian/pool/main/q/qd/qd_2.3.23+dfsg.1.orig.tar.xz"
sha256sum src.tar.xz
# 973a6b5cfdb629d6815daedc5087779a33e53af3c347fcd3b3d225759e285c06
```

3. 包版本串保持任务分支门禁同形（本任务为 `2.3.23-dfsg.1`，连字符形），**不要**
   改写成 Debian 的 `+dfsg.1` 加号形——CI 分支名门禁按
   「分支名去前缀 == 包目录名-版本」精确匹配。tarball 顶层目录
   （`qd-2.3.23+dfsg.1`）与包版本串不一致没有影响：配方的
   `get(self, **self.conan_data["sources"], strip_root=True)` 会剥掉唯一顶层目录。

deb.debian.org 不可达时用 `ports.ubuntu.com/pool/universe/<首字母>/<包名>/`
（universe 段的包），同一重打包文件。

### 禁止做法

- ❌ 把 `<包名>_<版本>.debian.tar.xz`（发行版维护差分）当成上游源——那是
  Debian 打包补丁，不是源码本体
- ❌ 用镜像代理域名（ghfast.top / gh-proxy.com 等，PF7 红线）绕下载
- ❌ 拿别的镜像算的 sha256 不经本机实测直接抄——CI 与审方都会复算

## 验证

```bash
# 同一文件从两个权威 pool 各下一次，哈希一致才写入 conandata.yml
curl -sL -o a.tar.xz "https://deb.debian.org/debian/pool/main/q/qd/qd_2.3.23+dfsg.1.orig.tar.xz"
curl -sL -o b.tar.xz "http://ports.ubuntu.com/pool/universe/q/qd/qd_2.3.23+dfsg.1.orig.tar.xz"
sha256sum a.tar.xz b.tar.xz   # 两行相同
```

## 关联条目

- E425（Debian orig tarball 保留空 submodule 目录的范围裁剪）——同是
  "Debian 重打包源" 家族的另一面
- E007 / E072 / E122（config.guess/config.sub 三元识别）——本类源码包里
  2021 年前的 config.sub 需要单独核对；2021-01 之后的版本已支持 aarch64，
  配方显式传 `--host=aarch64-unknown-linux-gnu` 时无需 ohos 三元补丁

## 来源

qd 2.3.23-dfsg.1 鸿蒙适配（2026-09-21）：LBNL 上游两个历史地址均死链，
改用 Debian pool `qd_2.3.23+dfsg.1.orig.tar.xz`，实测 sha256 与
ports.ubuntu.com 副本一致后写入 conandata.yml。
