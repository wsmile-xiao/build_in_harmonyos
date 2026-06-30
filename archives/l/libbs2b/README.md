# libbs2b

## 简介

libbs2b 是 Bauer stereophonic-to-binaural DSP 库，将立体声音频转换为双耳信号，用于耳机聆听时消除"头中效应"。

## OHOS 适配

- **config.guess**: 2009版脚本不含 HarmonyOS 检测，需添加 `aarch64-unknown-linux-ohos` 分支
- **config.sub**: 需添加3处 ohos 识别规则（内核、OS白名单、内核-OS组合）
- **sndfile**: 可选依赖，缺少时不编译 bs2bconvert 工具（仅影响转换功能，核心库不受影响）
- **mktemp**: HarmonyOS sandbox 限制 umask-077 目录写入，需 wrapper 设置 0755 权限
- **临时目录**: configure/config.status 中 `./confXXXXXX` 需改为 `$TMPDIR` 创建

## 依赖

- 无强制外部依赖
- libsndfile（可选，用于 bs2bconvert）

## 功能验证

```bash
bs2bstream --help       # 输出版本和用法
pkg-config --modversion libbs2b  # 返回 3.1.0
```

## 参考

- SourceForge: https://sourceforge.net/projects/bs2b/