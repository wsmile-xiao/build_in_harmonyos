# pari-seadata-big 20170418 适配笔记

## 对象与上游清点

- 上游：PARI/GP 官方数据包 `seadata-big.tar`
  （<https://pari.math.u-bordeaux.fr/pub/pari/packages/seadata-big.tar>）
- 发布日期 2017-04-18（HTTP `Last-Modified: Tue, 18 Apr 2017 17:57:30 GMT`），
  故 conan 版本取 `20170418`
- 原始归档大小 103526400 字节（98.7 MB），
  sha256 `7c4db2624808a5bbd2ba00f8b644a439f0508532efd680a247610fdd5822a5f2`
  （本地实测 = 上游 packages.html 公示值，双源一致）
- 成员清单（`tar -tf` 46 条 = 1 目录 + 45 文件）：
  `data/seadata/sea<p>.gz`（44 个，p 为 (500, 800) 区间素数：
  503, 509, 521, 523, 541, …, 787, 797）+ `data/seadata/README.big`
- 归档内**无源码、无构建系统、无测试目录**：
  `configure`/`Makefile`/`CMakeLists`/`*.c`/`tests/` 计数为 0

### 上游测试清点（先实测再回填）

| 上游测试类型 | 数量 | 依据 |
|---|---:|---|
| 单元测试 | 0 | 归档无测试源码 |
| 集成测试 | 0 | 归档无测试脚本 |
| 其他测试 | 0 | 仅数据与说明文件 |
| **合计** | **0** | |

官方 `packages.html` 说明数据由消费方 PARI/GP 使用；真实功能入口是 `gp` 的
`ellmodulareqn(p)` / `ellcard`（`gp` 是消费端解释器，不是本数据包的测试套件，
且需要 `pari/2.17.4` 与基础 `sea0` 才能跑通）。未删除、未修改、未伪造任何上游测试。

## 断点自检（开工前）

- worktree 分支 = `feat/pari-seadata-big-20170418`（与平台登记逐字符一致，未改名）
- 工作区无本包未提交改动；`archives/l/libXext/*` 的改动是**他队遗留**，未触碰
- learninglog 本库目录为空 → 按 AGENTS.md「八、当前状态（仅 provisioning 完成）」判为**新开**
- 发现上一轮遗留（仅作背景，不并入本分支）：
  - 官方仓保留 `refs/heads/feat/pari-seadata-big-20170418` @ `f78a9dcdca`（上一轮 4 个
    commit）；fork 侧同名分支已被平台随 PR 关闭自动清理（`git ls-remote fork` 无该分支）
  - PR **#9458**（closed）为上一轮尝试；最近一次 CI `#45024` 的失败原文是
    `conan create TIMED OUT after 3600s`，日志停在
    `pari-seadata-big/20170418: Downloaded 82.6MB 79% seadata-big.tar`
    ——即**单连接下载 98.7 MB 归档在 3600 s 内下不完**（该 Worker 无 `curl`，
    CI 预下载失效后回退到 conan 内置单连接下载；同一 PR 历史上 #44340/#44826 曾绿，
    说明这是 Worker 相关的不稳定失败）

## 打包方案（纯数据包范式，照 E999-draft-B37A / pari-elldata）

- `package_type = "unknown"` + `package_id(): self.info.clear()` → noarch，全平台共享一个包
- `settings` 四项全声明（L0p 要求），`configure()` 去掉 `os.version` / `compiler.cppstd`
- `build()` 只跑确定性数据验证器（与 test_package 同一脚本，`--source-root` 模式）
  → 损坏下载在 create 阶段即失败
- `package()`：`data/seadata/sea*.gz` → `share/pari/seadata/`；
  `README.big` → `share/doc/pari-seadata-big/` 与 `licenses/`
  （归档不带 COPYING，README.big 内含 GPL-2.0-or-later 声明，作为许可参考随包）
- `package_info()`：`cpp_info.libs/includedirs/libdirs/bindirs = []`、
  `resdirs = ["share"]`，导出 `PARI_SEADATA_BIG_DIR`（buildenv+runenv）与
  `user.pari-seadata-big:data_dir`（conf_info）
- 无补丁：`patches: []`（数据包零源码修改）

### source()：为什么不用裸 `get()`

本归档 98.7 MB、单一官方主机，且服务器对长连接会中途断开（本地实测单连接
8.8 MB 即 `transfer closed with 94654455 bytes remaining`）。上一轮 CI 的
超时原文（见上）印证了同一问题。同一归档的姊妹包
`archives/p/pari-seadate-big/20170418`（同 tarball、已合入 main）用**精确字节区间
并发下载**解决了它，本配方复用该已审核手法：

- 8 连接、每段 2 MiB，逐段校验收到的字节数，并对每段最多重试 3 次
- 只访问官方原始 URL；*不使用* 外部 `curl`/`wget`（L0o），只用 `urllib`
- 校验 HTTP 206 状态与完整 `Content-Range`，逐段长度精确匹配
- 拼接后整体校验 `size == 103526400` 与 sha256，**全部通过后才原子落盘**
- 2700 s 预算 + 单次 I/O 超时 ≤ 30 s；`read1()` 读取已到达数据，持续检查预算，
  避免服务器慢速滴流把 `read()` 卡在填缓冲区上
- CI 预下载把 `url` 改写成 `file://` 时仍走 Conan `get()`（完整 sha256 校验）
- 本地实测：50 段全部校验通过，98.7 MB 下载约 1 分钟（对比上一轮 3600 s 只到 79%）

### source() 加固（依据 PR #11663 的 4 轮 CI 真实失败）

CI 恢复后本 PR 连跑 4 轮全部红，失败原文（`conan create` 内 `source()`）：

| 轮次 | 构建 | Worker | 失败原文 | 耗时 |
|------|------|--------|----------|------|
| 1 | #54298 | CI-030 | `OSError: Failed byte range 18874368-20971519 after 3 attempts` | 211 s |
| 2 | #54358 | CI-030 | `OSError: Failed byte range 14680064-16777215 after 3 attempts` | 143 s |
| 3 | #54430 | CI-029 | `OSError: Failed byte range 6291456-8388607 after 3 attempts` | 38 s |
| 4 | #54586 | CI-030 | `OSError: Failed byte range 10485760-12582911 after 3 attempts` | 84 s |

另有一个共同点：4 轮日志里 CI 预下载都是
`[fail] [Errno 2] No such file or directory: 'curl'` —— 这些 Worker **没有 curl**，
`ci/conan/build_and_test.sh` 的预下载能力一直失效，所以必须靠配方自己下载。

诊断与修法：

1. **失败的分段每轮都不同**，且段 0 从未失败 ⇒ Range 本身可用，失败是**瞬时的**
   （连接被重置 / 读超时），不是"服务器不支持 Range"。
2. 原实现的致命点：**任一段 3 次尝试用尽就 `stopped.set()` 中止整个构建** ——
   50 段里只要有一段落难就全盘皆输，在抖动网络上几乎必然失败。
3. 修法（commit `63a16afa7a`）：
   - 单段失败**不再中止构建**，改为收集失败段，**多轮补齐**（`_PART_ROUNDS = 5`，
     每轮只重试仍缺失的段，轮间退避），每段合计 15 次机会
   - 单次连接读超时 **30 s → 120 s**（原先慢速滴流会触发 socket 超时误判失败）
   - 预算耗尽用独立的 `_DownloadBudgetExhausted` 抛出，与"可重试的 socket 超时"
     区分开（`TimeoutError`/`socket.timeout` 属 `OSError`，仍走重试路径）
   - 失败原因写入异常文本（原来只报 "after 3 attempts"，丢掉了根因）
   - 修完本地复跑：`conan create` rc=0，`build()` 7/7 + `test_package` 7/7

### source() 二次加固：断点续传（依据 build #60055 的真实失败）

CI 平台恢复后，本 PR 的 build **#60055**（worker CI-019）跑满 **2712 s** 后失败，
原文（说明多轮补齐已生效、但不够）：

```
Range pass 1: 37 range(s) still missing (e.g. OSError('truncated range (495865 != 2097152)'))
...
_DownloadBudgetExhausted: PARI download budget exhausted during a byte range transfer
elapsedTime=2712.607838
```

诊断：worker 的出口**在传输中途切断连接**（2 MiB 的分片只收到 ~0.5 MiB 就被砍），
而当时的实现"分片没收满就整段丢弃、下次从 0 重来" ⇒ 已收到的字节全废，
45 分钟只完成约 22/50 段。修法（本 commit）：

- **分片级断点续传**：保留已收字节，下次用 `Range: bytes=<start+have>-<end>` 从断点继续，
  进度单调累积，不再因中途截断而清零
- 段数上限提到 8 轮、总预算 2700 s → 3000 s（仍低于 CI 的 3600 s conan create 预算）
- 进度日志改为"已下 X MiB / 共 Y MiB + 未完成段数 + 样例错误"，便于从 CI 日志直接读数

**验证（本地截断服务器，`_work/resume_test.py` 留档）**：起一个把**每个响应都截断在
300 KiB** 的本地 HTTP 服务，向配方下载器喂 8 MiB 随机数据 —— 32 次请求后完整下完且
sha256 一致（`RESUME TEST: PASS`），证明"中途截断 → 断点续传"路径成立。
本地 `conan create` 仍 rc=0（build 7/7 + test_package 7/7）。

## R34 测试豁免口径（数据包无 API 可调用）

数据包无库、无头文件、无可执行文件 → 常规"编译 consumer 调 API"形态不适用，
验证以数据完整性为准。`test_package/verify_seadata_big.py` 对**被测包的真实内容**
做 7 条断言（build 阶段 source 模式 + test 阶段 package 模式各跑一遍）：

| # | 断言层 | 内容 |
|---|--------|------|
| 1 | 结构完整性 | source：`data/seadata/` 恰好 44 个 `sea*.gz` + `README.big`；package：`share/pari/seadata/` 恰好 44 个 `sea*.gz` |
| 2 | pin 表覆盖 | 内嵌哈希表覆盖全部 44 个数据文件 |
| 3 | 非空 | 无 0 字节数据文件 |
| 4 | 载荷同一性 | 44 个文件逐一匹配官方 20170418 载荷 sha256 |
| 5 | 流完整性 | 44 个文件全部可完整解压（gzip CRC/trailer 校验通过） |
| 6 | 内容健全性 | `sea503.gz` 解压后是已知的 p=503 Atkin 记录（`[503, "A", [1, [-1, 7439,`） |
| 7 | 文档健全性 | `README.big` 记载 ECHIDNA/Kohel、`500 < p < 800`、`ellcard` |

pin 表由**已校验的官方归档**实算生成（`test_package/hashes_seadata_big.py`），
`export_sources()` 同步携带验证脚本与它 import 的哈希表模块。

**故障注入反向验证**（证明非空壳）：

| 注入 | 期望 | 实测 |
|------|------|------|
| 截断 `sea521.gz`（1000 字节） | exit 1 | `rc=1`，`sea521.gz: sha256 mismatch` |
| 删除 `sea797.gz` | exit 1 | `rc=1`，`found 43 entries` |

## 复现

```sh
conan create archives/p/pari-seadata-big/20170418 \
  -pr:h=ci/conan/profiles/ohos-aarch64 \
  -pr:b=ci/conan/profiles/ohos-aarch64 \
  --build=missing
```

实测（本机 = OpenHarmony PC aarch64，Conan 2.29.1）：

```
source(): 50/50 段校验通过 → 大小 103526400 + sha256 匹配
build()  (source 模式): 7/7 断言 PASS
package(): Packaged 44 '.gz' files + 2 '.big' files（doc/license 各一份）
package_id: da39a3ee5e6b4b0d3255bfef95601890afd80709（noarch 空 id）
test()   (package 模式): 7/7 断言 PASS
conan create rc=0；产物 99 MB（share/pari/seadata/sea503.gz .. sea797.gz）
```

## 消费前提与边界

- 本包是**增补数据**：PARI 的 `seadata_cache()` 会先加载 `<datadir>/seadata/sea0`
  （基础 `sea0` 来自 `pari-seadata` / 官方 `seadata-small.tgz`，本归档不含）。
  缺少 sea0 时即使 `sea503.gz` 存在，`ellmodulareqn(503)` 仍会报文件缺失。
- 数据本身架构无关（noarch），无 `__OHOS__` 分支、无补丁；OHOS 侧无平台代码可改。
- 未上传制品仓（`status: built`），最终以官方 CI 复核为准。
