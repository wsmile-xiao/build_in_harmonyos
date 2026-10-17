# pmix 5.0.11 适配笔记（OHOS aarch64）

> 分支 `feat/pmix-5.0.11`（基于 upstream/main f45e2cbf67）。适配完成，本文件为终态归档笔记。

## 结果总览

| 项 | 状态 |
|---|---|
| 探索编译 | ✅ 全部跑通：configure（HWLOC: yes / Libevent: yes，均指 conan 包）→ make（libpmix.so.2.13.11 + 9 个 CLI）→ make install staging → pmix_info 冒烟（无参数输出 "PMIX: 5.0.11"） |
| 端到端 API 实测 | ✅ simptest 模式：PMIx_server_init rc=0 → register_client → setup_fork rc=0 → fork 子进程 PMIx_Init rc=PMIX_SUCCESS（nspace/rank 合法）→ PMIx_Finalize rc=PMIX_SUCCESS → PMIx_server_finalize rc=0 |
| 补丁 | ✅ 3 个干净补丁（0001 config.guess：umask 077→022 ×3 + HarmonyOS 识别；0002 config.sub：ohos 三处白名单；0003 configure：内嵌 config.status 模板 umask ×2）。refresh-patch --auto 曾连带收获 15 个构建污染补丁（pmix_config.h 探测结果 + run_tests00-13.pl 绝对路径注入），已恢复原始文件 + 清理编辑追踪器后剔除 |
| conanfile.py | ✅ package_type=library、requires libevent/2.1.12 + hwloc/2.14.0（ohpcd 已发布）、--with-libevent/--with-hwloc（conan package_folder）、--enable-pmix-binaries、package() 删 .la、package_info libs=[pmix]+pkg_config_name |
| conandata.yml | ✅ 官方 URL https://github.com/openpmix/openpmix/releases/download/v5.0.11/pmix-5.0.11.tar.gz + sha256=11d91183c4fd77117d9e7f186a1f4fde182895314b18fc5783fee7e2e5595e88（实测一致）+ 3 补丁声明 |
| test_package/ | ✅ test_pmix.c（8 C 断言，simptest 模式）+ conanfile.py（self.run(env="conanrun", stdout=file) 捕获输出 + try/finally rmtree + HMBS_TEST_PACKAGE_RESULT + pmix_info 版本断言 + 布局断言 ×3）+ CMakeLists.txt + MANIFEST.yml（13 断言） |
| conan-verify | ✅ G0/G1/G2/G3/G4 全 PASS（G2 含 test_package：HMBS_TEST_PACKAGE_RESULT: total=5 passed=5，其中 C 断言 8/8） |
| W3 本地 CI 模拟 | ✅ L0 质量 5 层 + L1 conan create + junk check 全过 |
| 软件级三件套 | ✅ archives/p/pmix/{README.md, commands.json（R38，9 个 CLI 工具声明）, manifest.yaml}（upstream main 无 pmix 软件级文件，从零新建，与既有 5.0.10 半成品目录共存不冲突） |
| 知识草稿 | ✅ E543（HMDFS umask 077 属主不可写，复现 3/3）/ E544（config.guess/sub 成对平台识别补丁模式）/ E545（simptest server 模式测试范式 + conan run() 用法） |

## 平台适配要点（可复用知识）

1. **HMDFS umask 陷阱（E011）**：HMDFS 上 `umask 077` 创建的 0700 属主目录连属主都不可写且 chmod 无法恢复（复现 3/3）。pmix 的 config.guess（×3 处）与 configure 内嵌 config.status 模板（×2 处）均含 `umask 077`，导致 configure 期 `mktemp -d` 临时目录不可写。补丁统一 077→022。
2. **config.guess/config.sub 成对补丁（E007/E072）**：pmix 5.0.11 自带 2021-01-25 版 autotools 脚本不认识 ohos。config.guess 需加 HarmonyOS 识别分支（猜出 `aarch64-unknown-linux-ohos`）；config.sub 需三处白名单（ohos-linux 映射、OS 白名单 ohos*、kernel-os 白名单 linux-ohos*）。两者必须成对，只补一个会报 "invalid host type"。
3. **PMIx 端到端测试必须 simptest server 模式**：PMIx 是 client/server 架构，客户端 PMIx_Init 无服务器时返回 PMIX_ERR_UNREACH(-25)（设计使然，非适配 bug）。测试按上游 test/simple/simptest.c 范式：PMIx_server_init（**5.x 是 3 参数签名**）→ register_client → setup_fork → fork 子进程带 server env 后 PMIx_Init/Finalize。
4. **适配版 conan run() 用法**：OHOS 适配版 conan 2.29.1 的 `ConanFile.run(command, stdout=None, cwd=None, ignore_errors=False, env="", quiet=False, shell=True, scope="build", stderr=None)` 无 timeout 参数、只返回 retcode；stdout 可接 open() 文件对象捕获输出（stderr 用 subprocess.STDOUT 合并）。且 CI L0d 门禁 grep `self\.run`——test() 纯 subprocess 会被判 stub_test_method。正确写法：`self.run(cmd, env="conanrun", stdout=f, stderr=subprocess.STDOUT, ignore_errors=True)` 后读文件解析断言行。
5. **test_package 中 self.cpp.package 陷阱**：test_package 的 `self.cpp.package` 指测试包自身（从未打包，不存在）的 package scope——直接用会得到空路径（表现为 rc=127 找不到二进制）。被测包产物必须经 `self.dependencies[self.tested_reference_str].package_folder` 定位。
6. **refresh-patch --auto 构建污染再生成**：探索期 in-place 构建会改 pmix_config.h（configure 探测结果）与 run_tests*.pl（@VAR@ 绝对路径替换），finish 的 refresh-patch --auto 会按编辑追踪器把它们重新收获成补丁。治理：从官方 tarball 恢复这 15 个文件原始态 + 清理 `.edit-tracker.json` 的 edited 列表（scan() 按基线指纹合并，只删补丁文件不恢复源文件会被再生成）。
7. **本地 W3 junk check 幻影 diff**：fork 的 origin/main 落后于 upstream main 时，`git diff origin/main...HEAD`（incremental 模式）会把基线之后他人合入的 69 个软件包算成本 PR 变更（JC6 误报）。治理：本地 `git update-ref refs/remotes/origin/main <upstream/main>`（纯本地操作，不推送）对齐 PR 真实基线；先提交最小集再跑 finish 使 W3 增量校验恰好覆盖 PR 文件集。full 模式（无提交时回退 ls-files）会扫出他人已入库的 `.ci-trigger`（util-linux-login 2.42.2，仍在当前 main），与本 PR 无关，勿动。

## 关键事实备忘

- **PMIx 5.x API**：PMIx_server_init(NULL, NULL, 0) 为 3 参数；PMIx_Get_version() 返回 "OpenPMIx 5.0.11 (PMIx Standard: 5.1, ...)"；`pmix_info --version` 走 CLI help 机制只打印帮助文本（上游设计，src/util/pmix_cmd_line.c:175），版本断言用无参数输出的 "PMIX: 5.0.11" 行。
- **ZLIB**：configure 找系统 zlib 则启用 pcompress/zlib 组件，找不到不阻塞（非核心），与 5.0.7 参考口径一致不加 zlib require。
- **产物布局**：lib/libpmix.so（删 .la 后）、include/pmix.h、bin/ 下 9 个 CLI（palloc/pattrs/pctrl/pevent/plookup/pmix_info/pmixcc/pps/pquery）——R38 要求软件级 commands.json 声明（type: tool）。
- **conan OHOS profile**：triplet aarch64-linux-ohos、clang 15、CONFIG_SHELL=/data/service/hnp/bin/bash。
- **知识命中**：E011（umask 077→022）、E007/E072（config.guess/sub 平台识别）。
