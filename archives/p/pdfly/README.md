# pdfly

## 简介

pdfly 是一个纯 Python CLI 应用程序，用于操作 PDF 文件。支持 PDF 合并、拆分、压缩、提取文本/图像、添加签名等功能。

## OHOS 适配

pdfly 是纯 Python 包，无需编译 C 代码。使用 flit_core 构建系统，直接生成 wheel 包。

适配要点：
- 无需修改源码
- 构建命令：`python3 -m pip wheel . --no-deps -w dist/`
- 安装命令：`python3 -m pip install dist/pdfly-*.whl --no-deps --target=...`

已知问题：
- 运行时依赖较多（pypdf, typer, pillow, cryptography 等）
- PyPI 下载可能较慢，建议配置国内镜像源

## 依赖

### 构建依赖
- flit_core >= 3.2

### 运行依赖
- pypdf[full] >= 5.1.0
- typer >= 0.12.4
- pillow
- pydantic
- rich
- fpdf2 >= 2.8.1
- asn1crypto
- cryptography
- endesive
- requests >= 2.32.5

## 功能验证

```bash
pdfly --version
pdfly --help
pdfly meta sample.pdf
pdfly extract-text sample.pdf output.txt
```

## 参考

- 官网：https://github.com/py-pdf/pdfly
- PyPI：https://pypi.org/project/pdfly/