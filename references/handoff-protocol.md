# HANDOFF 协议（脚本 → AI 交接格式）

> 脚本在需要 AI 介入时输出结构化交接块。AI 读到后按 `AI NEXT ACTIONS` 执行，完成后运行 `RESUME_CMD`。

## 交接块格式

```
╔═══ HANDOFF ══════════════════════════════════╗
║ EXIT_REASON: configure_failed                ║
║                | dependency_missing          ║
║                | build_tool_missing           ║
║                | command_mismatch             ║
║ EXIT_CODE: 2 (resumable) / 1 (fatal)         ║
║ STEP_FAILED: Step3                           ║
║ RESUME_CMD: python3 $SKILL_ROOT/scripts/ohc-run.py build ... --resume-from=Step3
║ KNOWLEDGE_HIT: E007 (config.guess) / none    ║
║ KNOWLEDGE_GAP: true/false                    ║
║ MISSING_DEPENDENCY: <软件名>                   ║
║ PRECOMPILED_AVAILABLE: yes/no                ║
║ LOG_FILE: <日志路径>                          ║
║ SRC_DIR: <源码路径>                           ║
║ AI NEXT ACTIONS:                             ║
║   1. 具体操作                                 ║
║   2. 运行 RESUME_CMD 继续                     ║
╚══════════════════════════════════════════════╝
```

## 字段说明

| 字段 | 说明 |
|------|------|
| `EXIT_REASON` | 退出原因：configure_failed / dependency_missing / build_tool_missing / command_mismatch |
| `EXIT_CODE` | 2 = 可恢复（resumable），1 = 致命（fatal） |
| `STEP_FAILED` | 失败发生在哪一步 |
| `RESUME_CMD` | 修复后继续执行的命令 |
| `KNOWLEDGE_HIT` | 知识图谱匹配结果（E 编号或 none） |
| `KNOWLEDGE_GAP` | 是否存在知识缺口 |
| `MISSING_DEPENDENCY` | 缺失的依赖软件名 |
| `PRECOMPILED_AVAILABLE` | 是否有预编译包可用 |
| `LOG_FILE` | 日志文件路径 |
| `SRC_DIR` | 源码路径 |
| `AI NEXT ACTIONS` | AI 应执行的具体操作步骤 |
