# fabric-completion 1 适配笔记

## 上游与来源

- fabric-completion：Python Fabric 部署工具（fabfile.org）`fab` 命令的
  bash 补全脚本（任务补全 + 长选项补全），纯 bash 数据，无编译产物。
- 上游仓库：https://github.com/n0740/fabric-completion（2015 年停更）。
  上游**无 tag/release**（Homebrew livecheck 亦 skip），故以 commit
  `5b59104` 钉死。本配方采用与 **Homebrew formula fabric-completion
  version 1** 完全相同的 source URL 与 sha256（`34db5a8b…a934a7`，
  本地下载实测与公式记录一致），版本号「1」即公式版本，与任务卡一致。
- tarball 仅 2 个文件：`fabric-completion.bash`（124 行）+ `README.md`
  （46 行），纯 ASCII LF。

## 许可证

- **MIT**（Homebrew 公式 license 字段 + 脚本头部全文：Copyright (C)
  2011 by Konstantin Bakulin + 完整 MIT 条款）。
- tarball 无独立 LICENSE 文件 → 本包**不设 licenses/ 目录**（保持上游
  发行原样），许可文本随脚本头部携带，探针逐字断言。

## OHOS 适配

纯数据包，无编译无链接（kicad-demos/inform6-library/ldraw-parts 范式）：

- `build()` 防漂移：2 文件在位 + 全树总数 == 2；
- `package()` 显式逐文件复制（文件少，比 copy("*")+excludes 更稳）：
  - `fabric-completion.bash` → `share/bash-completion/completions/`
    （Debian bash-completion 生态惯例路径；Homebrew 同语义仅多一步
    改名为 `fabric`，本包保留上游文件名——上游 README 的 source
    指令即指向该名）；
  - `README.md` → `share/doc/fabric-completion/`；
- `package_id` 清空；`cpp_info.resdirs` = completions 目录；
- 无 runenv：生态无统一环境变量，消费者按 README 指引 source 脚本。

## 测试口径

上游无测试套件（单脚本纯数据）。适配后消费者探针
（`test_package/fabric_completion_probe.cpp`）5 组断言：

1. 包内清单：completions/fabric-completion.bash 与 doc/README.md
   在位非空，completions/doc 各恰 1 文件，全树恰 2 文件（排除
   conan 2 写入包根的 conaninfo.txt/conanmanifest.txt 簿记文件，
   真机首跑实测修正口径）；
2. 脚本内容锚点：shebang、2011 Bakulin 版权、MIT 条款、
   `FAB_COMPLETION_CACHE_TASKS=true`、`.fab_tasks~` 缓存文件名、
   `__fab_completion` 函数、`fab --shortlist`/`fab --help`/`compgen`、
   上游原样拼写 `__fab_chache_mtime`（"chache" 为上游笔误，不修补）；
3. README 锚点：标题/Features/Installation（source 指令行）/Settings
   （两个环境变量名）；
4. 静态完整性：脚本 124 行、README 46 行精确计数，脚本首行 shebang +
   末行 `complete -o default -o nospace -F __fab_completion fab` 注册行，
   全文件无 CR（LF 发行）；
5. 截断/坏注册行注入负向（写入→校验拒绝→清理）。

## 真机验证（HarmonyOS PC 真机，2026-09-26）

### 首验 G2 FAIL：conan 2.29.1 拒绝裸单段版本号（已修复，本分支 1.0 归一化提交）

- `ohc-run.py conan-verify fabric-completion 1`：G0/G1 PASS，G2 FAIL
  ——`conan create` 在 **export 阶段**即报
  `ERROR: Invalid package version '1'`，未进入下载/构建。
- 真机最小复现（conan 2.29.1）：`version="1"` export 即拒绝；
  `version="1.0"` export 成功（`vt/1.0#...`）。
- 知识图谱命中 E225（CMakeToolchain 临时布局）为**误报**——真实根因
  是版本号格式；教训：G2 FAIL 先看 conan-create.log 首行真实 ERROR，
  再采信知识图谱建议。
- 修复：版本号归一化为 `1.0`（Homebrew formula version=1 的 conan
  合法形式，语义不变），manifest/conanfile/目录同步，重跑验证。
- 官方 main 无任何裸单段版本号先例（全部 X.Y 形式），归一化与本库
  惯例一致。

### 验证结论（重验，2026-09-26 16:20 实录）

- `conan-verify fabric-completion 1.0` **八道门禁 G0-G4/L2/L4/L5
  全绿，Verdict: PASS，判定「可标记 status: published」**
  （reports/conan-verify-report.md）。
- G2 conan create 真消费者探针 28 项断言逐项 [OK]，
  `fabric_completion_probe: all assertions passed`
  （reports/conan-create.log）。
- G3 无系统同名库冲突；G4 空包 ID 为纯数据包预期现象（package_id
  清空，与 ldraw-parts 同口径）；L2/L4/L5 无 cache 路径跳过。
- 重验前修正一处：探针「全树恰 2 文件」初版在真机 FAIL——conan 2
  在包根写入 conaninfo.txt/conanmanifest.txt 簿记文件；已改计数
  排除簿记（本地带簿记模拟复测通过）后重验全绿。
- ohc-run 自动 ghfast 注入后下载成功并自动恢复原始 conandata.yml
  （E017 预防机制实测工作正常）。

## 参考

- 上游仓库: https://github.com/n0740/fabric-completion
- Homebrew formula: https://formulae.brew.sh/formula/fabric-completion
- Fabric 官网: http://fabfile.org/
