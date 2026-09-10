# cfingerd

可配置的安全 finger 守护进程(Infodrom 维护),替代 GNU fingerd / MIT fingerd 等标准 finger 服务。支持逐用户开关 finger 服务、以 nobody 或用户身份运行脚本响应 finger 请求、隐藏用户、伪造用户、banner/footer 定制等。

- 上游: https://www.infodrom.org/projects/cfingerd/
- 许可证: GPL-1.0-or-later
- 语言: C
- 类型: tool(命令行工具,构建产物为 `cfingerd` 与 `userlist` 两个可执行文件)

## 版本索引

| 版本 | 状态 | 说明 |
|------|------|------|
| 1.4.3 | built | 2026-09-07 首次适配,OHOS aarch64 |

## 跨版本通用知识

- 构建系统为自定义 Perl `Configure`(非 autotools),非交互用法 `perl ./Configure -c foo=bar`;Perl ≥5.26 需 `PERL5LIB=$SRC`(cwd 不在 @INC)
- 运行时依赖 inetd/xinetd 拉起或 `-d` standalone(DAEMON_MODE 默认未编译);`-e [user]` 可模拟本地 finger,是沙箱内验证的正确方式
- finger 协议端口 79/tcp,配置文件 /etc/cfingerd.conf
