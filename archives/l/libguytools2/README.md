# libguytools2

## 简介
Guymager 取证镜像工具的支持库，提供日志（`t_Log`）、错误码注册表（`ToolError`）、
配置文件与命令行解析（`ToolCfg`）、信号守护线程（`ToolSignal`）以及系统信息查询
（`ToolSysInfo`，含 uname 与 MAC 地址）。

上游源码包名为 `tools-2.1.0.tar.gz`（项目名 libguytools / 包名 libguytools2）。

## OHOS 适配
- 构建系统: **qmake**（Qt5 `.pro` 项目；上游无 CMake/autotools）
- 依赖: `qt5-qtbase/5.15.2`（仅用 QtCore：`QMutex` 与公开 API 中的 `QString`）
- 产物: `libguytools.so.2.1.0`（SONAME `libguytools.so.2`）+ `include/libguytools/*.h`
- 补丁: 3 个（可移植头文件 / 版本与安装规则 / ToolError 返回值缺陷）
- 详见 [2.1.0/notes.md](2.1.0/notes.md) 获取适配详情

## 依赖
- qt5-qtbase/5.15.2（已发布，含 qmake/moc 工具链）

## 功能验证

上游**无任何测试用例**（无 `tests/`、无 `test_*.cpp`、`.pro` 未定义 `check`/`test`
目标，Debian 打包亦无测试目标 —— 清点证据见 [2.1.0/notes.md](2.1.0/notes.md)），
因此本包提供**消费者功能测试** `test_package/test_libguytools2.cpp`：用真实输入验证
真实结果，而非常量/返回值断言 ——

- `ToolCfg`：真实配置文件解析（`SECTION/ENDSECTION`，STRING/INTEGER/DOUBLE/PRESENCE/
  SET/HMS，命令行选项且**命令行优先于配置文件**），模板生成，10 类错误路径的错误码 +
  解析器日志 + 目标变量未被写入；
- `t_Log`：日志文件真实落盘并读回，三个等级的标签路由、printf 格式化、单例语义；
- `ToolError`：注册表生命周期、消息查表、errno 翻译、`ToolErrorCheck()` 日志内容；
- `ToolSignal`：真实 `SIGHUP`/`SIGTERM` 往返，handler 由守护线程投递；
- `ToolSysInfo`：`uname()` 与真实 `uname(2)` 逐字段交叉校验、MAC 的 `AddrStr`/`AddrVal` 交叉校验；
- HarmonyOS 平台行为：平台身份 / `TMPDIR` 契约 / OHOS 文件系统落盘 / `net/if.h` ioctl 路径 MAC 枚举。

`conan create` 编译并执行该测试（实测 `checks: 127 passed: 127 failed: 0`），
任一检查失败即 `conan create` 失败。

## 已知平台说明
- `toolsysinfo.h` 公开 API 使用 `QString` 但未 include `<qstring.h>`，消费者需自行引入
  （已在上游代码中保留原样，未修改；test_package 中显式 include）。
- OHOS sysroot 下 `linux/if.h` 与 `sys/socket.h` 冲突，已改用 `net/if.h`。

## 参考
- https://sourceforge.net/projects/libguytools/
