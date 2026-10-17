# lzip 1.24.1 适配笔记

## 编译环境
- 构建系统: 自研 configure（非 autoconf）+ Makefile（C++ 无外部依赖）
- 编译日期: 2026-09-20 首建；2026-09-22 03:15 清缓存干净重建复验（本 PR 证据绑定该次）
- 编译器: clang++（profile conf tools.build:compiler_executables，配方显式 CXX 传入）
- 状态: built（conan-verify G1/G2/G3/G4 PASS，含 build() 内 make check 上游 220 断言全量真实执行；
  证据：reports/conan-create.log 第 131 行 RUN: make check -j1、第 136 行 tests completed successfully.）
- worktree: ~/qzy/glm62-lzip-1.24.1 分支 feat/lzip-1.24.1（基于 origin/main 3030ec61c8）
- 任务号: 13807（依赖活动 activity_id=6，导入自领）

## 源码与选型
- 官方源: https://download-mirror.savannah.gnu.org/releases/lzip/lzip-1.24.1.tar.gz
  （savannah 为 lzip 上游 nongnu 项目的官方发布镜像；lzip.org 直连实测返回非 gzip
  内容——HTTP 层成功但载荷为 HTML/重定向页，故弃用直连、采用 savannah 官方镜像）
- sha256: 30c9cb6a0605f479c496c376eb629a48b0a1696d167e3c1e090c5defa481b162（设备实测）

## 编译步骤
1. recipe-search 无相似配方（语料 5594 条），首稿按 conan-init 模板手写。
2. configure 特性：自研脚本（非 autoconf），**只接受命令行 `var=value` 形态的变量赋值**
   （configure --help 明示 "specify them as ..."，脚本内 `CXX=*)`/`CXXFLAGS=*)`/`CXXFLAGS+=*)` case
   分支），**环境变量形态的 CXX/CXXFLAGS/LDFLAGS 一律忽略**；且默认 `CXX=g++`，`${CXX} --version`
   探测失败时回退 `CXX=c++` 并把 CXXFLAGS 重置为 `-O2`（脚本第 26/28/33 行）。
   设备实测对照（同一源码副本）：
   - `CXX=clang++ CXXFLAGS="-DQC10PROBE -O1" ./configure` → 生成 `CXX = c++` / `CXXFLAGS = -O2`（env 被忽略）
   - `./configure CXX=/…/clang++ CXXFLAGS="-DQC10ARG -O1"` → 生成值与传参一致（命令行有效）
   ⇒ 配方必须把 CXX 作为 configure **参数**显式传入（取自 profile conf
   tools.build:compiler_executables），不能依赖 VirtualBuildEnv 导出。
3. make -j1（HMDFS jobserver FIFO 先例）；make check -j1 真实执行上游 220 断言。
4. 安装：make install-bin + 命令行覆盖 INSTALL/INSTALL_PROGRAM/INSTALL_DATA/INSTALL_DIR
   为 cp/mkdir 语义——上游硬编码 /usr/bin/install*，HMDFS 用户态无 install 命令
   （实测 Error 127），cp 等价语义 CI worker 同样可用；不装 info/man（避开
   install-info 宿主工具依赖）。

## 测试账本（五维）
| 维度 | 数值 | 来源 |
|---|---|---|
| N_static 上游静态断言 | 220 | testsuite/check.sh 逐块计数，复算命令 `grep -c 'test_failed $LINENO' testsuite/check.sh` = 220（RUNTEST 脚本口径 §12.72；对照：`grep -c '|| test_failed'` = 214，另有 6 处 else 分支内独立 `test_failed $LINENO`；`grep -c test_failed` = 221 含函数定义行，不作计数口径） |
| N_registered | 1 runner（make check → testsuite/check.sh） | Makefile.in check 目标 |
| N_executed | 220/220 全量执行（单 runner 一次跑完，无用例被跳过） | 2026-09-22 干净重建 reports/conan-create.log：第 131 行 `RUN: … make check -j1` → 第 132–136 行 testing lzip-1.24.1/decompression/compression/bad input → `tests completed successfully.`（无 test_failed 输出） |
| 未执行/跳过 | 0 | 同上 |
| N_consumer 消费者测试 | 1 程序 / 6 断言组 | test_package/test_lzip.py |

- check.sh 单 runner 含 220 个 `test_failed $LINENO` 断言调用点（压缩/解压/完整性/错误恢复/
  截断/格式边界/选项矩阵），不拆分为独立用例，按 §12.72 脚本口径申报。
- 消费者测试：ELF 结构 + --version + -9 压缩真实收益 + -t 完整性 + roundtrip
  sha256 字节级一致 + 损坏流非零退出。

## 上游测试用例修改说明
未修改任何上游测试文件；testsuite/check.sh 原样执行。

## 遇到的问题与解决方案
| # | 问题 | 根因 | 解决 |
|---|---|---|---|
| 1 | make 报 c++: No such file or directory | buildenv 不导出 CXX；configure 探测 g++ 失败回退 c++ | 配方显式传 CXX=profile cpp（clang++） |
| 2 | install-bin 报 Error 127 | 上游硬编码 /usr/bin/install*，设备无 install 命令 | make 命令行覆盖 INSTALL* 为 cp/mkdir |
| 3 | 消费者 ELF 检查 FAIL | 白名单漏 libc++_shared.so（OHOS libc++ 运行时） | 白名单补齐 |

## 路径 B 判断（2026-09-22 QC-10 复核，覆盖 GLM-62 09-20 的"纯 A"结论）
判定：**create** —— 新增草稿
`knowledge/drafts/DRAFT-lzip-1.24.1-makefile-install-cmd-absent-makevar-override.{kv,md}`；
关联 Issue：**#3229** — https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos/issues/3229（早于本 PR 创建，双向互链）。

机制：上游 Makefile 把安装工具做成可覆盖变量（`INSTALL = install` + `$(INSTALL_PROGRAM)` 引用）时，
OHOS 用户态**根本没有 install 命令**，package 阶段以
`/bin/sh: install: inaccessible or not found` + `make: *** [Makefile:87: install-bin] Error 127` 失败；
解法=利用 GNU make「命令行变量优先于 makefile 内 `=` 赋值」这一自带能力，把
`INSTALL/INSTALL_PROGRAM/INSTALL_DATA/INSTALL_DIR` 覆盖为 `cp -f`/`mkdir -p`，
**免补丁、免把打包逻辑改写成 Python 复制、且 DESTDIR 与目录创建语义原样保留**。

四条件核对（§6.2 判 hit 的四个条件，本条**不满足第 2 条**⇒ create；申报口径为"同症状、另一条解法"，
不主张新签名）：
1. 症状：与正式条目 **E098**（`cp-chmod-replace`）**同一签名、同一根因、同一适用范围**
   （E098 error_signature = `install: command not found|sh: install: inaccessible or not found`），
   与 DRAFT-8958 的 `install: Permission denied`（被不可执行的 ~/usr/local/bin/install 遮蔽）不是同一签名。
   ⇒ 本条**不宣称发现新错误签名**。
2. 解法未被既有条目覆盖（create 的唯一依据）：全库 `grep -rn "INSTALL_PROGRAM" knowledge/` **0 命中**；
   E098 让人放弃上游 install 目标、自己手写 `mkdir -p && cp && chmod`；E108 按 R6 打补丁把 install
   换成 ginstall；DRAFT-8958 用配方侧 Python 复制。**"在 make 命令行覆盖 INSTALL/INSTALL_PROGRAM/
   INSTALL_DATA/INSTALL_DIR 变量把手、保留上游 install 目标与 DESTDIR 语义"这条路径知识库没写过**
   ——按 §6.2 条件 2（症状相同但用既有条目没写的另一条解法 ⇒ 不算 hit，按 create 报）申报。
   新增的适用面=零补丁、零上游源码改动、不引入设备侧 coreutils 依赖、上游以后加装 man/info 不必重写。
3. 引用精确：E098 / E108 / DRAFT-8958 / E312 / E313 / DRAFT-heatshrink-…-make-cflags-commandline-override
   的差异与组分清单已逐条写进草稿 `similar_to`；`draft-review` 实测 TOP3（2026-09-22）
   = **E108 0.30 / E098 0.28 / E307 0.27**，三态建议 `review-similar`（灰区，未触及 merge-into 阈值 0.55）。
4. 等效性（偏离既有解法前必须证明不丢信息）：见下节实测三项（落点、结构、断言全通过）。

判重与新增价值：`draft-review` 相似度结果见下节；可跨库复用的适用面=lzip 家族
（lzip/lzlib/plzip/pdlzip）与所有"自研 configure + 裸 Makefile 且 INSTALL 走变量"的 C/C++ 工具包。

### 偏离 E098/E108 的理由与等效性证据（§6.2 hit 条件 4）
同症状族已有两条正式条目：**E098**（`cp-chmod-replace`，自己手写 mkdir+cp+chmod、绕开上游 install 目标）
与 **E108**（`patch-makefile-in-ginstall`，按 R6 把上游源文件里的 install 换成 ginstall）。
本包**两条都未采用**，改走"make 命令行变量覆盖"，理由与等效性证据：
1. **E108 在本机可得**（据实说明，不回避）：`~/usr/local/bin/ginstall` = GNU coreutils 9.10、
   `-rwxr-x---` 可执行，且 conan buildenv 的 PATH 含 `~/usr/local/bin`（见
   reports/conan-create.log 第 29/49 行）⇒ 不是"标准解法不可用"，而是"存在代价更低的另一条路"。
2. **代价对比**：E108 要按 R6 改上游 `Makefile.in` ⇒ 每个版本维护一份补丁，且引入对设备侧
   harmonybrew coreutils 的运行时假设（CI worker 不保证装 ginstall）；本包上游已把安装工具做成
   `INSTALL`/`INSTALL_PROGRAM`/`INSTALL_DATA`/`INSTALL_DIR` 四个变量把手，用 GNU make 的
   "命令行变量优先于 makefile 内 `=` 赋值"规则即可**零补丁**替换，且只依赖 sh 必有的 `cp`/`mkdir`。
3. **等效性证据**（覆盖后逐项复验，未丢上游语义）：
   - `make install-bin DESTDIR=<t> INSTALL="cp -f" INSTALL_PROGRAM="cp -f" INSTALL_DATA="cp -f"
     INSTALL_DIR="mkdir -p"` → 日志按上游结构执行 `mkdir -p` + `cp -f` 两行，RC=0；
   - `find <t> -type f` → 产物落点 `<t>/storage/.../usr/bin/lzip`，与配方
     `cpp_info.bindirs = ["usr/bin"]` 声明一致；
   - 交付物功能面复验：ELF 结构（PIE AArch64，NEEDED 仅 libc++_shared.so/libc.so）+ `--version` +
     `-9` 压缩收益 + `-t` 完整性 + roundtrip sha256 一致 + 损坏流非零退出，6 组消费者断言全 PASS；
   - `make check -j1` 220 断言 `tests completed successfully.`（与打包方式改动无关，同日志）。
4. **模式位差异已标注**：`cp -f` 沿用源文件模式位、不执行 `-m 755/644`；本包只装一个可执行文件
   （上游构建产物本身即 0755），故无收敛需求；草稿 `safety_boundary` 第 ③ 条已写明需要模式收敛的
   包必须补 `chmod`。

**未进本 PR 的第二条机制（已入 `经验文档/B草稿库/` 通用池，谁撞上谁取名即用）**：
自研 configure 只认命令行 `var=value`、忽略环境变量，且探测失败静默回退 `c++` 并重置 CXXFLAGS
——本包靠显式传参解决，属配方平凡写法，故不占用本 PR 的 B 名额。

## 使用知识库记录
- recipe-search lzip：无相似配方（5594 条语料，2026-09-20 查询）。
- 基线对照：`archives/l/lzip/1.25`（autotools.install）与 `1.26`（notes 记录 install 命令不存在，
  当时用手动 mkdir+cp+chmod 绕过）——本 PR 的 1.24.1 用变量覆盖法，未改这两份归档。
- 知识图谱 E386/E540 家族规避参考（CONFIG_SHELL 路由、HMDFS 先例，本包自研
  configure 未触发，仅作为设计输入）。
---

**编译结束**: 2026-09-22 03:42
**最终状态**: built
