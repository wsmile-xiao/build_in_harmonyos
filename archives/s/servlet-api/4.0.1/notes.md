# servlet-api 4.0.1 适配笔记

## 编译环境
- 构建系统：Custom（BiSheng JDK `javac` + `jar`）
- 编译日期：2026-08-15
- 目标平台：HarmonyOS PC / arm64
- 状态：built

## 编译步骤
1. 下载并校验官方 `javaee/servlet-spec` 4.0.1 标签源码。
2. 使用 `javac -source 8 -target 8` 编译全部 77 个 Java 源文件。
3. 复制本地化资源和上游 `META-INF/MANIFEST.MF`，生成 `javax.servlet-api-4.0.1.jar`。
4. 通过消费者测试编译并运行 Servlet API 示例。

## 适配说明
该项目是纯 Java API JAR，不包含 JNI、ELF 或平台系统调用，因此产物与 CPU 架构无关，无需修改上游源码。上游 4.0.1 标签不包含测试目录，不能运行上游单元测试；本适配据实声明无上游测试，并提供 7 项消费者断言。

## 依赖版本
- BiSheng JDK 17.0.13（构建和测试工具）
- 无 Conan 运行时依赖

## 源码修改
无补丁。

## 验证命令
```bash
python3 scripts/ohc-run.py conan-verify servlet-api 4.0.1
```

## 交付物
| 文件 | 说明 |
|------|------|
| `libexec/javax.servlet-api-4.0.1.jar` | Java Servlet 4.0 API |
| `licenses/LICENSE` | 上游许可证 |
---

**编译结束**: 2026-08-15 16:36
**最终状态**: built
