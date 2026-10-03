# john-jumbo

John the Ripper "jumbo" 社区增强版 —— 密码安全审计与恢复工具集，支持数百种哈希格式（md5crypt/sha256crypt/sha512crypt/NT/Raw-MD5/PKZIP 等），本配方对应上游 1.9.0-jumbo-1（2019-05 发布）。

## 功能概述

| 组件 | 安装位置 | 职责 |
|---|---|---|
| john | bin/ | 主程序：哈希破解/基准自检/构建信息查询 |
| john.conf 等 11 个配置 + password.lst + .chr 字符集 + rules/ | bin/ | 运行时必需（与二进制同目录——1.9.0-jumbo-1 的 $JOHN = dirname(argv[0])） |
| relbench/mailer 等辅助工具 + 108 个 *2john 提取脚本 | share/john/ | 辅助工具与扩展脚本 |

> 注：8 个 argv[0] 别名入口（unshadow / unique / zip2john / gpg2john / rar2john /
> undrop / unafs / base64conv）本版本不随包发布——OHOS 全盘禁 symlink，配方仅发布
> john 本体与运行时数据；需要时可按 `cp bin/john bin/<别名>` 自建副本，
> john 按 argv[0] 分派，语义与上游符号链接等价。

## OHOS 适配

- 构建体系：上游 `src/Makefile.legacy` 的 `linux-arm64le` 目标（跳过 `./configure` —— 其 OS 探测无法识别 HarmonyOS；legacy 目标是上游官方为不支持系统提供的构建路径）。
- `-DJOHN_NO_SIMD`：arm64 SIMD 内联汇编在 OHOS clang 下编译失败（NEON `vroti_epi32` 宏），按上游注释禁用 SIMD 层。
- 依赖：OpenSSL 1.1.1w + zlib 1.3.1.1（均为制品仓版本，纯静态库、静态链入）——OpenSSL 系（openssl-enc）与压缩系（PKZIP）格式已由消费者测试 `--test` 自检覆盖。
- 消费者测试在真机实跑：`--list=build-info` 版本校验、7 格式自检（`--test`，含 PKZIP/openssl-enc 依赖路径）、5 组真实哈希 E2E 破解闭环。

## 依赖关系

- openssl/1.1.1w、zlib/1.3.1.1（均为制品仓已有版本）。

## 参考资料

- 上游项目：https://www.openwall.com/john/
- 上游发布 tarball：`john-1.9.0-jumbo-1.tar.xz`（sha256 见 `1.9.0/conandata.yml`）
