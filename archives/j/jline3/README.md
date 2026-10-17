# jline3 — OpenHarmony PC 适配

JLine3 是 Java 生态标准的控制台输入处理库，提供终端抽象（POSIX/Windows）、
行编辑读取器（LineReader）、补全/历史/快捷键与内建命令（Nano、Tmux、Top 等），
是 Spring Shell、Karaf、SBT 等工具的交互层基础。

- 官方源码：https://github.com/jline/jline3
- 官方 tag 归档：
  https://github.com/jline/jline3/archive/refs/tags/jline-3.3.1.tar.gz
- 许可证：BSD-3-Clause
- 上游版本：3.3.1（2017-06-06）
- Java 基线：全部产物为 Java 8 字节码（major 52）

## OpenHarmony 适配

本配方从官方 tag 源码构建 reactor 子集并执行上游完整测试，最终 Conan 包
包含以下 JAR（`lib/`）：

- `jline-3.3.1.jar`：聚合 bundle，内含 terminal/reader/builtins 全部类及
  JNA/Jansi 桥接类与服务描述符，可作为自包含消费 JAR；
- `jline-terminal-3.3.1.jar`；
- `jline-reader-3.3.1.jar`；
- `jline-builtins-3.3.1.jar`。

这些 JAR 是架构无关的 Java 字节码，不包含 OpenHarmony 原生 ELF。构建与
`test_package` 共享 SHA-256 固定的 BiSheng JDK 17.0.13 OpenHarmony AArch64
归档（系统未提供 JDK 17 时自动校验下载）。

### 平台差异要点

- **无本地库依赖**：`terminal-jna`/`terminal-jansi` 模块不打包（JNA/Jansi
  `.so` 需与 JDK 同签名）。系统终端在无 JNA/Jansi 环境自动降级为
  ExecPty 驱动（`exec stty`），与鸿蒙 Toybox/BusyBox stty 语义兼容，
  `test_package` 以真实 pty 验证 raw 模式与 winsize 往返。
- **headless 使用**：管道/重定向环境下 TerminalBuilder 降级为 dumb
  terminal，LineReader 功能完整可用。
- **构建环境**：JDK 17 工具链经补丁以 `--release 8` 编译（上游 `-profile`
  参数在 JDK 9+ 已移除）；OHOS 设备 JVM `user.home` 为 `"?"`，Maven 仓库
  固定在构建目录内。

## 使用方式

最简单的方式是把聚合 JAR 加入 classpath：

```bash
javac -cp jline-3.3.1.jar Example.java
java -cp ".:jline-3.3.1.jar" Example
```

Conan 包同时通过构建与运行环境公开 `JLINE3_JAR`，其值指向
`jline-3.3.1.jar`。

## 版本

| 版本 | 状态 | 日期 |
|---|---|---|
| 3.3.1 | built | 2026-09-25 |
