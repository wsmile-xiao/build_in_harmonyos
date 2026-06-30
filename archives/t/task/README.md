# Taskwarrior

Taskwarrior是一个命令行任务管理器，用于追踪和管理待办事项。

## 功能
- 任务创建、修改、删除
- 任务优先级和项目分组
- 任务依赖关系
- 报告生成

## 安装
```bash
curl -fsSL https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/pkgs/install.sh | sh -s -- task 2.6.2
```

## 使用
```bash
task add Buy groceries
task list
task 1 done
```

## 鸿蒙适配说明
- 同步功能已禁用（缺少GnuTLS）
- 需要ncurses库支持
