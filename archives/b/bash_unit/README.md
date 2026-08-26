# bash_unit

bash_unit 是一个单文件 Bash 单元测试框架，上游仓库为 <https://github.com/bash-unit/bash_unit>。

## 已适配版本

| 版本 | 状态 | Conan 引用 |
|---|---|---|
| 2.3.3 | built | `bash_unit/2.3.3@ohpcd/stable` |

配方将 `bash_unit` 脚本安装到 Conan 包的 `bin/`。构建阶段保留并执行完整上游测试，消费者测试会通过 Conan 运行环境实际调用包内命令。
