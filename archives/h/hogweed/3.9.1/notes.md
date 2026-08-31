# hogweed 3.9.1 — 适配笔记 (R01 bootstrap)

## 来源核验
- hogweed 无独立发布版，属于 GNU Nettle 项目（libhogweed 公钥加密库）。
- 官方发布 tarball: https://ftp.gnu.org/gnu/nettle/nettle-3.9.1.tar.gz
- SHA256: ccfeff981b0ca71bbd6fbcb054f407c60ffb644389a5be80d6716d5b550c6ce3（与官方/Debian 断言一致）
- 官方 git tag: nettle_3.9.1_release_20230601 → commit d2cc9b95b50440c331ee143312309951a7e8d7ca
- 官方仓库: https://git.lysator.liu.se/nettle/nettle

## 构建系统
- autotools（configure + make），随 nettle 源码一起构建 libnettle 与 libhogweed。
- 依赖 gmp（大数运算，R27 格式声明 gmp/6.3.0.1）。

## 待 adapt 阶段处理
- aarch64 汇编（fat 构建）与 config.guess/config.sub 平台识别（参考 nettle/3.10 的 47 个补丁）。
- 平台限制：/tmp 只读（TMPDIR 重定向）等（参考 gmp/gnutls 适配笔记）。

## R01 bootstrap 结论
- 官方来源、tag、校验值均已确认；最小归档/配方骨架已建立。
- 可进入首轮 adapt。
---

**编译结束**: 2026-08-31 09:37
**最终状态**: built
