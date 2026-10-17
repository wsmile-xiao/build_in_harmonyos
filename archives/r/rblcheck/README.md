# rblcheck — OpenHarmony 编译档案

## 软件简介
rblcheck 是 RBL/DNSBL 黑名单的**命令行查询工具**（Edward S. Marshall 原作，
Marco d'Itri 维护）：把待查地址构造成反向查询名（如
`2.0.0.127.zen.spamhaus.org`）交给系统解析器解析，据此判断该地址是否被列入黑名单；
也支持域名型、邮件哈希型、文件哈希型黑名单。许可证 GPL-2.0-or-later。
本次适配上游发布版 **20231210**。

| 选项 | 说明 |
|------|------|
| `-c` | 清空 zone 列表 |
| `-s <zone>` | 切换某个 zone（加入/移除） |
| `-l` | 列出当前 zone 列表并退出 |
| `-q` | 安静模式 |
| `-t` | 显示 TXT 记录 |
| `-m` | 命中首个即停止 |
| `-v` / `-h` | 版本 / 帮助 |

## OHOS 适配要点

### 1. `res_query` 在 OHOS 上可用（无阻塞）
configure 探测 `checking for res_query... yes` / `checking for getaddrinfo... yes`
全部通过，`<resolv.h>`、`<arpa/nameser.h>` 均存在，实测可直接链接 libc
**无需 `-lresolv`**。因此"musl 缺少 res_query"的常见担忧在 OHOS 上**不成立**，
本适配不需要解析器 shim 或替代实现。

### 2. HMDFS 上 700 权限目录不可写（真实阻塞，已修复）
`config.status` 用 `(umask 077 && mktemp -d "./confXXXXXX")` 创建临时目录，
权限为 700。而 `/storage/Users/currentUser` 位于 HMDFS，**700 目录连属主也无法写入**：

| 创建方式 | 结果权限 | 写入 |
|----------|----------|------|
| `(umask 077 && mkdir d)` | `drwx--S---` | **Permission denied** |
| `(umask 022 && mkdir d)` | `drwxr-s--x` | OK |

于是 configure 必然失败：

```
./config.status[756]: can't create ./conffA5XBi/subs1.awk: Permission denied
config.status: error: could not setup config files machinery
```

**注意**：外挂 `umask 022` **无效**——`config.status` 在子 shell 内显式设置 `umask 077`。

**修复**：在 `autoreconf --install` 之后，把**生成的** `configure` 中两处
`umask 077` 放宽为 `umask 022`。这是对构建期自行生成的文件的改写，
**不是对上游源码的修改**（本档案无 patch 文件，`ohos_source_changes: none`）。

### 3. 构建前置
上游 tarball **不含预生成的 `configure`**，须先 `autoreconf --install`
（autoconf / automake / libtool / pkg-config 在 OHOS 构建镜像齐备）。

## 依赖关系
- **运行期**：libcrypto（openssl）—— `rblcheck_LDADD = $(CRYPTO_LIBS)`，动态链接。
  保留上游默认后端 `--with-crypto-library=openssl`，hashed DNSBL 支持已编译进产物，
  因此 `openssl` 在 conanfile 中声明为 `requires()`（运行期依赖），
  并经 `PkgConfigDeps` 提供 `libcrypto.pc`。
- 被依赖: 无

## 上游测试
`Makefile.am` 恰好声明 3 个 automake 测试：

```make
TESTS = tests/clearlist tests/addlisting tests/removelisting
```

| 测试 | 断言 |
|------|------|
| `tests/clearlist` | `./rblcheck -c -l` 输出为空 |
| `tests/addlisting` | `./rblcheck -c -s testlisting -l \| grep -v '^#' \| uniq` == `testlisting` |
| `tests/removelisting` | `./rblcheck -c -s testlisting -s testlisting -l` 输出为空 |

**三者全部只操作本地 zone 列表，不访问网络或 DNS**——`-l` 在任何地址被检查之前就
`exit(0)`。因此本库**没有**因公网 DNSBL 服务不可用而 blocked 的用例。

`build()` 在 `make()` 后执行 `make check`，即**完整**上游测试集
（`upstream_total = 3`），**未跳过、未过滤、未减少**。真机结果：
`TOTAL: 3, PASS: 3, SKIP: 0, FAIL: 0`。

## 参考资料
- [上游仓库 rfc1036/rblcheck](https://github.com/rfc1036/rblcheck)
- [v20231210 源码归档](https://github.com/rfc1036/rblcheck/archive/refs/tags/v20231210.tar.gz)
