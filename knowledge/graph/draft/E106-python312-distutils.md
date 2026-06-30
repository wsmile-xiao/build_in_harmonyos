# E106: Python 3.12 distutils.msvccompiler 模块移除

## 错误特征

```
ImportError: No module named 'distutils.msvccompiler'
```

## 根因

Python 3.12 移除了 distutils 模块。setuptools 提供的兼容层将 msvccompiler 重命名为 _msvccompiler。

## 解决方案

修改导入语句：

```python
try:
    from distutils.msvccompiler import MSVCCompiler
except ImportError:
    from distutils._msvccompiler import MSVCCompiler
```

## 适用范围

所有使用 distutils.msvccompiler 的软件。
