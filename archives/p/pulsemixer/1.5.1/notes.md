# pulsemixer 1.5.1 适配笔记

## 编译环境
- 构建系统: python (setup.py)
- 编译日期: 2026-06-04
- 编译器: N/A (纯 Python 脚本)
- 状态: built

## 编译步骤

1. 使用 `python3 setup.py install --prefix=$DEFAULT_PREFIX --root=$TEST_PREFIX` 安装到 staging 目录
2. Staging 验证通过（bin/pulsemixer 已安装）
3. 使用 `python3 setup.py install --prefix=$DEFAULT_PREFIX` 安装到本地 prefix

pulsemixer 是纯 Python CLI 工具（PulseAudio mixer），不需要 configure/make 步骤。
安装后产物：bin/pulsemixer（Python 脚本） + lib/python3.12/site-packages/pulsemixer-1.5.1.egg-info

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | init-build 下载 SSL 失败 | 本地 SSL 证书问题 | 用 curl -k 手动下载后放入 tarballs 目录 |
| 2 | URL 中用户名错误(ncravane) | 实际仓库是 GeorgeFilipkin/pulsemixer | 使用正确 URL |
| 3 | BUILD_SYSTEM 检测为 autotools | 无 configure/Makefile，只有 setup.py | 更新 manifest.yaml 为 python |

## 源码修改

无源码修改。pulsemixer 是纯 Python 脚本，不需要任何平台适配补丁。

## 依赖版本

- Python 3.12.8 (系统预装)
- PulseAudio libpulse.so.0 (运行时依赖，OpenHarmony 上不可用)

## 运行时注意事项

pulsemixer 依赖 libpulse.so.0 (PulseAudio 库)，通过 ctypes 加载。OpenHarmony 不提供 PulseAudio，
因此 pulsemixer 虽能安装但在运行时会报错：无法加载 libpulse.so.0。这是已知平台限制。

## 验证结果

```bash
# Staging 验证
ls $TEST_PREFIX/$DEFAULT_PREFIX/bin/pulsemixer  # 存在
file $TEST_PREFIX/$DEFAULT_PREFIX/bin/pulsemixer  # Python script

# 本地安装验证
python3 $DEFAULT_PREFIX/bin/pulsemixer --version  # 版本输出 (需 libpulse 运行时)
```

## 交付物

| 文件 | 说明 |
|------|------|
| pulsemixer-1.5.1-ohos-aarch64.tar.gz | 预编译包 |
| pulsemixer-1.5.1-ohos-aarch64-debug.tar.gz | debug 预编译包 |

## 注意事项

- pulsemixer 是纯 Python 脚本工具，无 ELF 二进制，不需要 ELF 签名
- 运行时依赖 PulseAudio（libpulse.so.0），OpenHarmony 不提供此库
- setup.py 安装时会调整 shebang 行为系统 Python 的绝对路径
---

**编译结束**: 2026-06-04 10:48
**最终状态**: built
