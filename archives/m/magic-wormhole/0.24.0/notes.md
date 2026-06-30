# magic-wormhole 0.24.0 适配笔记

## 编译环境
- 构建系统: Python pip (setuptools)
- 编译日期: 2026-06-01
- 编译器: N/A (纯Python项目)
- Python版本: 3.12.8
- 状态: published

## 编译步骤

magic-wormhole 是纯 Python 项目，使用 pip 安装而非传统的 configure/make 流程：

1. **安装依赖**: 使用 pip install --no-deps 安装各依赖包，避免 cffi 重建问题
   - twisted 26.4.0 (pip install --no-deps)
   - autobahn 25.12.2 (pip install --no-build-isolation --no-deps)
   - txaio 25.12.2 (pip install --no-build-isolation --no-deps)
   - automat 25.4.16 (pip install --no-deps)
   - humanize 4.15.0 (pip install --timeout=300)
   - txtorcon 26.6.0 (pip install --no-deps)
   - zipstream-ng 1.9.2 (pip install --no-deps)
   - iterable-io 1.0.4 (pip install --no-deps)
   - qrcode 8.2 (pip install --timeout=300)
   - service_identity 23.1.0 (pip install --no-deps, 降级以兼容 cryptography 44.0.0)
   - pyopenssl 26.2.0 (pip install --no-deps)
   - hatchling 1.29.0 (pip install --timeout=300, 构建后端)

2. **pip DESTDIR 安装** (staging隔离):
   `pip install --no-deps --prefix=$DEFAULT_PREFIX --root=$TEST_PREFIX $BUILD_SRC_DIR`

3. **pip 本地安装** (模拟用户部署):
   `pip install --no-deps --prefix=$DEFAULT_PREFIX $BUILD_SRC_DIR`

4. **创建 .pth 文件**: 解决 pip 安装路径问题
   `echo "/storage/Users/currentUser/usr/local/lib/python3.12/site-packages" > $DEFAULT_PREFIX/lib/python3.12/site-packages/magic-wormhole.pth`

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | pip install autobahn 失败 (cffi 重建) | pip 尝试重建 cffi wheel, 但缺少 libffi-dev 头文件 | 使用 --no-build-isolation --no-deps, 依赖已安装的 cffi |
| 2 | autobahn import 失败 (缺 txaio) | autobahn 需 txaio 依赖但 --no-deps 跳过了 | 手动安装 txaio |
| 3 | service_identity import 失败 (cryptography.hazmat.asn1) | service_identity 26.1.0 要求 cryptography>=43 且有 asn1 模块, 系统 cryptography 44.0.0 不包含 | 降级 service_identity 到 23.1.0 |
| 4 | pip install 超时 (网络慢) | 从 PyPI 下载大型包(Twisted ~3.2MB)耗时较长 | 使用 --timeout=300 增加超时 |

## 依赖版本

| 依赖 | 版本 | 来源 |
|------|------|------|
| Python | 3.12.8 | 系统预装 |
| spake2 | 0.9 | 系统预装 |
| PyNaCl | 1.5.0 | 系统预装 |
| attrs | 24.3.0 | 系统预装 |
| cryptography | 44.0.0 | 系统预装 |
| click | 8.1.8 | 系统预装 |
| tqdm | 4.67.1 | 系统预装 |
| twisted | 26.4.0 | pip 安装 |
| autobahn | 25.12.2 | pip 安装 |
| txaio | 25.12.2 | pip 安装 |
| automat | 25.4.16 | pip 安装 |
| humanize | 4.15.0 | pip 安装 |
| txtorcon | 26.6.0 | pip 安装 |
| zipstream-ng | 1.9.2 | pip 安装 |
| iterable-io | 1.0.4 | pip 安装 |
| qrcode | 8.2 | pip 安装 |
| service_identity | 23.1.0 | pip 安装(降级) |
| pyopenssl | 26.2.0 | pip 安装 |

## 验证结果

```bash
$ wormhole --version
magic-wormhole 0.24.0

$ python3 -c "import wormhole; print(wormhole.__version__)"
0.24.0

$ wormhole send --help
Usage: wormhole send [OPTIONS] [TEXT]
  Send a text message, file, or directory

$ wormhole receive --help  
Usage: wormhole receive [OPTIONS] [CODE]
  Receive a text message, file, or directory
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| magic-wormhole-0.24.0-ohos-aarch64.tar.gz | 2033KB | 预编译包(纯Python脚本+包+pth) |
| bin/wormhole | 262B | 入口脚本(console_scripts) |
| bin/magic-wormhole | 262B | 入口脚本(别名) |
| lib/python3.12/site-packages/wormhole/ | - | Python包主体 |
| lib/python3.12/site-packages/magic-wormhole.pth | - | .pth路径文件 |

## 注意事项

1. **纯Python项目**: 不需要ELF签名、不需要strip、不需要RPATH设置
2. **依赖不打包**: wormhole 的依赖(twisted, autobahn等)不在预编译包中, 需用户系统已有或通过 cmd-pkgs 安装
3. **.pth文件**: 预编译包包含 magic-wormhole.pth, 需安装到系统 Python site-packages 以使 wormhole 可被 import
4. **service_identity 版本**: 降级到 23.1.0 以兼容系统 cryptography 44.0.0, 26.1.0 版本需要 cryptography.hazmat.asn1 模块
5. **pip --no-build-isolation**: 部分 Python 包(autobahn)使用 hatchling 构建后端, 需要此选项避免 cffi 重建问题
---

**编译结束**: 2026-06-01 21:11
**最终状态**: published
