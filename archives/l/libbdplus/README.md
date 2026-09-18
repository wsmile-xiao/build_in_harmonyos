# libbdplus

## 简介

VideoLAN 的 BD+ 研究库，实现 BD+ 系统规范，用于 Blu-ray 内容保护的 BD+ 虚拟机与转换表逻辑，是 libbluray 做 BD+ 解密的上游依赖之一。

## OHOS 适配

- configure 只认 `libgcrypt-config`/`gpg-error-config` 脚本探针，用 build 内 wrapper 回答
- 自带 config.guess（2018 版）无 ohos 识别，用相等 `--build/--host` 走 E007 fallback
- libaacs 仅是 noinst 示例的可选依赖，用 `--without-libaacs`
- 上游无自动化测试套件，按 no_tests 口径申报，test_package 提供 4 项消费者验证

## 依赖

- libgcrypt 1.11.0
- libgpg-error 1.55（经 libgcrypt 传递，配方显式声明以便 configure 探针取路径）

## 功能验证

```bash
pkg-config --modversion libbdplus  # 期望输出: 0.2.0
```

## 参考

- 官网: https://www.videolan.org/developers/libbdplus.html
- 源码: https://code.videolan.org/videolan/libbdplus
