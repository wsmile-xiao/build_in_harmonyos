# streamlink 8.4.0 适配笔记

## 编译环境
- 构建系统: Python (pip + pyproject.toml)
- 编译日期: 2026-05-21
- Python 版本: 3.12.9
- 状态: published

## 编译步骤

1. **准备依赖库（C 扩展依赖）**
   - 编译 libxml2 2.15.3（使用子任务，CMake 构建）
   - 编译 libxslt 1.1.45（使用子任务，CMake 构建）
   - 设置 PKG_CONFIG_PATH=~/usr/local/lib/pkgconfig

2. **安装 Python 依赖包**
   ```bash
   export PKG_CONFIG_PATH="$HOME/usr/local/lib/pkgconfig:$PKG_CONFIG_PATH"
   export LD_LIBRARY_PATH="$HOME/usr/local/lib:$LD_LIBRARY_PATH"
   export CFLAGS="-I$HOME/usr/local/include/libxml2 -fPIC -O2"
   export LDFLAGS="-L$HOME/usr/local/lib"
   python3 -m pip install lxml pycryptodome PySocks trio trio-websocket
   ```
   - lxml 6.1.1（编译耗时约 5 分钟，需要 libxml2/libxslt）
   - pycryptodome 3.23.0（编译耗时约 3 分钟）
   - PySocks 1.7.1、trio 0.33.0、trio-websocket 0.12.2（纯 Python 包，快速安装）

3. **安装 streamlink**
   ```bash
   cd /storage/Users/currentUser/tmpexport/builds/streamlink-8.4.0.work
   python3 -m pip install --prefix=$HOME/usr/local .
   ```
   - 成功编译 wheel 包：streamlink-8.4.0-py3-none-any.whl (565KB)
   - 安装到 ~/usr/local/bin/streamlink 和 site-packages

4. **创建预编译包**
   - streamlink-8.4.0-ohos-aarch64.tar.gz（4.5MB）
   - streamlink-deps-8.4.0-ohos-aarch64.tar.gz（10MB）

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | lxml 编译失败 | 缺少 libxml2/libxslt 开发包 | 使用子任务编译 libxml2/libxslt |
| 2 | SSL 证书验证失败 | 鸿蒙系统 SSL 配置问题 | 使用 curl -k 绕过证书验证 |
| 3 | ohc-run.py 源码识别错误 | 误将 docs 目录识别为源码 | 手动解压正确的 PyPI tarball |

## 源码修改

无补丁。Python 项目直接从 PyPI 源码包编译。

## 依赖版本

### 系统库依赖
- libxml2/2.15.3
- libxslt/1.1.45

### Python 包依赖
- certifi/2026.4.22（已安装）
- isodate/0.7.2（已安装）
- lxml/6.1.1（编译安装）
- pycountry/26.2.16（已安装）
- pycryptodome/3.23.0（编译安装）
- PySocks/1.7.1（安装）
- requests/2.34.1（已安装）
- trio/0.33.0（安装）
- trio-websocket/0.12.2（安装）
- urllib3/2.7.0（已安装）
- websocket-client/1.9.0（已安装）

## 验证结果

```bash
$ streamlink --version
streamlink 8.4.0

$ pkg-config --modversion libxml-2.0 libxslt
2.15.3
1.1.45
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| streamlink-8.4.0-ohos-aarch64.tar.gz | 4.5MB | streamlink 主程序包 |
| streamlink-deps-8.4.0-ohos-aarch64.tar.gz | 10MB | Python 依赖包（lxml/pycryptodome/trio等） |

## 注意事项

1. **必须先安装 libxml2/libxslt**：lxml 编译依赖这两个库
2. **需要设置 PKG_CONFIG_PATH**：pip 编译 lxml 时需要找到 libxml2/libxslt 的 pkg-config 文件
3. **Python 项目无需 ELF 签名**：纯 Python 包无需签名，但 C 扩展包（lxml/pycryptodome）已包含编译后的二进制模块
4. **依赖包分离打包**：streamlink 本体与依赖分开打包，方便用户选择安装
