# 补充 PR #13428：源码包 noarch 与资产校验的边界（不能豁免真实功能测试）

## 原问题与纠正

纯源码语言库可能没有 C/C++ 构建系统，也没有 ELF 交付物。noarch package_id 与标准语言生态布局可以用于这类资产，但旧稿“可验证性全部落在完整性”以及“无 API 可调”的结论错误：语言 API 不是 C ABI，却仍能由真实解释器执行。文件哈希不能证明宏展开或求值行为。

## 正确流程

保留固定源码 inventory、size、SHA-256 校验；安装为正常语言源码布局，并单列资产完整性。另用已发布目标运行时执行所有核心官方回归入口、实际安装消费者与独立平台场景。Common Lisp 导出标准 `CL_SOURCE_REGISTRY` S-expression，不采用旧稿非标准 `ASDF_SOURCE_REGISTRY_ADDITIONAL` 和无效 glob。语言/版本的任务身份仍须按平台真实记录处理，不能据目录规范化把不同软件任务等同。

## 真实验证与新增条目

PR #13428 的 `agnostic-lizard-20261005-r001` 实际原生 Conan create RC0；27/27 只表示源码资产。未修改官方 `examples.lisp`、`walking-examples.lisp` 两个完整核心入口2/2；真实宏展开求值消费者1/1；中文空格 HMDFS 文件实际读写专项1/1。唯一 launch、完整链验证、release/postrelease及自有进程清零完成。细节、查重增量和适用边界见同 PR 的 `E2026100505-draft-2301_80739235` 配对草稿。解释模式不证明编译模式、可选 debugger 或第三方互操作；本结果也不是平台 CI 或提审回执。
