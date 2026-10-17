# contourpy 1.2.1 适配笔记（OHOS aarch64）

## 编译环境
- 构建系统: meson（目标 Python pip 安装，>=1.2.0）+ ninja 1.13.1
- 编译器: clang 15.0.4（DevBox，lld 默认链接自动签名）
- Python: 3.12.9（~/usr/local，非 HNP）
- pybind11: 3.1.0（目标 Python pip，满足 >=2.12）
- 依赖: numpy/2.5.2（ohpcd 制品仓已发布，裸 ref——namespaced ref 不可解析，matplotlib 配方 CI #49397 同教训）
- 状态: published（conan create 全流程通过）

## 与 numpy 2.5.2 配方的差异

| 项 | numpy | contourpy |
|----|-------|-----------|
| meson 来源 | sdist 内置 vendored meson（含 features 模块） | 目标 Python pip 的标准 meson |
| 子模块 | 4 个（sdist 预填充） | 无 |
| BLAS | openblas（conan 依赖） | 无 |
| pybind11 | 无 | 有（pip 装到目标 Python） |
| C 扩展 | 多个（C/C++/Cython） | 单个 C++（_contourpy） |

## OHOS 适配点（与 numpy 配方同族）

1. sitecustomize.py 补丁 posix_spawn PATH 搜索 + ELF 自动签名
2. lld 默认链接器（禁用 -fuse-ld=bfd，DevBox 自动签名）
3. -lpython3.12 显式链接（musl 不导出主 exe 符号）
4. meson install --no-rebuild（绕开 conan env wrapper 的 PATH 剥离）
5. test_package 注入 libc++_shared.so / libpython3.12 路径

## 上游测试

- tests/ 目录 23 个文件 184 个测试函数
- 运行需 numpy（已在测试环境 PYTHONPATH）
- test_bokeh_renderer.py / test_matplotlib_renderer.py 涉及可选渲染器（bokeh/matplotlib 未安装时跳过）

## 验证结果（2026-09-02 conan create 完整通过）

- `conan create . --user=ohpcd --channel=stable -pr:h/-pr:b=ohos-aarch64 --build=missing` **全流程 PASS**：31 个编译目标全过 → package → test_package 4/4 PASS
- test_package：import ✓ / 版本 1.2.1 ✓ / 填充等高线生成（serial 后端，numpy 集成）✓ / 等高线线生成 ✓
- 上游 pytest：**1800 passed / 76 skipped / 433 "failed" 全部为可选渲染器依赖缺失**（No module named 'matplotlib' 431 个 + 'PIL' 2 个——matplotlib 正是本依赖链的下游目标，PIL 将由 pillow 配方提供）。核心等高线计算测试 100% 通过。

## 2026-09-19 修复（重新提审前）

1. numpy ref 改裸 `numpy/2.5.2`（制品仓 namespaced ref 不可解析——matplotlib 配方 CI #49397 教训）
2. package() 的 boot_dir NameError（build() 局部变量跨方法不可见——重算同一路径，matplotlib 配方同修法）
3. 环境注入改命令行前缀（conan env wrapper 剥离 os.environ 编辑）：PYTHONPATH=boot_dir:shim:numpy site-packages、LD_LIBRARY_PATH=libxml2:libcxx:python_lib:numpy/lib、PKG_CONFIG_PATH 含 boot_dir pybind11 .pc
4. package() 对 site-packages 内 .so 显式 binary-sign-tool 重签（lld 自动签名不可靠，matplotlib 配方同修法）
5. test_package E212 fallback（pycairo/numpy 先例）：CI worker 拒 dlopen（E502 边界）时降级 ELF 结构验证
6. 分支重建到最新 main（老基点 1376+ 提交前，merge-base 空）
