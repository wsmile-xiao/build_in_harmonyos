## 适配对象

- 软件：`flamethrower`
- 版本：`0.1.8`
- 任务：OHPCD contrib task 130
- 分支：`feat/flamethrower-0.1.8`
- 上游来源：Debian/SystemImager Flamethrower 0.1.8，不是同名 DNS-OARC C++ 项目

## 适配范围

本适配为纯 Perl 应用提供 Conan 配方、可重定位命令包装器、AppConfig 配置解析、udpcast 运行时依赖和 OpenHarmony PC aarch64 消费者验证。依赖固定为 `perl/5.42.2`、`appconfig/1.71.1` 和 `udpcast/20250223`。

## 测试情况

上游源码没有可执行测试套件，盘点结果为 `0/0`（不适用）。适配新增一个 `test_package` consumer，用于验证两个命令版本、模块与配置解析、可选 debug 的省略/显式路径、未知 accessor 精确诊断、udpcast 工具可见性和负向退出码传播，当前目标端结果为 `1/1`（100%）。

## 知识库查重与复用

现有知识条目没有覆盖 AppConfig 可选变量“先注册、再对返回值做 defined guard”的完整契约。本任务新增 E2154 草稿，记录 omitted debug、explicit debug 和 unknown accessor 三类验证边界；该结论可复用于其他基于 AppConfig 的 Perl 应用。

## 当前边界

`appconfig/1.71.1` 已通过 fresh isolated OHOS/arm64 `--build=never` 解析并从 `ohpcd` 下载。Flamethrower 的正式提交仍以最终 staged tree 的 W0-W5、独立 W4、finish、Pre-PR、当前 HEAD Review/CI 和贡献任务绑定为准。
