# coolmail

**X11 邮件通知工具**（xbiff 替代品，1995 年由 Byron C. Darrah 发布）

coolmail 监视一个邮箱文件（默认 `/var/spool/mail/<username>`），有新邮件时在桌面上
一个很小的窗口里播放一封信封的 3D 动画；点击窗口可以调用你指定的邮件阅读程序
（`-e` 选项）。相比 xbiff，它多出了动画、可选的声音提示和自定义命令。

## 用法

```bash
coolmail [options]
```

| 选项 | 说明 |
|------|------|
| `-f filename` | 监视指定邮箱文件，而不是默认的 `/var/spool/mail/<username>` |
| `-e command` | 点击时调用的命令（通常是邮件阅读器） |
| `-fr n` | 每次动画的帧数（默认 15） |
| `-int n` | 检查间隔秒数（默认 30），`-update` 同义 |
| `-mono` | 单色模式 |
| `-once` | 只在新邮件首次出现时响铃 |
| `-v` | 启动时打印监视的文件 |
| `-h` | 打印帮助并退出 |

标准 X Toolkit 参数（`-display`、`-geometry`、`-xrm` 等）同样可用；
`Coolmail.ad` 提供 `coolmail.monochrome`、`coolmail*geometry`、`coolmail.volume` 等资源默认值。

## 构建

- 构建系统：手写 GNU Makefile（无 configure 脚本）
- 版本：1.3（1995-09-19）
- 许可证：GPL-1.0-or-later（GPL v1 或更新版本）
- 源码：`coolmail-1.3.tgz`（26809 字节，发行物与 1996 年 LSM 记录一致）

## OHOS 适配

- **依赖**：`libxt/1.3.1`（传递 libx11/1.8.13、libsm/1.2.6、libice/1.1.2、xorgproto/2025.1、
  libxcb/1.17.0、libxau/1.0.11、libxdmcp/1.1.5）。OHOS 不预装任何 X 库，运行期需要
  依赖包 lib 目录在 `LD_LIBRARY_PATH` 中（DT_NEEDED：libXt.so.6 → libSM.so.6/libICE.so.6，
  libX11.so.6 → libxcb.so.1/libXau.so.6/libXdmcp.so.6）。
- **Makefile 变量覆盖而非改文件**：上游把 `-I/usr/X11R5/include`、`-L/usr/X11R6/lib`、
  `BINDIR=/usr/local/bin` 写死在 Makefile 里，配方在 `make` 命令行传入真实的 Conan 依赖
  目录与包内安装路径；`package()` 用显式 `copy` 复现 `make install` 的两条规则
  （上游 `install` 目标在目录不可写时静默跳过，HMDFS 权限语义下不可靠）。
- **移除 `-lXext`**：源码不调用任何 Xext 入口（`nm -D --undefined-only` 实测无 Xext 符号），
  而制品仓中与 `libx11/1.8.13` 图匹配的 libXext 没有可用 binary
  （`libxext/6.4.0.1` 的已发布 binary 是按 `libx11/6.4.0` 计算的 package_id）。
- **关闭 digitized audio**：上游声音后端是 OSS（`#ifdef linux` + `<linux/soundcard.h>` +
  `/dev/mixer`、`/dev/dsp`），OHOS SDK 无该头文件、设备也无 OSS 设备节点；采用上游
  README 明确记载的“注释掉 AUDIO/AUDIO_MODULE”配置。结果：`-af`/`-vol` 选项在无 AUDIO
  构建中不可用（上游行为，非适配引入）。
- **cuserid 移植补丁**：`cuserid()` 在 POSIX.1-2001 已删除，OHOS musl 只在静态
  `libc.a` 中保留该符号，`libc.so` 不导出；改为 `getpwuid(getuid())` →
  `getlogin()` → `LOGNAME` → `USER` 回退链（不引入 `__OHOS__` 条件编译，glibc 同样适用）。
- **已知限制**：设备与 CI worker 均无 X server（无 Xorg/Xvfb 可执行文件，制品仓未发布
  OHOS `xorg-server`），因此窗口绘制、动画与邮箱状态轮询无法在本环境运行；测试覆盖
  命令行路径（`-h`）与 Xt 初始化失败路径（无 DISPLAY 时的 `Can't open display`）。

## 依赖关系

- 编译期：`libxt/1.3.1`（含传递头文件 libx11/libsm/libice/xorgproto）、OHOS clang 15、GNU make
- 运行期：libXt.so.6、libX11.so.6、libSM.so.6、libICE.so.6、libxcb.so.1、libXau.so.6、libXdmcp.so.6

## 参考资料

- 上游发行物：https://cdn.netbsd.org/pub/pkgsrc/distfiles/coolmail-1.3.tgz
- Debian 源码页（上游站点已停用）：https://sources.debian.org/src/coolmail/
- 手册页：`share/man/man1/coolmail.1`；X 资源默认值：`share/X11/app-defaults/Coolmail`
