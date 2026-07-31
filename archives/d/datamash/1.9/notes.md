# datamash 1.9 适配笔记

## 构建策略

- 构建系统：Autotools
- 源码：GNU 官方 1.9 发布包，SHA256 已固定
- Conan 依赖：无
- 配置：禁用 NLS，保留本地 bash completion
- 安装：使用 `install-exec` 安装 `datamash` 和 `decorate`

## OHOS 适配

1. `config.guess` 增加 HarmonyOS / `__OHOS__` 识别。
2. `configure` 创建临时目录时使用 `umask 022`，避免 HMDFS 权限异常。
3. 上游 `config.sub` 已原生接受 `linux-ohos`，不再添加重复补丁。
4. 不修改上游测试内容和期望结果。

## 测试

上游 `make check` 注册 30 个测试程序，其中 23 个 Perl 套件包含
1,312 个显式测试条目。Linux/Clang 基线结果：

```text
TOTAL: 30
PASS:  27
SKIP:  3
FAIL:  0
```

三个跳过项分别是缺少 `de_DE.UTF-8` locale，以及上游默认关闭的两个
expensive 测试。Conan 配方仍执行完整 `make check`，没有删除或绕过测试。

`test_package` 额外执行 10 项打包后命令测试，覆盖两个可执行文件、统计、
分组、转置、表格检查、罗马数字排序和错误输入。

## 验证边界

- Linux 原生构建和上游测试：通过
- 本地 OHOS AArch64：未运行
- OHOS 构建、ELF 与动态依赖：以赛事官方 CI 为最终结果
