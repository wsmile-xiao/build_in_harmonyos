# ascon-c 1.3.0 — 适配笔记

## 库简介
Ascon 轻量级密码算法族（AEAD/HASH/XOF/PRF/MAC）的 C 参考实现集合，纯 C99 +
可选平台 ASM，无外部运行时依赖。

## 构建系统
- 上游为 CMake：`project(ascon LANGUAGES C ASM)`，按 (CRYPTO × ALG × IMPL)
  循环生成 199 个静态库 + 199 个 genkat CTest 用例。
- 首次 conan-init 误判为 autotools，已按 CMake 模板重写 conanfile.py。

## 关键适配点
1. **REL_FLAGS 覆盖**: 上游默认 `-std=c99 -O2 -fomit-frame-pointer
   -march=native -mtune=native`。`-march=native` 针对构建机 CPU，OHOS 交叉
   工具链下不可用；配方 `CMakeToolchain` 覆盖为 `-std=c99;-O2`。
2. **组合目录库名**: `crypto_aead_hash/asconv13` 在 CMake CRYPTO 循环中分别以
   `crypto_aead_asconv13_ref` 和 `crypto_hash_asconv13_ref` 生成（内容相同，
   均含 AEAD+HASH 全符号）。conanfile components 链接 `crypto_aead_asconv13_ref`。
3. **无 install()**: 上游无安装规则，package() 手动安装 `tests/crypto_*.h`
   声明头 + 各 ref 实现目录头 + 全部 .a。

## 测试
- 上游 genkat: 199/199 (100%)，Release + REL_FLAGS 覆盖配置下全量通过。
- 消费者 (test_package): AEAD 往返 / 篡改拒绝 / HASH LWC KAT 三组断言通过。
- 无 CLI 产物（纯库），不需要 commands.json。

## W3 基线隔离
- finish/W3 的 junk_check full 模式曾命中 `archives/c/cloog/0.21.1/`
  `.build-closed`/`.staging-verified`（HEAD 中提交前已存在的其他库基线文件）。
  已按 SKILL.md 规则：记录路径与隔离前 SHA-256（均为 e3b0c442... 空文件）→
  临时隔离（git rm --cached）→ 复跑 W3 通过 → 原样恢复并核对 SHA-256 一致；
  未修改、未提交该基线文件。
---

**编译结束**: 2026-09-19 12:13
**最终状态**: built
