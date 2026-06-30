# mackup 0.10.3 适配笔记

## 编译环境
- 构建系统: custom (Python hatchling)
- 编译日期: 2026-06-08
- 编译器: clang/clang++
- 状态: built

## 编译步骤

mackup 是纯 Python 应用，使用 pyproject.toml 和 hatchling 构建后端。

1. **下载源码**: 从 PyPI 获取 mackup-0.10.3.tar.gz
2. **初始化**: 使用 ohc-run.py init-build 创建工作目录和归档
3. **安装**: 使用 pip 安装到 staging 目录
   ```bash
   python3 -m pip install --target=/storage/Users/currentUser/tmp/test-install-mackup-0.10.3/storage/Users/currentUser/usr/local .
   ```
4. **验证**: 安装到系统并验证功能
   ```bash
   export LD_LIBRARY_PATH=/data/service/hnp/python.org/python_3.12/lib:$LD_LIBRARY_PATH
   mackup --version
   ```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | SSL 证书验证失败 | Savannah 站点证书问题 | 使用 PyPI URL 替代 |
| 2 | pip 命令不存在 | 系统只有 python3 -m pip | 使用 python3 -m pip 考虑到 Python 应用特性 |
| 3 | sqlite3 库加载失败 | LD_LIBRARY_PATH 缺少 Python 库路径 | 设置 LD_LIBRARY_PATH 包含 Python 库目录 |
| 4 | 质量门禁 G4 FAIL | 验证脚本不识别 Python 应用 | Python 应用无 ELF 二进制，属于特殊情况 |

## 源码修改

{如有补丁，列出文件名和修改内容；无则删除此节}

## 依赖版本

{列出本次编译依赖的具体软件版本}

## 验证结果

```bash
{验证命令和结果}
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| mackup-0.10.3-ohos-aarch64.tar.gz | 879K | 预编译制品包（Python 应用） |
| mackup-0.10.3-ohos-aarch64.tar.gz.sha256 | 100B | SHA256 校验和 |
| mackup-0.10.3-ohos-aarch64.tar.gz.md5 | 68B | MD5 校验和 |

**制品包内容**：
- bin/mackup: 可执行脚本
- mackup/: 主模块（8 个 Python 文件）
- docopt/: 依赖模块
- mackup-0.10.3.dist-info/: 包元数据
- docopt_ng-0.9.0.dist-info/: 依赖元数据

## 注意事项

{需要特别注意的点；无则删除此节}
---

**编译结束**: 2026-06-08 22:19
**最终状态**: built
