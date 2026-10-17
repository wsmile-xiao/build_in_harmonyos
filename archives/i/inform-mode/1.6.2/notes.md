# inform-mode 1.6.2 适配笔记

## 上游与产物

- 上游发行形式：inform6 Unix 发行包 `inform-6.42-r9.tar.gz`（IF Archive
  source/old/ 目录，6.42 发行线最终修订 r9）内的 `contrib/inform-mode.el`。
  inform-mode 上游未单独发行，官方分发即随编译器发行包；独立 Git 仓库为
  rupertl/inform-mode。sha256=687623aa…7b34 实测（与 inform6-compiler 6.42
  配方同源同包）。
- 产物为单文件 Emacs Lisp：63201 字节，`;; Version: 1.6.2`、
  `;; Released: 10-Oct-2013`。同一文件在 6.44-r7 发行包内 md5 逐字节一致
  （316fd248c86e76fe61ea67a8dcc27058），上游 6.42→6.44 期间未更新。
- contrib/ 目录另有 pblorb.pl、scanblorb.pl 与 README——属 blorbtools
  与贡献说明，非 inform-mode 包成员，本包只取 elisp。
- Debian/Ubuntu 同源打包：inform-mode 1.6.2 二进制包由 inform6-compiler
  6.42 源码包构建（all 架构），安装到 `/usr/share/emacs/site-lisp/
  inform-mode.el` —— 本包布局沿用该惯例（`share/emacs/site-lisp/`）。

## OHOS 适配

无运行时源码包（OHOS PC 未移植 Emacs），inform6-library 同款范式：

- `build()` 仅做防漂移校验：contrib/inform-mode.el 在位 + 63201 字节
  精确断言；
- `package()` 将 elisp 安装到 `share/emacs/site-lisp/`，GPL-3.0 全文
  经 export_sources 随包附于 `licenses/LICENSE-GPL-3.0.txt`；
- `package_id` 清空（源码包与 settings 无关）；
- `cpp_info.resdirs` 暴露 site-lisp 目录，`runenv_info` 定义
  `INFORMMODE_ELISP_DIR`。

许可证细节：发行包 COPYING 只覆盖编译器/库（Inform DM4/Artistic 2.0
双许可），inform-mode.el 自身头声明 GPL v3 or later —— 许可证正文必须
随包另附，故本地 LICENSE-GPL-3.0.txt 经 export_sources 提供（文件名避开
上游 COPYING，防 get() 覆盖）。

## 测试口径

上游无测试套件（单文件 elisp；主模式的验证方式是加载进 Emacs 检查
byte-compile 与交互行为，OHOS PC 无 Emacs 运行时，属环境限制）。
适配后消费者探针（test_package/inform_mode_probe.cpp）以内容级断言
代替运行时验证：

1. 目录清单：site-lisp 恰好 1 个文件（inform-mode.el）；
2. 文件在位、非空、63201 字节精确防漂移；
3. 内容标记：`;; Version: 1.6.2` / `;; Released: 10-Oct-2013` /
   `;; Keywords: languages` 版本头，GPL 声明行，功能符号
   `(defun inform-mode ()`、`;;;###autoload`、
   `(defvar inform-mode-map nil`、`(defvar inform-mode-syntax-table nil`、
   `(defcustom inform-command "inform"`、
   `(defcustom inform-interpreter-command "frotz"`；
4. licenses/LICENSE-GPL-3.0.txt 在位 + GPL-3.0 文本关键词；
5. 截断注入拒绝语义负向用例：把真实 elisp 原地覆盖为截断载荷 →
   断言尺寸防漂移逻辑必须检出拒绝（读回 != 63201）→ 恢复原载荷 →
   复验 63201 字节与版本头双锚点（证明探针路径真实读写包目录，
   且防漂移断言对截断有实际拦截语义）。

探针合计 22 项原子断言（5 组）。

## 真机验证（鸿蒙侧，2026-09-27）

`python3 scripts/ohc-run.py conan-verify inform-mode 1.6.2`
（华为 PC 真机，Conan 2.29.1 + ohos-aarch64 profile）：
**八道门禁全过**，判定「配方验证通过，可标记 status: published」。

- G0 ✅（构建系统 unknown，跳过预查询）
- G1 ✅ 配方完整性（name/version/source/build/package/package_info/export_sources/补丁应用调用/conandata/test_package 全项）
- G2 ✅ conan create 干净构建（真机实跑，含 test_package 探针）
- G3 ✅ 系统同名库隔离（R26）
- G4 ✅ 产物完整性
- L2/L4/L5 ✅（纯源码包无 cache 路径，跳过）
- 探针真机输出：`inform_mode_probe: all assertions passed`（22 项 [OK]
  逐项全过；含负向拒绝语义断言，真机 conan create 日志留存于设备侧，
  结论性证据以 reports/conan-verify-report.md 承载——PR 禁止 *.log，
  rule 19）

产物实测：`share/emacs/site-lisp/` 精确 1 文件（inform-mode.el，63201
字节）、`licenses/` 1 文件（LICENSE-GPL-3.0.txt，35149 字节），无多余
文件混入。源码直连 IF Archive 官方 URL 下载成功（inform-6.42-r9.tar.gz，
sha256 核验通过）；全引用
inform-mode/1.6.2@ohpcd/stable#1b41f441…:da39a3ee…。

配方层要点（真机实证）：

- export_sources 的本地 LICENSE-GPL-3.0.txt 正常随配方导出并落入
  source_folder，package() 按指定文件名复制——basic_layout 构建目录混入
  的 conanbuild*.sh/conaninfo.txt 天然不参与打包（日志确认 package()
  恰好打包 1 '.el' + 1 '.txt'）；
- build() 防漂移校验真机同过（63201 字节断言与探针双保险）；
- make -j20 的 jobserver mkfifo 在 /storage 报 Operation not permitted
  属已知环境怪癖，不影响编译链接（探针正常产出并实跑）。

## 复验（2026-09-27 20:25，PR #13227 AI 检视后加固）

atomgit-bot AI 检视（P0/P1=0）提出 P2/P3：P2=reports/conan-create.log
违反 rule 19（PR 禁止 *.log）；P3=负向用例「名不副实」（无拒绝语义）、
草稿 doc_file 悬空（误报——配套 .md 实际在 PR 内）。处置：

1. **删除 reports/conan-create.log**，构建证据由
   reports/conan-verify-report.md 结论性摘要承载（bot 认可方案）；
2. **负向用例改为真实拒绝语义**：原地截断注入 → 尺寸防漂移断言检出
   拒绝 → 恢复 → 复验 63201 字节 + 版本头（原子断言 20 → 22）；
3. 本机 MinGW L0 22/22 exit 0；**真机复验**：git fetch fork 新 head →
   checkout paths → `conan-verify` 八道门禁再次全过（G2 conan create
   PASS，探针 22 项 [OK] 全过，终态「可标记 status: published」），
   本报告 Date 与 G2 证据行已同步复验结果。

## 参考

- IF Archive source 索引: https://ifarchive.org/indexes/if-archive/infocom/compilers/inform6/source/
- Debian inform-mode: https://packages.debian.org/trixie/inform-mode
- 上游 Git 仓库: https://github.com/rupertl/inform-mode
