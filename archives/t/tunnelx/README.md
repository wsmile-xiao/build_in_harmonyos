# tunnelx (Tunnel / TunnelX)

Julian Todd 的 Java 2.5D 洞穴测绘绘图程序。基于 Survex 兼容的导线（centreline）
数据绘制洞穴平面/剖面图，并能在底层导线网络发生环路闭合调整时自动变形已有
图纸以重新贴合。

- 上游仓库：<https://github.com/goatchurchprime/tunnelx>
- 语言/构建：纯 Java（81 个 `src/*.java`，包名 `Tunnel`），**无 C/C++ 原生层**；
  上游构建入口为 `build`（`javac -version -d . src/*.java`）+ `jmake`（`jar cmf`）
- 运行入口：`Tunnel.MainBox`（AWT/Swing GUI），jar 清单 `Main-Class: Tunnel.MainBox`
- 运行环境：BiSheng OpenJDK 17.0.13（HarmonyOS PC 由 HNP 预装于 `~/bishengjdk17`）

## 版本

| 版本 | 状态 | 说明 |
|------|------|------|
| [20190701](20190701/) | 见版本目录 `manifest.yaml` | 上游 tag `R2019a`（`src/TN.java:58` = `version2019-07-01 DoES`） |

## HarmonyOS 适配要点

- 设备 `PATH` 中无 `java`/`javac`/`jar`：配方自动定位 HNP 预装的 BiSheng JDK，
  缺失时从 OpenHarmonyPCDeveloper `cmd-pkgs` 官方通道安装；
- HarmonyOS `/tmp` 不可写：安装的启动器 `bin/tunnelx` 将 `java.io.tmpdir`
  重定向到可写目录（`$TMPDIR` / `$HOME/tmp`），对应上游
  `src/FileAbstraction.java:136-142` 的临时目录回退链；
- JAR 自带 `symbols/`、`tutorials/` 及其 `listdir.txt`，应用自包含，运行目录无关
  （对应上游 `src/FileAbstraction.java:146-160` 的类加载器资源查找）。

## 安装后使用

```
conan install --requires=tunnelx/20190701
$CONAN_HOME/.../bin/tunnelx            # 或直接调用安装前缀下的 bin/tunnelx
```
