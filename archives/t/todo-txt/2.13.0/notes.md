# todo-txt 2.13.0 适配笔记

## 软件类型

- 纯 Bash 脚本应用，无 C/C++ 编译与链接步骤
- 上游 release tarball 只包含 `todo.sh`、`todo.cfg`、`todo_completion`
- 包类型设为 `application`，`cpp_info.libs = []`，仅暴露 `bin/`

## OHOS 适配

- 上游 `todo.sh` 已使用 `#!/usr/bin/env bash`，满足 OHOS 无 `/bin/bash` 的路径约束
- 默认配置安装为 `etc/todo/config`，并通过 `TODOTXT_GLOBAL_CFG_FILE` 注入运行环境
- 无系统同名动态库风险，R26 不适用
- 无 `settings.os == "Linux"` 判断，满足 R32

## 测试

- `test_package/test_todo_txt.sh` 使用打包后的 `todo.sh` 执行真实 CLI 流程：
  - `todo.sh -V` 校验版本
  - `add` 新增任务
  - `list` 查询任务
  - `do` 完成任务
  - `archive` 归档任务
  - 断言 `done.txt` 含归档记录且 `todo.txt` 已清空
- `MANIFEST.yml` 已声明 release tarball 不含完整上游测试套件，消费者测试覆盖核心 CLI 行为

## 验证命令

```bash
conan create archives/t/todo-txt/2.13.0 --build=missing
```
