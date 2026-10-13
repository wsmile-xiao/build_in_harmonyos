# interception-tools

> Linux 输入设备拦截生态的核心套件:udevmon 守护 + intercept 捕获 + uinput 注入

## 简介

interception-tools 是一套可组合的输入设备拦截工具,从内核 evdev 层读取
按键/指针事件,经 libevdev/libinput 处理后按 YAML 配置写回 uinput 虚拟
设备,实现按键重映射、大小写锁定改造等(经典插件:caps2esc)。由
udevmon 守护监听 udev 热插拔并按配置拉起 intercept 管道。

## OHOS 适配要点

- **构建**:mux 目标需 Boost.Interprocess(仓库 boost 配方未含该组件),
  已裁剪;udevmon/intercept/uinput 三工具保留;
- **链接**:udev/yaml-cpp 上游用裸 -l 名,补丁改 pkg_check_modules 统一
  走 conan 依赖图(libevdev 上游本就是 pkg_check_modules);
- **运行前提(集成阶段确认)**:CONFIG_INPUT、/dev/input/event*、
  eudev(udevd)运行时;udevmon 需用户 YAML 配置。

## 排除与替代

- mux 多路复用器与各插件(caps2esc 等)属运行时组合件,不在本包范围。

## 依赖

| 依赖 | 版本 | 说明 |
|------|------|------|
| libevdev | 1.13.7 | evdev 事件读写 |
| libudev | eudev 3.2.14 提供 | 输入设备发现 |
| yaml-cpp | 0.9.0 | udevmon/udevmon 配置解析 |

## 功能验证

```bash
udevmon -h      # 用法输出
intercept -h    # 用法输出
uinput -h       # 用法输出
```

## 参考

- [上游仓库](https://gitlab.com/interception/linux/tools)
- [插件生态](https://gitlab.com/interception/linux/plugins)
