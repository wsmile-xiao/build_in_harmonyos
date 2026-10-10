# japi-compliance-checker

Java API Compliance Checker (JAPICC) — A tool for checking backward API/ABI compatibility of a Java library.

## 简介

japi-compliance-checker 检查 Java 库两个版本之间的向后二进制与源码级兼容性：
解包 jar/jmod、用 `javap` 反编译类文件、比较公开 API 面（方法、字段、继承、
注解等），输出 HTML 兼容性报告与破坏点清单。亦支持 Scala 与 Java 9+（jmod）。

## 版本

- 当前编译版本: 2.4

## 依赖

- Perl 5 (≥ 5.8，仅需核心模块)
- JDK/OpenJDK（javap / jar / javac / java；鸿蒙上由配方按 jackson-core 先例
  自动定位/安装 BiSheng JDK 17）

## 安装

通过 Conan 安装：
```bash
conan install --requires=japi-compliance-checker/2.4 -r=ohpcd
```

## 使用

```bash
japi-compliance-checker OLD.jar NEW.jar     # 对比两个版本的 jar
japi-compliance-checker OLD.jmod NEW.jmod   # Java 9+ 模块
japi-compliance-checker -dump LIB.jar -dump-path ./API.dump   # 创建 API dump
japi-compliance-checker -test               # 内嵌回归测试套件
```

## 平台适配说明

### HarmonyOS 适配

1. **Perl 路径**: HarmonyOS Perl 不在 `/usr/bin/perl`，shebang 改为 `#!/usr/bin/env perl`
2. **安装方式**: 纯 Perl 脚本；上游 Makefile.pl 在 Perl 5.42+ 有兼容问题，
   配方在 build() 中执行等效安装（同 abi-compliance-checker 2.3 先例）
3. **wrapper**: bin/japi-compliance-checker 解析自身路径调用 share/ 下真实脚本，
   保证 $0 与 modules/ 定位
4. **JDK**: 运行时需要 JDK 工具（javap/jar/javac/java）；构建/测试按
   JAVA_HOME → ~/bishengjdk17 → PATH → cmd-pkgs 自动安装链解析

## 编译状态

- 2.4: published ✅
