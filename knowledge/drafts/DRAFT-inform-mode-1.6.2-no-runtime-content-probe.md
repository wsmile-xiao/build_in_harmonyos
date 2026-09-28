# OHOS PC 无运行时（Emacs 未移植）的解释型/数据型软件包：以内容级消费者探针（清单+尺寸防漂移+版本头/功能符号+许可证+负向注入）代替运行时验证

- **草稿 ID**: DRAFT-inform-mode-1.6.2-no-runtime-content-probe
- **来源**: inform-mode 1.6.2 HarmonyOS PC 适配（真机 conan 2.29.1 消费者探针 5 组断言全过）
- **分类**: conan / recipe / testing / ohos
- **状态**: 本地草稿（随 PR #13227 挂 knowledge/drafts/，路径 B 知识库扩展申请中）

## 问题 / 错误签名

- **无运行时可验证**：解释型软件包（Emacs Lisp 单文件 inform-mode.el）的运行方式依赖 Emacs，OHOS PC 真机未移植 Emacs——`load-file`/`byte-compile` 在真机不可行，`emacs: command not found` 类失败。
- **验证强度塌缩风险**：若退化为只断言"文件存在"，无法区分完整包与截断/篡改包（截断到 10 字节的 elisp 同样"存在"）；审查按 E2E 消费者用例口径不予通过。
- **环境不一致风险**：CI Linux 有 Emacs 而真机无；若运行时路径为唯一验证，两类环境口径分裂，真机必挂。
- **可观测特征**：消费者测试只有文件存在断言；或运行时条件判断缺失导致真机 conan create 在 test 阶段失败。
- **复现**：HarmonyOS PC 真机（aarch64，无 Emacs）直接复现；CI Linux 有 Emacs 不触发——**仅真机可见**。

## 根因

1. **OHOS PC 未移植 Emacs**：解释型包的运行时验证在目标平台不存在，属平台能力边界而非配方缺陷。
2. **验证设计默认"能跑起来"**：常规消费者测试以运行为前提，未为"无运行时平台"设计内容级基线。
3. **弱断言惯性**：数据/源码类包容易滑向"文件在就行"的最小断言，缺乏逐文件内容锚点。

## 最小修复方案

以五层内容级消费者探针代替运行时验证（test_package/inform_mode_probe.cpp）：

1. **目录精确计数**：site-lisp 恰好 1 个文件（防多余/缺失文件混入）；
2. **尺寸防漂移**：文件在位、非空、63201 字节精确断言（与 recipe build() 防漂移校验双保险）；
3. **元数据+功能符号**：`;; Version: 1.6.2` / `;; Released: 10-Oct-2013` / `;; Keywords: languages` 版本头，GPL 声明行，`(defun inform-mode ()`、`;;;###autoload`、`(defvar inform-mode-map nil`、`(defvar inform-mode-syntax-table nil`、`(defcustom inform-command "inform"`、`(defcustom inform-interpreter-command "frotz"` 逐条断言——证明内容完整且为真实发行物；
4. **许可证全文**：licenses/LICENSE-GPL-3.0.txt 在位 + "GNU GENERAL PUBLIC LICENSE" / "Version 3, 29 June 2007" 关键词；
5. **负向截断注入拒绝语义**：把真实 elisp 原地覆盖为截断载荷→尺寸防漂移断言检出拒绝（读回 != 63201）→恢复原载荷→复验 63201 字节+版本头（证明探针路径真实读写包目录，且防漂移断言对截断有实际拦截语义）。

要点：

- 运行时可用场景（CI Linux 有 Emacs）可叠加 byte-compile 条件路径（探测到 `emacs` 才执行），但不得作为唯一验证；内容级断言为跨环境一致基线。
- 尺寸断言常量必须来自上游发行物实测，与 recipe build() 防漂移共用同一常量来源，防止两端漂移。

回退方案（无 C++ 工具链的场景）：POSIX shell（grep/cmp/wc -c）实现同五层断言，断言语义不变，仅载体不同。

## 验证结果

| 环境 | 结果 |
|------|------|
| 本地（Windows MinGW）· 按 package() 布局 1:1 模拟包 | inform_mode_probe 5 组断言全过 |
| HarmonyOS PC aarch64 真机 · Conan 2.29.1 | conan create 消费者探针 5 组断言全过、EXIT=0 |
| CI Linux | 探针编译运行 5 组断言全过（无 Emacs 依赖） |

## 禁止策略

- 禁止只做文件存在断言——无法区分完整包与截断/篡改包，消费者测试形同虚设，审查不通过。
- 禁止以运行时运行为唯一验证（byte-compile/load-file 无条件执行）——OHOS PC 未移植 Emacs，真机必挂；运行时依赖必须做成条件路径，内容级断言为基线。
- 禁止尺寸/标记断言与上游发行物脱钩——断言常量必须来自上游实测，否则防漂移失效。

## 相关

- 相似条目：E193（大小写敏感测试在 HMDFS 挂——测试用例选择视角）；DRAFT-inform6-compiler-6.42-case-insensitive-alias-samefile（package() 大小写别名副本 SameFileError——打包阶段视角）。本条为 testing 阶段无运行时验证视角，与其互补不重叠。
- 关联经验：inform6-library 6.12.6（纯数据包内容级探针范式，14 文件清单 + 逐文件发行标记）与 mypaint-brushes/openkim-models/lebiniou-data 等数据包同族——"无原生构建产物即无运行时验证"的通用模式已多次实证。
