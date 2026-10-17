# E429 — 含可选 Go 模块的 C 主库被语言预检误判

## 错误特征

`lang-preflight` 因源码根目录存在 `go.mod`，输出“任务标记 cpp，实测源码为 go”，但项目实际主要交付 `libcap.a`、`libpsx.a` 和 C 头文件，Go 模块可通过 `GOLANG=no` 关闭。

## 触发条件

- 构建系统：自定义 Makefile
- 阶段：源码语言预检
- 项目同时包含 C 核心库、`go.mod` 和可选 Go 绑定
- C 源文件占比未达到统计阈值，但构建系统明确支持关闭 Go

## 根因分析

语言检测优先采用 manifest 特征。单独依据 `go.mod` 判断项目语言时，没有结合构建开关、安装目标和实际交付物，因而将带可选 Go 绑定的 C 主库误判为纯 Go 项目。

## 解决方案

### 推荐方案

核对项目的安装目标和语言开关。若主要产物是 C/C++ 库，且 Go 模块可被明确关闭，则记录混合源码证据，使用 `GOLANG=no` 构建和测试 C 库；语言预检工具后续应将构建开关和主要安装产物纳入判定。

### 禁止做法

- ❌ 仅因存在 `go.mod` 就终止 C 库适配。
- ❌ 在没有关闭 Go 构建的情况下假装 Go 工具链可用。

## 验证

```bash
test -f go.mod
grep -n 'GOLANG' Make.Rules Makefile
make -j1 GOLANG=no PAM_CAP=no SHARED=no
make -j1 test GOLANG=no PAM_CAP=no SHARED=no
```

验证应同时确认生成 `libcap.a`、`libpsx.a`，并通过 `cap_test`、`psx_test` 和 `libcap_psx_test`。

## 关联条目

- 相关：E250（OHOS 原生环境不含 Go 工具链）
