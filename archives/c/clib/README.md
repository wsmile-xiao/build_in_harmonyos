# clib — C 包管理器

clib 是 clibs 生态的 C 包管理器:从 GitHub 拉取并安装 C 包。本目录收录其
OpenHarmony PC(aarch64/OHOS)适配产物,含 9 个命令行工具。

## 功能概述

- `clib` 主程序:按 `which("clib-<command>")` 在 PATH 中分发子命令
- `clib-install`:按 clib.json/package.json 的依赖声明拉取并安装包
- `clib-search`:检索 clibs 包索引
- `clib-init`:初始化新项目骨架(生成 clib.json)
- `clib-configure` / `clib-build`:调用包声明的 configure/build 脚本
- `clib-update` / `clib-upgrade`:更新依赖 / 升级自身
- `clib-uninstall`:卸载包

## OHOS 适配要点

- **纯 Makefile 构建**:无 configure;配方经任务内 curl-config shim 把 Conan
  libcurl 的 include/lib 路径注入 Makefile(上游硬编码 `curl-config` 探测)
- **musl 无 pthread_cancel**:上游 `scripts/feature-test-pthreads` 构建期探测
  失败后自动走串行回退路径;测试 Makefile 已改走同一探测
- **无系统 CA 默认路径**:vendored http-get 运行时探测 CA 库
  (CURL_CA_BUNDLE/SSL_CERT_FILE env、常见 Linux 路径、
  /system/etc/security/certificates 目录)并设置 CURLOPT_CAINFO/CURLOPT_CAPATH
- **零 `__OHOS__` 条件编译**:平台差异全部经特性探测/运行时探测解决

## 依赖关系

### 编译依赖
- curl/8.15.0(Conan;传递依赖 openssl/3.5.6.1、zlib/1.3.1.1)

### 运行依赖
- libcurl.so(动态链接)
- CA 证书库(见上:env 或系统目录任一可用即可)

## 上游测试

- 上游套件:12 个 shell 集成测试 + test/package 56 用例 + test/cache 5 用例
- 本适配设备实测:TOTAL=73 PASS=73 FAIL=0 SKIP=0 NOT_RUN=0
- 测试构建适配逐项说明见版本目录 notes.md 与 PR

## 上游

- 仓库:https://github.com/clibs/clib
- 版本:2.8.7(2024-06-28)
- 许可证:MIT
