# bitcoin 31.1.1 适配笔记

## 1. 补丁归纳 (46 个, `patches/`)

全部为 **portability** 类型补丁，不改上游测试断言语义，仅做 OHOS 编译/链接兼容。

### 1.1 CMake 构建系统适配 (1 个)

| 补丁 | 目标 | 说明 |
|------|------|------|
| 0005 | src/CMakeLists.txt | OHOS 平台检测 / 编译选项适配 |

### 1.2 平台 API 兼容 (源文件级, ~35 个)

| 编号区间 | 主题 | 代表补丁 |
|----------|------|----------|
| 0006-0014 | 网络/HTTP/IPC/kernel 适配 | netif.cpp, pcp.cpp, httpserver.h, i2p.cpp, init-common.cpp, libmultiprocess gen.cpp, bitcoinkernel_wrapper.h, chainparams.cpp |
| 0017-0027 | 网络/RPC/脚本/policy 适配 | net.cpp, net_processing.cpp, netaddress.cpp, mini_miner.cpp, ephemeral_policy.cpp, private_broadcast.cpp, pubkey.h, rpc-client.cpp, rpc-mempool.cpp, rpc-server.cpp, script-descriptor.cpp |
| 0031-0042 | signet/span/txmempool/uint256/util/check/log/validation/wallet 适配 | signet.cpp, span.h, txmempool.cpp, uint256.h, util-check.cpp, util-check.h, util-log.h, util-overloaded.h, util-strencodings.h, validation.cpp, wallet-db.cpp, wallet-transaction.h |
| 0043-0048 | validation-views/uint256/test-ranges/test-coinsviewoverlay/strencodings/transaction_identifier | C++20 ranges/views → 迭代器改写, span CTAD 修复 |

### 1.3 测试源文件补丁 (7 个, 0049-0055)

| 补丁 | 目标 | 说明 |
|------|------|------|
| 0049 | src/test/logging_tests.cpp | C++20 语法兼容 (OHOS libc++ v15 缺失 `std::ranges`/`std::views` 子集) |
| 0050 | src/test/netbase_tests.cpp | `std::ranges::*` → 标准迭代器改写 |
| 0051 | src/test/prevector_tests.cpp | prevector 测试兼容改写 |
| 0052 | src/test/private_broadcast_tests.cpp | `std::views` → 手写循环 |
| 0054 | src/test/wallet/db_tests.cpp | wallet db_tests 兼容改写 |
| 0055 | src/test/span_tests.cpp | `std::span` CTAD: 为 `SpannableYes` 补充 `value_type` 与 const 限定 |

> **0053** (`src/util/string.h`) 属于工具头适配,非测试源文件补丁。

### 1.4 抽查复核 (0049/0052/0055)

- **0049** (`logging_tests.cpp`): 仅将 `std::ranges::` 调用替换为等价 `std::` 迭代器版本,无断言修改。✓
- **0052** (`private_broadcast_tests.cpp`): `std::views::filter` → 手写 `for` 循环 + `if` 谓词,语义等价,无断言修改。✓
- **0055** (`span_tests.cpp`): 为 `SpannableYes` 结构体补充 `value_type` typedef 与 `const` 成员限定,使 `std::span` CTAD 在 OHOS libc++ v15 (定义 `_LIBCPP_HAS_NO_INCOMPLETE_RANGES`) 下走旧版 `value_type` 指南。语义等价,无断言修改。✓

## 2. 补丁编号不连续说明

### 2.1 缺口映射

| 缺口 | 原因 |
|------|------|
| 0001-0004 | 上游原始补丁位 (Bitcoin Core CI 用),本次适配从 0005 开始 |
| 0015-0016 | 合并至 0014 (chainparams) 或跳过 (上游无对应改动) |
| 0028-0030 | 合并至 0027 (script-descriptor) 或跳过 |

### 2.2 不重编号的决策

- **风险**: 重编号需同步修改 conandata.yml 的 `patch_file` 路径与 `patches/` 目录文件名,任何错位会导致 `apply_conandata_patches()` 找不到文件 → build() 失败。
- **决策**: 保留原始编号 (0005-0055, 含缺口),仅确保 conandata.yml 的 46 个条目与 patches/ 目录 46 个文件逐一对应。缺口原因记录于此,不影响构建。

## 3. 依赖版本选择理由

| 依赖 | 选定版本 | 理由 |
|------|----------|------|
| sqlite3 | 3.49.1 | ohpcd remote 已发布; Bitcoin Core 31.1 要求 SQLite ≥ 3.7.7; 钱包 BDB 迁移至 SQLite 的最低稳定版 |
| libevent | 2.1.13 | ohpcd remote 已发布; Bitcoin Core 31.1 要求 libevent ≥ 2.0.21; 2.1.13 是 conan-center-index 稳定版 |
| boost | 1.84.0 | ohpcd remote 已发布; Bitcoin Core 31.1 要求 Boost ≥ 1.64.0; 1.84.0 包含 C++20 兼容修复 |

> 以上版本均为 ohpcd remote 中真实可用版本 (经 CI R37 gate 校验)。

## 4. 沙箱限制

### 4.1 HMDFS uid 映射 / 临时目录权限（已绕过：TMPDIR 指向 CI 同款路径）

- **现象**: OHOS 沙箱内 `test_bitcoin` 全量串行运行时,若 TMPDIR 指向权限受限目录 (如 build_folder 下),首个用例因 uid 映射导致临时目录 `posix_stat` Permission denied 失败,失败后全局 args 状态残留,引发后续用例 `AddArg` 断言连锁 SIGABRT。
- **规避 (2026-08-18 实证)**: `test_package/conanfile.py` 的 `test()` 将 `TMPDIR` 指向 CI 同款路径 `/data/storage/el2/base/cache` (可写且属主正确),并传入 `-- -testdatadir=<可写目录>`。
- **结果**: **全量 734 用例实跑 `*** No errors detected`** (`Running 734 test cases...` → No errors, EXIT=0),详见 round-3 CI 日志。

### 4.2 OHOS fs-verity 代码签名

- **现象**: OHOS 内核按 ELF `.codesign` fs-verity 哈希校验 exec。`cmake --install` 重写 RPATH 会使签名失效 → EPERM(126)。
- **规避**: `conanfile.py` 的 `package()` 用 `shutil.copy2` 字节级复制构建产物 (静态库/二进制/头文件),**不走 cmake --install**。
- **参考**: afdko/osmcoastline 大型 CMake 库适配经验。

### 4.3 conandata URL 镜像前缀

- **现象**: 官方版本 conandata.yml 前 6 个 URL 用镜像前缀 (gh-proxy.com/mirror.ghproxy.com/ghproxy.com/gitclone.com/moeyy.cn/kkgithub.com),官方直连排第 7。
- **修复**: URL 列表改为官方直连优先 (仅 1 条 `https://github.com/bitcoin/bitcoin/archive/refs/tags/v31.1.tar.gz`),镜像前缀由 CI 机制按需注入,不在 conandata 主 URL 手写。

## 5. 上游测试实跑策略

### 5.1 BUILD_TESTS=ON 构建 test_bitcoin

`conanfile.py` 的 `generate()` 中 `BUILD_TESTS=ON`,CMake 构建产出 `test_bitcoin` 二进制 (承载 734 个上游单元用例)。

### 5.2 test() 阶段实跑子集

`test_package/conanfile.py` 的 `test()` 中:
1. 运行消费者程序 `test_bitcoin` (验证头文件与静态库链接正确)
2. 运行主包 `bin/test_bitcoin -- -testdatadir=<可写目录>` (上游测试全量 734 用例实跑)

### 5.3 全量 734 用例实跑（2026-08-18 突破）

- 将 `TMPDIR` 指向 CI 同款路径 `/data/storage/el2/base/cache` (可写且属主正确) 后,`test_bitcoin` **全量 734 用例实跑 `*** No errors detected`** (EXIT=0),已集成进 `test_package` 的 `test()` 阶段并纳入 round-3 CI。
- 此前受 uid 映射/临时目录权限限制的 620 例环境性连锁失败已被该 TMPDIR 策略绕过,不再适用。
- **不允许伪造通过**, N/A 只能用于未运行项。

## 6. SHA-256 核实说明

- conandata.yml 声明 SHA-256: `88afbbc865f7527ebca82c197056ecc1877b6782d0fb1fe032b12f86bdd7e39e`
- 本次环境无法独立联网核实该值 (设备端无 GitHub 直连保证),保留 conandata 声明值并如实记录。
- Conan `get()` 会在下载后自动校验 sha256,若不匹配将 fail-fast。
