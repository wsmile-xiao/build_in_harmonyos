# since — 带状态的 tail

## 简介
`since` 是一个「有记忆的 tail」：它记录每个文件上次被查看到的位置，
再次运行时只输出这之后新追加的行，适合反复查看日志而不想重看旧内容。
状态默认保存在 `$HOME/.since`，可用 `SINCE` 环境变量指定其他路径。

## 版本历史
- 1.1: 编译成功 (2026-09-21)

## 特点
- 纯 C 单文件项目（since.c，约 1.8k 行），手写 Makefile，无 configure
- 无第三方依赖，只用 POSIX 接口；inotify 存在时用于 `-f` 跟随模式
- 上游站点仅提供 HTTP，取 salsa.debian.org 的 upstream 分支（内容逐文件校验一致）

## 用法
```bash
since /var/log/messages            # 只显示上次查看之后新增的行
since -z /var/log/messages         # 丢弃既有内容，把当前位置记为起点
since -f /var/log/messages         # 跟随模式（inotify 可用时事件驱动）
since file1 file2                  # 多文件，输出带 ==> file <== 分隔头
```
