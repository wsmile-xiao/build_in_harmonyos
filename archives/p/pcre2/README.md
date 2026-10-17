# PCRE2 OpenHarmony PC adaptation

## 基本信息
- 软件: pcre2
- 当前版本: 10.47
- 构建系统: Autotools
- 目标: ohos-aarch64

## 编译指导
- 静态 PIC 形式提供 8/16/32 位码元库和 POSIX 包装层。
- 启用 JIT；`make -j1 check` 是配方构建的强制步骤。
- `pcre2grep` 不链接可选的 zlib 或 bzip2。

## 补丁清单
- `config.sub` 接受 Conan 使用的 `aarch64-linux-ohos` 三元组。
- `configure` 通过当前构建目录能力探测选择可用的 POSIX shell。
- OHOS 构建环境绑定系统 `mkdir -p`，避免 `config.status` 直接执行 HMDFS 中的 `install-sh`。
- `make check` 仅通过所选 shell 解释两个上游脚本测试，编译后的测试 ELF 保持直接执行。

## 已知限制
- 包保持静态，避免与系统同名 PCRE2 共享库发生装载冲突。

## 功能验证
- 上游测试：`make -j1 check`，官方库存 4 项。
- 消费者测试：8/16/32 位 API、POSIX API、`pcre2grep`、`pcre2test`、
  pkg-config 静态链接消费者和 `pcre2-config` 重定位校验。
