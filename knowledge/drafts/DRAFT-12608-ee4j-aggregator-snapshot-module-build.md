# draft-jakarta-auth-3.0.0-ee4j-aggregator-snapshot-module-build

## 症状

jakarta-authentication-api 3.0.0 的 release tarball（tag 3.0.0-RELEASE）根 pom：

```
<artifactId>authentication-parent</artifactId>
<version>3.0.0-SNAPSHOT</version>    ← 发布 tag 里聚合器版本停在 SNAPSHOT
<modules>
  <module>api</module>
  <module>spec</module>
</modules>
```

而 api/pom.xml 的 parent 是外部 `org.eclipse.ee4j:project:1.0.6`（非聚合器）。

按常规思路在根目录 `mvn package` 会把 SNAPSHOT 聚合器拉入构建生命周期，产生
解析与部署噪音；`mvn install` 更会把 SNAPSHOT 聚合器装进本地仓库，污染后续构建。

## 根因

EE4J（jakartaee/*）发布流程用 tag 打包时只更新模块版本，根聚合器 parent 版本
保持 SNAPSHOT；模块 pom 的 parent 指向外部 ee4j:project（继承关系）与聚合器
（模块聚合关系）分离。这是 authentication/mail/activation 等 EE4J 家族的共同
发行形态。

## 修复

conanfile.py build() 只进模块目录构建：

```python
# build() 内（authentication 3.0.0 例：模块在 api/）
self.run(f'bash -c "cd {self.source_folder}/api && mvn clean package -B -DskipTests=false"',
         env="conanbuild")

# package() 从模块目录取产物
jar_path = os.path.join(self.source_folder, "api", "target",
                        f"jakarta.authentication-api-{self.version}.jar")
```

三禁：不在根目录 `mvn package`、不 `mvn install`、不依赖聚合器版本号。

## 验证

- jakarta-authentication-api 3.0.0：`cd api && mvn clean package -B` 本地干净构建
  （零补丁零告警），产物 45346 字节，与官网发行 jar 一致

## 经验

- 见到 release tarball 根 pom 带 SNAPSHOT 先别慌：看子模块 pom 的 parent 是否外部
  —— 外部 parent 说明模块可独立构建。
- 模块自身 `<version>` 与聚合器无关，配方版本号以模块为准。
- EE4J 家族（authentication/mail/activation/el/websocket…）同形态，可批量套用。
