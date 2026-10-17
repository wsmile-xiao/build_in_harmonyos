# ngircd 28 HarmonyOS PC 适配笔记

## 概述
- 软件：ngircd 28（轻量级 IRC 服务端 daemon，纯 C，autotools 构建）
- 上游：https://github.com/ngircd/ngircd（Rel-28）
- 适配路径：archives/n/ngircd/28/
- 构建目标：aarch64-linux-ohos（OpenHarmony PC / HarmonyOS PC，clang 15 交叉编译）

## 依赖与配置决策
| 项 | 决策 | 依据 |
|---|---|---|
| openssl | conan requires openssl/3.5.8.1，--with-openssl | ohpcd 有 1.1.1w~3.5.8.1；检测走 PKG_CHECK_MODULES([OPENSSL],[libssl libcrypto])，PkgConfigDeps 生成 .pc 命中 |
| zlib | conan requires zlib/1.3.1.2，--with-zlib | ohpcd 有 1.3.1.x；检测走 AC_CHECK_FUNCS(deflate)+AC_CHECK_HEADERS(zlib.h)，AutotoolsDeps 注入路径命中 |
| libident | ~~conan requires libident/0.32，--with-ident~~ → **--without-ident 裁剪** | 仓内已适配（archives/l/libident/0.32）但**未发布到 ohpcd 制品仓**：conan download 返回非标准错误 "system acceleration policy not enabled"，CI L0i 门禁归为 registry_unreachable（非 R36 not-found 分支）。IDENT 为可选 AUTH 协议，按规程退路 --without-ident 并记录证据。本机可先本地构建 libident 入 cache 验证 --with-ident 可行，但 CI worker 无此 cache 且 R36 要求依赖必须发布 |
| gnutls | --without-gnutls | 不在仓 |
| 文档 | 无需裁剪 | configure 无 --without-doc 选项；doc 构建仅静态文本+sed，无外部工具（doxygen 仅 make srcdoc） |
| 静态/共享 | 不适用 | ngircd 无 libtool、无库产物，纯可执行 daemon |

## 遇到的问题与解决方案
| # | 问题 | 现象 | 解决方案 |
|---|---|---|---|
| 1 | HMDFS umask 077 | configure 内 `umask 077 && mktemp -d "./confXXXXXX"` 创建 0700 临时目录，HMDFS 上后续文件操作 Permission denied | patches/0001-configure.patch：两处 umask 077 → 022（nettle/libident/aircrack-ng 同款问题） |
| 2 | config.guess/sub 识别 | 预判需补丁 | **无需处理**：ngircd 28 自带 config.sub 已含 ohos 分支（`\| ohos*` 与 `linux-ohos*- )`），实测 configure 交叉探测通过 |
| 3 | 安装目录 | upstream install 到 $(sbindir)/ngircd | package() 折叠 sbin/ → bin/（accel-ppp 同款手法） |
| 4 | 上游 testsuite | 依赖 expect(1)+telnet(1)，本机无 expect | 15 个 testsuite 用例 SKIP（exit 77 不失败）；portabtest + check-version + check-help 3 例可真跑；daemon 冒烟兜底（见 test_package） |

## 测试设计
- make check：portab/portabtest（1 C 单测）+ ngircd/check-version、check-help（2 shell 测试）真跑
- test_package 冒烟三件套：
  1. `ngircd -V`：版本输出断言（含 "ngircd 28"）
  2. `ngircd --configtest --config <最小配置>`：配置解析断言（退出码 0）
  3. `ngircd --nodaemon` 绑定 127.0.0.1 高位端口，裸 socket 发 NICK/USER，断言收到 001 欢迎行，随后正常 shutdown

## 已知限制
- 无头环境无 expect 解释器：上游 testsuite 15 例 SKIP（非失败），已如实计入 PR 测试对比
- 交叉编译产物为 OHOS ELF，仅能在 OHOS/鸿蒙 PC 环境运行（本机即目标平台）
