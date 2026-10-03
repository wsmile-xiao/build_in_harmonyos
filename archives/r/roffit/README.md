# roffit

roffit 是 Daniel Stenberg（curl 作者）编写的单文件 Perl 脚本工具，用于将
nroff/troff 格式的 man page 转换为 HTML 页面，是 curl 等项目文档工具链的
组成部分。

- 上游仓库: https://github.com/bagder/roffit
- 许可证: curl (MIT-style, SPDX: curl)
- 类型: CLI 工具（纯 Perl 脚本，无编译）
- 运行时依赖: perl/5.42.2.3（ohpcd 制品仓）

## 鸿蒙 PC 适配要点

- 补丁 0001：以纯 Perl 等价实现替代非核心 CPAN 模块 HTML::Entities，
  输出与上游黄金文件字节级一致。
- test_package 复现上游 `make test` 黄金文件用例。

## 版本

| 版本 | 状态 | 说明 |
|------|------|------|
| 0.17 | published | 首次适配（上游版本） |
