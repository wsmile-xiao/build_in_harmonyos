# TooN 0.0-git20240623085717.2982ecc



日期：2026-09-25。任务 #11221，平台分支 `feat/toon-0.0-git20240623085717.2982ecc`。



## 固定来源与范围



- 上游 `edrosten/TooN` commit `2982ecc24dd66dea42d0b587c0ec48df398b27fb`；固定源码归档 SHA-256 `5ac56b4fc7dd1a498a4e5217973722f6c49b56ebe661bb158ca7ca03079e6d33`。

- 配方接受 C++14 和 C++17 profile，目标为通过正式 OHOS aarch64 CI 的 C++17 配置；C++17 真机构建与消费者结果待验证。六项 LAPACK 可选功能/测试不在本候选支持范围内。

- Conan 包保留上游 `COPYING` 原文。



## 已有真机证据



- H1-003 原始包 SHA-256 `be41f63275c3fcce23a25d3fcac6bd4a7f7f8e22cbeaf25dd5707ef5c71c25b9`：Conan 包创建成功；16 项无 LAPACK 核心结果全部 `Passed`。两个 `initializer_list_fail_1/2` 的 `Compile error!` 是负向编译测试预期输出；swap 的空输出与空期望文件一致。该轮消费者因 Conan 导入错误未加载、未编译、未运行。

- H1-004 原始包 SHA-256 `dfc5bbdb64179b93f8aa0e9aa617efd41cd11fcc3dc2a33d6079a017572007f2`：测试 runner 把完整 binary ref 传给 `conan test` 导致解析 recipe 失败，消费者没有到达编译。

- H1-005 原始包 SHA-256 `b8faa9337a512990abbcfa7d6f0b3f4165bbb1637453afa420029ad843d526e0`：唯一消费者复验通过，精确选中缓存包 `toon/0.0-git20240623085717.2982ecc#ccf6f3f895195265ce2837271ddb4098:20ce5ca62dba04ef245a37652eafaea893be3909#0aaec2724b0652705c7659edf9f3937a`；CMake configure/build 完成并真实运行 `./toon_consumer`，ELF AArch64 (`e_machine=183`)。此轮只验消费者，没有重跑核心16项。



这些 H1-003/005 结果是分别限定范围的独立真机证据，不是框架 W3，也不代表 W4 或官方 CI 已通过。



## 此候选改动与待验证项



Candidate 006 从 candidate 004 继承六个配方/消费者文件，新增框架要求的 `test_package/MANIFEST.yml` 和版本 `manifest.yaml`，供官方 finish/W3 质量门和 G0 消费。W3 必须按框架官方 `finish toon 0.0-git20240623085717.2982ecc built` 流程执行一次；它会在新的私有 RUNROOT/CONAN_HOME 中运行完整无 LAPACK Conan create/test，因此该次 W3 内部会重新构建并运行上游核心测试与消费者。这是框架 W3 本身的验收，不用 H1-003/005 冒充。



这段是 candidate 006 当时的待验记录；后续结果见下方。Windows 静态检查、差异和固定输入哈希不等同于 OHOS/W3 验证。



## Candidate 007 修订



candidate 006 的官方 finish 未能进入 Conan create：私有克隆的 `origin/main` 仍指向 `d47316a8`，JC6 将 53 个软件目录误判为当前差异；该轮 L0 失败，16 项上游测试和消费者均未运行。原始归档 SHA-256 `0031985f13d9cc6e1f6e1aa718f2b6ffcf74d10b5aedcb2e7a3c80ef9795e2c5`。



本候选把 Matrix 拷贝构造修复从配方内联文本替换改为 `conandata.yml` 声明的标准补丁，增加 `export_sources()` 导出补丁，并在 `source()` 中调用 `apply_conandata_patches(self)`。测试范围和断言不变。W3-006 失败记录保留；candidate007 W3 必须使用全新私有 RUNROOT/Conan home，并在克隆内将 `refs/remotes/origin/main` 显式指向固定框架基线 `3edb1a22b9cd49aab142477cbda886e8563dab2b`，不得改动公共仓库。



## 2026-09-26：candidate 008 结果与 009 修复



H1-W3-008 原始归档 SHA-256 `52d9c58c38789bdddbf3f23f7c34dfb168faa8447c565bc1e2bbf611d7562979`。官方 `finish` 最终 RC=1；其内部 W3 的 `setup.sh` 与 `build_and_test.sh` 均 RC=0，私有 C++14 Conan 创建成功，无 LAPACK 核心 16/16 `Passed`，两个预期负向编译测试出现 `Compile error!`，CMake 消费者实际在 AArch64 ELF 上构建和运行。六项 LAPACK 可选测试为 `Missing`，不计通过。G0 `clean-verify` 用 GNU `patch -p1` 应用原零上下文补丁失败；G2 默认 profile 使用 C++17，与本配方明确的 C++14 范围冲突；全局知识图谱、摘要生成和提交就绪另有未解决项。对 H1 原始归档只读扫描后，摘要异常的首个触发文件确定为已有 qpdf 12.3.2 清单的重复 `knowledge_gained` 键，与 TooN 清单无关。W3 的通过不表示整个 `finish` 或官方 CI 通过。



Candidate 009 只改 `matrix.hh` 补丁的定位上下文，并补齐此处事实记录，保持配方、测试断言、源归档与 C++14 范围不变。旧零上下文补丁在本地 `git apply` 后落到文件末尾，形成类外构造函数声明并导致 C++14 编译错误；009 补丁定位在 `Matrix(){}` 后的类体内。对固定上游源码，009 经本机 GNU `patch --dry-run -p1` 和 `git apply --check` 接受，本机 MinGW g++ 8.1 的 C++14 固定/动态矩阵拷贝编译及运行 RC=0。此为 Windows 主机检查，不是 OHOS 结果；009 仍需独立 H1 目标机复验、W4、官方 CI 与贡献审核。



## 2026-09-26：candidate 010 — G0 hunk 格式调整



009 的 H1 原始 `finish` 仍因 G0 `patch -p1` 报 `Hunk 1 FAILED 116/116`；同一轮 W3 由 Conan patch 路径通过。只读审计证实 H1 原始源码头文件 SHA 与固定源码一致，H1 的 patch SHA 与 candidate 009 一致。对固定源码使用本机 WSL GNU patch 2.7.6 复现：candidate 009 手写 hunk 在 `--fuzz=0` 失败、默认模式需 fuzz=1；同一目标变化由 `diff -u` 生成的标准 hunk `@@ -117,6 +117,9 @@` 在 `--fuzz=0` 下 dry-run 通过。



Candidate 010 只将补丁改为该标准 hunk，源码变更仍是在类体内 `Matrix(){}` 后插入相同默认拷贝构造。本机 WSL GNU patch 2.7.6 的 `--fuzz=0` dry-run 通过；在独立固定源码副本实际应用后，`matrix.hh` SHA-256 为 `dbe540c1ea7134beec16be0550ecee6e28948602e2b2bd4a4bd83bc97d6b3d9b`，与 H1 W3-009 Conan 包头文件逐字节一致。该同一源码语义已在 candidate 009 的 OHOS W3 中验证（16/16 核心通过、consumer AArch64 实际运行）。010 尚无 H1 G0 结果，仍需二级协调一次限定 patch-only 验证；候选 patch 输出与上述哈希不符时，不复用 009 W3 作为同一代码结果。G2 profile、全局门禁、finish 与材料问题仍独立待处置。



## 2026-09-27：candidate 011 官方补丁生成收据



- 在固定框架基线 `3edb1a22b9cd49aab142477cbda886e8563dab2b` 的脚本上执行 `python3 scripts/ohc-run.py refresh-patch --auto toon 0.0-git20240623085717.2982ecc --project-dir <scratch-project>`，Linux Python 3.12.3、GNU patch 2.7.6，退出码 0。

- 输入原始源码 tarball SHA-256 `5ac56b4fc7dd1a498a4e5217973722f6c49b56ebe661bb158ca7ca03079e6d33`；官方生成输出 SHA-256 `c280a292050b6eabed4737b2fd41803ca0390d3baf7c7bbaf1e504d113fb4ad0`。该文件按字节复制至包内既有规范文件名 `patches/0001-matrix-copy-constructor.patch`；包内补丁 SHA-256 与生成输出相同。

- fresh source 上 `patch --fuzz=0 -p1` 成功应用，结果 `TooN/internal/matrix.hh` SHA-256 `dbe540c1ea7134beec16be0550ecee6e28948602e2b2bd4a4bd83bc97d6b3d9b`，与先前已观测结果一致。

- 此次仅重新生成补丁字节；配方、测试、源码改动和 C++14 范围未变。候选 ZIP 输入哈希发生变化，因此 H1 仅需由二级协调执行一次新的 G0 patch-only 核验。W3、G2、官方 CI 和完整 finish 仍未由本收据验证。



## 2026-09-27：candidate 012 — 默认 C++17 配置支持



公开正式 PR CI 记录注入 `CONAN_PROFILE=ohos-aarch64`，该 profile 使用 C++17。candidate 011 的 `validate()` 仅接受 C++14/gnu14，虽已在显式 C++14 profile 下通过 W3 与独立 G2，无法证明正式默认配置可构建。



candidate 012 只扩展配方 profile 校验以接受 C++14/gnu14 与 C++17/gnu17，并将 manifest 的 `language_standard` 标为正式 CI 目标 C++17；源码补丁、源归档和消费者断言未变。011 的证据继续只代表 011/C++14。



H1 对 candidate 012 固定输入在默认 `ohos-aarch64`（host/build `compiler.cppstd=17`）下完成官方 `setup.sh` 与 `build_and_test.sh`，均 RC=0；无 LAPACK 上游核心测试 16/16 `Passed`，CMake consumer 以 C++17 构建并在 AArch64 上实际运行。独立 `conan-verify --profile ohos-aarch64` 也 RC=0，报告 verdict PASS；G4 报告仍有“无法找到 package ID”警告，但同轮 create 日志列出包 ID `6b129b068851896169fae42d399fa922d239ce8a`。L2/L4/L5 因无 cache 路径跳过，G0 E490 预警保留，R46 为 `status=partial` 草稿。独立 W4 证据续审 PASS（P0=0、P1=0、P2=1），核实固定输入与上述真机结果。



这些结果只证明 H1 W3 脚本与独立 G2 在 C++17 下通过。完整 `finish`、正式远端 PR/CI 尚未运行；不得写成完整 finish 或官方 CI 通过。完整证据索引见工作区候选审计记录，不属于此软件包文件。



## 2026-09-29：candidate 012 验证证据勘误



H1 W3 与独立 G2 的原始输入仍是 ZIP SHA-256 `835d3f460442bd80c9dbe9139ae39887e6d1bf2aabd16acc30964f7c1ed101c3`，框架基线为 `3edb1a22b9cd49aab142477cbda886e8563dab2b`。这两项证据只覆盖该次输入及其中的包代码；此后只修改本文件的表述与格式，不把旧结果称作新提交的重跑。上游核心测试 16/16 通过，六项 LAPACK 可选用例未运行；OHOS aarch64 C++17 consumer 构建并实际运行。



G2 原始 `conan-create.log` 给出完整引用：`toon/0.0-git20240623085717.2982ecc@ohpcd/stable#e19099b5bf34c5751d3a8d45b7ea9709:6b129b068851896169fae42d399fa922d239ce8a#13734f1c5956006c1e228bdd53823131`。同轮 `conan-verify-report.md` 的 G4 虽为 PASS，但附有“无法找到程序包 ID”警告；因此包 ID 和 revision 由 create 原始日志确认，G4 的 ID 查找/缓存路径核验警告仍如实保留，不能将其写作无警告的产物完整性检查。L2/L4/L5 因无 cache 路径跳过，G0 E490 预警保留，R46 为 `status=partial` 草稿。完整 `finish` 与正式远端 CI 未运行。


## 2026-10-02 未发布的 CI 兼容修补候选

当前已发布 head 2c2144cbdf19878101b38a1bc9f9d069c7143829 的最新 CI #66479/internal77270 在 config.status:602 读取 confghliPh/subs1.awk 时 Permission denied；具体 owner/ACL/mount/open 根因尚未证实。

0002 仅由 OHOS recipe 的 TOON_CONFIG_STATUS_MKDIR=1 启用 mkdir 创建路径；保留 umask 077、构建树内目录、原非零出口和清理规则。mkdir 成功后才登记 tmp，避免碰撞失败触发 trap 删除预存目录。其他平台仍优先 mktemp。成功创建到登记间仍存在上游已有的信号漏清理窄窗口。

此候选不改变核心16项、消费者或 LAPACK 范围。历史 H1/CI 不证明本候选通过；受影响静态独审、唯一 H1 的目录护栏及一次 clean Conan create（含现有核心16项与consumer）待执行，候选官方 CI 未测。


## 2026-10-02 新受影响 H1 结果（前节待测状态的后续）

固定候选 ZIP SHA256 0b56a3fbca3f504feb13733af0314384adff55c1273d898c074593a879c66786；源码/0001/0002/recipe/test_package与该固定输入一致。新请求 orrkri-11221-toon-20261002-normal-sh-profile-01，私有ROOT /data/storage/el2/base/files/toon-ci-mkdir-20261002-0b56a3fb，全新CONAN_HOME无旧包。正常/system/bin/sh身份/目录准入及成功/碰撞护栏通过：实际目录0700、临时文件0600，KEEP碰撞哨兵保全。唯一 forced source Conan create RC0，原核心16/16（包括两项预期Compile error!）和现有consumer真实编译/运行1/1；六项LAPACK仍未运行。未加跑完整W3/G2/finish、独立重复consumer或全W4。

本轮使用独立私有profile SHA256 d311f0d72d0b81a1e7f875bcd4ef1957ac0db97c38df135566eddceb508ff3af，只将原profile 7ebd43d28468fe5795bd149ccf81b42429eb5ef63965914388eea2e9d711b793的CONFIG_SHELL/SHELL两行改为/system/bin/sh；原共享profile未改。本PR不把此私有profile写入共享配置或强制recipe解释器，不声称原默认HNP Bash环境已被本次验证；候选官方CI仍须其自身结果。

新conanbuildenv实际导出两行systemsh，config.status首行为#! /system/bin/sh。create日志含TOON_CONFIG_STATUS_MKDIR=1 ./configure，生成脚本保留0002条件；按调用链推断变量继承给config.status，未直接采样短命进程env或追加trace。patched configure SHA256 df7b39e5115a4ad1305006c9e52f85115ffe7d24c6229b1b2a843f0cd8f4e469。
包引用：toon/0.0-git20240623085717.2982ecc#9950f8b5baf0785494d8b68a5dfdd5eb:6b129b068851896169fae42d399fa922d239ce8a#13734f1c5956006c1e228bdd53823131。消费者ELF64 AArch64(machine183) SHA256 5c71d362409b50440fccfdf486d03961b1dafffa55e1c7fb7aa5a7174cf1dfd5。

结果原件SHA256 ab94a2fda5d23afd47ae085da286e1b97b822170c35d462031899a09370c7d6e；原raw-evidence.tar.gz 729063B/SHA256 49ecd9c38a4f44d3ddd94ecf9a4ff8723c256f9d139721e9f1fa4c0a77d15617，180条原始文件清单逐项摘要/大小匹配，清单自身为第181文件。证据保存在维护者工作区 work/toon/evidence/h1-ci-mkdir-20261002-normal-sh-01/。

原日志CMake Problem parsing /proc/meminfo、System is unknown to cmake Platform/HarmonyOS诊断保留；运行RC0不抹去诊断。Windows MSYS mode700断言FAIL(mode755)、旧官方CI #66479/internal77270 Permission denied及根因UNKNOWN保持。H1通过不代替官方CI或完整框架W3。未运行的范围不改为PASS。

原有效W4及历史W3/G2仍按各自固定输入保留；新增0002/recipe增量独审SHA f3b34ce3586b1d5ad27e61795c1369ed402212992d6d69da7e934a9609faae0c，私有profile两行增量独审SHA cf0c67f1b81b4424a75fd4ff104e93703ba93b49654eff8442a09c0984979a53，均静态PASS/P0=0/已发现P1=0。这两份增量不冒称完整W4重跑；此证据追加仅文字变化，不重复H1。
