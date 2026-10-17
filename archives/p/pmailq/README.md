# pmailq — Postfix 邮件队列管理工具

## 简介

pmailq 解析 Postfix `mailq` 输出，按发件人、错误信息、大小、队列状态批量列出（list）、机器可读输出（parse）或删除（del）队列消息。

- **主页**: https://github.com/k0lter/pmailq
- **许可证**: WTFPL-2.0
- **语言**: Python 3（单文件脚本）
- **构建系统**: custom（无编译，直接安装脚本）

## 运行方式

```bash
pmailq [OPTIONS] [ list | parse | del ]
pmailq -e "*@example.com" parse
pmailq -m "*connection*timed*out" del
pmailq --help
```

## 依赖

- 构建时：无（仅需 python3 做语法校验）
- 运行时（可选）：postfix（提供 `postqueue` / `postsuper`）、python3

## 鸿蒙平台适配要点

1. 纯 Python 脚本，无需工具链补丁；在 OHOS Python 3 下直接运行
2. 上游无测试套件，test_package 用 PATH 垫片伪造 postqueue/postsuper 做全链路验证
3. 上游 0.7 包内 `_VERSION` 仍为 '0.6'，属上游版本常量滞后，不视为适配缺陷
