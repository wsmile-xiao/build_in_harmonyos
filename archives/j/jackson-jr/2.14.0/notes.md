# jackson-jr 2.14.0 适配笔记

## 来源与许可证

- 官方仓库：`https://github.com/FasterXML/jackson-jr`
- 官方 tag：`jackson-jr-parent-2.14.0`
- tag 解析提交：`bb965a3d57056491b33599bed2bdadb660f75749`
- 官方源码归档：
  `https://github.com/FasterXML/jackson-jr/archive/refs/tags/jackson-jr-parent-2.14.0.tar.gz`
- 官方源码归档 SHA-256：
  `020d7b3f3fb0f9a08648a7836f098ebe6530574a91c38ac66a2533fd84cffe94`
- 许可证：Apache-2.0；源码根目录的 `LICENSE` 会进入 Conan 包的 `licenses/`。
  上游 `README.md` 作为文档安装到 `share/doc/jackson-jr/README.md`，不会混入
  许可证目录。

## 构建设计

配方使用上游自带的 Maven Wrapper 3.6.3，从源码执行 `clean verify`，仅跳过不影响
运行时产物的 Javadoc 生成。构建覆盖全部六个 reactor 模块：

1. parent；
2. jr-objects；
3. jr-retrofit2；
4. jr-stree；
5. jr-annotation-support；
6. jr-all。

没有修改上游源码，也不需要 OpenHarmony 专用补丁。Java 工具进程在 OpenHarmony
PC 上把 `os.name` 归一为 `Linux`，避免 Maven 及插件把未识别的 `HarmonyOS`
名称误判为不支持平台。配方要求 `java` 与 `javac` 同属一个 JDK 17；若系统未提供，
则直接下载并校验官方 BiSheng JDK 17.0.13 OpenHarmony AArch64 归档：

- URL：
  `https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/pkgs/bishengjdk-17.0.13-ohos-aarch64.tar.gz`
- SHA-256：
  `ce074909ff5c13e7e7675eb243ee15424f0343610312c526552a1a08d199e28f`

`test_package` 先核验 `JAVA_HOME`、常用 BiSheng 安装位置和 `PATH` 中的 JDK；
均不可用时，从被测 `jackson-jr` 依赖的 `conandata.yml` 读取上述同一组版本、
URL、文件名和 SHA-256，再下载到自身构建目录。这样不复制固定工具元数据，也不依赖
主配方源码目录，符合 Conan 2 解析依赖图后在 `test()` 阶段访问依赖信息的生命周期。

普通运行时 class 是 Java 8 字节码（major 52），五个 JAR 中版本化的
`META-INF/versions/9/module-info.class` 是 Java 9 字节码（major 53）。
产物不使用 C/C++ 编译器。

## 上游测试

2026-07-30 在 WSL Ubuntu x86_64、OpenJDK 17.0.19 上运行官方 Maven reactor：

- jr-objects：104/104；
- jr-stree：20/20；
- jr-annotation-support：26/26；
- 合计：35 个 Surefire 套件，150/150；
- failures：0；
- errors：0；
- skipped：0；
- jr-retrofit2 与 jr-all 上游没有独立测试源，但均完成真实编译和打包。

本次上游验证的 reactor 六个模块均为 `SUCCESS`。Javadoc 中缺失注释的警告属于
上游文档质量问题；正式配方跳过 Javadoc，不影响字节码、测试或运行时 JAR。

## 产物检查

修复后最终官方源码构建得到：

- `jackson-jr-all-2.14.0.jar`：583,445 bytes；
- SHA-256：
  `096937412e4181268acb6b46f17ba7291931ab5f54cf916b1f128d45464cc194`；
- JAR 条目：286；
- class 数：238；
- `JSON.class`、`JrsObject.class` 和重定位后的 `JsonFactory.class` 均存在；
- 普通运行时 class 的 major version 为 52（Java 8）；
- 版本化 JPMS 描述符的 major version 为 53（Java 9）；
- 五个模块产出的精确 JAR 均非空且通过 ZIP CRC 检查。

该哈希是本次本地 JDK/Maven 构建的观测值，不作为跨 JDK 构建必须相同的发布基线。

## 消费者测试与边界

`test_package` 使用 Conan 包内的 `jackson-jr-all` JAR 编译并运行真实 Java
消费者，覆盖对象/集合读取、Bean 往返、null 特性、组合器、字节输出、数组、
大数、简单 Tree 和错误输入，共 25 个运行时断言；同时要求五个模块的精确 JAR
全部存在、非空且 ZIP 完整，检查 `jr-all` 的 3 个关键条目与 238 个 class，并分别
枚举五个 JAR 的全部普通 class 验证 Java 8 magic/major 52，并验证 Java 9 JPMS
描述符的 magic/major 53，共 29 项包/JAR 验证。

## Conan、W3 与 R34 收据

- 本轮审核修复后的 `conan create` 于 2026-07-30 18:17（UTC+8）完成，完整
  Conan 引用：
  `jackson-jr/2.14.0#5a2c2e1a1444799d20d6f8260cefe46b:da39a3ee5e6b4b0d3255bfef95601890afd80709#10ec96c563ea0e3c3fe49246875b46f4`；
- 上述创建过程从标准 GitHub tag 归档 URL 下载源码并通过固定 SHA-256 校验；
  最终包内 `licenses/` 仅有 `LICENSE`，上游 README 位于
  `share/doc/jackson-jr/README.md`；
- W3：L0、L1、L1e、L4、L5 均通过；纯 Java 库没有 `bin/`，L2 正常跳过；
- 本轮 `conan create` 再次运行全部 35 个上游 Surefire 套件和 150 个测试，
  随后运行 25 个消费者运行时断言和五模块 JAR 结构/字节码检查；
- 此前独立 R34：把当时最终包的精确
  `lib/jackson-jr-retrofit2-2.14.0.jar` 临时移走后，`conan test` 以退出码 1
  失败并明确报告该 JAR 缺失；原样恢复后，其 SHA-256 仍为
  `dc37630efa45dfca98d4108f9886e7f7cdddfc0c51617819c32f94a5a3259180`，
  同一 `conan test` 以退出码 0 通过，并再次输出五个 JAR 验证和 25 个运行时
  断言通过。这证明非 `jr-all` 模块也不存在静默漏包窗口。该负向扰动没有在本轮
  仅涉及来源 URL、JDK 回退与文档落点的修改后重复执行。

这些 W3 与 R34 收据来自 WSL Linux JVM，使用 OHOS/armv8 Conan profile 解析包图；
它们证明配方、包内容和消费者测试链有效，但不等同于 OpenHarmony PC 目标机运行收据。

## 已知边界

- 本地上游测试在 x86_64 WSL JVM 上运行，不等同于物理 OpenHarmony PC 设备验收。
- JAR 架构无关；OpenHarmony PC 仍需提供 BiSheng JDK 17 或兼容 JVM。
- 配方需要 Maven Central 网络访问以解析上游声明的构建插件与 Java 依赖。
- 目前没有在物理 OpenHarmony PC JVM 上执行消费者测试，不声称设备侧已验收。
