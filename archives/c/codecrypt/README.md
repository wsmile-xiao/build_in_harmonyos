# codecrypt

后量子密码学命令行工具 (ccr) — 类 GnuPG 的加密/签名程序，仅使用抗量子计算攻击的算法：

- **加密**: McEliece QC-MDPC（紧凑 QC-MDPC 变体）
- **签名**: 基于 Merkle 树的哈希算法（FMTSeq 变体）

上游: https://github.com/exaexa/codecrypt (mirror; 主仓 codeberg.org, 官网 http://e-x-a.org/codecrypt/)

许可证: LGPL-3.0-or-later (库部分) / 程序本体见上游 COPYING

## 版本

| 版本 | 状态 | 说明 |
|------|------|------|
| 1.8 | published | OHOS aarch64 适配, cryptopp 全算法套件 (26 算法) |

## 构建

- 构建系统: autotools（tarball 无 configure，autogen.sh 引导）
- 依赖: gmp/6.3.0.1, fftw/3.3.11, cryptopp/8.9.0（均已在制品仓发布）
- 工具链: automake/1.18 + libtool/2.5.4 (tool_requires)
- OHOS 适配: pwrng.cpp 增加 termios 版 readpassphrase（musl 无 getpass）
