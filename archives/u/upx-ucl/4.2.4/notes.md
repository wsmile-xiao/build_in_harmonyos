# upx-ucl 4.2.4 适配笔记

## 身份与版本
- 任务库名 `upx-ucl`，上游即 UPX（https://github.com/upx/upx），发布 tag v4.2.4
  （2024-03-28）。产物：单一可执行 `upx`（CMake install → bin/upx）。
  → R38 commands.json（type: tool）。
- 源码包取上游 GitHub Release 原件
  `https://github.com/upx/upx/releases/download/v4.2.4/upx-4.2.4-src.tar.xz`，
  Windows 实测下载，sha256 = 5ed6561607d27fb4ef346fc19f08a93696fa8fa127081e7a7114068306b8e1c4。

## 查重（两项独立检查）
1. archives/ 目录：`archives/u/upx-ucl/4.2.4/` 不存在 → 通过。注意
   `archives/u/upx/5.1.1/` 已存在（同一上游、旧框架格式条目，无 conanfile.py），
   属不同库目录 + 不同版本，不构成路径重复。
2. CI L0j 口径：制品仓是否存在 upx-ucl/4.2.4 同版本二进制 —— 必须在 MateBook
   `conan download "upx-ucl/4.2.4" -r=ohpcd --only-recipe`（或按现行 SKILL 的
   查重命令）确认；upx/5.1.1 版本不同不拦截，但需在真机确认 L0j 判定口径。

## W0 依赖清单（Windows 静态分析，2026-09-29）
| 依赖 | 来源 | 结论 |
|---|---|---|
| ucl | vendor/ucl | 自带，无需外部包 |
| zlib | vendor/zlib | 自带 |
| lzma-sdk | vendor/lzma-sdk | 自带 |
| doctest（测试头文件） | vendor/doctest | 自带 |
| valgrind（可选头文件） | vendor/valgrind | 自带 |

**零外部依赖**，制品仓无阻塞项。CMake ≥ 3.8（OHOS 真机自带的 cmake 满足），
C++17，无 .git → GITREV 自动禁用，无 git describe 需求。

## 构建设计（见 conanfile.py 文档字符串）
- 纯 CMake VPATH 构建，CMakeToolchain + cmake.install()。
- OHOS libc++：`CMAKE_CXX_FLAGS="-stdlib=libc++"`、
  `CMAKE_EXE_LINKER_FLAGS="-lc++ -lpthread"`（ada/4.0.0 cache_variables 同款；
  archives/u/upx/5.1.1 knowledge_gained: cmake_with_libcxx）。
- upx/5.1.1 knowledge_gained 另两条照搬备查：
  ① vendor_bundled：无需外部依赖（本配方已落实）；
  ② harmonyos_cmake_warning：CMake 不识别 HarmonyOS 平台会告警但不影响编译
  （预期日志有 warning，非错误）。
- 测试面：上游原生注册 44 用例（9 CLI + 8 自打包 + list/fileinfo/-t + 8 解包 +
  7 比较 + 1 run-unpacked + 8 run-packed；Windows 首版误写 53，已按真机日志更正）。
  配方以 `UPX_CONFIG_DISABLE_RUN_PACKED_TEST=True` 关闭 run-packed 组（见下）
  → 实跑 36 用例，build() 内硬失败模式运行（回归必须阻断打包）；
  `UPX_CONFIG_DISABLE_EXHAUSTIVE_TESTS=True` 关闭 4×7 级别 exhaustive 矩阵
  （≈170 个重复自打包），控制 CI 时长。

## 真机第 1 轮验证记录（MateBook，2026-09-30，SHA 26fa96909）
- conan create exit 0；ctest **44|36|8|0**——8 个失败全部为 upx-run-packed 组，
  `BAD_COMMAND "Process not started ... [permission denied]"`；其余全绿
  （含 1 个 run-unpacked、消费者 6/6）。
- **决定性对照实验**（work/verify-logs/packed-exec-evidence.md，真机存档）：
  同一构建目录内未加壳 upx execve rc=0；加壳 upx 在构建树 / 用户 tmp（mode 755）/
  /data/local/tmp 三处全部 Permission denied（rc=126/127）；/proc/mounts 显示
  所有相关挂载**均无 noexec**（findmnt 设备上不存在，用 /proc/mounts 替代）。
- **根因定性**：HM-MAC（hmmac=use_task）策略在 execve 层拦截 UPX 自解包运行时
  （/proc/self/exe 重映射类），先于任何 upx 代码执行；加壳/解包作为工具操作
  普通文件不受影响（实测全绿）。**这是平台边界，不是配方缺陷，也不是 noexec**。
- 配方处置：关闭 run-packed 组并在此记录证据；其余 36 用例改为硬失败模式
  （撤掉 accessibility 式 record-don't-block——已无环境性失败面，回归必须拦）。
- finish 记录：close-archive 成功（manifest→built、notes 更新）；step5b 报
  缺 export_sources()（真实缺口，本版已补 `export_conandata_patches` 先例形态）；
  step3/step7/step8 为工具/环境项（tarball 定位、知识图谱积压 2436、gen_summary bug）。
- 审计记录：R1 轮审计唯一 P1 为 53→44 计数错误（本版四处同源修正）；
  各轮 P0–P3 分数以真机 `reports/audit-result.json` 工具留痕为准
  （门禁产物不进 git），notes 不手写分数。
- NEEDED（bin/upx）：libc++_shared.so、libc.so。
- 工具链观察（非本任务缺陷，供仓库反馈）：conan-verify G2 会在每轮
  finish 时把 gh-proxy.com（PF7 黑名单域）注入 conandata.yml url 首位
  （第 1/3 轮均复现）；git 内提交的字节始终为单条官方 URL，MateBook
  在 finish 后按交接字节还原工作区文件，属固定操作步骤。已通过
  feedback 渠道向仓库反馈。

## 路径 B 素材（知识库扩展候选，真机证据已在手）
- **新问题类（540 条既有知识未覆盖）**：HM-MAC（use_task）在 execve 层拦截
  "自解包类"可执行文件（UPX 的 /proc/self/exe 重映射运行时）——同一目录、
  同一用户、无 noexec 挂载的前提下，未加壳二进制可执行、加壳二进制
  Permission denied。识别特征：BAD_COMMAND/permission denied 且三处目录
  （构建树/用户 tmp/data/local tmp）一致拒绝 + /proc/mounts 无 noexec。
- 影响面推断：一切依赖 execve 后自重映射/自解包的程序（upx 加壳产物、
  某些 launcher/wrapper）在该策略下系统性不可运行；而"用 upx 加壳/解包文件"
  的工具用法完全正常。
- 证据链：真机对照实验三位置 × 加壳/未加壳 + /proc/mounts + ctest 8 连败
  签名（work/verify-logs/packed-exec-evidence.md，MateBook 存档）。
- 真机验证后按 knowledge/drafts 模板写 kv+md 对，PR 前缀【知识库扩展】。

## 真机已核实事项（第 1 轮闭环）
1. libc++ 链接 OK（-stdlib=libc++ / -lc++ -lpthread 生效，NEEDED 仅
   libc++_shared.so + libc.so）。
2. CMake "HarmonyOS platform not recognized" 告警出现，无害（5.1.1 经验印证）。
3. run-packed 8 连败 → HM-MAC execve 拦截（见上，已定性并关闭该组）。
4. run-unpacked 通过；test_package mktemp chmod 770 方案有效，cmp 可用，
   消费者 6/6。
5. 源 URL GitHub Release 在真机网络可达。

## 上游测试
- 上游 ctest 套件完整保留（除 exhaustive 矩阵，理由见上），在 build() 内
  真实运行；test_package 另加消费者往返测试。test_package/MANIFEST.yml
  记录上游测试清点证据（R51）。
---

**编译结束**: 2026-09-30 20:40
**最终状态**: built
