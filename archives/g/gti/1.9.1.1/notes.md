# gti 1.9.1.1 编译与测试记录

## 源码

- 包版本：`1.9.1.1`（上游 `v1.9.1` 的 OHPCD 包装修订版本，用于避开已发布 `gti/1.9.1` 制品冲突）
- 上游版本：`v1.9.1`
- 官方源码：`https://github.com/rwos/gti/archive/refs/tags/v1.9.1.tar.gz`
- SHA-256：`f8a3afdd3967fe7d88bd1b0b9f5cb62ae04dc9ba458238da91efc213f61a9cf9`
- 构建系统：Makefile
- 外部依赖：无

发布包仅包含 `gti.c`、Makefile、文档和 shell 补全文件，没有
`test/`、`tests/`、测试源文件或测试目标，因此上游自动化测试用例为 0。

## 适配内容

- 使用 Conan 从官方源码和固定 SHA-256 可复现构建。
- 在终端宽度查询失败或返回 0 时回退到 80 列，避免非 TTY 环境读取未初始化值。
- 打包 `gti`、man page、Bash/Zsh 补全和许可证。
- OHOS 正式打包环境中使用 `/data/service/hnp/bin/binary-sign-tool` 对 ELF 签名。
- 新增 5 个确定性的 `test_package` 场景，共 21 个断言。

## 验证结果

### Linux Conan 与本地 CI 模拟

- GCC：14.2.0
- `conan create`：通过
- 仓库 `ci/conan/build_and_test.sh`：L0、L1、L1e、L2、L4、L5 全部通过
- 新增测试：5/5（100%），21/21 断言通过
- L1e 破坏性反向验证：移走 `bin/` 后测试按预期失败

### OHOS 交叉编译

- DevEco OHOS clang：15.0.4
- `aarch64-linux-ohos`：编译和链接通过
- `x86_64-linux-ohos`：编译和链接通过
- 两个产物均为 PIE ELF，仅动态依赖 `libc.so`

### 鸿蒙 PC 模拟器

- 环境：OpenHarmony 6.1.0.115，x86_64
- HDC 推送产物 SHA-256：
  `1ececbdaa464fa4426280d10c24a043608d43b0bdb2b8a97891ac66859964678`
- 新增测试：5/5（100%），21/21 断言通过
- 子进程退出码 23 可正确传播
- git 不存在时按预期返回失败
- 指定缺失的 gti 产物时测试按预期返回 `REMOTE_RC=1`

## 限制说明

本地模拟器镜像不包含 CI Worker 的 `binary-sign-tool`，因此模拟器验证的是
DevEco OHOS x86_64 产物的直接执行。配方中的签名步骤仍需由官方 OHOS Worker
在当前提交上验证；本文不把尚未产生的官方 CI 结果写成通过。

**最终状态**：built
