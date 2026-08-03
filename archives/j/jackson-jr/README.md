# jackson-jr — OpenHarmony PC 适配

Jackson jr 是 FasterXML Jackson 项目的轻量级 JSON 数据绑定实现。相比完整的
`jackson-databind`，它以更小的 JAR 和较低的初始化开销提供常用的对象、集合、
Java Bean、流式组合器与简单 JSON Tree 功能。

- 官方源码：https://github.com/FasterXML/jackson-jr
- 官方 tag 归档：
  https://github.com/FasterXML/jackson-jr/archive/refs/tags/jackson-jr-parent-2.14.0.tar.gz
- 许可证：Apache-2.0
- 上游版本：2.14.0
- Java 基线：普通运行时 class 为 Java 8；版本化 JPMS 描述符为 Java 9

## OpenHarmony 适配

本配方从官方 tag 源码构建全部 Maven 模块，并执行上游完整测试。最终 Conan 包
包含以下 JAR：

- `jackson-jr-all-2.14.0.jar`：自包含 JAR，内含 objects、stree 与重定位后的
  Jackson Core，适合直接使用；
- `jackson-jr-objects-2.14.0.jar`；
- `jackson-jr-stree-2.14.0.jar`；
- `jackson-jr-annotation-support-2.14.0.jar`；
- `jackson-jr-retrofit2-2.14.0.jar`。

这些 JAR 是架构无关的 Java 字节码，不包含 OpenHarmony 原生 ELF。普通运行时
class 为 Java major 52；五个 JAR 的
`META-INF/versions/9/module-info.class` 为 major 53。OpenHarmony PC 配方要求
同一 `JAVA_HOME` 下经核验的 JDK 17，系统未提供时使用 SHA-256 固定的
BiSheng JDK 17.0.13 OpenHarmony AArch64 归档。`test_package` 也从被测依赖的
`conandata.yml` 读取同一组固定版本、URL 与 SHA-256，在找不到完整 JDK 17 时执行
同样的校验下载回退，避免消费者测试仅依赖机器预装状态。

Conan 包的 `licenses/` 只包含 `LICENSE`；上游 `README.md` 安装到
`share/doc/jackson-jr/README.md`。

## 使用方式

最简单的方式是把自包含 JAR 加入 classpath：

```bash
javac -cp jackson-jr-all-2.14.0.jar Example.java
java -cp ".:jackson-jr-all-2.14.0.jar" Example
```

Conan 包同时通过构建与运行环境公开 `JACKSON_JR_JAR`，其值指向
`jackson-jr-all-2.14.0.jar`。

## 版本

| 版本 | 状态 | 日期 |
|---|---|---|
| 2.14.0 | built | 2026-07-30 |
