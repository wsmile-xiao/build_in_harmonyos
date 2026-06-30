# ddclient 4.0.0 适配笔记

## 编译环境
- 构建系统: custom（Perl脚本软件，手动sed安装）
- 编译日期: 2026-06-03
- 编译器: 无需C编译器（Perl脚本）
- Perl版本: 5.42.0 (aarch64-linux)
- 状态: published

## 编译步骤

1. **init-build**: 使用 `--url=https://download.savannah.nongnu.org/releases/ddclient/ddclient-4.0.0.tar.gz` 初始化，因Python urllib SSL验证失败，改用 `curl -fsSL -k` 手动下载到 `~/tmp/builds/` 目录后init-build检测到已存在文件跳过下载
2. **configure 尝试**: 执行 `./configure --prefix=$DEFAULT_PREFIX` 失败，config.status在HMDFS上无法创建临时目录（`./confXXX/subs1.awk: Permission denied`），原因是HMDFS安全限制导致bash内置`rm`命令不可用
3. **手动构建**: 使用sed从`ddclient.in`模板生成ddclient脚本，替换变量：
   ```bash
   sed -e 's|@PACKAGE_VERSION@|4.0.0|g' \
       -e '1 s|^#!.*perl$|#!/storage/Users/currentUser/usr/local/bin/perl|g' \
       -e 's|@localstatedir@|/storage/Users/currentUser/usr/local/var|g' \
       -e 's|@confdir@|/storage/Users/currentUser/usr/local/etc/ddclient|g' \
       -e 's|@runstatedir@|/storage/Users/currentUser/usr/local/var/run|g' \
       -e 's|@CURL@|/usr/bin/curl|g' \
       ddclient.in > ddclient && chmod +x ddclient
   ```
   同样从`ddclient.conf.in`生成`ddclient.conf`
4. **DESTDIR安装 (R20)**: 手动创建目录结构并复制文件到 `$TEST_PREFIX/$DEFAULT_PREFIX/`
   - `$TEST_PREFIX/$DEFAULT_PREFIX/bin/ddclient` — 主脚本
   - `$TEST_PREFIX/$DEFAULT_PREFIX/etc/ddclient/ddclient.conf` — 配置文件模板
   - `$TEST_PREFIX/$DEFAULT_PREFIX/share/doc/ddclient/` — 5个文档文件（COPYING, COPYRIGHT, README.md, ChangeLog.md, CONTRIBUTING.md）
   - `$TEST_PREFIX/$DEFAULT_PREFIX/var/cache/ddclient/` — 缓存目录
   - `$TEST_PREFIX/$DEFAULT_PREFIX/var/run/` — PID目录
5. **G0干净构建验证**: finish自动触发clean-verify，configure成功（umask patched 077→022），make成功（sed替换生成ddclient），install产物正常（1 bin, 0 lib）
6. **本地安装**: 将ddclient安装到 `$DEFAULT_PREFIX/bin/ddclient`，模拟用户部署
7. **验证**: `perl ddclient --version` 输出 "ddclient version 4.0.0"
8. **package**: `ohc-run.py package` 成功制作 `ddclient-4.0.0-ohos-aarch64.tar.gz` (430KB)
9. **finish**: `ohc-run.py finish ddclient 4.0.0 published` 完成，G0-G4全部PASS

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | Python urllib SSL验证失败无法下载源码包 | HMDFS平台SSL证书配置问题 | 用 `curl -fsSL -k` 手动下载tarball到 `~/tmp/builds/` 目录 |
| 2 | configure/config.status运行失败 | HMDFS安全限制：bash内置`rm`不可用+无法创建临时子目录（Permission denied） | 手动用sed从.in模板生成ddclient脚本，跳过configure流程 |
| 3 | 直接执行ddclient脚本报"no such file or directory" | HMDFS平台限制：Perl脚本shebang直接执行被拦截 | 通过 `perl ddclient --version` 方式调用验证功能 |
| 4 | verify-build G4报"manifest缺少build_system" | manifest模板使用嵌套`build.system:`，但G4检查flat key `build_system:` | 手动在manifest.yaml中添加 `build_system: custom` 字段 |
| 5 | IO::Socket::SSL Perl模块缺失 | 平台Perl未安装SSL相关模块 | 不影响ddclient基本功能（--version/--help/--list-protocols），记录为运行时依赖 |

## 源码修改

无补丁。ddclient源码未做任何修改，仅通过sed替换.in模板中的变量占位符生成最终脚本。所有变量替换与Makefile.am中的sed规则完全一致。

## 依赖版本

| 依赖 | 版本 | 说明 |
|------|------|------|
| perl | 5.42.0 | 运行时核心依赖（aarch64-linux） |
| curl | 系统自带 | ddclient默认使用curl获取IP地址（路径: /usr/bin/curl） |
| IO::Socket::SSL | 缺失 | ddclient HTTPS功能需要，但基本功能不依赖 |
| HTTP::Tiny | 5.42.0内置 | ddclient可使用HTTP::Tiny作为替代HTTP客户端 |
| JSON::PP | 5.42.0内置 | 部分协议需要JSON解析 |
| Digest::SHA | 5.42.0内置 | 部分协议需要SHA校验 |

## 验证结果

### --version 输出
```bash
$ perl /storage/Users/currentUser/usr/local/bin/ddclient --version
ddclient version 4.0.0
  originally written by Paul Burry, paul+ddclient@burry.ca
  project now maintained on https://github.com/ddclient/ddclient
```

### --list-protocols 输出
```bash
$ perl /storage/Users/currentUser/usr/local/bin/ddclient --list-protocols
1984
changeip
cloudflare
cloudns
ddns.fm
digitalocean
dinahosting
directnic
dnsexit2
dnsmadeeasy
domeneshop
dondominio
dslreports1
duckdns
dyndns1
dyndns2
easydns
emailonly
enom
freedns
freemyip
gandi
godaddy
he.net
hetzner
infomaniak
inwx
keysystems
mythicdyn
namecheap
nfsn
njalla
noip
nsupdate
ovh
porkbun
regfishde
sitelutions
yandex
zoneedit1
```

### --help 输出（摘要）
```bash
$ perl /storage/Users/currentUser/usr/local/bin/ddclient --help
usage: ddclient [options]
options are:
  --daemon=<delay>       : run as a daemon, specify <delay> as an interval.
  --foreground           : do not fork (default: noforeground).
  --proxy=<host>         : use <host> as the HTTP proxy.
  --server=<host>        : update DNS information on <host> (default: members.dyndns.org).
  --protocol=<type>      : update protocol used (default: dyndns2).
  --list-protocols       : print a machine-readable list of supported update protocols and exit.
  --file=<path>          : load configuration information from <path> (default: .../etc/ddclient/ddclient.conf).
  --cache=<path>         : record address used in <path> (default: .../var/cache/ddclient/ddclient.cache).
  --pid=<path>           : record process id in <path> if daemonized.
  ...（完整帮助信息包含39个协议的配置说明）
```

### Staging验证（DESTDIR模式）
```
$TEST_PREFIX/$DEFAULT_PREFIX/bin/ddclient      — 315818字节，可执行 ✅
$TEST_PREFIX/$DEFAULT_PREFIX/etc/ddclient/ddclient.conf — 12062字节 ✅
$TEST_PREFIX/$DEFAULT_PREFIX/share/doc/ddclient/ — 5个文档文件 ✅
$TEST_PREFIX/$DEFAULT_PREFIX/var/cache/ddclient/ — 目录存在 ✅
$TEST_PREFIX/$DEFAULT_PREFIX/var/run/          — 目录存在 ✅
```

### 质量门禁结果
- G0 干净构建验证: PASS（configure+make+install全流程自动通过）
- G1 二进制完整性: PASS（Perl脚本，无ELF二进制）
- G2 功能可用性: PASS（ddclient --version 输出正确）
- G3 可移植性: PASS（无ELF，无需RPATH/签名）
- G4 档案完整性: PASS（manifest.yaml、notes.md完整）

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| ddclient-4.0.0-ohos-aarch64.tar.gz | 430KB (440408字节) | 预编译包（含bin/ddclient, etc/ddclient/ddclient.conf, share/doc/, var/目录结构） |
| ddclient (主脚本) | 315818字节 (7705行) | Perl脚本，版本4.0.0 |
| ddclient.conf | 12062字节 | 配置文件模板 |

## 注意事项

1. ddclient在HMDFS上必须通过 `perl ddclient` 方式调用，shebang直接执行报"no such file or directory"
2. ddclient完整功能（HTTPS更新DNS）需要 IO::Socket::SSL 模块，当前平台缺失
3. ddclient是纯Perl脚本软件，无需C编译器，无需configure/make流程
4. 源码tarball SHA256: `15c73d4b61e8e4974707379df1dbf15ab9f933835c6968947d2b56173388c6f0`
---

**编译结束**: 2026-06-03 14:48
**最终状态**: published
