# Scala 2.12.21 — 适配笔记

## 软件信息
- **软件名**: scala
- **版本**: 2.12.21
- **类型**: JVM 预编译分发包（非 C/C++ 源码）
- **License**: Apache-2.0
- **Homepage**: https://www.scala-lang.org/

## 构建系统说明
Scala 2.12.21 是 JVM 预编译分发包，内含：
- `bin/` — shell 脚本工具 (fsc, scala, scalac, scaladoc, scalap)
- `lib/` — JAR 文件 (scala-library.jar, scala-compiler.jar 等)
- `doc/` — 文档
- `man/` — man 页面

**无 configure 脚本，无 Makefile**。"编译"步骤为：下载 → 解压 → 安装到 staging → 验证。

## 依赖
- **bishengjdk 17.0.13** — 通过 cmd-pkgs 安装的 JVM 运行时
  - 安装命令: `curl -fsSL .../install-jdk.sh | sh -s -- 17.0.13`
  - 安装路径: ~/bishengjdk17

## 构建过程
1. 安装 bishengjdk 17.0.13
2. 下载 scala-2.12.21.tgz (GitHub SSL 不稳定，使用 scala-lang.org 镜像)
3. 解压分发包
4. 复制 bin/ 和 lib/ 到 staging
5. 验证命令行工具: scala, scalac, scaladoc, scalap, fsc
6. Smoke test: 编译运行 HelloWorld.scala — ✅ 通过

## 关键问题
1. **GitHub SSL 问题**: OHOS 上 GitHub 下载 SSL 不稳定，改用 scala-lang.org/files/archive/ 镜像
2. **/tmp 只读**: 使用 $TMPDIR 代替 /tmp (E002)
3. **JVM 依赖**: Scala 需要 JVM，通过 cmd-pkgs 安装 bishengjdk

## Conan 配方要点
- `build()`: 无编译步骤，仅平台检查
- `package()`: 复制 bin/, lib/, man/, doc/ 到 package_folder
- `package_info()`: 设置 PATH, SCALA_HOME, CLASSPATH 环境变量
- `system_requirements()`: 检查 java 可用性
- `conandata.yml`: 使用 scala-lang.org URL + 正确 SHA256
---

**编译结束**: 2026-07-02 16:44
**最终状态**: built
