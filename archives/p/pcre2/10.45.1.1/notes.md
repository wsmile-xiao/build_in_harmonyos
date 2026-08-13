# pcre2 10.45.1.1 适配笔记

## 编译环境

- 构建系统: Autotools + Conan 2
- 编译日期: 2026-08-11
- 编译器: clang/clang++
- 目标平台: HarmonyOS PC aarch64
- 状态: shadow CI passed

## 编译步骤

配方下载 PCRE2 10.45 源码，应用 HarmonyOS 平台识别和 HMDFS 权限补丁，
只恢复已知 Autotools 辅助脚本的执行位，然后通过 `sh configure` 配置静态
8/16/32 位码元库。构建完成后执行上游 `make -j1 check`，再由 Conan 运行
`test_package` 消费者测试。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `configure` 或辅助脚本报 `Permission denied` | 源码经过 HarmonyOS/HMDFS 路径后未保留执行位 | 仅对 `configure`、`config.guess`、`config.sub`、`install-sh`、`missing` 恢复执行位，并通过 `sh` 调用 `configure` |
| 2 | 下游需要 `libpcre2-16`/`libpcre2-32` | 默认配置只启用 8 位码元库 | 增加 `--enable-pcre2-16` 和 `--enable-pcre2-32`，并声明 Conan components |

## 源码修改

- `0001-config.guess.patch`: 识别 HarmonyOS。
- `0002-config.sub.patch`: 接受 `linux-ohos` 目标三元组。
- `0003-configure.patch`: 使用 `umask 022` 创建 `config.status` 临时目录，避免 HMDFS 权限问题。

## 依赖版本

无第三方运行时依赖。

## 验证结果

```bash
zsh ci/conan/build_and_test.sh archives/p/pcre2/10.45.1.1

make -j1 check: 3/3 top-level suites passed
Conan test_package: 1/1 passed
L0/L1/L2/L4/L5: passed
```

## 交付物

静态库包括 `libpcre2-8.a`、`libpcre2-16.a`、`libpcre2-32.a` 和
`libpcre2-posix.a`，并安装 `pcre2-config`、`pcre2grep`、`pcre2test`。

## 注意事项

知识内容只提交到 `knowledge/drafts/`；正式 `knowledge/graph/E###.kv` 条目由
主编审核分配编号后入库。
