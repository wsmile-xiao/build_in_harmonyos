## ① PR 信息
- **三方库名称**: zeek
- **上游版本**: 8.2.1
- **上游仓库地址**: https://github.com/zeek/zeek （官方发布源: https://download.zeek.org/zeek-8.2.1.tar.gz，sha256 a8067c75cc89bef4b58019230434a90073671a7cabfcf7ac616ac872a40a2edd）
- **适配路径**: 路径 C（高难度挑战）
- **使用知识库**: OpenHarmony PC 适配 SKILL（CMake 4.x 交叉工具链、host 生成器工具链、musl 兼容性、E002/E013/E085/E222/E233 类经验）；本 PR 贡献 6 条新知识草稿 E429-E434（见 ⑥ 知识贡献）

## ② 高难度判定（四特征命中表）

| 官方四特征 | 命中 | 证据（结合实测） |
|---|---|---|
| 强绑定系统私有接口 / 无抽象层 | ✅ | OHOS musl sysroot 缺 fts(3)/libfts（E432，zeekygen fatal）；glibc 专属 API 无 POSIX 等价（E233 POLLRDHUP 等需能力探测）；broker 依赖 std::pmr 而 libc++ 15.0.4 缺 <memory_resource> 标准头（E429）；dlopen 动态加载路径（E013） |
| 私有构建工具链 | ✅ | bifcl/binpac/gen-zam 三个 host 生成器需先针对 host 平台编译、再为目标平台生成代码；交叉编译下 CMake 4.1.2 的 ALIAS 目标名展开缺陷致 Error 127（E431，$<TARGET_FILE:...> 修复） |
| 汇编 / 闭源 / 特殊调度 | ✅ | 特殊调度：auxil/spicy/3rdparty/fiber 用户态 fiber 协程库 + auxil/libkqueue 用户态 kqueue 移植层，CMake 平台检测均无 OHOS 分支，需补能力宏（补丁 0013/0015）；本库无汇编、无闭源参与 |
| 巨大依赖链 + 全量测试成本极高 | ✅ | 76 个平台兼容补丁（本批次最大补丁量）+ auxil/spicy、auxil/broker、3rdparty 三个子模块合入源码树；btest 集成套件 285 个 .test + 1824 个 .zeek 脚本，最小构建下三项技术原因无法全量离线运行（③ 逐项说明），需全量构建验收机补跑 |

## ③ 测试用例对比

### 上游库测试用例统计（申报 N，如实清点）

| 测试类型 | 上游用例数 | 说明（来源） |
|---|---|---|
| btest 集成套件（.test） | 285 | testing/btest，`find '*.test'` 实测口径（与审查方实测一致）；TestDirs 注册口径另有 2 个 .zeek 独立项（af_packet.plugin、core.pppoe-over-qinq），合计 287 |
| ctest 单元测试 | 35 | 26 broker.*（libbroker 消息层）+ 8 python-*（Python 绑定）+ 1 其它（ctest 注册口径） |
| 冒烟 | 1 | zeek --version |
| **合计** | **321** | 285 + 35 + 1；btest 的 1824 个 .zeek 为被 .test 引用的辅助脚本，不计独立用例 |

### 适配后测试用例统计（实测）

| 测试类型 | 适配后用例数 | 对比上游 | 说明 |
|---|---|---|---|
| 冒烟 zeek --version | 1/1（100%） | 持平 | 断言输出 "zeek version 8.2.1" |
| ctest broker.* 单元测试 | 26/26（100%） | 持平 | broker.backend 由可移植补丁 0003（认 TMPDIR，空回退 /tmp）+ TMPDIR=可写目录运行解决（notes.md P10 / E434）；此前 13 项 SEGFAULT 的 broker 测试全部消除（E429 pmr shim） |
| ctest python-* | 0/8（N/A） | 缩减 | 最小构建未启用 Python 绑定（构建形态取舍，逐项原因见 ③ 缩减说明） |
| btest 集成套件 | 0/285（N/A） | 缩减 | 三项技术原因见 ③ 缩减说明，待全量构建验收机补跑 |
| 鸿蒙特有测试（消费者用例 test_package，conan L1） | 4/4（100%） | 新增 | OHOS 构建二进制 OHOS 环境实跑：case1 版本断言；case2 pcap 回放三连接断言（tcp:80/tcp:443/udp:53）；case3 TLS ClientHello SNI；case4 DNS 查询 + HTTP 请求事件断言（R34 非空壳） |
| **合计** | **31** | 缩减（N/A 项不计入） | 1 + 26 + 4 = 31（python-* 8 项、btest 285 项 N/A 不计入可执行合计） |

**汇总**：可执行上游单元测试子集 26/26 = 100%；鸿蒙特有消费者测试 4/4 = 100%；冒烟 1/1 = 100%；合计 31/31 = 100%。

### 测试缩减原因（与规则2/3同源，显式说明）

- **ctest python-* 8 项**：最小构建形态未启用 Python 绑定（zeekctl/zkg/zeek-client 等工具依赖 Python 运行时，随形态关闭）——构建形态取舍，非适配缺陷。
- **btest 285 项**（harness 在本环境可启动，完整套件无法全量离线运行，逐项具体技术原因）：
  1. **最小构建加载 base 脚本失败**：`scripts/base/packet-protocols/igmp/main.zeek` 在 zeek_init 无条件 `Reporter::error("Failed to register IGMP Spicy analyzer.")`——IGMP 分析器由 Spicy 生成，DISABLE_SPICY 构建必然缺失该注册，上游脚本未对禁-Spicy 构建做条件守卫 → `zeek -b` 初始化即 fatal；
  2. **HMDFS 只读 /tmp**（E002）：btest 需在临时目录落 Baseline/输出对比，无法创建临时文件 → 多数「写临时 + diff」类型测试环境不可行；
  3. **pcap 回放类**：`-r *.pcap` 回放 + btest-diff 的测试（如 checksums.test）依赖 Baseline 目录可写 + 完整 base 脚本加载，同上受阻。
  - 判定：属**环境/构建形态限制**，非适配缺陷；完整 btest 需在「ENABLE_SPICY 全量构建 + 可写工作目录」的 CI/真机验收机上运行（⑥ TODO 如实标注）。

### 补全测试用例说明

- 上游已有完整测试体系（btest 集成 + ctest 单元），**无需补全**上游等价测试。
- 按 R34/L1 补全**鸿蒙特有消费者测试 test_package**（鸿蒙特有测试）：test.sh 4 用例实跑 OHOS 构建二进制——case1 版本断言 + case2 pcap 回放三连接（tcp:80/tcp:443/udp:53）+ case3 TLS SNI + case4 DNS/HTTP 事件断言（4/4 通过）；test.c 为 C 消费端，链接被测包断言 `zeek version 8.2.1` 输出。

## ④ 上游测试用例修改说明

- [x] **否**，上游测试用例逻辑 0 处修改（285 个 .test、1824 个 .zeek、35 项 ctest 均保持上游原样）
- [ ] 是
> 证据：仅 2 处**测试工具（harness/辅助代码）可移植修复**，均无平台宏、不触及任何测试断言：
> 1. **补丁 0012**（`auxil/btest/btest` L1525）：`subprocess.call(["rm", ...])` → `shutil.rmtree(ignore_errors=True)`。原因：OHOS 下 os.posix_spawn 的外部命令 PATH 解析失败（FileNotFoundError），btest 无法清理旧工作目录；通用可移植写法。
> 2. **补丁 0003**（`auxil/broker/libbroker/broker/detail/filesystem.cc` `make_temp_file_name` POSIX 分支）：硬编码 `/tmp` 前缀不认 `TMPDIR` → 改为读 `::getenv("TMPDIR")`（空回退 `/tmp`）+ `mkstemp`（snprintf 定长缓冲，溢出 exit(1)）。原因：HMDFS `/tmp` 只读（E002）致 `broker.backend` 失败；标准 POSIX 惯例（TMPDIR 优先），未设 TMPDIR 时与上游行为完全一致，仅使测试在只读 /tmp 环境可运行（知识 E434）。

## ⑤ 验证结果

- 编译状态: **通过**（conan create exit 0；W3 本地 CI 日志 10322 行全绿）
- 上游可运行子集通过率: **26/26（100%）**（broker.* 单元测试实测，含 broker.backend 修复后）
- 鸿蒙特有消费者用例通过率: **4/4（100%）**（test_package 消费者测试：版本断言 + pcap 回放三连接 + TLS SNI + DNS/HTTP 事件断言）
- 冒烟: `./src/zeek --version` → `zeek version 8.2.1`（exit 0）
- 全量 btest: 本环境 N/A（③ 三项技术原因），待 ENABLE_SPICY 全量构建 + 可写工作目录验收机补跑（⑥ TODO）
- 本地 CI（W3）`{exit_code: 0, step: W3_local_ci, log_sha256: d8805868674b4c7943588c93c3b4e6d0c2ec0ef651e799585ec5461004145155}`，.ci-result.json 由 finish W3 自动生成（2026-09-24 03:01 重验，覆盖 CI 第 1 轮修复后构建形态），日志哈希防伪造

## ⑥ 补充说明（难点/卡点 + 已知限制）

### ① 难点：76 个平台兼容补丁解决的关键问题（重点项 = 事实 + 解法 + 结论；逐文件明细见 8.2.1/notes.md 与 patches/）

1. **0001-0011 auxil/broker 消息层（11 补丁）— std::pmr 缺失（E429）**：broker 37 处使用 std::pmr::polymorphic_allocator/monotonic_buffer_resource，OHOS libc++ 15.0.4 无 `<memory_resource>` 标准头、experimental 头只声明未定义（13 项测试 SEGFAULT）。解法：自写 shim 头 `<memory_resource>` 经 -I 注入（复用 SDK experimental 基类 + 自实现对齐 bump-pointer monotonic_buffer_resource + 补全局资源符号）。结论：13 个曾 SEGFAULT 的 broker 测试 100% 恢复。
2. **0012 auxil/btest — posix_spawn PATH 解析失败**：OHOS os.posix_spawn 外部命令 PATH 解析 FileNotFoundError → shutil.rmtree 可移植修复。结论：btest harness 可启动。
3. **0013-0015 auxil 支撑库（libkqueue/fiber/paraglob）— 用户态调度库平台检测**：libkqueue（用户态 kqueue 移植）与 fiber（用户态协程）的 CMake 环境检测无 OHOS 分支。解法：补 CMake 能力宏检测（零平台宏，R8）；paraglob 可移植修复。结论：两库正常参与构建。
4. **0016-0020 auxil/spicy/hilti-runtime（5 补丁）— HILTI 运行时编译器兼容**：bitfield/set/vector/util/regexp 在 clang 15.0.4 + 旧 libc++ 下的 C++20 缺口修复。结论：hilti runtime 编译通过。
5. **0021-0023 cmake/{BifCl,BinPAC,Gen-ZAM}.cmake — ALIAS 目标名不展开（E431）**：CMake 4.1.2 交叉模式下 add_custom_command(COMMAND Zeek::BifCl ...) 保留 :: ALIAS 字面量 → Error 127。解法：改 `$<TARGET_FILE:...>` 生成器表达式。结论：三生成器步骤全过（无平台宏）。
6. **0024-0075 src/ 核心（52 补丁）**：逐文件可移植修复——glibc 专属 API（POLLRDHUP 等能力探测 + POSIX 等价，E233）、std::ranges 缺失算法集改写经典 STL（E430，47 文件 83+ 使用点，含 C 数组 std::begin/std::end 派生陷阱）、construct_at 聚合体初始化不支持（E433，src/script_opt CallInfo/DispatchInfo 补显式构造，对应补丁 0057-0059）、fts.h 缺失（E432，0074 zeekygen Target.cc 改 std::filesystem::recursive_directory_iterator）、pthread_cancel（E085）、backtrace（E222）等。
7. **0076 tools/systemd-generator — zeek-cluster-config.cc 可移植**：OHOS 无 systemd，生成器编译兼容修复。
8. **+2 个 shims**（shims/ 走 -I 注入与 weak 符号链入，不进 patches/）：平台符号缺口补齐（dlopen 路径 E013 等）。

补丁全集：**76 个**（原有 70 按文件路径字母序整体重排编号保全集一致 + 本地完善新增 6：broker TMPDIR（0003）+ hilti runtime 编译器兼容 ×5（0016-0020））；76 个补丁逐一 orig→apply→diff 验证与适配工作树逐字节一致；**全部 R8 合规：patches/ 无 `__OHOS__` 平台宏**（能力宏 / POSIX 接口 / weak shim 三策略）。

### ② 已知限制（主动披露）

- **构建形态（裁剪项）**：最小可行 core `DISABLE_SPICY=ON` + `DISABLE_JAVASCRIPT=ON` + `ENABLE_CLUSTER_BACKEND_ZEROMQ=OFF` + `INSTALL_ZEEKCTL=OFF` + `INSTALL_ZKG=OFF` + `INSTALL_ZEEK_CLIENT=OFF`（配方已对齐完整形态；CI 第 1 轮（2026-09-24）红根因：配方此前缺三个 INSTALL 标志，CI worker 的 HNP Python 无 Development 组件，死于 pysubnettree `find_package(Python Development)`，本次配方对齐修复——属与 DISABLE_SPICY 同构的构建形态取舍，非失败逃逸）。逐项理由：Spicy 应用层分析器路径不在本版本范围（依赖 Spicy 的 base 脚本加载 fatal，③ 第 1 条）；JavaScript 引擎随形态关闭；zeromq 集群后端关闭（broker 消息层以 libbroker.so 库形式入包）；zeekctl/zkg/zeek-client 依赖 Python 运行时（CI worker/目标环境无 Python Development 组件）关闭（对应 8 项 ctest python-* N/A）。
- **TODO**：① 全量构建（ENABLE_SPICY）+ 可写工作目录验收机补跑 btest 全量套件（285 项）；② Spicy/HILTI 工具链独立包化后开启全形态（可作后续依赖项 PR）。
- **依赖**：requires `libpcap/1.10.6`、`openssl/3.5.8.1`、`zlib/1.3.1`；tool_requires `flex/2.6.4`、`bison/3.8.2`（swig 随 zeekctl 移除：pysubnettree 为其唯一消费者；W0 预检确认均已发布制品仓）。
- **子模块策略**：auxil/spicy、auxil/broker、3rdparty 三个子模块已合并入源码树（官方 tarball 含目录别名符号链接环，cp -a 保留符号链接）；conandata.yml 指向官方发布源（R39 合规，sha256 见 conandata.yml）。
- **证据文件入库方式**：本包 5 个证据文件（audit-result.json / build-report.md / conan-verify-report.md / pr-body.md / test-report.md）以 git 跟踪状态直接入库（tracked 文件不受忽略规则影响），供 W4 审计与 R51 测试追溯。根 .gitignore 的 reports/ 例外先例块（tcping/jsonifier 等 11 包）属框架维护 PR 范畴，本 PR 不触碰 .gitignore、未改动任何忽略规则（本 PR 变更范围收敛为 archives/ + knowledge/）。
- **机械门禁说明（透明声明）**：已本地完整 dry-run preflight——PF1 单包闸 / PF2 制品闸 / PF3 测试闸 / PF4 依赖闸 / PF5 平台宏闸 / PF6 前缀闸 / PF7 源URL闸 / PF8 配方静态闸 / R52 审计交叉校验**全部绿**；唯一红项 PF9 路径闸对新包属设计性误判（实现要求所有 archives 路径 ≥5 层，而软件级 manifest.yaml/README.md/commands.json 为归档规范 §6 必备，且 main 历史 libpff/libmodi/minibwa 新包合并先例均含此三文件并过 CI）→ 按工具 HANDOFF 明示的自担通道在建 PR 时跳过该机械项复跑，以 CI 为最终仲裁（本 PR 含 80+ 个版本目录文件，无 "No packages to build" 风险）。
- **本地 W4 Pre-PR 审计**：`reports/audit-result.json` verdict=pass（P0=0/P1=0；P2×1 不阻断 = conandata patch_description 风格（code-style §12）；P3×3 均为已裁决/已披露项），独立子任务上下文隔离执行，R52 sha256 证据 108/108 与磁盘一致。本轮为 CI 第 1 轮修复后的复审（第 2 轮）：第 1 轮 P2「软件级 README/manifest 残留 swig 声明」修复后复审清零。
- **特殊特性说明（路径 C）**：① 混合语言架构：C++ 主体 + Zeek 脚本语言 + Spicy DSL（本版本 Spicy 关闭，保留 C++ 引擎 + 脚本解释器）；② 私有 host 生成器工具链（bifcl/binpac/gen-zam，见 ⑥① 难点 5）；③ 大依赖与子模块合入源码树（见 ⑥② 子模块策略）；④ 平台符号缺口补齐策略：CMake 能力宏 + weak 符号 shim + 可移植改写（零平台宏）。
- **平台适配点**：P1-P10 共 10 个平台特有点均按 现象/证据/修复 三件套实测记录于 `8.2.1/notes.md`（≥3 个，满足路径 C 要求），兼容性评估详见 `8.2.1/compatibility.md`。
- **知识贡献（6 条草稿，12 文件）**：`knowledge/drafts/` 新增 6 条（各含 .kv + .md 配套，source_pr=11976）：E429 std::pmr/<memory_resource> 缺失（shim 头 backport）、E430 std::ranges 算法集整批缺失（经典 STL 改写）、E431 CMake ALIAS 目标名不展开（$<TARGET_FILE>）、E432 fts 缺失（std::filesystem 改写）、E433 construct_at 聚合初始化（显式构造）、E434 /tmp 只读 + TMPDIR 不识别（可移植改写）。注：E430-E434 草稿编号与正式库无关主题条目撞号（社区草稿顺序取号的既成状态），promote 时由主编重编号；E429 编号空闲。
