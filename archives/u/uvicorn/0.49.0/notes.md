# uvicorn 0.49.0 适配笔记

## 编译环境
- 构建系统: Python (pyproject.toml + hatchling)
- 编译日期: 2026-06-08
- 编译器: N/A (Python 包)
- 状态: built

## 编译步骤

本次编译采用 Python wheel 构建方式：

1. **源码下载**
   - 从 PyPI 下载源码包：uvicorn-0.49.0.tar.gz
   - 使用 curl -k 绕过 SSL 证书验证问题

2. **解压源码**
   ```bash
   tar -xzf uvicorn-0.49.0.tar.gz
   cd uvicorn-0.49.0
   ```

3. **构建 wheel 包**
   ```bash
   python3 -m pip wheel . --wheel-dir ~/tmp/wheels --no-deps
   ```

   成功生成：uvicorn-0.49.0-py3-none-any.whl (70K)

4. **安装测试**
   ```bash
   mkdir -p ~/tmp/test-install-uvicorn
   python3 -m pip install ~/tmp/wheels/uvicorn-0.49.0-py3-none-any.whl \
       --target ~/tmp/test-install-uvicorn --no-deps
   ```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | ohc-run.py init-build SSL 证书验证失败 | 鸿蒙环境缺少 SSL 证书配置 | 使用 curl -k 手动下载源码包 |
| 2 | pip3 命令不存在 | 需要使用 python3 -m pip | 使用 `python3 -m pip` 替代 `pip3` |

## 源码修改

无补丁。Python 包使用 pyproject.toml 配置，无需源码修改即可在鸿蒙上构建。

## 依赖版本

### 核心依赖（运行时必需）
- click >=7.0
- h11 >=0.8
- typing_extensions >=4.0 (仅 Python <3.11)

### 可选依赖（standard extras）
- httptools >=0.8.0
- uvloop >=0.15.1 (Linux only)
- watchfiles >=0.20
- websockets >=10.4
- PyYAML >=5.1
- python-dotenv >=0.13

## 验证结果

```bash
PYTHONPATH=~/tmp/test-install-uvicorn python3 ~/tmp/test-install-uvicorn/bin/uvicorn --version
```

输出：
```
Running uvicorn 0.49.0 with CPython 3.12.8 on HarmonyOS
```

✅ 验证成功

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| uvicorn-0.49.0-py3-none-any.whl | 70K | Python wheel 包 |
| test-install-uvicorn/bin/uvicorn | 250B | 启动脚本 |

## 注意事项

1. **启动脚本路径问题**：生成的 bin/uvicorn 包含硬编码的 Python 路径：
   ```
   #!/data/service/hnp/python.org/python_3.12/bin/python3.12
   ```

   用户安装时需要根据实际 Python 路径进行调整，或直接使用：
   ```bash
   python3 -m uvicorn
   ```

2. **依赖安装**：wheel 包构建时使用了 `--no-deps`，用户需要手动安装核心依赖：
   ```bash
   pip install click h11
   ```

3. **推荐安装方式**：建议用户直接从 PyPI 安装：
   ```bash
   pip install uvicorn
   ```

   或安装完整版本（包含性能优化依赖）：
   ```bash
   pip install uvicorn[standard]
   ```

4. **Python 包的特殊性**：
   - Python 包通常不需要编译适配，可直接在鸿蒙上使用
   - 本归档主要用于记录和提供 wheel 包备份
   - 不需要像 C/C++ 程序那样的补丁和复杂配置
---

**编译结束**: 2026-06-08 12:11
**最终状态**: built
