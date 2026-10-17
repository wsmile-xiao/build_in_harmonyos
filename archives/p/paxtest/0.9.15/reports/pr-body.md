## PR 信息

- **三方库名称**：paxtest
- **上游版本**：0.9.15
- **上游仓库地址**：https://github.com/opensrcsec/paxtest
- **适配路径**：路径 A（基础适配）+ 路径 B（贡献创新，见「路径 B 知识贡献说明」）
- **使用知识库**：常规 make/补丁流程无直接技能命中；知识库对照使用 E045（W^X）与 `DRAFT-boxfort-ohos-code-page-integrity`（代码页完整性 XPM，用于路径 B 草稿的边界划分）；本 PR 新增知识草稿 `knowledge/drafts/E546-draft-9C4A-paxtest-ohos-memory-protection-probing.{kv,md}`
- **关联 Issue**：[#3523](https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos/issues/3523)（与本 PR 双向关联）

---

## 测试用例对比

### 上游库测试用例统计

| 测试类型 | 上游用例数 | 说明 |
|----------|-----------|------|
| 攻击探测（exec/mprot/writetext） | 15 | paxtest 套件本体：execstack 族 5 + mprotect 变体 5 + 共享库 bss/data 2 + 共享库 mprotect 2 + writetext 1 |
| 随机化测量（randbody） | 13 | 每项 1500 次采样（anon/heap×2/main×2/shlib/vdso/stack×2/argv-env×2/shlibdelta×2） |
| 随机化测量（fastrandbody） | 2 | 内存耗尽场景，每项 25 次 |
| 返回攻击（RET/RETX） | 4 | rettofunc strcpy/memcpy 及 PIE 变体 |
| **合计** | **34** | 上游即安全回归套件本体，无独立断言框架；通过 = 运行成功并给出结果 |

### 适配后测试用例统计

| 测试类型 | 适配后用例数 | 与上游对比 | 说明 |
|----------|-------------|-----------|------|
| 真机实跑并给出结果 | 31 | — | 攻击探测 15 + 随机化 12 + fast-rand 2 + rettofunc strcpy 2（kiddie 与 blackhat 各一轮，driver rc=0） |
| 语义性无输出（aarch64） | 2 | — | rettofunc memcpy / memcpy PIE：返回地址在 x30 而非栈帧，未劫持控制流（如实记录） |
| 平台差异中止 | 1 | — | VDSO randomization：OHOS `/proc/self/maps` 无 `[vdso]` 条目（如实记录） |
| **鸿蒙特有测试** | **21** | 新增 | `test_package/` 消费者断言（`conan create` 内真实执行；含负向对照） |
| **合计** | **55** | | |

## 上游测试用例修改说明

### 是否存在对上游测试用例的修改？

- [x] **否**，未修改上游任何测试用例
- [ ] **是**，存在对上游测试用例的修改（请在下方逐条说明）

> 说明：34 个测试程序与驱动 `genpaxtest` 的判定逻辑、断言与通过口径均未改动。唯一的测试相关补丁是
> `patches/0005-shellcode.h.patch`——为 aarch64 增加 `__aarch64__` 分支（ARM64 `ret`，0xd65f03c0）：
> 它补的是「目标架构最小运行序列」（缺少时 exec 系探针无正判定力，可执行/不可执行内存都表现为
> Killed），**不是为通过而修改判定**；chpax 的 a.out 支持移除（0001–0004）属构建期 portability。

## 补全测试用例说明

### 上游是否存在无测试用例，适配后补全的情况？

- [ ] **否**，上游已有测试用例覆盖
- [x] **是**，上游无断言式测试框架，适配后补全了消费者测试（请在下方说明）

> - **补全的测试范围**：新增 `test_package/`（21 条断言）——包结构与 34 个测试程序可执行；
>   execstack/anonmap/mprotstack/writetext 探测真实执行且显式拒绝 `Vulnerable`；getamap/getstack1
>   地址输出；randexhaust1 随机化质量行；驱动无参数负向对照。
> - **补全原因**：上游测试面是"可执行测试程序本体"，无 Conan 消费者视角的安装后回归；补 `test_package`
>   覆盖真实包产物（CI L1e 破坏性负向验证通过，证明测试实质依赖被测包）。
> - **新增测试文件清单**：
>   1. `archives/p/paxtest/0.9.15/test_package/conanfile.py`
>   2. `archives/p/paxtest/0.9.15/test_package/test_paxtest.sh`
>   3. `archives/p/paxtest/0.9.15/test_package/MANIFEST.yml`

## 验证结果

- 编译状态：通过（`conan create` EXIT=0，profile `ohos-aarch64-device`）
- 上游测试用例通过率：31/31 可判定项（100%；kiddie 与 blackhat 两轮 driver rc=0）；另有 2 项按
  aarch64 语义正常退出无输出（rettofunc memcpy / memcpy PIE）、1 项因平台差异中止（VDSO
  randomization）——逐项原因见 `reports/test-report.md`，非静默跳过
- 新增测试用例通过率：21/21（100%）

## 路径 B 知识贡献说明

- **新增草稿**（与归档适配同一原子 PR 交付）：
  - `knowledge/drafts/E546-draft-9C4A-paxtest-ohos-memory-protection-probing.kv`
  - `knowledge/drafts/E546-draft-9C4A-paxtest-ohos-memory-protection-probing.md`
- **知识主题**：OHOS 内核内存保护/ASLR 的探针测量与解读口径（含非 x86 探针适配）——先补目标架构
  最小 shellcode 恢复判定力，再按"内存类别×操作"矩阵实测，按"不可利用≠保护存在"口径解读并列明判定盲区。
- **触发实例**：paxtest 0.9.15 适配——修复前 exec 系 15 项因上游 `shellcode.h` 无 aarch64 分支而
  "一律 Killed"（盲判，与保护生效不可区分）；补 ARM64 `ret` 后恢复正反判定，得到完整探测矩阵与
  ASLR 质量数据（15/15 Killed；12 项 19–23 bits；VDSO 不可测）。
- **新增价值（查重结论）**：`knowledge/graph/index.tsv`（KC 口径 542 条）+ `knowledge/drafts/`
  （4183 文件）全量实查：`paxtest`/`shellcode`/`exec stack` **0 命中**；邻近条目 E045（W^X 事实）、
  `DRAFT-boxfort-ohos-code-page-integrity`（XPM 路径枚举）、`DRAFT-gas-arm64-clang-integrated-as`
  （匿名 `PROT_EXEC` 可用）、`DRAFT-libffcall-2.5-trampoline-exec-page`（构建期绕行）——均无
  「系统性探针测量 + 解读口径 + 判定盲区清单」；`draft-review` 预审（命令
  `python3 scripts/ohc-run.py draft-review E546-draft-9C4A-paxtest-ohos-memory-protection-probing`）输出建议 **create**（最高相似 E045=0.19，
  低于合并阈值）。
- **验证证据**：`reports/device-kiddie.log`、`reports/device-blackhat.log`（driver rc=0）、
  `reports/test-report.md` §4/§5、`patches/0005-shellcode.h.patch`、test_package 21/21 断言。
- **知识库扩展 Issue**：[#3523](https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos/issues/3523)
  （分支 `feat/paxtest-0.9.15`）。

## 补充说明

### 构建环境

- HarmonyOS PC 真机（aarch64），OHOS SDK clang 15.0.4，GNU make 4.4.1，Conan 2.29.1（OHOS 适配版），
  profile `ohos-aarch64-device`
- 上游源码（官方 GitHub tag 归档端点）：`https://codeload.github.com/opensrcsec/paxtest/tar.gz/refs/tags/paxtest-0.9.15`；
  SHA256 `51fe6c1eef8050fa73f2a8e620cf70a5a34a79d68cb22d07b941cf8e6c0677e7`（与 Debian orig 解包内容
  逐文件一致，仅 gzip 封装差异；上游官网 pax.grsecurity.net 仅列到 0.9.7-pre4，0.9.15 的官方发布位于该 tag）

### 验证命令

```bash
conan create archives/p/paxtest/0.9.15 -pr:h=ohos-aarch64-device -pr:b=ohos-aarch64-device \
  --build=missing --user=ohpcd --channel=stable          # test_package 21/21
cd <pkg>/bin/paxtest && ./paxtest kiddie  "$LOG.kiddie"  # driver rc=0
cd <pkg>/bin/paxtest && ./paxtest blackhat "$LOG.blackhat" # driver rc=0
zsh ci/conan/build_and_test.sh archives/p/paxtest/0.9.15 # L0/L1/L1e/L4/L5 PASS
```

### 配方要点

- `build()` 直调 `make -j1 -f Makefile.psm CC=<Conf c> LD=<Conf ld | "ld">`（R33：编译器取 Conan conf；
  上游 Makefile.psm 硬编码 `CC=gcc` / `LD=ld`）
- `package()` 将完整运行目录安装到 `bin/paxtest/`（34 测试程序 + 15 helper + shlibs + C 源码与
  Makefile，便于重建）；软件级 `commands.json` 按 R38 声明工具包
- 5 个 portability 补丁：0001–0004（chpax 移除 a.out 支持——musl 系 sysroot 无 `<a.out.h>`）、
  0005（shellcode.h 补 aarch64 分支）

### 合并冲突处理（2026-10-04）

- 本 PR 曾与 `main` 发生 **add/add** 冲突：`knowledge/drafts/E545-draft-9C4A.{kv,md}` 与另一并行
  任务的同编号草稿重名。处理：保留 main 中先合并的版本；本任务草稿改名为
  `knowledge/drafts/E546-draft-9C4A-paxtest-ohos-memory-protection-probing.{kv,md}`（带任务 slug
  以防再次撞名；kv 的 `id:` 与 `doc_file:` 已同步），`draft-review` 复跑仍为建议 create。
- 已合并 `origin/main` 后无其它冲突；本地 CI 与 W4 审计在合并后复跑通过。

### 已知限制与未执行项

| 未执行项 | 技术原因 |
|----------|----------|
| VDSO randomization | OHOS `/proc/self/maps` 无 `[vdso]` 条目 → getvdso 无输出 → randbody 中止该行（如实记录） |
| rettofunc memcpy / memcpy PIE | aarch64 返回地址在 x30 寄存器而非栈帧，256B 栈溢出未劫持控制流（体系结构语义） |
| blackhat 对抗语义 | clang 无嵌套函数 → 按上游 `#ifdef __clang__` 回落 kiddie 语义（上游实现限制） |

### 产物验证

| 产物 | 类型 | 验证方式 |
|------|------|----------|
| `bin/paxtest/{34 个测试程序}` | 可执行 | 真机 kiddie/blackhat 全量两轮 driver rc=0（15/15 Killed、随机化 12 项 19–23 bits） |
| `bin/paxtest/{chpax,paxbin,15 helper}` | 可执行 | 包内携带并随套件运行；chpax 在 OHOS 上为惰性工具（内核无 PaX 标志可设） |
| `licenses/COPYING` | 许可 | GPL-2.0-or-later 随包安装 |
