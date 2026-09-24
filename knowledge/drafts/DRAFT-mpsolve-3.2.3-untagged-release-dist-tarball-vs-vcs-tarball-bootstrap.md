# 上游版本没有 VCS tag 时怎么找权威发布物，以及「归档形态」如何决定整层构建引导

## 场景一：`refs/tags/<ver>.tar.gz` 返回 404，不等于这个版本不存在

`curl -sI https://github.com/robol/MPSolve/archive/refs/tags/3.2.3.tar.gz` → **404**。
按"没有 tag 就是没有这个版本"处理，会直接放弃一个真实存在的发布版。

事实是：**tag 是 VCS 的一种便利，不是发布的必要条件**。MPSolve 最新 tag 停在 3.2.1，
而 3.2.3 只以项目页上的 `make dist` 产物发布：

```
https://numpi.dm.unipi.it/wp-content/uploads/2025/08/mpsolve-3.2.3.tar.bz2
sha256 1f2e239c698c783b63a5e6903e76316c0335a01d71c466a8551e8a3f790b3971   (3.3 MB)
```

**权威性怎么交叉验证？** Debian 的打包者已经在替你验证了：`mpsolve_3.2.3.orig.tar.bz2`
就是取自这个 tarball。两边的 sha256 一致 ⇒ 可以认定这就是官方发布物。同源的还有
GNU ftp（`ftp.gnu.org/gnu/<pkg>/`）、KDE（`download.kde.org`）等项目自建发布目录——
本仓库里已经有 233 个 `deb.debian.org` / 147 个 `download.kde.org` / 69 个
`ftp.gnu.org` 来源，非 GitHub 来源是常态而不是例外。

**另一条线索更好用：master 的 `AC_INIT`。** 3.2.3 没有 tag，但 master 的
`configure.ac` 里 `AC_INIT` 已经写着 3.2.3 —— 说明 master 就是 3.2.3 的开发线。
把它当一个**可交叉比对的旁证**（比对文件 blob 是否逐字节相同），但**不要**把
master 的 snapshot 当发布物钉进 conandata（见 `forbid_2`）。

## 场景二：同一版本的两种归档，差着一整层构建引导

真正决定配方形态的不是版本号，而是**归档是 dist tarball 还是 VCS snapshot**。
一条命令就能判定：

```sh
tar tjf mpsolve-3.2.3.tar.bz2 | grep -E '/(configure|Makefile\.in|aclocal\.m4)$'
```

命中 ⇒ **dist tarball**（`autoreconf` 的产物已经被上游生成好并打进去了）；
只命中 `configure.ac`/`Makefile.am` ⇒ **VCS snapshot**。两者对配方的要求：

| | VCS snapshot（`archive/<sha>.tar.gz`） | dist tarball（项目页 / Debian orig） |
|---|---|---|
| `configure` | 无，必须 `autoreconf -fi` | 自带 |
| `tool_requires` | 需 autoconf / automake / libtool（钉精确版本） | **不需要** |
| `pkg.m4` | 缺，必须把 `ACLOCAL_PATH` 指到 pkg-config 的 `share/aclocal`，否则 `PKG_CHECK_MODULES` 展开成语法错误 | 已展开进 `aclocal.m4` |
| OHOS 禁 shebang exec | 需把 autotools 脚本包成 ELF 启动器 | 无此问题（只有一个 `configure`） |
| 引导风险 | 高：三个 tool_requires + 脚本执行域 | 低：一条 `sh ./configure` |

本包的 3.2.1 走的是**左列**（GitHub tag tarball），3.2.3 走的是**右列**。所以
3.2.3 的配方是 3.2.1 的**减法**：`build_requirements()` 整个删掉、`ACLOCAL_PATH`
注入删掉、ELF 启动器那套绕行删掉，`build()` 直接从 `sh ./configure` 起跑。

## 场景三：换版本时，"旧归档的补丁清单"必须逐条重新验证

这一条比上面两条更容易踩，因为它**不会被版本号的变化提示**。

3.2.1 带一个补丁 `0001-mps-mpc-register-keyword.patch`：`mps/mpc.h` 里有
`register signed long int`，而 C++17 移除了 `register` 关键字，`-std=c++17` 下
`nroots-polynomial.cpp` 等编译失败。到了 3.2.3，**上游自己修掉了**。照搬的结果是
`patch` 直接 `Hunk #1 FAILED`，CI 死在 source 阶段。

判定方式只有一种：**对新 tarball 逐条 `patch --dry-run`（或直接试着 apply），能过的
才是真还需要**。本包最终 `patches: {}`，`archives/m/mpsolve/3.2.3/` 下没有
`patches/` 目录。

同一族还有两个更容易忽略的：**上游测试文件也在变**——本包 `src/tests/` 的 19 个
`.c/.cpp/.h` 与 `Makefile.am` 在 3.2.3 tarball 与 master 上逐字节相同，所以
"上游测试数"的申报口径可以直接沿用；如果哪天某个测试文件改了，先前的用例数申报
就作废了。**判定"测试集合有没有变"最省事的办法就是比 blob 哈希**：

```sh
curl -s "https://api.github.com/repos/<org>/<repo>/contents/<dir>?ref=master" \
  | jq -r '.[]|"\(.name) \(.sha)"' | sort        # master 侧
for f in <dir>/*; do printf '%s %s\n' "$f" "$(git hash-object "$f")"; done | sort   # tarball 侧
# 逐行比对：全部相同 ⇒ 测试集合未变
```

## 推广

凡上游用 `STREQUAL "Linux"` 决定平台分支是"一次全 miss"（见
`DRAFT-openxr-1.1.63-...`）；同理，凡上游用 **VCS tag** 承载版本发布，没有 tag 的
版本就是一次"来源真空"——填空的办法不是猜，而是：**先判有无 tag → 再判发布物在哪
（并用 Debian orig 的 sha256 交叉验证）→ 再判归档形态（一条 `tar tjf | grep`）→
最后逐条重验旧补丁**。这四步做完，配方该是加法还是减法就唯一确定了。
