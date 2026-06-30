# fortls 3.2.2 编译笔记

## 编译环境

- **操作系统**: OpenHarmony
- **Python版本**: 3.12.9
- **构建系统**: Python setuptools
- **源码来源**: 华为云 PyPI 镜像

## 编译步骤

### 1. 安装构建工具

由于系统缺少 pip/setuptools/wheel，需手动安装：

```bash
# 下载 wheel 包（华为云镜像）
cd ~/tmp/downloads
curl -k -L -o setuptools-68.0.0-py3-none-any.whl https://repo.huaweicloud.com/repository/pypi/packages/py3/s/setuptools/setuptools-68.0.0-py3-none-any.whl
curl -k -L -o wheel-0.41.2-py3-none-any.whl https://repo.huaweicloud.com/repository/pypi/packages/py3/w/wheel/wheel-0.41.2-py3-none-any.whl
curl -k -L -o pip-24.0-py3-none-any.whl https://repo.huaweicloud.com/repository/pypi/packages/py3/p/pip/pip-24.0-py3-none-any.whl

# 解压安装到 site-packages
python3 << 'EOF'
import zipfile, sys, os
site_packages = os.path.join(sys.prefix, 'lib', f'python{sys.version_info.major}.{sys.version_info.minor}', 'site-packages')
for whl in ['setuptools-68.0.0-py3-none-any.whl', 'wheel-0.41.2-py3-none-any.whl', 'pip-24.0-py3-none-any.whl']:
    with zipfile.ZipFile(whl, 'r') as z:
        z.extractall(site_packages)
EOF
```

### 2. 下载源码

```bash
cd ~/tmp/downloads
curl -k -L -o fortls-3.2.2.tar.gz https://repo.huaweicloud.com/repository/pypi/packages/source/f/fortls/fortls-3.2.2.tar.gz
tar -xzf fortls-3.2.2.tar.gz
```

### 3. 源码修改

由于从 tar.gz 下载而非 git 仓库，setuptools_scm 无法获取版本号，需静态指定：

```diff
--- pyproject.toml.orig
+++ pyproject.toml
@@ -35,7 +35,7 @@
     "lsp",
     "fortls",
 ]
-dynamic = ["version"]
+version = "3.2.2"
 requires-python = ">=3.7"
```

补丁文件：`patches/0001-static-version.patch`

### 4. 构建 wheel 包

```bash
cd fortls-3.2.2
python3 setup.py bdist_wheel --dist-dir ~/tmp/builds/archives/f/fortls/3.2.2/packaging
```

### 5. 安装依赖

```bash
# 下载依赖包
curl -k -L -o json5-0.9.25-py3-none-any.whl https://repo.huaweicloud.com/repository/pypi/packages/py3/j/json5/json5-0.9.25-py3-none-any.whl
curl -k -L -o packaging-21.3-py3-none-any.whl https://repo.huaweicloud.com/repository/pypi/packages/py3/p/packaging/packaging-21.3-py3-none-any.whl

# 安装到测试目录
mkdir -p ~/tmp/test-install-fortls-3.2.2
python3 -m pip install --target ~/tmp/test-install-fortls-3.2.2 \
  fortls-3.2.2-py3-none-any.whl \
  json5-0.9.25-py3-none-any.whl \
  packaging-21.3-py3-none-any.whl --no-deps
```

### 6. 创建预编译包

```bash
cd ~/tmp/test-install-fortls-3.2.2
tar -czf fortls-3.2.2-ohos-aarch64.tar.gz \
  fortls fortls-3.2.2.dist-info \
  json5 json5-0.9.25.dist-info \
  packaging packaging-21.3.dist-info \
  bin/fortls
```

### 7. 创建 debug 包

```bash
cd ~/tmp/builds/fortls-3.2.2
mkdir -p ~/tmp/builds/archives/f/fortls/3.2.2/packaging/debug
cp -r fortls fortls.egg-info build pyproject.toml setup.cfg setup.py ~/tmp/builds/archives/f/fortls/3.2.2/packaging/debug/
cd ~/tmp/builds/archives/f/fortls/3.2.2/packaging
tar -czf fortls-3.2.2-ohos-aarch64-debug.tar.gz debug/
```

## 问题与方案

| 问题 | 解决方案 |
|------|---------|
| pip/setuptools/wheel 未安装 | 从华为云镜像下载 wheel 包并手动解压安装 |
| pypi.org 网络超时 | 使用华为云 PyPI 镜像 repo.huaweicloud.com |
| setuptools_scm 版本检测失败 | 修改 pyproject.toml 静态指定版本号 |
| GitHub 下载失败 | 使用 PyPI 镜像下载源码 tar.gz |

## 验证结果

```bash
PYTHONPATH=~/tmp/test-install-fortls-3.2.2 python3 -m fortls --version
# 输出: 3.2.2
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| fortls-3.2.2-ohos-aarch64.tar.gz | 2.1MB | 预编译发布包 |
| fortls-3.2.2-ohos-aarch64-debug.tar.gz | 2.3MB | Debug 包（源码+构建目录） |
| fortls-3.2.2-py3-none-any.whl | 270KB | wheel 包 |
| 0001-static-version.patch | 368B | 补丁文件 |

## 注意事项

1. 网络连接 PyPI/GitHub 困难，建议使用华为云镜像
2. Python 3.12+ 的 site-packages 路径为 `lib/python3.12/site-packages`
3. 纯 Python 项目无需 ELF 签名