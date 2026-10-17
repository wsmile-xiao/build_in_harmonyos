# nettle 3.10.2 适配笔记（2026-09-10，鸿蒙 PC 专项·依赖项）

## 概要
- 上游：GNU nettle 3.10.2（LGPL-2.1+，autotools），依赖 gmp/6.3.0（仓内已有）。
- 官方 main 原有 3.10.2/ 目录仅 manifest.yaml(status: partial) + notes.md 占位（2026-04-17），本任务补全交付：conanfile.py / conandata.yml / patches/ / test_package/ / manifest / notes。
- sha256 = fe9ff51cb1f2abb5e65a6b8c10a92da0ab5ab6eaf26e7fc2b675c45f1fb519b5（ustc/tuna 双镜像本地比对 = Homebrew nettle@3 公开值，三源一致）。

## 遇到的问题与解决方案
| 问题 | 解法 |
|------|------|
| E007: config.guess 不识别 HarmonyOS（报 aarch64-unknown-linux-ohos 之外系统失败） | 补丁 patches/0001-config.guess.patch（同 3.9.1，已验证对 3.10.2 干净 apply） |
| E011: configure 临时目录 umask 077 在 hmdfs 上失败 | 补丁 patches/0002-configure.patch 改 022（源：3.9.1 的 0003-configure.patch 改名，验证干净 apply） |
| 3.10.2 config.sub 是否需要补丁？ | **不需要**：3.10.2 config.sub 原生已含 `ohos*` 与 `linux-ohos*` 映射（config.sub L2070/L2213），与 4.0（需要 0002-config.sub.patch）不同 |
| gmp 依赖如何传入 configure | 3.10.x configure 仍支持 `--with-include-path` / `--with-lib-path`（4.0 起移除），conanfile.py generate() 直接传 gmp 包 include/lib 路径 |
| 3.x 与 4.x API 差异 | 3.x `sha256_digest(&ctx, SHA256_DIGEST_SIZE, digest)` 三参数；test_package/test.c 按 3.x 写 |

## 构建与测试结果
- conan create（ohos-aarch64 profile，CC=clang）：成功，包 4c86cf6efe39ba37993c67250d7692d360f0b04b。
- 上游 make check：**All 116 tests passed**（testsuite 116/116，含 AES/DES/ChaCha/SM4/GCM/CCM/SIV、SHA 家族、HMAC、PBKDF2、Ed25519/Ed448、ECDSA、RSA、cxx、symbols 等）+ examples **All 3 tests passed**（rsa-sign/rsa-verify/rsa-encrypt），rc=0，失败 0、跳过 0。
- test_package：ctest 1/1 + 消费者二进制 PASS（SHA256('abc') 已知摘要、AES-128 已知密文），共 2/2。

## 历史占位（2026-04-17，官方登记，原文保留如下）

# nettle 3.10.2 编译进度

**日期**: 2026-04-17
**状态**: 🔄 编译中

## 步骤记录

| 步骤 | 状态 | 备注 |
|------|------|------|
| Step 1 init | ⏳ | |
| Step 2 patches | ⏳ | |
| Step 3 configure | ⏳ | |
| Step 4 make | ⏳ | |
| Step 5 install | ⏳ | |
| Step 6 safety | ⏳ | |
| Step 7 check | ⏳ | |
| Step 8 staging | ⏳ | |
| Step 9 package | ⏳ | |
| Step 10 deploy | ⏳ | |
| Step 11 finish | ⏳ | |

## 发现与知识

<!-- 编译过程中发现的问题和解决方案 -->

---

**编译结束**: 2026-04-17 21:53
**最终状态**: partial
