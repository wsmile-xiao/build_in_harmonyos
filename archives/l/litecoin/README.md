# litecoin

Litecoin Core 0.21.4 — 莱特币全节点 / 共识引擎 / MWEB（MimbleWimble 扩展块）隐私层的 OHOS aarch64 适配。

## 功能概述

- **全节点** (`litecoind`): P2P 网络节点，区块同步与广播，scrypt PoW 验证
- **CLI 工具**: `litecoin-cli` (RPC 客户端), `litecoin-tx` (交易构造/检查), `litecoin-wallet` (钱包工具)
- **钱包**: Berkeley DB 6.2.32（db_cxx C++ API）
- **MWEB**: Litecoin 专属 MimbleWimble 扩展块隐私层（libmw + secp256k1-zkp）
- **共享库**: `libbitcoinconsensus`（脚本验证共识引擎）

## 上游信息

- 上游仓库: https://github.com/litecoin-project/litecoin
- 发布标签: v0.21.4 (2024-10)
- 源码包 SHA-256: `ba0922213f69c1b1a1d6c3441c5ea3696b538437533555ab74268f075f0de5d3`
- 许可证: MIT

## HarmonyOS 适配要点

- autotools 构建系统（bitcoin 系 0.21 末代 autotools 大版本）
- boost 三包合并布局（boost/1.84.0 头 + boost1.84-thread/system 库）
- musl 兼容: BOOST_SP_NO_PTHREAD_SETCANCELSTATE + ghc::filesystem strerror_r patch
- 构建开关: --without-gui --disable-tests --disable-bench --disable-zmq
- 详见 [0.21.4/notes.md](0.21.4/notes.md)

## 版本索引

| 版本 | 状态 | 说明 |
|------|------|------|
| 0.21.4 | 首次适配 | autotools, MWEB, db/6.2.32 钱包 |
