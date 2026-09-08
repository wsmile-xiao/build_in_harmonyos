# E552 — lang-preflight 源码统计被生成文档资产污染致 mixed 误报：文档资产识别与按主体裁定

## 问题概述

AI Worker 协议 R47 强制在适配前执行 lang-preflight（lang_detect.py），其三级判定为
manifest > 构建系统 > 源码统计(≥70%)，冲突判 mixed 并**自动写入 env_unsupported 终态**。
当上游把 doxygen 等工具生成的 HTML 文档提交进 tag 时（jquery.js、search/*.js、
*.html、*.svg 等文档资产），source_stats 会把这些文件按扩展名计为 nodejs/html
"源文件"。一旦文档资产数量超过真实源码文件，统计主体即被劫持，产生
"manifest=cpp 但统计 nodejs 占 79%" 型冲突 → `detected=mixed` → 自动终态
env_unsupported（含 R46 兜底写入共享路径 result.json），整个任务被误杀。

## 典型错误（utfcpp20 0.3，任务 #5895 实录）

```
❌ 语言不匹配: task=cpp, detected=mixed → env_unsupported
{
  "expected": "cpp",
  "detected_language": "mixed",
  "language_evidence": {
    "build_system": "cmake",
    "manifest": "CMakeLists.txt project(",
    "source_stats": "源文件 28 个（nodejs:22, cpp:6），主体占比 79%"
  },
  "notes": [ "冲突: manifest=cpp 但统计 nodejs 占 79% → mixed" ]
}
```

真实源码为 include/utfcpp20.hpp + src/*.cpp + tests/*.cpp 共 6 个 C++ 文件
（100% C++，CMake 构建）；"nodejs:22" 全部是 doc/html/ 下的 doxygen 生成资产
（jquery.js、dynsections.js、search/*.js 等）。

## 识别特征（与真实混合项目的区分）

1. `language_evidence.source_stats` 中 nodejs/html 计数异常大，且这些文件路径
   **全部位于 doc*/ 目录**（`find <src> -name "*.js" -not -path "*/doc/*"` 计数为 0）；
2. manifest 判定（如 `CMakeLists.txt project(`）与构建系统判定（cmake/meson）
   均与任务语言一致——真实混合项目至少有一处实质冲突；
3. js/html 文件内容为生成的 HTML/JS（含 jquery 特征串），非手写逻辑。

## 根因

lang_detect 的源码统计按扩展名计数，未区分"生成文档资产"与"手写源码"。
文档类扩展名（js/html/css）在含提交文档的仓库里天然数量庞大，主体占比
超过 70% 即与 manifest 判定冲突 → mixed。

## 处置方案（三步）

1. **取证**：列出全部 js/html 文件路径，证明全部位于 doc*/ 文档目录；
2. **按主体裁定**：manifest 与构建系统均判任务语言 → 按任务语言继续适配
   （R47 附录"绑定包按源码主体判"同族裁定；先例：tinydng、tinyvdb、hashchop、
   smashtable 的 lang-preflight 误报族）；
3. **终态覆盖**：全门禁闭环后 `ohc-run.py result <pkg> <ver> --status success
   --force` 覆盖自动写入的 env_unsupported 终态（注意共享路径
   ~/ohpcd-ai-worker-result.json 也要覆盖，防跨任务串扰），误报证据写入 notes.md。

**禁止**：删除上游文档资产、篡改 lang_detect 脚本规避统计——属篡改上游/框架文件。

## 查重与新增价值

知识库既有 lang-preflight 误报条目覆盖：rockspec manifest 优先级（E543-234A，
hashchop）、pybind11/裸 CPython 绑定（tinydng/smashtable，D.4-2）、残缺解压
（stats）、BUILD.gn/oh-package.json（另一族）。**文档资产污染 source_stats
为本族第五类独立触发向量**，此前无条目覆盖；本条给出可直接复用的识别特征
（三条判定）与处置流程。

## 适用范围与反例

- 适用：上游提交了生成文档资产的 C/C++ 项目，manifest/构建系统/真实源码主体一致；
- 反例：js 文件不在 doc 目录（真实 nodejs 混合项目）、或 manifest/构建系统
  确实与任务语言冲突——此时属真实语言不匹配，遵 env_unsupported 交平台；
- 解除条件：lang_detect 修复文档目录白名单后本条自动失效。

## 触发实例

utfcpp20 0.3（任务 #5895，PR !8542）：按本条处置完成全部适配——上游 16/16
测试真机全量通过、消费者测试 9 断言通过、conan-verify 八门禁 PASS、W3/W4 通过、
CI 绿、AI Review 无问题——证明误报处置流程可完整闭环。
