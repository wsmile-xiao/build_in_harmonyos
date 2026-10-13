# xwrited

Display write(1) and wall(1) messages as desktop notifications
(GApplication + GDBus client, GLib based).

- 上游：<https://code.guido-berhoerster.org/projects/xwrited/>
- 版本：3（`xwrited --version` 打印 `xwrited 3`）
- 产物：`bin/xwrited` 命令行守护 + autostart desktop 文件 + de/en/id 本地化目录
- 适配：手写 Makefile，utmpx 后端（`OS_NAME=OHOS`），零补丁
