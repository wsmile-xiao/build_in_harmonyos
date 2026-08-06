# check-jsonschema 0.28.4 适配笔记

## 编译环境
- 构建系统: custom (Python/pip)
- 编译日期: 2026-06-04
- 编译器: N/A (Python项目)
- 状态: built

## 编译步骤

Python CLI工具，使用pip3安装：
1. `pip3 install check-jsonschema==0.28.4 --break-system-packages --no-warn-script-location`
2. Python .so依赖需要ELF签名（rpds, regress, charset_normalizer）
3. rpds/regress __init__.py需要ctypes preload补丁（解决$ORIGIN/../.libs RPATH在HarmonyOS不被解析的问题）
4. `pip3 install --root=$TEST_PREFIX` 创建staging目录（DESTDIR模式）

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | Python SSL模块ImportError | _ssl.so链接libcrypto符号未找到 | LD_LIBRARY_PATH加入harmonybrew/lib |
| 2 | rpds .so Permission denied | HarmonyOS ELF签名要求 | ohc-run.py sign-elf 签名所有.so |
| 3 | rpds/regress ImportError: libgcc_s bundled库RPATH不解析 | HarmonyOS musl ldso不处理$ORIGIN RPATH | 修改__init__.py ctypes preload libgcc_s |
| 4 | check-jsonschema ModuleNotFoundError | pip3安装到/usr/local但Python不搜索 | 安装到harmonybrew Python site-packages |

## 源码修改

### 0001-rpds-init-ctypes-preload.patch
修改rpds/__init__.py，在from .rpds import *之前添加ctypes preload bundled libgcc_s:
```python
import ctypes
import os
_libgcc_path = os.path.join(os.path.dirname(__file__), '..', 'rpds_py.libs', 'libgcc_s-0bf60adc.so.1')
if os.path.exists(_libgcc_path):
    ctypes.CDLL(_libgcc_path, mode=ctypes.RTLD_GLOBAL)
```

### 0002-regress-init-ctypes-preload.patch
修改regress/__init__.py，类似ctypes preload:
```python
import ctypes
import os
_libgcc_path = os.path.join(os.path.dirname(__file__), '..', 'regress.libs', 'libgcc_s-39080030.so.1')
if os.path.exists(_libgcc_path):
    ctypes.CDLL(_libgcc_path, mode=ctypes.RTLD_GLOBAL)
```

## 依赖版本

- jsonschema 4.26.0
- rpds-py 2026.5.1
- regress 2025.10.1
- ruamel.yaml 0.18.6
- requests 2.34.2
- click 8.4.1
- charset_normalizer 3.4.7
- attrs 26.1.0
- referencing 0.37.0
- jsonschema-specifications 2025.9.1
- certifi 2026.5.20
- idna 3.18
- urllib3 2.7.0

## 验证结果

```bash
$ /storage/Users/currentUser/usr/local/bin/check-jsonschema --version
check-jsonschema, version 0.28.4
```

## 交付物

| 文件 | 说明 |
|------|------|
| check-jsonschema-0.28.4-ohos-aarch64.tar.gz | 预编译包 |

## 注意事项

- Python项目在HarmonyOS上需要特殊处理：
  1. 所有.so文件必须ELF签名
  2. auditwheel bundling的库(.libs)RPATH在HarmonyOS不被解析，需要ctypes preload补丁
  3. pip3 --prefix安装后Python不会自动搜索usr/local site-packages
---

**编译结束**: 2026-08-06 03:31
**最终状态**: built
