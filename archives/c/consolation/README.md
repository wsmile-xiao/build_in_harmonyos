# Consolation

> 复用 Linux 内核虚拟终端(kbd 驱动)复制粘贴能力的虚拟控制台守护进程

## 简介

consolation 是一个运行于虚拟控制台(VT,虚拟终端)的守护进程,通过
libinput 读取输入事件,为纯文本控制台提供类似 GPM 的鼠标选择/复制/
粘贴能力。它从内核 VT(kbd)驱动读取键盘、经 libevdev/libinput 处理
鼠标事件,把选中内容写回 TTY。体积小、依赖少,是无图形会话环境下
控制台鼠标支持的轻量方案(同类软件:gpm、jamd)。

## OHOS 适配要点

- **构建期**:musl 无 glibc 全局 `program_invocation_short_name`,补丁
  在 `!__GLIBC__` 下提供静态 fallback(仅 usage() 输出使用);
- **man 页**:上游 consolation.8 由「运行编译产物」生成,交叉构建下
  不可行,配方按「文档不构建」口径中性化(见 0.0.10/notes.md);
- **运行期(集成阶段确认)**:
  - 内核需启用 `CONFIG_VT`(虚拟终端)且存在 `/dev/tty0`;
  - 依赖 udev 运行时(eudev 的 udevd)做输入设备发现;
  - 上游自带 `consolation.service.in`(systemd 单元),OHOS 无 systemd,
    集成时需改写启动方式。

## 排除与替代

- 不适合图形会话下的剪贴板(那是 Wayland/X 的职责);本工具只服务
  VT 控制台场景。

## 依赖

| 依赖 | 版本 | 说明 |
|------|------|------|
| libinput | >= 1.5(configure 探测到 >= 1.26 更优) | 输入事件抽象 |
| libudev | eudev 3.2.14 提供 | 输入设备发现 |
| libevdev | >= 0.4 | evdev 封装 |

## 功能验证

```bash
consolation --help      # 用法输出
consolation --version   # 版本输出
# 常驻(需 VT 环境):consolation --udev
```

## 参考

- [上游主页](https://salsa.debian.org/consolation-team/consolation/)
- [Debian 源包页](https://packages.debian.org/source/sid/consolation)
