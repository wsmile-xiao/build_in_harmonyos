# bitcoin

Bitcoin Core 31.1 — 比特币共识引擎 / 全节点 / 钱包实现的 OHOS aarch64 适配。

## 功能概述

- **共识引擎** (`bitcoin_consensus`): 区块/交易验证脚本引擎
- **全节点** (`bitcoind`): P2P 网络节点，区块同步与广播
- **钱包** (`bitcoin_wallet`): BDB/SQLite 持久化钱包 (ENABLE_WALLET=ON)
- **CLI 工具**: `bitcoin-cli` (RPC), `bitcoin-util` (交易工具), `test_bitcoin` (单元测试)
- **静态库**: `libbitcoin_common`, `libbitcoin_consensus`, `libbitcoin_crypto`, `libbitcoin_util`, `libbitcoin_clientversion`

## 上游信息

- 上游仓库: https://github.com/bitcoin/bitcoin
- 发布标签: v31.1 (2026-07-06)
- 源码包 SHA-256: `88afbbc865f7527ebca82c197056ecc1877b6782d0fb1fe032b12f86bdd7e39e`
- 许可证: MIT

## HarmonyOS 适配要点

- **构建系统**: CMake (Bitcoin Core 31.1 从 autotools 迁移至 CMake)
- **编译器**: OHOS SDK clang 15.x, C++20
- **补丁**: 46 个 portability 补丁 (`patches/`)，处理 `std::ranges`/`std::views` 缺失、`source_location` polyfill、`span` CTAD、Boost signals2、`-lrt`/`-ldl` 链接适配等
- **package() 策略**: 用 `shutil.copy2` 字节级复制构建产物 (静态库/二进制/头文件)，**不走 cmake --install** — OHOS 内核按 ELF `.codesign` fs-verity 哈希校验 exec，cmake install 重写 RPATH 会使签名失效 → EPERM(126)
- **测试**: BUILD_TESTS=ON 构建 `test_bitcoin` (734 上游用例); test_package 3 断言实跑 `util_tests/parse_hex` 子集

## 依赖

| 依赖 | 版本 | 用途 |
|------|------|------|
| `sqlite3` | 3.49.1 | wallet 持久化存储 (ENABLE_WALLET=ON) |
| `libevent` | 2.1.13 | P2P 网络 / RPC HTTP 事件循环 |
| `boost` | 1.84.0 | program_options / filesystem / container / signals2 |

## 可选功能开关

| 选项 | 值 | 说明 |
|------|----|------|
| BUILD_GUI | OFF | Qt GUI 不构建 |
| WITH_ZMQ | OFF | ZMQ 发布订阅关闭 |
| ENABLE_IPC | OFF | IPC 多进程关闭 |
| ENABLE_EXTERNAL_SIGNER | OFF | 外部签名器关闭 |
| BUILD_BENCH | OFF | 基准测试不构建 |
| BUILD_FUZZ_BINARY | OFF | 模糊测试二进制不构建 |
| ENABLE_WALLET | ON | 钱包功能开启 |
| BUILD_TESTS | ON | 单元测试构建 (test_bitcoin) |

## 构建命令

```bash
export PATH=/storage/Users/currentUser/usr/local/bin:/data/service/hnp/bin:$PATH
export TMPDIR=$HOME/tmp

cd /storage/Users/currentUser/build_in_harmonyos
conan create archives/b/bitcoin/31.1.1 \
    -pr:h=ci/conan/profiles/ohos-aarch64 \
    -pr:b=ci/conan/profiles/ohos-aarch64 \
    --build=missing
```

## 测试运行

```bash
# 上游测试 (test_bitcoin, 734 用例)
<package_folder>/bin/test_bitcoin --run_test=util_tests/parse_hex -- -testdatadir=$HOME/tmp/btc-test

# test_package 消费者验证 (3 断言)
#   CI 在 conan create 的 test() 阶段自动运行
```

## 文件清单

```
archives/b/bitcoin/31.1.1/
├── PR_DESCRIPTION.md          # PR 描述与测试用例对比
├── README.md                  # 本文件 (库级说明)
├── commands.json              # 命令清单 (JSON)
├── conandata.yml              # Conan 数据: 源码 URL/sha256/补丁列表
├── conanfile.py               # Conan 配方: CMake 构建 + shutil.copy2 package
├── manifest.yaml              # 版本级清单 (依赖/配置/状态)
├── notes.md                   # 适配笔记 (补丁归纳/限制/编号映射)
├── patches/                   # 46 个 portability 补丁
│   ├── 0005-src-CMakeLists.txt.patch
│   ├── ...
│   └── 0055-src-test-span_tests.cpp.patch
└── test_package/              # Conan L1 测试包
    ├── CMakeLists.txt
    ├── MANIFEST.yml           # 上游测试声明
    ├── conanfile.py           # test() 显式 self.run()
    └── test.cpp               # 3 个真实库符号断言
```

## 参考资料

- 上游仓库: https://github.com/bitcoin/bitcoin
- 官方网站: https://bitcoincore.org/
- 许可证: MIT
- 适配笔记: [notes.md](notes.md)
- 命令清单: [commands.json](commands.json)
