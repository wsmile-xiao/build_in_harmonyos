# jupyter-events

Jupyter Event System 库：一个纯 Python 事件系统，为 Jupyter 应用提供结构化、可验证、异步的事件日志与 schema 验证。

- **版本**: 0.12.0
- **构建系统**: hatchling (纯 Python 包)
- **许可证**: BSD-3-Clause
- **上游**: https://github.com/jupyter/jupyter_events

## 功能

- `jupyter_events.EventLogger` — 异步事件日志器，支持 schema 注册与数据校验
- `jupyter_events.EventSchema` — JSON Schema 定义与验证
- CLI 命令 `jupyter-events`：
  - `jupyter-events --version`
  - `jupyter-events --help`
  - `jupyter-events validate <schema>` — 校验 schema 是否合法（对合法 schema 返回 0，非法返回 1）

## 适配说明 (OHOS / HarmonyOS PC aarch64)

纯 Python 包，无需编译。Conan 配方通过 `pip install` 将包与运行时依赖
(referencing、jsonschema、python-json-logger、pyyaml、traitlets、packaging、
rfc3339-validator、rfc3986-validator、click、rich) 装入包目录的
`lib/python3.12/site-packages`，并提供 `bin/jupyter-events` 入口脚本，
通过 `PYTHONPATH` 运行。

## 版本索引

| 版本 | 状态 | 日期 |
|------|------|------|
| 0.12.0 | built | 2026-08-01 |
