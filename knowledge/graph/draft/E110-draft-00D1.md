# E110: Java构建工具缺失(Ant/Maven/Gradle)

## 严重度: 🟡 2 (中等 — Java 项目阻塞，但不影响 C/C++ 编译)

## 触发场景

尝试构建 Java 项目时，缺少 Ant/Maven/Gradle 构建工具。

## 现象

```
zsh:1: command not found: ant
zsh:1: command not found: mvn  
zsh:1: command not found: gradle

# 或在构建脚本中
Cannot run program "ant": error=2, No such file or directory
```

## 根因

鸿蒙平台未预装 Java 构建工具（Ant/Maven/Gradle），且 cmd-pkgs 预编译包仓库中无这些工具。

| 构建工具 | 系统预装 | cmd-pkgs | 需要手动安装 |
|----------|:--------:|:--------:|:------------:|
| Apache Ant | ❌ | ❌ | ✅ |
| Apache Maven | ❌ | ❌ | ✅ |
| Gradle | ❌ | ❌ | ✅ |

## 修复方案

### 方案 1: 手动安装 Ant（推荐）

```bash
# 1. 下载 Ant 二进制发布版
curl -k -L https://archive.apache.org/dist/ant/binaries/apache-ant-1.10.14-bin.tar.gz \
  -o ~/downloads/apache-ant-1.10.14-bin.tar.gz

# 2. 解压到用户目录
tar -xzf ~/downloads/apache-ant-1.10.14-bin.tar.gz -C ~/usr/local/

# 3. 配置环境变量（添加到 ~/.zshrc）
export ANT_HOME=$HOME/usr/local/apache-ant-1.10.14
export PATH=$ANT_HOME/bin:$PATH

# 4. 验证安装
ant -version
# Apache Ant(TM) version 1.10.14 compiled on August 16 2023
```

### 方案 2: 使用预构建的 Java 应用（回退）

大多数 Java 应用（如 Tomcat）提供官方二进制发布版，无需从源码构建：

```bash
# 直接下载 Tomcat 二进制发布版
curl -k -L https://archive.apache.org/dist/tomcat/tomcat-10/v10.1.31/bin/apache-tomcat-10.1.31.tar.gz \
  -o ~/downloads/apache-tomcat-10.1.31.tar.gz

# 解压即可运行
tar -xzf ~/downloads/apache-tomcat-10.1.31.tar.gz -C ~/usr/local/
~/usr/local/apache-tomcat-10.1.31/bin/catalina.sh start
```

**为什么推荐使用预构建版本**：
- Java 应用跨平台，无需针对 OpenHarmony 特殊编译
- 源码构建主要用于定制版本，普通用户无需
- 避免构建工具链配置问题

## 验证

```bash
# 检查 Ant 是否安装
ant -version 2>&1 || echo "Ant not installed"

# 检查 Maven 是否安装
mvn -version 2>&1 || echo "Maven not installed"

# 检查 Gradle 是否安装
gradle -version 2>&1 || echo "Gradle not installed"
```

## 禁止策略

| 禁止操作 | 原因 |
|----------|------|
| `apt-get install ant` | 鸿蒙不支持 apt 包管理器 |
| `yum install ant` | 鸿蒙不支持 yum 包管理器 |
| `brew install ant` | 鸿蒙不支持 Homebrew |

## 影响范围

所有使用 Ant/Maven/Gradle 构建的 Java 项目：
- Apache Tomcat (Ant)
- Apache Hadoop (Maven)
- Spring Framework (Gradle/Maven)
- Hibernate (Maven)
- Eclipse Jetty (Maven)

## 关联

- E083: BiSheng JDK System.load 签名校验（Java JNI 库签名问题）
- E034: CA 证书包缺失（导致 SSL 下载失败）

## 注意事项

1. **Java 应用与 C/C++ 库的区别**
   - Java 应用不需要"编译"为机器码
   - 源码构建仅用于定制版本
   - Java 应用跨平台，无需针对 OpenHarmony 特殊处理

2. **构建工具链选择**
   - Ant: 传统构建工具，适合 Tomcat 等老项目
   - Maven: 现代 Java 标准，依赖管理强大
   - Gradle: 灵活的构建系统，适合复杂项目

3. **网络下载限制**
   - 鸿蒙网络环境可能存在 SSL 证书问题
   - 使用 `-k` 参数绕过证书验证
   - 或使用 archive.apache.org（已验证的归档站点）

---

*最后更新: 2026-05-22*
*来源事件: tomcat-10.1.31 编译失败*