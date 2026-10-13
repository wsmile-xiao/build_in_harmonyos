# jenkins-debian-glue

jenkins-debian-glue 是 Michael Prokop（grml/Debian 开发者）编写的
Jenkins CI 粘合脚本集，用于在 Jenkins 中直接从 Git/Subversion 仓库
构建 Debian/Ubuntu 软件包，并提供 reprepro 仓库管理与 TAP 格式质量
检测辅助脚本。

- 上游仓库: https://github.com/mika/jenkins-debian-glue
- 许可证: MIT
- 类型: CLI 工具集（纯 bash/ruby 脚本，无编译）
- 运行时依赖: 系统 bash、grep、file、ruby（OHOS PC 内置
  /data/service/hnp/bin）；jdg-* 构建类脚本的完整功能（dpkg 构建、
  pbuilder、reprepro 等）依赖 Debian 打包工具链，在 OHOS 上仅
  通用文本处理类脚本可用

## 鸿蒙 PC 适配要点

- 补丁 0001：shebang `/bin/bash` → `/usr/bin/env bash`；tap/* 的
  file(1) 探测移植（OHOS file 不支持 `-Pbytes=32`/`-i`）。
- test_package 以纯 bash 逐项 1:1 重放上游 `make check` 的 18 项
  shunit2 断言（shunit2 在 OHOS 不可用），19/19 通过。
- 软件级 `commands.json` 已声明（R38，tool 类型）。

## 版本

| 版本 | 状态 | 说明 |
|------|------|------|
| 0.23.6 | published | 首次适配（上游版本） |
