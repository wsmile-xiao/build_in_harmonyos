# autoenv 0.4.0 适配笔记

## 编译环境
- 构建系统: custom
- 编译日期: 2026-07-15
- 编译器: N/A (pure shell)
- 状态: published

## 编译步骤

autoenv 是纯 shell hook 项目，不产生 native 二进制。Conan 配方下载 v0.4.0 源码，执行上游 `sh tests/test.sh` 作为可运行平台上的测试，然后将 `activate.sh`、README 和 LICENSE 打入包中。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 初始化下载阶段证书校验失败 | Python 默认 CA 路径未指向本机证书文件 | 使用 `SSL_CERT_FILE=/storage/Users/currentUser/usr/local/ssl/cert.pem` 重新初始化 |
| 2 | 项目无编译产物 | autoenv 只提供 shell hook | 将 `activate.sh` 作为 `res/autoenv/activate.sh` 资源文件交付 |

## 源码修改

无源码补丁。

## 依赖版本

无第三方 Conan 依赖。

## 验证结果

```bash
bash ci/scripts/preflight_check.sh autoenv/0.4.0
python3 scripts/ohc-run.py init-build autoenv 0.4.0 --url https://github.com/hyperupcall/autoenv/archive/refs/tags/v0.4.0.tar.gz --tar tar.gz --auto
conan create archives/a/autoenv/0.4.0 --build=missing
```

## 交付物

| 文件 | 说明 |
|------|------|
| res/autoenv/activate.sh | autoenv shell hook |
| res/autoenv/README.md | 上游使用说明 |
| licenses/LICENSE | MIT license |

## 注意事项

使用时需要在目标 shell 中 source `res/autoenv/activate.sh`。autoenv 默认会在首次遇到 `.env` 时进行授权；测试中使用 `AUTOENV_ASSUME_YES=1` 避免交互。
---

**编译结束**: 2026-07-15 06:47
**最终状态**: published
