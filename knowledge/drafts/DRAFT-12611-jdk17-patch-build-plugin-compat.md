# draft-jakarta-inject-2.0.1-jdk17-patch-build-plugin-compat

## 症状

jakarta-inject-api 2.0.1 在 bishengjdk 17.0.13+（JDK 17.0.13 及更高补丁版）上
`mvn clean package` 两类报错：

```
# 报错一：bundle 插件 manifest 阶段崩溃
[ERROR] Failed to execute goal org.apache.felix:maven-bundle-plugin:4.2.1:manifest ...
java.util.ConcurrentModificationException
    at java.util.zip.ZipFile$Source.keySet(ZipFile.java:1517)

# 报错二：javadoc 阶段 doclint 标题层级
[ERROR] error: heading used out of sequence: <H3>, compared to implicit preceding heading: <H1>
```

## 根因

1. maven-bundle-plugin 4.2.1 内置 bnd 4.x，其 manifest 生成依赖 JDK 的 ZipFile 内部
   实现；JDK 17.0.13+ 补丁版本修改了 `ZipFile$Source` 的内部结构，bnd 4.x 在其上
   触发 ConcurrentModificationException。
2. JDK 17.0.13+ 的 javadoc doclint 强制校验 javadoc 注释中的标题层级（`<h3>` 紧跟
   `<h1>` 视为 out of sequence），上游旧注释风格在新 doclint 下报错。
3. 上游发行 tarball 的 pom 停留在旧 JDK 时代（2018-2020 年维护），从未在新补丁版
   JDK 上构建过。

## 修复

conandata 平铺补丁（patch_type: portability，build() 内 apply_conandata_patches 应用）：

```xml
<!-- pom.xml 就地修改一：bundle 插件 4.2.1 → 5.1.9（bnd 5.1.2） -->
<plugin>
  <groupId>org.apache.felix</groupId>
  <artifactId>maven-bundle-plugin</artifactId>
  <version>5.1.9</version>  <!-- 原 4.2.1 -->
  ...

<!-- pom.xml 就地修改二：javadoc doclint 关闭 -->
<plugin>
  <artifactId>maven-javadoc-plugin</artifactId>
  <configuration>
    <doclint>none</doclint>
    ...
```

关键坑位：
- **pluginManagement 覆盖无效**：继承插件若在子 pom 已显式声明版本，
  pluginManagement 的 version 不生效——必须找到声明处就地改版本。
- 同一 parent pom 若以 `<maven-bundle-plugin.version>` 属性管理版本（如 cdi 4.0.1
  的 5.1.2），则只改属性即可，无需改插件声明。
- 补丁文件用 `diff -u --label a/pom.xml --label b/pom.xml` 生成（conan 打补丁需要
  a/ b/ 标签路径），本地文件差异检测用 `patch -p1 --dry-run -R` 验证补丁与已改树
  严格一致。

## 验证

- jakarta-inject-api 2.0.1：补丁后 `mvn clean package -B -DskipTests=false` 本地全绿
- jakarta-cdi-api 4.0.1：同 doclint 补丁后 56/56 TestNG 测试全过（跨包复用证明一类问题）

## 经验

- 构建插件报错先看 JDK 版本：旧 pom + 新 JDK 补丁版是高频组合，升级插件版本是
  第一解法，而不是改 JDK。
- doclint 报错标题层级时优先 `<doclint>none</doclint>`（API 文档风格无法逐条改注释）。
- 同一补丁主题跨多个包复用时，每包仍需独立验证（bundle 插件版本属性管理方式不同）。
