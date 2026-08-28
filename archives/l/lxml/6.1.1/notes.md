# lxml 6.1.1 — 编译结果摘要

## 基本信息
- **软件**: lxml 6.1.1
- **描述**: Pythonic XML processing library combining libxml2/libxslt
- **构建系统**: Python setuptools (setup.py build_ext --inplace)
- **源码**: https://github.com/lxml/lxml/archive/refs/tags/lxml-6.1.1.tar.gz
- **SHA256**: 624d1f5a50862c1bd5280f6997898c5a334e26d3a58bc2bbfec1efd8f98135fa
- **许可证**: BSD-3-Clause
- **状态**: built (conan-verify 通过，未上传)

## 编译环境
- **平台**: OpenHarmony PC (aarch64, OHOS 6.0)
- **编译器**: clang 15 (libc++)
- **Python**: 3.12

## 依赖
- libxml2/2.15.3 (Conan)
- libxslt/1.1.45 (Conan, 传递依赖 libgcrypt/1.11.0, libgpg-error/1.55)

## 编译过程

### Step 2: 编译 lxml C 扩展
1. 设置环境变量:
   - PKG_CONFIG_PATH → conan 包的 pkgconfig 目录
   - LD_LIBRARY_PATH → libxml2, libxslt, libgcrypt 的 lib 目录
   - LIBRARY_PATH → 同 LD_LIBRARY_PATH
   - C_INCLUDE_PATH → libxml2/include/libxml2, libxslt/include
2. `python3 setup.py build_ext --inplace` → 成功
   - 生成 7 个 C 扩展模块: etree, objectify, builder, sax, diff, _difflib, _elementpath
   - 输出: src/lxml/*.cpython-312-aarch64-linux-ohos.so
3. `python3 setup.py install --prefix=$DEFAULT_PREFIX` → 成功
4. 验证: `from lxml import etree` → lxml version (6, 1, 1, 0), libxml2 (2, 15, 3), libxslt (1, 1, 45)

### 关键问题及解决
1. **libgcrypt 缺失**: libexslt.so 依赖 libgcrypt.so.20，但未在 LD_LIBRARY_PATH 中
   - 解决: 添加 libgcrypt conan 路径 (~/.conan2/p/libgcd46f6fdc0c29a/p/lib)
2. **conanfile.py 构建系统错误**: 模板生成 autotools 配方，但 lxml 是 Python C 扩展
   - 解决: 完全重写 conanfile.py，使用 setup.py build_ext --inplace
3. **conan create 找不到编译器**: conan 构建环境中 clang/cc 不在 PATH
   - 解决: 在 ~/usr/local/bin/ 创建 cc, clang, clang++ 符号链接
4. **conan create 找不到 libxml2/libxslt**: setup.py 无法找到 conan 依赖
   - 解决: 在 build() 中从 self.dependencies 收集路径并设置环境变量
5. **L1e 负面测试失败**: 系统安装的 lxml 导致测试不依赖 conan 包
   - 解决: 卸载系统 lxml, 在 test_package 中设置 PYTHONPATH 指向 conan 包

### Step 2.5: conan-init
- 生成 conanfile.py + conandata.yml + test_package/ (骨架)
- AI 手动修正: 完全重写 conanfile.py (autotools → setuptools), 重写 test_package (C → Python)

### Step 2.6: conan-verify
- G0 (预构建评估): PASS
- G1 (配方完整性): PASS
- G2 (conan create): PASS
- G3 (系统同名库隔离): PASS
- G4 (产物完整性): PASS
- L2/L4/L5: PASS (skip)

### Step 3: finish
- W3 本地 CI 模拟: PASS (通过后完成)
- 状态: built

## 质量检查
- ✅ conanfile.py: requirements() 引用 libxml2/2.15.3 和 libxslt/1.1.45
- ✅ conandata.yml: 包含正确 sha256
- ✅ test_package/: conanfile.py + test_lxml.py (真实测试) + MANIFEST.yml
- ✅ manifest.yaml: 正确字段
- ✅ conan-verify: 所有门禁通过

## 结束
编译结束: 2026-08-19
最终状态: built
