# mathc 2019.02.16.0 适配笔记

## 编译环境
- 构建系统: 无（纯 C99 单翻译单元库，官方 tag 仅 LICENSE/README.md/mathc.c/mathc.h）
- 编译日期: 2026-09-22
- 编译器: clang 15.0.4 (OHOS aarch64 toolchain, /data/service/hnp/bin/clang)
- 状态: built

## 编译步骤

1. 官方源码：https://github.com/felselva/mathc tag v2019.02.16.0
   tarball SHA-256: 2caa0830215491fbc9cf62e2eb30e36e4747d9568d25633542914851b20c0e67
   （实测下载文件与官方 git clone tag 逐字节一致：mathc.c a63ed7f1…、mathc.h 2d74b58b…）
2. init-build：官方 tarball 直接下载失败（URL 返回 HTML），改用官方 tag 归档地址
   `https://github.com/felselva/mathc/archive/refs/tags/v2019.02.16.0.tar.gz` 成功
3. lang-preflight (R47): task=cpp, detected=c — 兼容族，通过
4. 配方：mathc 无构建系统，参照 sili 先例在 conanfile.py 直接编译 mathc.c → libmathc.a
   （R33 编译器取自 Conan conf；R32 os in ("Linux","OHOS")；package_info 补 system_libs=["m"]，
   因 mathc.h 公开 API 使用 sqrtf/sinf/cosf）
5. conan-init 生成配方后重写 conanfile.py；conandata.yml 填入实测 SHA-256
6. **上游缺陷修复**：官方 v2019.02.16.0 的 mat3/mat4_rotation_quat 四元数旋转矩阵
   实现含两处缺陷（q0[8] 越界读 → 应为 q0[2]；对角项 (yy-zz)/(xx-zz)/(xx-yy) →
   应为 (yy+zz)/(xx+zz)/(xx+yy)），导致绕 Z 90° 旋转结果错误；经 git clone 官方
   tag 逐字节核对 SHA-256 确认为上游真实缺陷，生成 patches/0001-mathc.c.patch（+8/-8）
7. HarmonyOS 专项测试 test_package/harmonyos_test.c：12 项断言（平台宏识别 + vec3
   加减/点积/叉积/长度 + mat4 identity/平移 + quat 绕 Z 90° 旋转 + perspective 逆矩阵
   + nearly_equal/clampi），修复后 ALL PASS 退出码 0
8. conan-verify 8 道门禁全 PASS（G0-G4 + L2/L4/L5），G2 conan create 通过
9. finish（W2 结构 + R36 依赖 + W3 本地 CI）：W3 首次 JC fail 命中其他库基线空文件
   （cloog/kics），执行基线隔离复验（记录路径+隔离前 SHA-256 → git rm --cached →
   重跑 pass → 恢复并核对 SHA-256）后 .ci-result.json exit_code=0

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | init-build 下载返回 HTML | 传入仓库首页 URL（HTML 页） | 改用官方 tag 归档 URL（archive/refs/tags/v2019.02.16.0.tar.gz） |
| 2 | quat 绕 Z 90° 旋转断言失败 | 官方 v2019.02.16.0 mat3/mat4_rotation_quat 上游缺陷（q0[8] 越界 + 对角项符号错误） | patches/0001-mathc.c.patch 修复 + 专项测试复验 12/12 |
| 3 | 首次测试还失败 | 测试文件自身 rot[4] 数组过小（mat4 需 16 元素） | 修正为 rot[16]，非库问题 |
| 4 | W3 JC1/JC5 junk fail | 零提交分支 junk_check full 模式扫描整仓，命中其他库（cloog/kics）main 基线空文件 | 基线隔离复验（git rm --cached → 重跑 → 恢复 + SHA-256 核对），复用 E291/dr_mp3 知识 |
| 5 | conandata.yml 被 E017 镜像注入污染 | conan-verify E017 预防临时注入 ghfast/gh-proxy 镜像未清理 | 提交前扫描并恢复官方 HTTPS URL，删除 .ghfast-bak/.orig 残留，重核 SHA-256 |

## 源码修改

- patches/0001-mathc.c.patch：修复官方上游 mat3/mat4_rotation_quat 四元数旋转矩阵缺陷（+8/-8）
- 补丁为 correctness 类型，非平台专属；已实测验证（guard: verified）

## 依赖版本

无外部依赖（requirements 为空，零依赖库）。

## 上游测试台账（双口径）

- 官方 tag v2019.02.16.0 归档清点（`tar tzf` 正式证据）仅含：
  `mathc-2019.02.16.0/{LICENSE, README.md, mathc.c, mathc.h}` — **无测试源、
  无测试框架、无样例/基准/fixture、无构建系统**（Makefile/CMake/configure 均不存在）
- **source_declared_total = 0**（官方 tag 按完整枚举无任何上游测试声明）
- **configured_executable_total = 1**（当前 OHOS 配置注册的独立可执行用例：
  test_package/harmonyos_test.c）
- **executed_passed_total = 1（本配置可执行集合通过率 1/1 = 100%）**
- 全量通过率：通过 1 / 发现 0（上游）+ 1（鸿蒙专项）= 1/1 可执行项（上游无声明项不计分母的
  全集口径：官方 tag 声明 0 项，实测无可运行上游用例，如实记录）
- 映射逐项：上游声明（无）→ 构建配置（无注册）→ 构建目标（无上游目标）→ ctest -N
  （本配置 1 项 test_mathc）→ 实际执行日志（reports/w3-local-ci.log 内 ctest 1/1
  test_mathc PASS）
- 补充：mathc 为纯数学库，官方仓库长年无独立测试套件（README 亦未声明），
  专项测试 12 断言覆盖 vec/mat/quat 全功能域

## 验证结果

- HarmonyOS 专项测试 harmonyos_test.c: 12/12 断言 ALL PASS，退出码 0
- conan create: G2 PASS（含 test_package 消费者验证 1/1）
- W3 本地 CI: .ci-result.json exit_code=0（基线隔离复验后）
- conan-verify 8 门禁全 PASS

## 知识候选与路径决定

- 路径判定：**B（知识库扩展）** — reports/knowledge-candidate-ledger.md 七轴查重结论：
  候选 1（mathc quat 旋转矩阵上游缺陷）四范围未命中、组合/边界新增且经真实日志验证 →
  **new_draft**，创建 knowledge/drafts/mathc-2019.02.16.0-quat-rotation-matrix-defect.{kv,md} 配对；
  候选 2（JC 基线隔离）复用 E291/dr_mp3 既有知识，不建新草稿
- PR 前缀：【知识库扩展】

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py | Conan 配方（纯 C 库直接编译，R33/R32/R26 合规） |
| conandata.yml | 官方 URL + 实测 SHA-256 |
| patches/0001-mathc.c.patch | 上游 mat3/mat4_rotation_quat 缺陷修复（correctness） |
| test_package/harmonyos_test.c | HarmonyOS 专项测试（12 断言，非空壳） |
| test_package/MANIFEST.yml | 上游测试声明（官方 tag 无上游测试，如实记录） |
| reports/knowledge-candidate-ledger.md | 知识候选台账 + 七轴查重 + 路径决定 |
| knowledge/drafts/mathc-2019.02.16.0-quat-rotation-matrix-defect.{kv,md} | 路径 B 知识草稿 |

## 注意事项

- mathc 为非 CLI 纯库（无 bin 产物），按 R38 无需 commands.json
- 消费者用例 = test_package/harmonyos_test.c（通过已安装公开头文件 mathc.h + libmathc.a
  调用公开 API），与上游（无）/鸿蒙专项（同一文件，L1 消费者视角）分别计数
- 禁止 force-push/rebase/merge；commit/push/PR 按任务授权执行

---

**编译结束**: 2026-09-22
**最终状态**: built
