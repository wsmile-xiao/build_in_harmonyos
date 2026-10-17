# DRAFT-7939-gpgmepy-swig-setup-py-bypass

## SWIG Python 扩展绕过 autotools 直驱 setup.py

### 问题

OHOS PC 开发环境缺少 automake/libtool，上游用 autotools + setup.py build 构建 SWIG Python 扩展时 configure 失败。

### 根因

OHOS 仅提供 bare clang + make，不包含 autotools 完整栈。上游 configure.ac 用 AC_CONFIG_FILES([setup.py]) 依赖 automake 生成 setup.py，缺失时 aclocal/configure 均失败。

### 处理方法

在 Conan 配方 build() 中用 Python 字符串替换模拟 autotools 的模板生成逻辑：读取 setup.py.in，用 Conan 依赖路径替换占位符（@VERSION@/@GPGME_CFLAGS@/@GPGME_LIBS@ 等），写入 build 目录作为 setup.py，直接调用 python setup.py build。

### 落地

gpgmepy 2.0.0 配方 `_setup_py()` 方法实现此模式。

### 适用范围

所有在 OHOS 上用 autotools + SWIG 构建 Python 扩展的包。
