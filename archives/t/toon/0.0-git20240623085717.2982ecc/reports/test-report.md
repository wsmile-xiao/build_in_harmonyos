# TooN 0.0-git20240623085717.2982ecc 测试报告（candidate 012）

## 固定输入

- 任务：主活动 #11221，领取账号 `orrkri`；发布分支 `feat/toon-0.0-git20240623085717.2982ecc`，以官方 `main` `317e16ed5acf6882e7c8b54ff48c3e11a981cd96` 为父提交。实际提交和远端回读 SHA 见发布回执。
- 上游源码：`https://github.com/edrosten/TooN`，commit `2982ecc24dd66dea42d0b587c0ec48df398b27fb`；源码包 SHA-256 `5ac56b4fc7dd1a498a4e5217973722f6c49b56ebe661bb158ca7ca03079e6d33`。
- Candidate 012 刷新后的 diff SHA-256 `d93f1cd518cc42997f8f0d252c5a4708b6105b8887f905e253026ce8f69fe405`、manifest SHA-256 `69f0041d8901271d867f202ea8ba6586a2a102237bff48f2aeebd2580537cce2`；2026-09-29 handoff ZIP SHA-256 `370e8a14583438cb6d3d68bc344558e7498f7b995ae1331743c3245f26e880fa`。ZIP 仅更新 notes 证据勘误/末尾空行格式及派生的 HANDOFF 元数据，未重新发送至 H1 或重跑。九个包文件中仅 notes 改变；配方、包 manifest、patch、测试包、源码和 profile 与已测输入逐字节相同。
- W3/G2 真机执行绑定原 ZIP SHA-256 `835d3f460442bd80c9dbe9139ae39887e6d1bf2aabd16acc30964f7c1ed101c3`、框架基线 `3edb1a22b9cd49aab142477cbda886e8563dab2b`、H1 固定 HEAD `55be3a016bd415a5f3230e0fd49dd370034a3bea`。current ZIP 相对该输入只改 `notes.md` 与派生 `HANDOFF.json`；配方、manifest、补丁、测试包、源码和 profile 字节未变。W4 delta PASS 绑定 current diff/manifest/ZIP；没有声称 current ZIP 在 H1 重跑。

## 测试结果

| 类别 | 用例数 | 结果 | 说明 |
|---|---:|---:|---|
| 上游核心测试 | 16 | 16/16 通过 | TooN `make test` 核心集合；两项预期负向编译用例输出 `Compile error!` 并按预期通过。 |
| 上游 LAPACK 可选测试 | 6 | 0/6 未运行 | 配置使用 `--disable-lapack`；保留在总用例数中，不计为通过。 |
| 上游测试合计 | 22 | 16/22 通过，6 未运行 | 核心子集为 16/16；全上游测试通过率按包含未运行项的 16/22 披露。 |
| Conan 消费者 | 1 | 1/1 构建并运行 | OHOS aarch64 上使用 C++17；ELF `e_machine=183`；日志记录 `RUN: ./toon_consumer`。W3 与 G2 都运行了消费者，但按场景计一次。 |

- W3 官方 `setup.sh` 与完整 `build_and_test.sh`：RC=0，自然退出，16 项核心测试全部通过；证据仅绑定旧测试 ZIP `835d3f…101c3` 和框架基线 `3edb1a…dab2b`，不证明 notes 刷新或新提交经过真机重测。
- 独立 G2 官方 `conan-verify --profile ohos-aarch64`：RC=0，verdict PASS；同轮原始 create 日志显示包 ID `6b129b068851896169fae42d399fa922d239ce8a`、revision `13734f1c5956006c1e228bdd53823131`，且消费者实际运行。G4 报告仍有“无法找到程序包 ID”警告，ID/revision 的核对来源是 create 日志。
- profile host/build 的 `compiler.cppstd=17`；profile SHA-256 `7ebd43d28468fe5795bd149ccf81b42429eb5ef63965914388eea2e9d711b793`。

## 仍须披露的限制

- 独立 W4 对当前刷新候选的 manifest、diff、ZIP 和证据边界复核为 PASS，P0/P1/P2=0/0/0。此前提交级复核指出的 notes 末尾多余空行已删除；本项候选级结论不替代对最终提交树的单独差异审阅。G4 文档对照疑点已用同轮原始 `conan-create.log` 核对，但 `conan-verify-report.md` 的 G4 警告仍保留；不声称 G4 警告或 cache-path 检查已修复。相较 H1 测试输入仅 notes 与派生 HANDOFF 元数据变化，未重跑 H1。
- 2026-09-29 通过现有 Git Credential Manager 对 AtomGit `/api/v5/user` 的只读认证返回 `login=orrkri`。认证后的个人 Fork refs 中此前没有 TooN 任务分支；Fork `main` `7f702efc1d070f666c0e1036cf79faaff7943ed6` 是官方目标 `main` `317e16ed5acf6882e7c8b54ff48c3e11a981cd96` 的祖先。发布分支以最新官方 main 为父提交。实际提交、远端回读及 PR 状态见同日发布回执。
- 只读比较确认 `ci/conan/build_and_test.sh`、`scripts/ohc-run.py`、`scripts/ohc/{workflow_checks,conan_verify,clean_verify,finish,close_archive}.py` 在 W3/G2 基线 `3edb1a22b9cd49aab142477cbda886e8563dab2b`、H1 核对的 c611、当前 main 317e 三者字节相同；对应 SHA 见 `work/toon/delivery/w4-012-source-diff-blocker.md`。这核实了官方仓库中这些文件的版本连续性，但旧 G2 `project-dir` 是 H1 私有 runroot HEAD `55be3a016bd415a5f3230e0fd49dd370034a3bea`，旧归档不含其实际 runner 字节，故不把这项对照扩写为对私有 runroot 执行字节的证明。H1 c611 回执仍见 `work/toon/evidence/h1-readonly-c611-001/RESULT.md` SHA-256 `f6cca6803e06e570deb542b86320691f04c07b384900d1ee787870b568201a62`。
- L2/L4/L5 因无 cache 路径跳过，不能写作扫描通过；G0 留有 E490 预警；R46 为 `status=partial` 草稿。
- 完整 `finish` 未运行。经核 c611 `finish.py` 会依次再次执行 Conan verify 和 W3，且无 selective/reuse 参数；step8 仍强制要求 `packaging/` 与 `.staging-verified`，和同版 R19/R20 废弃旧手工打包/DESTDIR 的规则冲突。此为内部工具冲突记录，不表示 `finish` 已通过或官方已豁免。
- 完整 `finish` 未运行。W3/G2 真机结果不等于官方 CI 或完整交付通过；正式远端 CI、PR、任务关联和提审状态以后续发布回执中的 API 回读为准。

## 原始证据

- W3 归档：`D:\华为鸿蒙\work\toon\evidence\h1-w3-012\toon-w3-012-20260927-8b7c4e62a1-w3-raw.tar.gz`；SHA-256 `76aee8eca3a9f7d6e9d41542f0b8332ef444b51a65780b2a677a84a5e6312f54`。
- G2 归档：同目录 `toon-w3-012-20260927-8b7c4e62a1-g2-raw.tar.gz`；SHA-256 `635b07a73d3bc59a158606a3282a3a785cfce6ca79c0dbfef818f78a0d370f7f`。
- current W4 附录：`C:\Users\admin\.codex\worktrees\b518\华为鸿蒙\work\toon\delivery\w4-012-evidence-addendum.md`；SHA-256 `614e6d5ee0d265e287a33fee3943b0e439499b4d5015e0d602fdb7788999f98f`。


## 2026-10-02 配置临时目录增量（未发布候选）

基线 head 2c2144cbdf19878101b38a1bc9f9d069c7143829，CI #66479/internal77270 FAIL，config.status 读取 subs1.awk 权限拒绝。新增 OHOS-only mkdir 选择与成功后登记清理路径；现有核心16项/负向预期/消费者断言未变。新增候选 H1、功能测试和官方 CI 均未测；Windows 针对护栏检查单列于原 audit，不作为真机通过率。


## 2026-10-02 新受影响 H1 结果（前节待测状态的后续）

固定候选 ZIP SHA256 0b56a3fbca3f504feb13733af0314384adff55c1273d898c074593a879c66786；源码/0001/0002/recipe/test_package与该固定输入一致。新请求 orrkri-11221-toon-20261002-normal-sh-profile-01，私有ROOT /data/storage/el2/base/files/toon-ci-mkdir-20261002-0b56a3fb，全新CONAN_HOME无旧包。正常/system/bin/sh身份/目录准入及成功/碰撞护栏通过：实际目录0700、临时文件0600，KEEP碰撞哨兵保全。唯一 forced source Conan create RC0，原核心16/16（包括两项预期Compile error!）和现有consumer真实编译/运行1/1；六项LAPACK仍未运行。未加跑完整W3/G2/finish、独立重复consumer或全W4。

本轮使用独立私有profile SHA256 d311f0d72d0b81a1e7f875bcd4ef1957ac0db97c38df135566eddceb508ff3af，只将原profile 7ebd43d28468fe5795bd149ccf81b42429eb5ef63965914388eea2e9d711b793的CONFIG_SHELL/SHELL两行改为/system/bin/sh；原共享profile未改。本PR不把此私有profile写入共享配置或强制recipe解释器，不声称原默认HNP Bash环境已被本次验证；候选官方CI仍须其自身结果。

新conanbuildenv实际导出两行systemsh，config.status首行为#! /system/bin/sh。create日志含TOON_CONFIG_STATUS_MKDIR=1 ./configure，生成脚本保留0002条件；按调用链推断变量继承给config.status，未直接采样短命进程env或追加trace。patched configure SHA256 df7b39e5115a4ad1305006c9e52f85115ffe7d24c6229b1b2a843f0cd8f4e469。
包引用：toon/0.0-git20240623085717.2982ecc#9950f8b5baf0785494d8b68a5dfdd5eb:6b129b068851896169fae42d399fa922d239ce8a#13734f1c5956006c1e228bdd53823131。消费者ELF64 AArch64(machine183) SHA256 5c71d362409b50440fccfdf486d03961b1dafffa55e1c7fb7aa5a7174cf1dfd5。

结果原件SHA256 ab94a2fda5d23afd47ae085da286e1b97b822170c35d462031899a09370c7d6e；原raw-evidence.tar.gz 729063B/SHA256 49ecd9c38a4f44d3ddd94ecf9a4ff8723c256f9d139721e9f1fa4c0a77d15617，180条原始文件清单逐项摘要/大小匹配，清单自身为第181文件。证据保存在维护者工作区 work/toon/evidence/h1-ci-mkdir-20261002-normal-sh-01/。

原日志CMake Problem parsing /proc/meminfo、System is unknown to cmake Platform/HarmonyOS诊断保留；运行RC0不抹去诊断。Windows MSYS mode700断言FAIL(mode755)、旧官方CI #66479/internal77270 Permission denied及根因UNKNOWN保持。H1通过不代替官方CI或完整框架W3。未运行的范围不改为PASS。

原有效W4及历史W3/G2仍按各自固定输入保留；新增0002/recipe增量独审SHA f3b34ce3586b1d5ad27e61795c1369ed402212992d6d69da7e934a9609faae0c，私有profile两行增量独审SHA cf0c67f1b81b4424a75fd4ff104e93703ba93b49654eff8442a09c0984979a53，均静态PASS/P0=0/已发现P1=0。这两份增量不冒称完整W4重跑；此证据追加仅文字变化，不重复H1。
