# SKILL 执行流程反馈报告

> 本报告由 SKILL 自动生成，记录本次编译适配全流程中的失败、效率和改进发现。
> 文件位置: `feedback/SKILL_FEEDBACK_{ID}.md`（项目根，与 `knowledge/` 同级）

---

## 背景

- **软件名称**: {software}
- **版本**: {version}
- **构建日期**: {build_date}
- **构建系统**: {build_system}
- **上游仓库**: {upstream_url}
- **适配路径**: {adaptation_path}
- **补丁数量**: {patch_count}
- **编译依赖**: {dependencies}
- **最终状态**: {build_status}

---

## 情况

### 执行概要

本次 SKILL 执行流程涵盖从源码准备到 PR 提交的完整链路。以下是关键节点的执行情况：

| 阶段 | 步骤 | 结果 | 说明 |
|------|------|------|------|
| init-build | 源码下载/解压 | {init_build_result} | {init_build_note} |
| build | 编译构建 | {build_result} | {build_note} |
| conan-verify | 配方验证 | {verify_result} | {verify_note} |
| finish | 归档收尾 | {finish_result} | {finish_note} |
| submit | PR提交+AI检视+CI | {submit_result} | {submit_note} |

### 失败与问题

{failures_and_issues}

> 如无失败，填写"本次流程未遇到阻塞性问题"。

### 知识图谱使用情况

- **引用知识条目**: {knowledge_ref}
- **新增知识草稿**: {knowledge_drafts}
- **引擎命中情况**: {engine_hits}
- **未覆盖的错误模式**: {uncovered_patterns}

### AI 检视结果

- **检视阶段到达**: {ai_review_phase}
- **变更摘要评估**: {summary_evaluation}
- **检视意见数量**: {review_opinion_count}
- **检视意见处理**: {opinion_handling}

### CI 结果

- **本地 CI 模拟 (W3)**: {local_ci_result}
- **远程 CI (PR 校验)**: {remote_ci_result}
- **CI 失败原因**: {ci_failure_reason}

### 效率分析

- **HANDOFF 次数**: {handoff_count}
- **重试次数**: {retry_count}
- **关键瓶颈**: {bottlenecks}
- **耗时较长的步骤**: {slow_steps}

---

## 建议

### SKILL 设计改进

{skill_design_suggestions}

> 针对 SKILL 流程设计、门禁机制、HANDOFF 机制等方面的改进建议。
> 例如：某步骤门禁过于严格/宽松、流程顺序不合理、缺失某个检查环节等。

### 模板改进

{template_suggestions}

> 针对 conanfile.py 模板、PR body 模板、test-report 模板等方面的改进建议。
> 例如：模板缺失某些字段、自动填充覆盖率不足、占位符过多等。

### 自动化补全

{automation_gaps}

> 针对需要人工介入的环节，提出自动化改进建议。
> 例如：某些检查可以自动化、错误恢复可以更智能、依赖解析可以更完善等。

### 知识图谱覆盖

{knowledge_coverage_gaps}

> 针对知识图谱未覆盖的错误模式，建议新增哪些 E-entry。
> 例如：本次遇到的新错误模式应该沉淀为知识条目等。

---

## 作者

- **姓名**: {author_name}
- **邮箱**: {author_email}
- **Agent ID**: {agent_id}
- **生成时间**: {timestamp}
- **PR 编号**: {pr_number}
- **Git Commit**: {git_commit}