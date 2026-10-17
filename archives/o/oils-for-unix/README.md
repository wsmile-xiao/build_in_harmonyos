# oils-for-unix

Oils for Unix 是 Oils 项目发布的 C++ 版 Unix shell，是 bash 的升级路径。它以单个 `oils-for-unix` 二进制（busybox 风格）提供两个 shell：

- **OSH** — 兼容 POSIX/bash 的 shell，用于运行既有 shell 脚本；
- **YSH** — 结构化数据 shell，融合 shell、Python、JSON、YAML 的表达能力。

安装后 `bin/` 下包含 `oils-for-unix`、`osh`（符号链接）和 `ysh`（符号链接）。

## OHOS 适配

- **构建系统**：自定义 POSIX shell `./configure` + `_build/oils.sh` 编译驱动（非 autotools、非 raw Makefile）。
- **依赖**：无强制第三方依赖（仅需 C++11 编译器 + libc/libc++）；GNU readline 为可选依赖，OHOS 未提供，已通过 `--without-readline` 禁用（不影响脚本/非交互功能）。
- **平台差异**：上游默认安装 `strip` 后的二进制，但 OHOS 上 strip 重写后的镜像会触发 ELF 校验 `Operation not permitted`，故打包未 strip 的二进制（功能一致、可直接运行）。

## 验证

```bash
osh -c 'echo hi'          # hi
ysh -c 'echo hi'          # hi
oils-for-unix --version   # Oils 0.37.0
```

## 参考

- 官网：https://oils.pub/
- 源码仓库：https://github.com/oils-for-unix/oils
- 发行说明：https://oils.pub/release/0.37.0/
