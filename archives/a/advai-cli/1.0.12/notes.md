# advai-cli 1.0.12 适配 notes

## 包信息

- 类型：Python CLI 工具（application，pip 安装）
- 上游：https://github.com/Advai-X/advai-cli （MIT）
- 简介：统一 CLI，管理本地技能、外部 CLI、浏览器自动化与终端 AI 对话
- 运行时依赖：aiohttp>=3.9（含 C 扩展）、click>=8.1

## 适配要点

1. **源码获取**：PyPI sdist tarball（files.pythonhosted.org），镜像回退到 GitHub tag tarball
2. **构建方式**：系统 Python3 + pip 安装（同 imgp 先例）
   - aiohttp/click 从社区 pip 源（pypi.cnb.cool）安装到 `~/usr/local`（可执行文件系统，规避 ~/.local noexec）
   - `--force-reinstall --prefix=~/usr/local`，避免缓存到 noexec 的 user site-packages
3. **aiohttp C 扩展 .so 权限**：HMDFS 上 pip 装的 .so 保持 770（other 无读/执行），chmod 不生效（E046）
   → 用 copy2→`install -m 755` 写回强制赋权（同 imgp 方案）
4. **setuptools**：`pip install setuptools==75.8.0`（社区源有，避免裸下载 files.pythonhosted.org）
5. **advai-cli 本体**：`pip install <src> --no-build-isolation --no-deps`
6. **打包**：bin/advai 可执行文件 + advai Python 包 + dist-info

## 测试用例

- test_import：`import advai` 模块可导入，版本正确
- test_cli：`advai --help` 输出完整帮助

## 已知限制

- 浏览器自动化等高级功能依赖外部浏览器，测试仅验证 CLI 与模块导入
