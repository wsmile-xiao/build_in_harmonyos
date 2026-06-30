# E099: config.guess 无法识别 HarmonyOS

## 问题表现

configure脚本执行时无法识别系统类型：
```
config.guess: unable to guess system type
cannot determine system type
HarmonyOS: unknown
```

## 根因分析

uname返回"HarmonyOS"，config.guess脚本中没有对应的匹配模式，导致无法识别系统类型。

## 解决方案

修改config.guess添加HarmonyOS到匹配模式：

```bash
sed -i 's/Linux|GNU|GNU/\/*/Linux|GNU|GNU/*|HarmonyOS/' config.guess
sed -i 's/aarch64:Linux:\*:\*/aarch64:Linux:*:*|aarch64:HarmonyOS:*:*/' config.guess
```

## 影响范围

所有使用autotools的项目，configure需要识别系统类型的软件。

## 验证方法

```bash
./config.guess | grep -E "aarch64.*linux.*gnu"
echo "HarmonyOS recognized correctly"
```

## 分类

- 类别: platform, detection, autotools, configure
- 严重性: 2（可通过修改config.guess解决）
- 贡献者: 0D0A