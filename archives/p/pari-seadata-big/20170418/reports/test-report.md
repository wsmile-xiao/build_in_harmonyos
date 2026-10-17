# pari-seadata-big 20170418 — 测试报告

## 一、被测对象与来源

| 项 | 值 |
|----|----|
| 软件 / 版本 | `pari-seadata-big` / `20170418` |
| 上游归档 | `https://pari.math.u-bordeaux.fr/pub/pari/packages/seadata-big.tar` |
| 归档 sha256 | `7c4db2624808a5bbd2ba00f8b644a439f0508532efd680a247610fdd5822a5f2` |
| 归档大小 / 发布日期 | 103526400 字节 / 2017-04-18 |
| 归档成员 | 44 × `data/seadata/sea<p>.gz`（p ∈ (500, 800) 素数）+ `data/seadata/README.big` |
| 构建系统 | 无（纯数据包） |

## 二、上游测试清点（实测，非推测）

清点方式：`tar -tf seadata-big.tar` 全量枚举 + 归档内检索构建/测试文件。

| 上游测试类型 | 数量 | 依据 |
|---|---:|---|
| 单元测试 | 0 | 归档无测试源码，无 `tests/` / `*.c` / `*.gp` |
| 集成测试 | 0 | 归档无测试脚本；无 `configure` / `Makefile` / `CMakeLists.txt` |
| 其他测试 | 0 | 归档仅含数据文件与说明文件 |
| **合计** | **0** | |

上游声明（`README.big` / `packages.html`）：数据由消费方 PARI/GP 的
`ellcard` / `ellmodulareqn` 使用。`gp` 解释器**不是**本数据包的测试套件，
且不在 `test_package` 依赖内（会引入完整 PARI/GMP 依赖树），故
`upstream_scenarios_executed = 0`，豁免理由见 `test_package/MANIFEST.yml`。

## 三、适配后测试设计（R34 数据包豁免）

数据包无库、无头文件、无二进制，无可调用 API → 验证以**数据完整性**为准。
`test_package/verify_seadata_big.py` 对被测包真实内容做 7 条断言，在
`build()`（source 模式）与 `test()`（package 模式）各执行一遍。

| # | 断言 | 拦截能力 |
|---|------|----------|
| 1 | 文件集合精确匹配（source：44 `sea*.gz` + `README.big`；package：44 `sea*.gz`） | 缺失 / 多余文件 |
| 2 | 内嵌 pin 哈希表覆盖全部 44 个数据文件 | pin 表不完整 |
| 3 | 无 0 字节数据文件 | 空文件 |
| 4 | 44 个文件逐一对上官方 20170418 载荷 sha256 | 截断 / 损坏 / 替换 / 重新压缩 |
| 5 | 44 个文件 gzip 全量解压（CRC/trailer 校验） | 位翻转、CRC 错误 |
| 6 | `sea503.gz` 解压后是已知 p=503 Atkin 记录 `[503, "A", [1, [-1, 7439,` | 内容错位 |
| 7 | `README.big` 记载 ECHIDNA/Kohel、`500 < p < 800`、`ellcard` | 文档缺失 |

pin 表由**已校验的官方归档**实算生成，测试运行时不从待测包反推期望值。

## 四、实测结果

环境：本机 = OpenHarmony PC（aarch64），Conan 2.29.1，
profile `ci/conan/profiles/ohos-aarch64`（host=build=OHOS/armv8/clang 15）。

```
$ conan create archives/p/pari-seadata-big/20170418 \
      -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 \
      --build=missing
...
pari-seadata-big/20170418: Downloading the official seadata-big archive with 8 parallel byte ranges (45-minute budget)
pari-seadata-big/20170418: Verified byte ranges: 50/50
pari-seadata-big/20170418: Calling build()
[PASS 01] data directory holds exactly the 44 sea*.gz files plus README.big (found 45 entries)
[PASS 02] pinned payload hash table covers all 44 data files
[PASS 03] no packaged data file is empty
[PASS 04] all 44 data files match the official 20170418 payload sha256 (first failures: [])
[PASS 05] all 44 data files decompress completely (first failures: [])
[PASS 06] sea503.gz decompresses to the known p=503 Atkin polynomial record (b'[503, "A", [1, [-1, 7439')
[PASS 07] README.big documents the Atkin polynomials for 500 < p < 800 used by ellcard
pari-seadata-big: 7/7 data-integrity assertions passed
pari-seadata-big/20170418: Calling package()
pari-seadata-big/20170418: package(): Packaged 44 '.gz' files
pari-seadata-big/20170418: package(): Packaged 2 '.big' files: README.big, README.big
pari-seadata-big/20170418 (test package): Running test()
[PASS 01..07] package 模式 7/7 通过
rc=0
```

| 统计项 | 结果 |
|--------|------|
| `conan create` 退出码 | **0** |
| build()（source 模式） | **7/7 PASS** |
| test_package（package 模式） | **7/7 PASS** |
| package_id | `da39a3ee5e6b4b0d3255bfef95601890afd80709`（noarch 空 id） |
| 打包产物 | `share/pari/seadata/sea503.gz .. sea797.gz`（44）+ `share/doc/pari-seadata-big/README.big` + `licenses/README.big`，99 MB |

### 故障注入反向验证（证明测试非空壳）

| 注入 | 期望 | 实测 |
|------|------|------|
| 截断 `sea521.gz` 到 1000 字节 | exit 1 | `rc=1`，`all 44 data files match ... first failures: ['sea521.gz: sha256 mismatch']` |
| 删除 `sea797.gz` | exit 1 | `rc=1`，`share/pari/seadata holds exactly the 44 sea*.gz data files (found 43 entries)` |

### 源下载健壮性（针对 CI 已知失败模式）

`source()` 对官方 HTTPS 源使用精确字节区间并发下载（8 连接 / 每段 2 MiB /
单段 3 次尝试 / 5 轮补齐缺失段 / 预算 2700 s / 单次读超时 120 s），逐段校验
HTTP 206 + `Content-Range` + 段长，拼接后整体校验 `size` 与 sha256，全部通过才
原子落盘；CI 预下载（`file://`）路径仍走 Conan `get()` 完整校验。

依据：#11663 的 4 轮 CI 红均因 `Failed byte range … after 3 attempts`（失败段每轮
不同、段 0 从未失败 ⇒ 抖动网络下的瞬时失败），且这些 Worker 无 `curl`（CI 预下载
持续失效）。因此单段失败不再中止构建，改为多轮补齐；本机实测 50/50 段通过。

## 五、结论与边界

- 上游测试合计 0（实测）；无删除、无修改、无伪造。
- 新增消费者测试 7 条断言，source 与 package 双端各 7/7 通过；故障注入可拦截。
- 数据为架构无关资源，无补丁、无平台代码；最终以官方 CI（`conan-build-test`）复核为准。
- 本包是**增补数据**：消费方仍需基础 `sea0`（`pari-seadata` / `seadata-small`）。
