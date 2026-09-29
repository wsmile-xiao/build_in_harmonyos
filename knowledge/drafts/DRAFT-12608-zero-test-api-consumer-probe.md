# draft-jakarta-auth-3.0.0-zero-test-api-consumer-probe

## 症状

jakarta-authentication-api 3.0.0（Jakarta Authentication 3.0 SPI）上游发行 tarball
中只有主源码，无任何测试：

```
api/src/ 下仅 main/java（24 个主源码），无 test 目录
→ 无法沿用「上游测试实跑」路线满足 R34 实质性验证
```

## 根因

规范 API 类发行物（jakarta.*/javax.* 各 spec API）普遍是 API-only 模块：上游只
维护接口与注解，测试在 TCK（独立仓库）而非发行 tarball 中。适配方不能以「上游
无测试」为由跳过 R34——需要自建消费方探针。

## 修复（探针设计口径，五步）

```java
// ① API 面清点：覆盖不同子包的 8 个代表性类/接口
String[] classes = {
    "jakarta.security.auth.message.config.ServerAuthContext",
    "jakarta.security.auth.message.module.ServerAuthModule",
    "jakarta.security.auth.message.config.AuthConfigProvider",
    "jakarta.security.auth.message.config.ClientAuthContext",
    "jakarta.security.auth.message.AuthStatus",
    "jakarta.security.auth.message.MessageInfo",
    "jakarta.security.auth.message.MessagePolicy",
    "jakarta.security.auth.message.callback.CallerPrincipalCallback",
};
// 逐个 Class.forName + 每行 "OK: loaded <fqcn>"（日志可审计）

// ② 语义契约断言（弥补「能加载≠语义对」）
if (!Class.forName("...module.ServerAuthModule").isInterface())  // SPI 必须是接口
    System.exit(1);
if (Class.forName("...AuthStatus").getField("SUCCESS").getType()
        != Class.forName("...AuthStatus"))  // 状态常量类型自洽
    System.exit(1);

// ③ PASS 标记：全过后输出单行 "PASS: ..."
```

```bash
# ④ assertion_count 口径（MANIFEST.yml）
#    1 JAR 存在 + 1 javac 编译 + 10 程序内断言 + 1 PASS = 13
#    upstream_tests 用「无测试源码」说明性条目占位（保留结构合规）
# ⑤ test.sh 环境
#    JAVA_HOME 候选含真机路径 /storage/Users/currentUser/usr/local/bishengjdk17
#    TMP_DIR="$(mktemp -d 2>/dev/null || mktemp -d "$HOME")"   # /tmp 只读 EROFS 回退
```

## 验证

- jakarta-authentication-api 3.0.0：真机 test_package 13 检查项全过
- jakarta-inject-api 2.0.1：同口径 11 检查项全过（跨包复用，一类问题证明）

## 经验

- 「上游零测试」不等于「无可验证」：消费方探针 + 契约断言同样满足 R34，且更贴近
  用户在鸿蒙上的真实使用方式。
- 断言清单要覆盖不同子包（防止 jar 打包时漏目录），日志每断言一行（CI 审查可数）。
- assertion_count 口径写进 MANIFEST 注释，避免审查时对数字来源有争议。
