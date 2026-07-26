# bashunit

bashunit 是 TypedDevs 维护的 Bash 测试框架。0.40.0 官方发布物是一个可执行的单文件 Bash CLI，不是 Autotools 或 C/C++ 源码归档。官方网站为 <https://bashunit.com/>。

## 已适配版本

| 版本 | 状态 | Conan 引用 |
|------|------|------------|
| 0.40.0 | built | `bashunit/0.40.0@ohpcd/stable` |

配方下载并校验官方 release 资产，将 `bashunit` 安装到 Conan 包的 `bin/`，消费者测试会实际执行版本命令及一条包含断言的 Bash 测试。
