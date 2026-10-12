# orafce 4.16.7 编译笔记

## 软件简介

orafce 是 PostgreSQL 的 Oracle 兼容扩展，提供 Oracle 风格的
日期、字符串、数学与 PL/SQL 包等函数，用于降低从 Oracle 迁移到 PostgreSQL 的成本。

## 编译过程

### Phase 1: 源码与依赖

- 源码: https://github.com/orafce/orafce/archive/refs/tags/VERSION_4_16_7.tar.gz
- 版本: 4.16.7
- 构建系统: PGXS（PostgreSQL Extension Building Infrastructure）
- 依赖: postgresql/18.3（OHOS aarch64 预编译二进制，提供 pg_config / PGXS / 服务端头文件）

### Phase 2: 编译

- 使用 clang 通过 PGXS 编译 orafce.so
- 链接参数: --unresolved-symbols=ignore-all --allow-shlib-undefined
  （PG 服务端符号在 CREATE EXTENSION 加载时解析）
- 产物: lib/orafce.so + extension/orafce.control + extension/orafce--*.sql

### Phase 3: 验证

- conan create 干净构建通过（无源码补丁，PGXS 直接编译）
- test_package 驱动上游 pg_regress 套件（19 个测试组，含 harmonyos_feasibility 端到端用例）
- ELF 冒烟测试（test_orafce.c 经 clang 编译并由 self.run 执行）

## 质量门禁

- G1 配方完整性: ✅ PASS（apply_conandata_patches 调用点存在，无补丁时为安全 no-op）
- G2 conan create: ✅ PASS
- W3 本地 CI: ✅ PASS（写入 .ci-result.json）

---

## 对话记录

### 对话 #1 2026-10-09 — OHOS PC aarch64 适配启动

执行本地门禁链（conan-verify → finish → W3 本地 CI → W2 PR 原子性），
完成 orafce 4.16.7 在 OpenHarmony PC (aarch64, musl) 的 Conan 2 适配。
---

**编译结束**: 2026-10-10 21:19
**最终状态**: published
