# mypy 2.1.0 适配笔记

## 编译环境
- 构建系统: pip (Python包)
- 编译日期: 2026-06-10
- 编译器: N/A (pure Python package)
- 状态: built

## 编译步骤

mypy是Python+C扩展包，采用pip wheel方式构建：

1. 从Aliyun PyPI镜像下载源码: `curl -L http://mirrors.aliyun.com/pypi/packages/82/15/.../mypy-2.1.0.tar.gz`
2. 从Aliyun镜像下载纯Python wheel: `curl -L http://mirrors.aliyun.com/pypi/packages/0d/2a/.../mypy-2.1.0-py3-none-any.whl`
3. 下载依赖: `mypy_extensions-1.1.0`, `typing_extensions-4.14.1`, `pathspec-0.12.1`
4. 手动解压wheel到DESTDIR staging目录
5. 创建入口脚本(wrapper): `mypy`, `dmypy`, `mypyc`, `stubgen`, `stubtest`
6. 验证: `PYTHONPATH=... python3 -c "from mypy.version import __version__; print(__version__)"` → 2.1.0

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | HTTPS下载超时 | OHOS环境不支持HTTPS出站 | 切换pip到HTTP Aliyun镜像 |
| 2 | init-build嵌套源码检测错误 | 脚本误将docs/目录提升为源码 | 手动修复.work目录为实际mypy源码 |
| 3 | 自动构建(make)失败 | mypy是Python包,Makefile是Sphinx文档 | 改用pip wheel手动构建 |
| 4 | DESTDIR staging安装空 | pip在受限网络下挂起 | 手动解压wheel+创建wrapper脚本 |

## 源码修改

无源码修改(纯Python包,直接使用wheel)

## 依赖版本

| 依赖 | 版本 |
|------|------|
| typing_extensions | 4.14.1 |
| mypy_extensions | 1.1.0 |
| pathspec | 0.12.1 |

## 验证结果

```bash
PYTHONPATH="$DEFAULT_PREFIX/lib/python3.14/site-packages" python3 -c "from mypy.version import __version__; print(__version__)"
# 输出: 2.1.0
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| mypy-2.1.0-ohos-aarch64.tar.gz | 11.5MB | 预编译包(pure Python) |

## 注意事项

- mypy是pure Python包,mypy-2.1.0-py3-none-any.whl,无C扩展需要编译
- 需要PYTHONPATH设置才能运行(wrapper脚本已包含)
- 网络环境仅支持HTTP(非HTTPS),需配置pip为HTTP镜像
