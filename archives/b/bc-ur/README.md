# bc-ur

Blockchain Commons UR Library（UR / "Uniform Resources" 编码的 C++ 参考实现，
BCR-2020-005）——用于在 URI 与 QR Code 中传输结构化二进制数据
（区块链钱包互操作场景：多签名 PSBT、账户信息交换等）。

- 官方仓库: https://github.com/BlockchainCommons/bc-ur
- 语言: C++17（零第三方依赖，内部自带 sha2/crc32/memzero/xoshiro256）
- 构建系统: autotools（发布 tarball 自带预生成 configure + 手写 Makefile.in）
- 产物: 静态库 `libbc-ur.a` + `include/bc-ur/*.hpp` 公开头（非 CLI，无 commands.json）

## 版本索引

| 版本 | 状态 | 备注 |
|------|------|------|
| 0.3.0 | built | HarmonyOS PC (aarch64, clang 15 / libc++) 零补丁适配；21/21 上游用例 + 消费者/鸿蒙专项 2/2 通过；路径 B 知识草稿 DRAFT-bc-ur-0.3.0-makefile-install-bare-name-in-source 随本包同 PR 交付 |