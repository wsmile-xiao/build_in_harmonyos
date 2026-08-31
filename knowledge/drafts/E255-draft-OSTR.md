# E255 - Conan test_package 在 OHOS 上应先解析可用 shell 再跑脚本

> **结构化数据**: [E255-draft-OSTR.kv](E255-draft-OSTR.kv)
> **类别**: testing/shell/tmpdir/portability | **严重度**: 🟡 | **阶段**: testing

## 症状

`test_package` 还没真正跑包内命令，就先因为 shell 不可用或临时目录不可写而退出。

## 根因

OHOS 的 shell 入口不一定在默认 PATH 里，bash 常在 `/data/service/hnp/bin/bash`。同时，很多脚本默认把临时文件扔到 `/tmp`，而这在 OHOS 上可能是只读的。

## 修复

1. 先找 `CONFIG_SHELL`。
2. 再找 PATH 里的 `bash`。
3. 最后回退到 HNP bash。
4. 把临时文件放到 `$HOME/tmp` 或显式 `TMPDIR`。

## 验证

- `test_package` 实际执行
- shell 脚本能落临时文件
- 退出码来自包本身，而不是环境缺口

## 关系

- `similar_to -> E002, E165, E221`
