# glances 4.5.4 适配笔记

## 编译环境
- 构建系统: custom (setuptools/pyproject.toml)
- 编译日期: 2026-08-06
- 编译器: N/A (pure Python, no C/C++ compilation needed)
- 状态: built

## 编译步骤

1. 下载 glances-4.5.4.tar.gz 源码包 (PyPI)
2. `python3 -m pip install . --no-deps --target=$TEST_PREFIX` 安装 glances 本体
3. `python3 -m pip install psutil defusedxml packaging jinja2 pyinstrument shtab --target=$TEST_PREFIX/glances-deps` 安装运行时依赖
4. 验证 glances 模块和二进制入口存在

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | psutil C 扩展无法加载 | OHOS ELF 签名限制，未签名的 .so 不可加载 | 平台限制（E179），本地测试改为从源码读取 __version__ 而非 import |
| 2 | pip 下载源不可用 | 默认 PyPI 源无法访问 | 配置社区 pip 源 pypi.cnb.cool |
| 3 | init-build 嵌套源码检测错误 | docs/ 目录被误识别为嵌套源码 | 手动修正 .orig 和 .work 目录 |
| 4 | 打包后依赖全部损坏（psutil/jinja2 等无法 import，pyinstrument 的 types.py 遮蔽 stdlib types） | package() 中 copy(..., keep_path=False) 将 glances-deps/ 拍平，包目录结构被毁 | keep_path=True 保留 pip --target 的包布局；test_package 增加依赖结构硬校验（2026-09-17 修复） |
| 5 | CI L0p 门禁失败：settings 缺 compiler/build_type | 2026-08 新增门禁要求 settings 四项齐全 | settings = "os", "compiler", "build_type", "arch"（2026-09-04 修复） |
| 6 | CI JC1 门禁将 .submit-state.json 判为运行时状态文件 | 前次提交误将运行时状态文件入库 | git rm --cached 移除（2026-09-17 修复） |
| 7 | W4 审计 P1：MANIFEST upstream_test_in_build: true 虚假声明 | build() 未集成上游 pytest（E179 限制下无法运行） | 改为 false 并注明原因（2026-09-17） |
| 8 | W4 审计 P2：test_glances.py 回退相对路径永不可解析；fallback 触发条件过宽可能掩盖真实故障 | dirname(__file__)/.. 在仓库与 Conan 上下文均无对应物；binary 任意失败都走回退 | find_spec 定位包真实位置；fallback 前强制验证 glances 自身输出 "psutil library not found"（E179 特征），否则硬失败（2026-09-17） |

## 源码修改

无补丁。glances 是纯 Python 包，pip install 直接构建成功。

## 依赖版本

| 依赖 | 版本 | 说明 |
|------|------|------|
| psutil | 7.2.2 | C 扩展，社区源提供 OHOS 适配 wheel |
| defusedxml | 0.7.1 | 纯 Python |
| packaging | 26.3 | 纯 Python |
| jinja2 | 3.1.6 | 纯 Python |
| markupsafe | 3.0.3 | C 加速可选，纯 Python 回退可用（jinja2 依赖） |
| pyinstrument | 5.1.2 | 含 C 扩展（OHOS wheel），无 ELF 签名时不可导入 |
| shtab | 1.12.1 | 纯 Python |

## 验证结果

```bash
# 构建验证
python3 -m pip install . --no-deps --target=$TEST_PREFIX
# → Successfully installed Glances-4.5.4

# 包结构验证
ls $TEST_PREFIX/bin/glances     # → entry point script exists
ls $TEST_PREFIX/glances/__init__.py  # → Python package exists
```

## 注意事项

- psutil C 扩展 (.so) 在 OHOS 上需要 ELF 签名才能 dlopen（E179 平台限制，实测本地编译 .so 同样被拒），test_package 在 .so 不可加载时回退到：依赖结构校验 + 纯 Python 依赖导入 + 源码版本校验
- glances/__init__.py 在导入时检查 psutil，缺失则输出 "psutil library not found" 并 sys.exit(1)——该消息本身证明 glances 包代码在正确执行
- 运行时依赖通过 pip install --target 打包到 glances-deps/ 目录（keep_path=True，2026-09-17 修复拍平 bug）
- pip 解析的实际依赖版本以构建时为准（当前：psutil 7.2.2 / jinja2 3.1.6 / markupsafe 3.0.3 / shtab 1.12.1 / defusedxml 0.7.1 / packaging 26.3 / pyinstrument 5.1.2）
---
**编译结束**: 2026-08-06 14:06（2026-09-17 二次修复：依赖打包拍平 bug + JC1 状态文件 + L0p settings）
**最终状态**: built
