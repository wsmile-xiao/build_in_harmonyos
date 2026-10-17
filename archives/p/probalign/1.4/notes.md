# probalign 1.4 适配记录

- Conan 参考：`probalign/1.4`
- 分支：`feat/probalign-1.4`
- 工作树：`/storage/Users/currentUser/qzy/主理-33-probalign-1.4`（B 机 / HarmonyOS PC aarch64）
- 目标平台：HarmonyOS PC AArch64（musl，clang 15，`aarch64-linux-ohos`）
- 上游主页：<https://web.njit.edu/~usman/probalign/>
- 许可证：Public-Domain（上游 README 自述 "made freely available as PUBLIC DOMAIN software"，仓库内无 LICENSE 文件，故把载有该声明的 README 一并安装到 `licenses/`）

## 软件与构建系统画像

probalign 用 profile HMM 的后验概率解码对多条蛋白质或核酸序列做比对，输出 MFA 或
CLUSTAL W 版式。上游 1.4（2010-11）发布形态是一个 30060 字节的 tarball，解包 14 个文件
（`Main.cc` `PostProbs.cc` `ComputeAlignment.cc` `ReadMatrix.cc` + 7 个头 + Makefile + README +
RELEASE_NOTES），共 5022 行，**零第三方依赖**，构建系统是**裸 Makefile**（11 行，只有
`all`(L5)、`probalign`(L7)、`clean`(L10) 三条规则）。

Makefile 实测信号（逐字开档复核，与 SCT 台账一致）：

| 信号 | 实测 |
|---|---|
| 烧死系统路径 | False |
| `PREFIX` 变量 | False（**没有 install 目标**，安装步骤由配方承担） |
| `install` 目标 | False |
| `-Werror` | False |
| `TESTS` / `check` 目标 | False（**上游 0 测试**） |
| 硬编码编译器 | `CXX = g++`（目标机不存在 g++） |
| 链接行 | `-lm` 写在源文件**之前**（老式写法） |

## 症状与根因

### 1. `CXX = g++` 在目标机上不存在

**症状**：直接 `make` 会以 `g++: not found` 起步。

**根因**：上游 Makefile 用简单赋值把编译器钉在 g++ 上；HarmonyOS PC 的工具链只有
clang 15（`/data/service/hnp/bin/clang++`），没有 g++。

**最终方案**：`make -j1 CXX="<conan clang++>"`。make 的命令行变量定义优先级高于
Makefile 内的普通赋值（非 `override`），因此**不必给上游打补丁**即可注入工具链，
上游 `-O3 -W -Wall -funroll-loops` 原样保留。

编译器取自 Conan 的 `tools.build:compiler_executables`（R33：不得依赖 `${CXX}`
这类 shell 变量，CI worker 上为空）。

### 2. 上游链接行 `-lm` 位于目标文件之前

**症状（预期）**：现代 lld 按左到右顺序解析，`-lm` 前置通常导致 `undefined symbol: log/exp`。

**实测结论**：**没有发生**。clang 15 + lld 直接吃下上游原样的链接行并链接成功，
因此**不打无谓的补丁**。已试过的失败方案（见下）先于验证被放弃，未落地为改动。

### 3. 包内 ELF 在真机上不可执行

**症状**：`conan create` 走到 test_package 时报
`PermissionError: [Errno 13] Permission denied: .../p/bin/probalign`，
即便文件 mode 已是 0755。

**根因**：HarmonyOS 内核拒绝加载没有有效 `.codesign` 数据的 ELF，Conan 包缓存目录
里的可执行文件同样受此约束。单纯 `chmod 755` 无用。

**最终方案**：`package()` 内对最终产物自签——`llvm-objcopy --remove-section .codesign`
清掉陈旧签名段，再 `binary-sign-tool sign -selfSign 1` 输出到临时文件，确认产物存在后
`os.replace()` 原子换回，最后重设执行位（签名工具会改写文件）。签名工具路径按
`user.ohos:sign_tool` → `OHOS_SIGN_TOOL` → PATH → worker 约定路径回退；非 OHOS 目标
跳过。**签名必须发生在 test_package 消费之前**，这是"构建成功"与"交付可执行"的分界线。

（本节机理复用同仓已合并先例 `archives/c/cronutils/1.1` 及其
`knowledge/DRAFT-cronutils-1.1-raw-makefile-ohos-cli-signing.md`，非本次新发现。）

### 4. 构建目录与源码目录的关系

**症状**：裸 Makefile 在源目录内 `.o` 与产物，Conan 默认 layout 会把 build 目录
另指一处，导致 `make` 找不到源文件、`package()` 找不到产物。

**最终方案**：`basic_layout(self)` 之后把 `self.folders.build = "."`，让源/构建同目录，
与上游 Makefile 的隐含假设一致。

## 已试过的失败方案

1. **`init-build` 首跑失败**（本轮实拍，非 probalign 本身的问题）：
   `scripts/ohc-run.py init-build` 以 RC=1 崩在 `scripts/ohc/check_env.py`。
   最小复现：把 `/storage/Users/currentUser/usr/local/bin` 放进 PATH，然后
   `python3 -c "import shutil,subprocess; p=shutil.which('automake'); subprocess.run([p,'--version'])"`。
   根因链：该目录下 `automake` 的 shebang 是 `#!/storage/Users/currentUser/usr/local/bin/perl`，
   而那个 perl **不存在**（设备上 perl 在 `/data/service/hnp/bin/perl`）⇒ exec 抛
   `FileNotFoundError` ⇒ 落入 `check_env._check_cmd` 的 `except Exception: return False, str(e)`，
   而 `e` 未定义 ⇒ `NameError` 直接掀掉整个 init-build。
   处置：**不改框架代码**，改为只把私有目录 `~/tmp/ch/z33-bin`（内仅一枚 `nice` 符号链接）
   放进 PATH。副作用是 `check_env` 报 `cc/c++ 未找到` 的告警，属环境事实不是配方缺陷。
   这条属框架侧潜伏 bug（任何 `~/usr/local/bin` 在 PATH 上的窗口都会撞），
   已按"不改 `scripts/`"红线留在盘上证据里，交主代理定夺是否单独提框架 Issue。
2. **`conan-init` 猜成 autotools**：模板生成的 `configure_args`/`AutotoolsToolchain`/
   `cpp_info.libs=["probalign"]` 对一个无 configure 的 CLI 全部不适用，按
   `conanfile-makefile.py.tmpl` 的口径重写为 `package_type="application"`、
   直接 `make`、`bindirs=["bin"]`、无 `libs`。
3. **`-h` / `--help` / 长选项路线**（设想用来做 usage 断言）：实测上游**没有** help，
   `probalign -h` 报 `ERROR: Unrecognized option: -h` 且 RC=1，长选项一律不识别。
   故 usage 断言不成立，改为断言"长选项被拒且非零退出"这一真实契约。
4. **G1 配方完整性首跑 FAIL**（RC=2）：`conan-verify` 的 G1 要求 `export_sources()`
   与"补丁应用调用"两项存在，而本包**上游零补丁**，首稿因此被拦。
   证据：`archives/p/probalign/1.4/reports/conan-verify-report.md`
   （`❌ conanfile.py 缺少: export_sources() 方法` / `❌ conanfile.py 缺少: 补丁应用调用`）。
   处置：补 `export_conandata_patches(self)` + `apply_conandata_patches(self)` 这对挂钩
   （`conandata.yml` 的 `patches: {}` 使其今天是空操作），而不是给包塞假补丁来"喂"门禁。
5. **W3 首跑被 L1e 判为假测试**（`finish` RC=2）——本轮最值钱的一条，见下节独立分析。
   判决行原文（`reports/w3-local-ci.log`）：

   ```text
   [ok] probalign/1.4 — conan create passed
   [ok] L1a: test_package was executed by conan create
   [ok] L1b: Test execution evidence found in log
   [step] L1e: Destructive negative test (R34)...
           [sabotage] bin/ moved away
   [fail] L1e: test passed WITHOUT package artifacts — fake test detected (R34)
   L0_RESULT=pass: all checks passed
   L1_RESULT=fail: negative test: test does not depend on package
   L2_RESULT=skip: probalign version/help failed
   [fail] probalign/1.4 — L1 official test failed
   ```

   注意其自相矛盾的形态：**同一份日志里 conan create 真的跑过 29/29 断言
   （`reports/conan-create.log` 第 206 行 `PASS: probalign packaged consumer test
   (29/29 assertions)`），L1a/L1b 也因此为绿**，但破坏性反向验证却说"测试不依赖被测包"。
   这不是配方写错，而是**首稿 `test()` 里的 `can_run()` 护栏在 L1e 的调用方式下必然为假**：

   - L1e 重跑测试用的是 `conan test <test_package> <ref> -pr <host-profile>`，**只给 host profile**；
   - 此时 conan 的 build profile 回落到 CONAN_HOME 里的 `profiles/default`，
     而那份 default 是 `os=Linux / compiler.libcxx=libstdc++11`；
   - host=OHOS vs build=Linux ⇒ conan 判定为交叉构建 ⇒ `can_run()` 返回 False
     ⇒ 首稿 `if not can_run(self): return` **静默返回 0**
     ⇒ `conan test` 退出码 0 ⇒ L1e 得出"产物被搬走测试还能过 = 假测试"。

   最小复现（B 机，逐字可跑）：

   ```bash
   conan test archives/p/probalign/1.4/test_package "probalign/1.4@ohpcd/stable" \
       -pr ci/conan/profiles/ohos-aarch64 --build=missing
   # → 第 63 行：probalign consumer test skipped: target cannot run here   RC=0
   conan test ... -pr ci/conan/profiles/ohos-aarch64 -pr:b ci/conan/profiles/ohos-aarch64
   # → 第 100 行：PASS: probalign packaged consumer test (29/29 assertions) RC=0
   ```

   两行只差一个 `-pr:b`，一个静默跳过、一个真跑 29 条——这就是假绿的入口。

   **最终方案**：删掉 `can_run()` 护栏，`test()` 无条件执行消费者脚本。
   依据：本包是 `package_type="application"`，唯一可消费产物就是 `bin/probalign`；
   "跑不了"对 CLI 包而言是**失败**而不是**跳过**。修后本地按 L1e 的口径做破坏性复现
   （搬走包缓存里的 `bin/` 再 `conan test`）：`NEGATIVE_RC=1`，
   脚本报 `FAIL: probalign is missing from .../bin`，产物随后原样恢复。
   证据：`/storage/Users/currentUser/tmp/uc2/z33-probalign/l1e-negative.log`。
   （护栏写法来自仓内先例 `archives/c/cronutils/1.1/test_package/conanfile.py`，
   同一段 `if not can_run(self): return` 放在任何 CLI 包上都同样地静默绕过 L1e。）

## 消费者测试（赛道二）

上游 0 测试，故测试强度全部落在 `test_package`，且必须是**真比对**而非文件存在性检查。
`test_probalign.py` 以使用者身份运行安装后的签名二进制，喂入蛋白质与核酸各 3 条序列，
断言 **29 项**：

- 产物维度：包内 `probalign` 是 ELF 且带执行位（2 项，只是入场券，不作为通过依据）；
- 行为维度：
  - 默认参数下的比对结果**逐字命中**在目标机上采集的 golden（含 `Alignment tree: ((s1 s2) s3)`）；
  - 比对矩阵**等宽**（矩形性）；
  - **去 gap 后逐条还原**输入序列——这一条把"输出里确实做了插入/删除推断"钉死；
  - 两次运行**逐字节一致**（后验解码不抽样，故可锁 golden）；
  - 改 `-T 1 -go 8 -ge 0.5` 后 s3 的 indel **确实换列**，且换列后仍能还原输入
    （证明 gap 位置是被计算出来的，不是字符串补白）；
  - `-clustalw` 整段输出命中 CLUSTAL W golden，序列行与 MFA 行一致，conservation 标记行存在；
  - `-nuc` 命中核酸 golden 同样三性质；`-prot`、`-a`、`-v`、两个 `-score_matrix` 取值各断其行为
    （`-v` 断"stdout 不变 + stderr 出现 Computing posterior matrix 且显著变长"）；
  - 四条**失败码路径**：输入文件缺失（RC≠0 且错误串点名文件）、长选项（RC≠0 + Unrecognized option）、
    零参数（RC≠0）、`-T not-a-number`（RC≠0 + Invalid floating-point value）。

golden 采集与复算证据：`~/tmp/uc2/z33-probalign/{d1,d2,nuc-1,nuc-2,par-1,par-2}.out`
（两两 sha256 相同）。

## 五维账本

| 维度 | 读数 | 口径 |
|---|---|---|
| 上游静态声明数 | **0** | Makefile 仅 `all`/`probalign`/`clean` 三目标；`make -n check`、`make -n test` 均 "No rule to make target"（RC=2）；`grep -niE "check\|test\|TESTS" Makefile` 无匹配（RC=1）；树内无 tests/、无 configure |
| 上游注册可执行数 | **0** | 同上，无任何测试注册面 |
| 上游实测通过数 | **0/0** | 没有可运行的上游测试，不虚构分母、不缩分母 |
| 跳过数 | **0** | 无 skip 项；`L2_RESULT=skip` 是框架口径（CI 裸跑二进制不加载 runenv），属门禁自身行为，不计入测试分母 |
| 失败数 | **0** | — |
| 适配后消费者断言 | **29/29 通过** | `test_package/test_probalign.py`，退出码由断言决定 |

skip 的技术原因说明：上游 0 测试 ⇒ 不存在"上游测试被跳过"一事；本包所有 29 条断言
均为实跑（`conan create` 内与 `conan test -pr/-pr:b` 内各一次，两处都是 29/29）。

门禁判决行原文与时间（B 机，均本轮实拍）：

```text
conan-verify (cv2.log 02:15:35)  : G1 PASS / G0 / G2 PASS / G3 PASS / G4 / L2 / L4 / L5
                                   ✅ 配方验证通过: probalign 1.4  →  VERIFY_RC=0
W3 本地 CI (w3-local-ci.log 02:21:13):
  [ok] probalign/1.4 — conan create passed
  [ok] L1a: test_package was executed by conan create
  [ok] L1b: Test execution evidence found in log
  [ok] L1e: Negative test confirmed — test genuinely depends on probalign
  L0_RESULT=pass: all checks passed
  L1_RESULT=pass: test_package executed
  L2_RESULT=skip: probalign version/help failed
  L4_RESULT=pass: patches clean
  L5_RESULT=pass: bin/ has content
  Total:   1   Success:   1
.ci-result.json 02:21:13 : exit_code=0  integrity_hash=777e1d6030d831ab
                           log_sha256=6847e25dd059be83a723205e4ffc569b1ba2a6cd27257d31bfcb71587771dbef
finish Step 5/10 (W3)     : ✅ W3 本地 CI 模拟通过
finish Step 9/10 (W2)     : ✅ 仅含配方变更 (8 文件)，无框架文件
```

W3 日志真伪三条（按取证口径逐条核）：判决标记数 **53 > 0**；
`w3-local-ci.log` mtime **02:21:13 晚于本轮 conan-verify 的 02:15:35**；
md5 **03230822f5b5bc7cf747f256aea37ed0** ≠ `conan-create.log` 的
**95fa51215495d0f4584cf3244a14efd3**。

`finish` 未达全绿的两处及其性质（都不属本包阻塞项，交主代理收口时知悉）：

- `step5b`（finalize-archive，非致命 RC=2）：`软件级缺失 README.md`、
  `缺少 release/debug tar.gz`、`notes.md 无对话记录`。
  同仓已合并先例 `archives/c/cronutils/` 亦无软件级 README.md ⇒ 与 merged 口径一致。
- `step8`（gen_summary，非致命）：`'str' object has no attribute 'append'`；
  `SUMMARY.md` 按 SKILL 属协作者只读面，未触碰。
- `Step 10 submit 就绪预检` 另列 3 项（`reports/test-report.md`、`packaging/`、
  `.staging-verified`）为警告级，属 submit 前置，不归本执行段。

上游清点证据（绝对路径，B 机）：

- `/storage/Users/currentUser/tmp/uc2/z33-probalign/make-n-check.log`
  ——`make -n check` / `make -n test` 均 `No rule to make target`（RC=2），
  Makefile 目标全集只有 `all`(L5)、`probalign`(L7)、`clean`(L10)，
  `grep -niE "check|test|TESTS" Makefile` 无匹配（RC=1），解包 14 个文件逐条列全。
- `/storage/Users/currentUser/tmp/uc2/z33-probalign/cross-framework-test-scan.log`
  ——**跨框架复扫**（防只按 automake/ctest/gtest/pytest 口径清点而漏记语言绑定用例）：
  对实物 tarball（sha256 `b221a27c5cbc3e5c707b0514c71301806074a2bf54047b57bd2d40497b663c29`，
  `tar tzf` 15 条目、解包后 14 个文件）跑
  `grep -rlE "Test::More|use_ok\(|def test_|TEST_CASE|add_test\(|enable_testing" .` ⇒ **零命中**（RC=1）；
  `find . -type d \( -name t -o -name tests -o -name test -o -name spec -o -name Testing \)` ⇒ **零命中**；
  全文件清单同件列出 ⇒ 上游 1.4 无任何已注册测试面，`N_static = 0` 成立（本条与上一条共同构成有效取证，
  下一条框架脚本失败记录**不作证据**）。
- `/storage/Users/currentUser/tmp/uc2/z33-probalign/extract-upstream-tests.log`
  ——仓内 `ci/tools/extract_upstream_tests.sh` 在设备上**跑不起来**：脚本 L33 硬编码
  `WORK_DIR="/tmp/upstream_test_analysis_$$"`，而设备 `/tmp` 只读
  ⇒ `mkdir: Read-only file system`，RC=1。属框架侧可移植性缺陷（按红线不改 `ci/`），
  故上游 0 测试的取证改走上面的直接审计口径，证据强度更高（目标全集 + 全文件清单）。
- `/storage/Users/currentUser/tmp/uc2/z33-probalign/manual-make1.log`（clang 15 首建，RC=0，仅告警）
- `/storage/Users/currentUser/tmp/uc2/z33-probalign/manual-make2.log`（上游原样 CXXFLAGS 复建，RC=0）
- `/storage/Users/currentUser/tmp/uc2/z33-probalign/standalone-test1.log`
  （消费者测试脱离 conan 先对 `make` 出来的二进制跑通 29/29，避免用 `conan create` 试错）

## 适用边界

- 只覆盖上游 1.4 的 `.orig` 原包；Debian 的 `debian/` 打包层未被使用也不被引用。
- 目标为 OHOS/Linux POSIX；`validate()` 对其它 OS 直接 `ConanInvalidConfiguration`。
- 配方是 `package_type="application"`，不导出任何头文件/库（`includedirs`/`libdirs` 置空），
  下游只能当命令行工具消费。
- 自签只在 `settings.os == "OHOS"` 生效；缺 `binary-sign-tool` 的机器（如纯交叉环境）
  只告警并跳过签名，此时**不得**宣称真机交付通过。
- 核酸/蛋白质两条模型路径都实测过；`-score_matrix` 只接受上游支持的 `nuc_simple` 与
  `gonnet_160` 两个取值，未验证其它矩阵名。
- probalign 的后验解码在本机表现为确定性的，golden 锁的是**本机 clang 15 + musl**下的
  浮点结果；换编译器版本或浮点选项理论上可能移动 indel，届时应更新 golden 而非放宽断言。

## 声明（3+2）

- 适配路径：路径 B（贡献知识草稿）——在裸 Makefile + 零依赖 + 上游 0 测试的基础适配之上，
  本轮唯一的硬障碍（L1e 判假测试）的成因是**框架 L1e 调用参数不对称**，属与 E374 不同
  层次的跨库机制，已沉淀为草稿（见下方「知识库扩展」）。
- 使用知识库：**E374**（`Separate Conan consumer compile-link proof from unavailable
  signed runtime execution`，其 `forbid_1_pattern` 明确禁
  `can_run\(self\).*return.*pass`）——本包踩的正是该禁令的**另一条触发路径**，
  见上文 W3/L1e 一节；复用 `archives/c/cronutils/1.1` 与其
  `knowledge/DRAFT-cronutils-1.1-raw-makefile-ohos-cli-signing.md`（裸 Makefile 的
  OHOS 包内 ELF 自签、软件级 `commands.json` 范式）；
  `knowledge/drafts/DRAFT-clang-fno-common-header-globals.md`（预判 -fcommon 家族，
  实测本包未触发，故未引入 `-fcommon`）；E299/PF7（取源镜像改写与本地路径取源禁令）。
  检索手段：`recipe-search probalign`（语料 6173 条，无相似配方）、
  `preflight_check.sh`、`knowledge/graph` 按 makefile / fcommon / can_run / L1e 关键字检索
  （命中 E294、E301、E374、E380、DRAFT-E2175 等，逐条比对后只有 E374 与本轮机制同源）。
- 知识库扩展：新增草稿 `knowledge/drafts/DRAFT-probalign-1.4-l1e-conan-test-missing-build-profile.kv`
  与同名 `.md`（.kv/.md 配对；`source_pr` 留空待本 PR 号回填）。
  机制一句话：框架 L1e 的 `conan test` 调用只传 `-pr`（host profile）不传 `-pr:b`，
  build profile 因此回落到 CONAN_HOME 的 `default`（实测 `os=Linux`），host=OHOS 配 build=Linux
  被判为交叉构建 ⇒ `test()` 里的 `can_run(self)` / `cross_building(self)` 早退护栏必然命中 ⇒
  测试体被静默 `return 0`，而 L1e 的判据恰好是退出码且把输出整个丢弃（`build_and_test.sh:1646-1647`，
  `[fail]` 分支在 `:1650`、`[ok]` 分支在 `:1656`）⇒ **一个真测试会在 L1e 里被跳过并判成假测试，
  一个假测试反而能过 L1e**，即验证通道失真且失真方向与 R34 意图相反。
  判 **create**（原记 none，经主代理裁定升格）的理由是**层次差**：E374 是配方作者层的**写法禁令**，
  其 `root_cause` / `affected_scope` 的前提明写 same-OS worker、build 与 host settings match，
  关切签名工具链缺失时如何如实上报 NOT_RUN；本条是**框架层的调用参数不对称导致验证通道失真**，
  build/host 之所以不一致并非工人环境而是 `conan create` 传了 `-pr:b`、L1e 没传。二者是
  「禁令」与「为何违反禁令的后果无法被 L1e 自行发现」的关系，已在草稿 `similar_to: E374` 留交叉引用。
  查重与预审：`python3 scripts/ohc-run.py draft-review DRAFT-probalign-1.4-l1e-conan-test-missing-build-profile --top 8`
  ⇒ 质量预检 signature/root_cause/rec 三项全 ✅，**预审建议 = create**，
  相似 TOP8 最高仅 E204 score=0.18（libvpx configure，异机制），E374 score=0.06；
  另按 `can_run`/`cross_building`/`-pr:b`/`假绿`/`false pass`/`L1e` 逐关键字人工比对过
  `knowledge/graph` 与 `knowledge/drafts`，无语义重复（E307/E294/E301/E283/E286/E353/E540 均不同层）。
  ⚠ 本条只对本包断言「CI/L1e 中实际发生」（round2 判假、round3 判真的两轮 A/B 为证）；
  对其它带同类护栏的归档（已合并的 `archives/c/cronutils/1.1/test_package/conanfile.py:23-26`）
  只断言「写法命中三条件、属潜在暴露」，未复跑其 L1e，故不声称其已被误判。
- 关联 Issue：#3356（https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos/issues/3356）——Issue 由主代理于 2026-09-25 建立，标题即本草稿机制（L1e 的 conan test 缺 -pr:b 致交叉早退护栏静默跳过真测试）。
  另记两条与本体无关但值得留痕的**框架侧**观察，均按红线未改 `ci/`、未改 `scripts/`，
  若要立项应各自单开框架 PR：
  ①`scripts/ohc/check_env.py:33` 的 `except Exception: return False, str(e)` 中 `e` 未定义；
  ②`ci/conan/build_and_test.sh` L1e 重跑 `conan test` 时只传 `-pr`（host），
  未传 `-pr:b`，导致任何用 `can_run()` 护栏的 test_package 在该步被静默跳过而呈"假绿"。
---

**编译结束**: 2026-09-25 02:20
**最终状态**: built

