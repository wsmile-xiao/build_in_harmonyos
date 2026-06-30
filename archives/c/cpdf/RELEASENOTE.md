# cpdf — HarmonyOS aarch64 预编译包

## 软件简介
cpdf 是一个纯Python CLI工具，基于PyPDF2提供PDF文件操作功能。
- 官网: https://github.com/py-pdf/cpdf
- 许可证: BSD-3-Clause
- 类型: 文档处理工具 (PDF CLI)
- 依赖: python3, PyPDF2, click, pydantic

> ⚠️ 此为 Python cpdf 0.0.7 (PyPDF2 wrapper)，非 CoherentPDF cpdf v2.9 (OCaml专业PDF工具)

## 快速安装

### 方式1: 本地安装
```bash
tar xzf cpdf-0.0.7-ohos-aarch64.tar.gz -C ~/usr/local
cd ~/usr/local && sh install-cpdf-0.0.7.sh
```

### 方式2: 在线安装
```bash
curl -fsSL <url>/install.sh | sh -s -- 0.0.7
```

## 可用版本

| 版本 | 状态 | 构建系统 | 补丁数 | 测试通过 |
|------|------|----------|--------|----------|
| 0.0.7 | built | custom (pip) | 3 | 基本功能 |

## 当前版本 (0.0.7) 详情

### 包内容
```
bin/
  cpdf             # shell wrapper脚本
lib/
  python3.12/
    site-packages/
      cpdf/        # Python模块
        __init__.py
        cli.py
        models.py
```

### 包大小
- 主包 (runtime): 22KB
- debug包 (仅含README): 2KB

### 编译信息
| 项目 | 值 |
|------|-----|
| 构建系统 | pip (custom) |
| 编译器 | N/A (pure Python) |
| 目标架构 | aarch64 |
| 目标系统 | HarmonyOS |
| 质量门禁 | PASS (G1-G3), WARN (G4: 纯Python无二进制) |
| 测试结果 | 基本功能PASS (cat/metadata) |
| 补丁数 | 3 |

### 安装验证
```bash
# Module import验证
python3 -c "import cpdf; print(cpdf.__version__)"  # 输出: 0.0.7

# CLI验证
bin/cpdf cat input.pdf output.pdf   # 合并PDF
bin/cpdf metadata input.pdf          # 查看元数据
```

## 使用示例
```bash
# 合并PDF
bin/cpdf cat input1.pdf input2.pdf merged.pdf

# 查看PDF元数据
bin/cpdf metadata document.pdf

# ⚠️ extract_images功能不可用 (PIL/Pillow沙箱限制)
```

## 环境要求
- HarmonyOS/OpenHarmony aarch64
- Python 3.12+
- 依赖: PyPDF2, click, pydantic (需预装)

## 编译备注
- 纯Python包，使用pip --no-deps + 手动安装依赖
- 需创建shell wrapper脚本作为CLI入口
- PIL/Pillow功能受限(HarmonyOS沙箱)