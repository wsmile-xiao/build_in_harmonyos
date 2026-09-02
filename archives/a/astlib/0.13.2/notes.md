# astlib 0.13.2 适配笔记

## 编译环境
- 构建系统: Python setuptools (pip install --target) 含 SWIG WCSTools 扩展
- 编译器: clang 15 / HarmonyOS SDK
- 状态: built
- 上游: https://github.com/mattyowl/astLib (PyPI astLib 0.13.2)

## 源码获取
- URL: https://files.pythonhosted.org/packages/df/ee/682e8212fe5008eebc475218e3cd633b73637b354836d200a0c50d9b47e4/astlib-0.13.2.tar.gz
- SHA256: f2f4f978cbf6518136be582f709ce18296029006a30330d17befe95ca659584d

## 编译步骤
1. `get()` 解压 PyPI 源码包
2. `build()` 阶段先运行上游 `pytest tests/test_all.py -v` 报告通过率（单用例 test_dl）
3. `python3 -m pip install --no-deps --no-build-isolation --target <staging> .` 触发 setup.py 构建
   - setup.py 的 `build_PyWCSTools_ext` 编译 `PyWCSTools/wcssubs-3.9.7/*.c` 并链接生成 `PyWCSTools/_wcs` 扩展
   - 使用 sysconfig 的 CC/CFLAGS，自动注入 -fPIC
4. `package()` 将 staging 下的 `astLib/`、`PyWCSTools/` 及 egg-info 完整复制到 `lib/python3.x/site-packages`
5. `package_info()` 暴露 PYTHONPATH 供消费者

## 依赖
- 运行时 Python 依赖 (pip): numpy, scipy, matplotlib 建议安装但不强制；核心 `astCalc.dl` 仅需 scipy，缺失时 conan 仍可安装但测试会警告
- 无 Conan C++ 依赖

## 上游测试
- 位置: `tests/test_all.py`
- 内容: `assert(2834.89 < astCalc.dl(0.5) < 2834.90)` 单用例
- 执行: `pytest tests/test_all.py -v` 在 `build()` 中执行，已在 HarmonyOS aarch64 实测通过

## 补全测试
- `test_package/test_astlib.py` 四断言:
  1. astCalc.dl(0.5) 数值区间校验（上游用例复现）
  2. astStats/astCoords 调用
  3. PyWCSTools.wcs 扩展导入
  4. astImages 导入

## 遇到问题
- 原始 `archives/a/astlib` 已有 0.9.0 (C++ Eurocontrol 版本，poco 依赖)，与本 Python 版本同名但不同上游。0.13.2 为 Python 分支，README 保留 C++ 描述，0.13.2 独立说明；软件级 manifest 未强制合并。
- WCSTools wcssubs 在 musl/HarmonyOS 上无特殊补丁，-Wstrict-prototypes 等 flag 已在 setup.py 中自动移除，HarmonyOS 上可直接编译。
- scipy 未在 ohpcd 制品仓提供，消费者需 `pip install scipy` 后完整体验；核心计算测试已覆盖。

## 验证
- HarmonyOS aarch64 预检: `conan create` 成功，`pip --target` 产物含 astLib/PyWCSTools，`pytest` 上游 1/1 通过，`test_astlib.py` 4 断言通过
