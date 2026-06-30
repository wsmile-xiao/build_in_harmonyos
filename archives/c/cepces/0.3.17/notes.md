# cepces 0.3.17 编译记录

## 编译状态：built (成功)

## 版本信息

- 实际版本：0.3.17
- 原请求版本：0.3.9-r1（不存在，使用最新稳定版本）

## 编译环境

- Python: 3.12.8
- 构建系统: setuptools (纯Python包)
- 依赖已满足：
  - krb5 1.22.2 (已安装到 /storage/Users/currentUser/usr/local/)
  - python-gssapi 1.8.3 (wheel已安装)
  - requests-gssapi 1.4.0 (pip安装成功)
  - requests 2.32.3
  - cryptography 44.0.0

## 编译方法

cepces是纯Python包，使用setuptools构建。由于pip build隔离环境问题（需要maturin），采用以下方法：

1. 使用setuptools egg_info生成元数据
2. 使用install命令直接安装：
   ```bash
   python3 -c "from setuptools import setup; setup()" install \
     --prefix=$DEFAULT_PREFIX \
     --root=$TEST_PREFIX \
     --single-version-externally-managed
   ```

## 关键依赖处理

### gssapi模块ELF签名问题

python-gssapi的.so文件需要ELF签名才能在OpenHarmony上执行。使用SKILL的sign-elf工具批量签名：
```bash
python3 $SKILL_ROOT/scripts/ohc-run.py sign-elf <file>
```

### LD_LIBRARY_PATH设置

Python的ctypes模块依赖libffi.so.8，需要将/data/service/hnp/python.org/python_3.12/lib放在LD_LIBRARY_PATH最前面：
```bash
export LD_LIBRARY_PATH=/data/service/hnp/python.org/python_3.12/lib:/storage/Users/currentUser/usr/local/lib:$LD_LIBRARY_PATH
```

## 源码信息

- 上游URL：https://github.com/openSUSE/cepces
- 下载URL：https://github.com/openSUSE/cepces/archive/refs/tags/v0.3.17.tar.gz
- 源码类型：纯Python包（pyproject.toml）
- 构建系统：setuptools

## 安装产物

- 预编译包：cepces-0.3.17-ohos-aarch64.tar.gz (512KB)
- 安装位置：lib/python3.12/site-packages/cepces/
- 可执行脚本：libexec/certmonger/cepces-submit

## 质量门禁结果

- G0 (干净构建): PASS (纯Python包无编译)
- G1 (二进制完整性): PASS (无二进制文件)
- G2 (功能可用性): PASS (可导入)
- G3 (可移植性): PASS (无RPATH需求)
- G4 (档案完整性): PASS
---

**编译结束**: 2026-05-21 22:52
**最终状态**: built
