# rblcheck 20231210 适配笔记

## 软件简介
rblcheck 是 RBL/DNSBL 黑名单的**命令行查询工具**：把待查地址构造成反向查询名
（如 `2.0.0.127.zen.spamhaus.org`）交给系统解析器解析，据此判断该地址是否被列入
黑名单。原作者 Edward S. Marshall，2019 年起由 Marco d'Itri 维护。
许可证 GPL-2.0-or-later。本次适配上游发布版 **20231210**。

| 选项 | 说明 |
|------|------|
| `-c` | 清空 zone 列表 |
| `-s <zone>` | 切换某个 zone（加入/移除） |
| `-l` | 列出当前 zone 列表并退出 |
| `-q` / `-t` / `-m` | 安静模式 / 显示 TXT / 命中即停 |
| `-v` / `-h` | 版本 / 帮助 |

## 编译环境
- 构建系统: autotools（**tarball 不含预生成的 configure，须先 `autoreconf --install`**）
- 目标平台: OpenHarmony OHOS / aarch64（clang 15.0.4）
- 加密后端: **openssl**（上游默认，保留 hashed DNSBL 支持）

## OHOS 适配发现

### 发现一：OHOS libc **提供** `res_query`（好消息）
configure 探测结果：

```
checking for res_query... yes
checking for getaddrinfo... yes
```

`<resolv.h>` 与 `<arpa/nameser.h>` 均存在，实测 `res_query` 可直接链接 libc、
**不需要 `-lresolv`**。因此"musl 缺少 res_query"的常见担忧在 OHOS 上**不成立**，
rblcheck 不需要任何解析器 shim 或替代实现。

### 发现二：HMDFS 上 700 权限目录不可写（真实阻塞，已修复）
**原始失败**：

```
configure: creating ./config.status
./config.status[756]: can't create ./conffA5XBi/subs1.awk: Permission denied
config.status: error: could not setup config files machinery
```

**定位**：autoconf 生成的 `config.status` 用下列方式创建临时目录：

```sh
tmp=`(umask 077 && mktemp -d "./confXXXXXX") 2>/dev/null` &&
...
(umask 077 && mkdir "$tmp")
```

即目录权限为 **700**。

**根因（在 OHOS 真机上最小复现）**：

| 创建方式 | 结果权限 | 向其写入文件 |
|----------|----------|--------------|
| `(umask 077 && mkdir t700)` | `drwx--S---` | **Permission denied** |
| `(umask 022 && mkdir t755)` | `drwxr-s--x` | OK |

`/storage/Users/currentUser` 位于 HMDFS（`/data/service/el2/100/hmdfs/account`）。
在该文件系统上，**mode 700 的目录连属主自己也无法写入**。config.status 因此建不了
`subs1.awk`，configure 失败。

**注意**：外挂 `umask 022` **无效** —— config.status 在子 shell 内部显式设置了
`umask 077`，外层 umask 影响不到它。

**修复**：在 `autoreconf --install` 之后，把**生成的** `configure` 中两处
`umask 077` 放宽为 `umask 022`。这是对本步骤自行生成的文件的构建期改写，
**不是对上游源码的修改**（本档案 `ohos_source_changes: none`，无 patch 文件）。
本仓已有的 libpipeline 配方对同一问题采用了等价处理。

修复后：configure rc=0，make rc=0，make check 全通过。

## 上游测试
`Makefile.am` 恰好声明 3 个 automake 测试：

```make
TESTS = tests/clearlist tests/addlisting tests/removelisting
```

三者均为 `/bin/sh` 脚本，全部只操作 rblcheck 的**本地 zone 列表**
（`-c` 清空 / `-s <zone>` 切换 / `-l` 列出并退出）：

| 测试 | 断言 |
|------|------|
| `tests/clearlist` | `./rblcheck -c -l` 输出为空 |
| `tests/addlisting` | `./rblcheck -c -s testlisting -l \| grep -v '^#' \| uniq` == `testlisting` |
| `tests/removelisting` | `./rblcheck -c -s testlisting -s testlisting -l` 输出为空 |

**关键**：`-l` 在 `optind == argc` 检查之前就 `exit(0)`（见 `rblcheck.c` 的
`case 'l'`），因此**三个测试都不访问网络或 DNS**。这意味着本库**没有**因公网
DNSBL 服务不可用而无法执行的用例，不需要申报 BLOCKED。

`build()` 在 `make()` 之后执行 `make check`，即**完整**上游测试集：
`upstream_total = 3`。**未跳过、未过滤、未减少**。

真机 `make check` 输出：

```
PASS: tests/clearlist
PASS: tests/addlisting
PASS: tests/removelisting
# TOTAL: 3
# PASS:  3
# SKIP:  0
# FAIL:  0
```

## 加密后端
保留上游默认 `--with-crypto-library=openssl`，hashed DNSBL（SHA/base32）支持已编译进
产物。因此 libcrypto 是**运行期**依赖（`rblcheck_LDADD = $(CRYPTO_LIBS)`，动态链接），
在 conanfile 中声明为 `requires("openssl/3.5.7")`（ohpcd 有预编译包）。
配方用 `PkgConfigDeps` 提供 `libcrypto.pc`，使 `PKG_CHECK_MODULES(crypto, libcrypto)`
能够成功。

## 打包要点
- `bin/rblcheck`
- `licenses/COPYING`
- 运行期需要 libcrypto（由 openssl 依赖提供）

## 验证结果
（等待 Harmony PC 真机 `conan create` 后填写）

<!-- notes-end -->
