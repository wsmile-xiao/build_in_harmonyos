# DRAFT-14404：OpenSSL 3.3.0 rand-seed=getrandom 完全排除 DEVRANDOM（实测）

## 适用场景
适配 OpenSSL 3.3.x 系配方（含 quictls fork）到 OHOS 时核验 E235 修复手段
的排除效果；排查 3.3.0 与 3.5.x 的熵源文件路径差异。

## 报错签名（命中任一即适用）
```
DEVRANDOM_WAIT（configdata.pm 中出现即表示 DEVRANDOM 块未被排除）
OPENSSL_RAND_SEED_DEVRANDOM
rand_unix.c.*__fd_chk（3.5.x 路径签名；3.3.0 路径不同见下）
```

## 根因 / 实测结论
- 3.3.0 带 `--with-rand-seed=getrandom`：configdata **0 次** DEVRANDOM
  出现（完全排除，非编译回退），rand_unix.c 零补丁通过构建 + make test
  全量 3185 项
- **路径差异备忘**：3.3.0 熵源 = `providers/implementations/rands/seeding/
  rand_unix.c`；3.5.x = `crypto/rand/rand_unix.c`。E235 条目签名按 3.5.x
  路径书写，3.3.0 命中时路径不同但 flag 结论相同
- E235 verification_cmd（`llvm-nm -u libcrypto.a | rg __fd_chk`）3.3.0 下
  应无输出

## 修法
1. OpenSSL 3.3.x 配方统一带 --with-rand-seed=getrandom（与 3.5.x 同口径）
2. 核验方法：`grep -c DEVRANDOM configdata.pm`（=0 即完全排除）
3. rand_unix.c 零补丁；若某 3.3.x 小版本未完全排除，按 E235 主方案处理
   并回写本条目

## 验证
- quictls/3.3.0-quic1：configdata 0 次 DEVRANDOM + make test Result: PASS
  （2026-09-29 本机 OHOS aarch64 实测）
