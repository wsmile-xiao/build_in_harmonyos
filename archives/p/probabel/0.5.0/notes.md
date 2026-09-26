# notes.md — probabel 0.5.0 OHOS 适配笔记（DS-34 续做，2026-09-22）

## 1. 任务与来源

- 平台任务 9728（活动：开源鸿蒙PC专项积分赛-依赖，activity_id=6）
- 上游：GitHub GenABEL-Project/ProbABEL tag v0.5.0（官方 tarball，sha256 与 conandata 一致）
- worktree：`~/qzy/glm61-probabel-0.5.0`，分支 `feat/probabel-0.5.0`（基线 origin/main=3030ec61c8）
- CONAN_HOME：`~/tmp/ch/home-qc10-probabel`（global.conf jobs=2 + ohpcd remote + 共享 dlcache）
- 前任：glm-61（配方初稿）→ QC-10（消费者测试重写+软链修复+干净重建全绿，2026-09-22 停工扫尾）→ DS-34（文档/提交/PR 收口）

## 2. W0 依赖发布核验

无外部依赖（`dependencies: []`）：Eigen 3.2.1 为上游捆绑源码，随 tarball 分发；
perl 仅运行包装器需要（OHOS hnp perl 提供）。W0 preflight PASS。

## 3. W0b 历史经验

`archives/p/` 无 probabel 历史（本 PR 为首适）。语言预检：cpp ✓（autotools）。
tarball 无生成版 configure，需 `autoreconf -fi`（pkg.m4 已在设备可得）。

## 4. 上游测试五维账本

| 维度 | 数值 | 口径 |
|---|---|---|
| N_static | 14 | `checks/Makefile.am` TESTS=$(check_SCRIPTS)=11（5+2+4）+ `checks/R-tests/Makefile.am` HAVE_R 时 3 |
| N_registered（本环境） | 11 | R-tests 注册 0：环境无 R 解释器 |
| N_executed | 11 | 干净重建 `make -j1 check` Testsuite summary 原样读数 |
| 未执行分类 | 3 | 原因=环境无 R（非本次适配造成）；其中 2 项上游自标 XFAIL |
| N_consumer | 1 程序 / 9 组断言 | test_package/test.sh，真实编译+运行+断言 |

- `checks/Makefile.am` 的 `XFAIL_TESTS = check_pacoxph_nocovar.sh` 为上游笔误：
  该脚本**不存在于 TESTS** ⇒ 实际预期失败项 0，不得据此缩小分母。
- 实测证据（单次干净重建，2026-09-22 QC-10）：
  - 日志 `~/tmp/uc2/qc10-r2/probabel-final-create.log`：CREATE_RC=0；第 101 行
    `Calling build()`；第 30653 行 `RUN: env SHELL=/data/service/hnp/bin/bash make -j1 check`；
    两处 Testsuite summary：`checks/` = TOTAL 11 / PASS 11 / SKIP 0 / XFAIL 0 / FAIL 0 /
    ERROR 0；`checks/R-tests/` = TOTAL 0（HAVE_R 为假，未注册）；第 30873 行
    `test_package: PASS（9 组消费者断言）`。
  - `conan-verify probabel 0.5.0` → G1/G2/G3/G4 PASS，VERIFY_RC=0
    （`~/tmp/uc2/qc10-r2/verify-probabel-2.log`）。

## 5. 适配要点（按踩坑顺序）

1. **autoreconf -fi**：tarball 只带 configure.ac，不生成 configure；设备 pkg.m4 可得，
   标准 autoreconf 路径即可。
2. **E011/E114（configure umask 077）**：configure 内 `umask 077 &&` 在 HMDFS 上
   权限异常，配方 build() 内 `replace_in_file` 就地移除（tarball 生成文件，不留 patches/）。
3. **E386 同族（CONFIG_SHELL/hnp bash 路由）**：configure/make/install 均以
   `env -u CONFIG_SHELL SHELL=/bin/sh` 前缀执行；上游套件按上游自身写法用
   `env SHELL=/data/service/hnp/bin/bash make -j1 check`（checks 脚本必须 bash，
   见第 4 点）。构建目录 getcwd 问题由 env 路由规避。
4. **fd-3 惯用法改写（本 PR 不申报的第二条机制，一 PR 一知识）**：上游 `checks/test_qt.sh`
   在 hnp bash 下 `line 31: 3: Bad file descriptor`（`exec 3>/dev/null`/`>& 3` 写法），
   静默丢输出。配方把 checks/*.sh 的 shebang 改为 hnp bash 并将 fd-3 惯用法改写为
   `>/dev/null 2>&1` 等价形式。修后 Bad-fd 行数 0（`~/tmp/uc2/qc10-r2/pbfd3b.sh` A/B 对照）。
   与 E553（fd3-pipeline-tap-driver，修法=翻 SHELL）同族但解法相反——本包 TESTS 脚本
   依赖 bash 特性（`echo -e`、`${var:${#name}}`）**不能**翻 SHELL，只能改写 fd 惯用法，
   属可申报的另一条解法；按 §6.2⑦#1 本 PR 只带软链草稿，该机制记入 B 草稿库待成套配送。
   诚实性说明：A/B 两臂在裸脚本复现环境里都因 E386 getcwd 噪声未走完（FAILED 同现），
   B 臂通过的证据只有真实构建链（make -j1 check 11/11）。
5. **src/probabel 包装器 shebang**：`#!/usr/bin/perl` 在 OHOS 不存在，改 hnp perl 路径
   （在配方 build() 内 sed 就地改写，不入 patches/；0001 只含 configure.ac 的 4 处 `VAR+=` 改写）。
6. **0001 补丁描述纠偏（实测否证原描述）**：原写"toybox sh silently drops `+=`"——
   本设备实测**不成立**：`/bin/sh` 与 `/system/bin/sh` 均为 MIRBSD KSH R59，
   `VAR+=" x"`、空值/未定义时均正常追加；hnp bash 亦正常（其报错是 E386 getcwd 噪声，
   非 `+=` 语义）。该补丁保留理由=把非 POSIX 的 `VAR+=` 追加改为 POSIX 等价写法、
   消除对 shell 方言的依赖（CI worker 的 /bin/sh 未实测）；并非本机失败的必要条件。
7. **0002 补丁**：类内 `static const double` 初值化（EPS/CHOLTOL）在 clang C++14 下
   需 `constexpr`（coxph_data.h、reg1.h）。
8. **-std=gnu++14**：bundled Eigen 3.2.1 使用 C++17 已删除的 `std::binder1st/std::bind2nd`。
9. **probabel.pl 别名不可重定位（B判定=create，本 PR 知识）**：上游 `src/Makefile.am:436`
   用 `ln -s $(DESTDIR)$(bindir)/probabel probabel.pl` 装别名；conan `package()` 不带
   DESTDIR ⇒ 链接目标被固化成**构建期 package_folder 绝对路径**，原地自测全过、
   换 CONAN_HOME/换机即悬空。修法：package() 内改写为相对链接，OSError（HMDFS 拒绝
   建软链，E018/E050 家族）时退化为复制 + chmod 755。证据：修前 `ls -l` 记录、
   修后 `probabel.pl -> probabel`、重定位 A/B 模拟（`~/tmp/uc2/qc10-r2/pbsym.sh`/`pbsym2.sh`）。

## 6. 消费者测试设计（test_package/test.sh，9 组断言）

1. probabel 包装器可执行并输出用法；2. palinear 在真实输入上跑通并产出结果文件；
3. 结构断言（表头关键列、SNP 数与 map 一致、名称与顺序一致；test.map 内部混用
   制表符与空格 ⇒ 取首列一律 `awk '{print $1}'，cut -f1 会把整行当第一列）；
4. dose 与 dose.fvi 输入结果逐字节一致（上游 test_qt.sh 同契约）；5. 与上游
   verified_results 按**列名对齐**的数值锚点（5 SNP × 12 列，容差 1e-9，跳过 -c 的
   chrom 列；该基准文件对当前 inputfiles 已过期——只有 5 行而 test.map 有 6 SNP，
   上游自己的套件也不与它逐字节比，故只作数值锚点而非逐字节基准）；6. `-c 19` 语义
   （去 chrom 列后与不带 -c 的输出逐字节一致）；7. 缺 -d 必须非零退出；
8. palogist/pacoxph 已装且响应（extract-snp 上游默认关闭且自述 not finished，不属交付面）；
9. probabel.pl 别名可解析可执行。素材 input/ 与 expected/ 的 md5 与上游
   checks/inputfiles 一致。

## 7. 产物与已知边界

- `probabel` 包装器**不支持** `--version` / `--help`（W3 的 L2 平台功能矩阵实测报
  `probabel --version/--help failed (non-blocking)`）：这是上游 perl 包装器的既有行为，
  它把无法识别的选项透传给底层分析程序，非本次适配引入；`palinear`/`palogist`/`pacoxph`
  三个分析二进制的 `--help` 正常。消费者测试因此**不**以 `--version` 作为可用性判据，
  改用真实输入跑通 + 结果结构断言（见第 6 节）。


- 产物（工具型，cpp_info 仅 bindirs）：bin/{palinear, palogist, pacoxph, probabel, probabel.pl}
- R 参照测试（R-tests/，3 项）需 R 解释器：环境无 R，未注册未执行（上游 HAVE_R 条件接线，
  其中 2 项上游自标 XFAIL）——非本次适配造成。
- extract-snp 默认关闭（上游 configure.ac:202-206 自述 "not finished yet"），不属交付面。

---
**编译结束**: 2026-09-22 10:10
**最终状态**: built
## 8. 对话记录

> #1/#2 转录自交接包 `~/tmp/uc2/handoff/probabel-0.5.0/README-handoff.md` 与 git 记录
> （非本窗亲历，来源已标注）；#3 为本窗 Q-21 实测。

### 对话 #1 [2026-09-22 QC-10]

- 问题: 交付包 `bin/probabel.pl` 别名软链换 CONAN_HOME/换机后悬空——上游 `src/Makefile.am:436`
  用 `ln -s $(DESTDIR)$(bindir)/probabel probabel.pl` 造别名，conan `package()` 无 DESTDIR 安装
  时链接目标被固化为**构建期绝对 package_folder** 路径；原地自测全绿，重定位即断
- 操作: `package()` 内改写为相对链接；HMDFS 拒绝建软链时（E018/E050 家族）退化为复制 + chmod 755
- 结果: 清缓存干净重建 `conan create` RC=0，`make -j1 check` TOTAL 11/PASS 11（日志
  `~/tmp/uc2/qc10-r2/probabel-final-create.log:30692`）；该机制成对写成
  `DRAFT-probabel-0.5.0-destdir-baked-symlink-alias-non-relocatable.{kv,md}`

### 对话 #2 [2026-09-22 DS-34]

- 问题: `conandata.yml` 中 0001 补丁描述写成"toybox sh 静默丢弃 `+=` 导致丢失 Eigen -I"，
  本设备实测**否证**——`/bin/sh` 与 `/system/bin/sh` 均为 MirBSD KSH R59，`VAR+=" x"`（含空值/未定义）正常追加
- 操作: 改写描述口径为"上游 configure.ac 用非 POSIX 的 `VAR+=` 追加编译器标志；本机 mksh 可接受
  ⇒ 该补丁不是本机失败的必要条件，保留理由=改 POSIX 等价写法、消除 shell 方言依赖（CI worker 未实测）"；
  同时补齐 version/software 两级 manifest、notes、软件级 commands.json（L0k 要软件级）、
  改写 `test_package/MANIFEST.yml` 与 test.sh 的 9 组断言同源
- 结果: 精确提交 `602e5e1dbd`；`draft-review` 判 create（最高相似 0.21）

### 对话 #3 [2026-09-22 Q-21 本窗]

- 问题: 接手时 worktree 有一处**未提交**改动（`conanfile.py` 把 E011 的 `sed -i 's/umask 077 && //g'`
  换成 conan `replace_in_file`），旧的 `.conan-verified` 标记不覆盖该代码 ⇒ 按"证据绑定当前代码"不可直接交付
- 操作: 重跑 `conan-verify probabel 0.5.0`（经 build-slot 槽位闸 + gate 8000MB）复验当前工作树
- 结果: G0/G1/G2/G3/G4 全 PASS、`VERIFY_RC=0`、整份日志 `Bad file descriptor` 命中 0；
  改动以 `37ddca2355` 精确提交；随后 `finish probabel 0.5.0 built` 的 **W3 本地 CI 模拟通过**、
  W2 原子性通过（仅 22 个配方文件、无框架文件）。
  遗留两项 ⚠️ 与本项目无关：`gen_summary` 崩在他人归档
  `archives/q/qpdf/12.3.2{,.1}/manifest.yaml`（自制 YAML 解析器不认其形态，全库 10556 个 manifest 中仅此 2 个失败），
  `scripts/` 只读、需框架单独 PR；W5 报的 E219/E253/E305 `root_cause` 为空亦属他人条目。
---

## 7. CI 二进制夹具 git-am 兼容（主理-35 2026-09-25 01:4x，A 机）

- **现象**：PR !11933 此前每轮 CI 判决失败，且判决文本误标为网络问题。
- **根因**（Q-21 定位，主理-35 落地处置）：平台 CI 以 `git-am` 方式套用 PR diff 且不带
  `--binary`，`test_package/input/test.dose.fvd`/`.fvi` 是二进制文件 ⇒ `patch does not
  apply`（sngrep !11715 同根因）。
- **修法**：两夹具以 `base64 -w76` 文本化入仓（`*.b64`），git 移除二进制；
  `test_package/conanfile.py` 的 `test()` 先把 `.b64` 解码还原到 conan 源副本再跑
  `test.sh` —— git 工作树与 PR diff 从此不含二进制，解码产物只存在于构建缓存副本。
- **验证**：解码回读 md5 与原文件一致（fvd=`010244210d087fd2f482255ea232b79b`、
  fvi=`954d83f9936945b96b7e82c1d66dc8e8`）；本机 `conan create` rc=0，
  test_package 9 组消费者断言全 PASS（`~/tmp/uc2/z35-probabel/create-after-b64.log`，
  包体缓存命中零重编）。
- **机制沉淀**：与 sngrep 共用 ⇒ 已入 `经验文档/B草稿库/` 通用池（binary-test-fixture-platform-checkout-patch-not-apply-base64（B草稿库 M23 权威 slug））；本 PR 的 B 判定维持 create（destdir 符号链接不可重定位，草稿已入库），
  本机制属通用池、不占本 PR 一 PR 一知识额度。
---

**编译结束**: 2026-09-25 01:40
**最终状态**: built

## 2026-09-26 CIW-7 bootstrap 补记（worker 无 automake 的仓内标准解）

- CI 干净 worker `build()` 报 `Can't exec "aclocal"`（判决 build#61481/#61490，FileUtils.pm 路径证实只挂了 hnp autoconf_2.72 系）。
- 一度用 runner-path-prepend（HOME 下 aclocal 目录前缀，9f5326c1/ad899cc6eb）——**已废弃**：worker 的 HOME 没有 automake，且空 prepend 曾把 PATH 清成 ""。
- 正解 = 仓内标准打法（abiword-plugin-clarisworks/3.0.8:113-114、argp-standalone 同式）：`tool_requires("automake/1.18")` + `tool_requires("libtool/2.5.4")`（ohpcd 已发布，rrev 65a7ba60/fe9f8e73，`conan download --only-recipe` 实测），`autoreconf` 经 `self.run(..., env="conanbuild")` 注入。
- 验证：A 机仿真 worker PATH（无 ~/usr/local/bin、无 harmonybrew、hnp 无 automake）`conan create -pr:h -pr:b` 全链 PASS，9 组消费者断言全过（~/tmp/ciw7_probabel_fix8.log）。
