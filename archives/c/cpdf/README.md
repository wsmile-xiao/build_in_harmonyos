# cpdf — OpenHarmony 编译记录

## 软件概述
- **名称**: cpdf (Pure-Python PDF CLI tool)
- **官网**: https://github.com/py-pdf/cpdf
- **类型**: PDF命令行工具 (文档处理)
- **许可证**: BSD-3-Clause
- **依赖**: python3, PyPDF2, click, pydantic

> ⚠️ 注意：Python cpdf 0.0.7 ≠ CoherentPDF cpdf v2.9（OCaml专业PDF工具，功能强大但需OCaml编译器）

## 可用版本

| 版本 | 状态 | 构建系统 | 补丁数 | 测试结果 | 编译日期 |
|------|------|----------|--------|----------|----------|
| 0.0.7 | ✅ built | custom (pip) | 3 | 基本功能PASS | 2026-05-25 |

---

## 编译指导 (0.0.7)

### 前置要求
| 工具 | 版本要求 | 检查命令 |
|------|---------|---------|
| python3 | >= 3.12 | `python3 --version` |
| pip | 最新 | `pip --version` |

### 安装依赖
```bash
pip install pypdf2 click pydantic
```

### 编译命令
```bash
# 下载源码
curl -L -o cpdf-0.0.7.tar.gz \
  https://files.pythonhosted.org/packages/72/cd/fb8ca61b75f6848744c4dc06a6515b1c8e4be0735e4f39925e68f29f7382/cpdf-0.0.7.tar.gz

# 解压
tar -xzf cpdf-0.0.7.tar.gz
cd cpdf-0.0.7

# 安装 (--no-deps避免pip挂起)
pip install --no-deps cpdf-0.0.7

# 创建staging
mkdir -p staging/bin staging/lib/python3.12/site-packages
cp -r cpdf staging/lib/python3.12/site-packages/
# 创建 bin/cpdf wrapper脚本 (见0003 patch)
```

### 验证安装
```bash
python3 -c "import cpdf; print(cpdf.__version__)"  # 输出: 0.0.7
bin/cpdf cat input.pdf output.pdf                    # 合并PDF
bin/cpdf metadata input.pdf                          # 查看元数据
```

---

## 补丁清单

| # | 补丁文件 | 类型 | 说明 |
|---|---------|------|------|
| 1 | 0001-cpdf.egg-info-PKG-INFO.patch | auto | 更新元数据版本(2.1→2.4)和依赖声明 |
| 2 | 0002-cpdf.egg-info-entry_points.txt.patch | auto | 修复entry_points末尾多余空行 |
| 3 | 0003-add-harmonyos-wrapper-script.patch | manual | 新增bin/cpdf shell wrapper脚本 |

---

## 已知问题与解决

| 问题 | 原因 | 解决方案 |
|------|------|---------|
| pip install cpdf挂起 | pip下载依赖时网络慢 | 使用 `--no-deps` + 手动安装依赖 |
| extract_images不可用 | PIL/Pillow .so权限被拒(HarmonyOS沙箱) | 基本功能(cat/metadata)正常 |
| 无bin/cpdf入口 | 纯Python包pip不生成可执行入口 | 创建wrapper shell脚本 |

---

## 知识沉淀

1. **pip --no-deps**: HarmonyOS环境中pip下载依赖容易超时，使用 `--no-deps` 分步安装
2. **Python wrapper**: 纯Python CLI包需要创建shell wrapper脚本，通过 `python3 -m <module>` 调用
3. **PIL沙箱限制**: HarmonyOS沙箱不允许加载第三方.so，影响依赖PIL的功能

---

## 预编译包下载

| 包名 | 大小 | 类型 |
|------|------|------|
| cpdf-0.0.7-ohos-aarch64.tar.gz | 22KB | 运行时 |
| cpdf-0.0.7-ohos-aarch64-debug.tar.gz | 2KB | 仅含README (纯Python无调试符号) |

---

## 功能验证代码

```bash
# 验证安装
bin/cpdf --help
# 合并PDF
bin/cpdf cat input1.pdf input2.pdf output.pdf
# 查看元数据
bin/cpdf metadata input.pdf
```