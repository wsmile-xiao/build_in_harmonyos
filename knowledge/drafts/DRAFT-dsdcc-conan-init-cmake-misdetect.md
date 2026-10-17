# conan-init 对 CMake 项目误判构建系统为 autotools 的处理

- **Draft**: DRAFT-dsdcc-conan-init-cmake-misdetect
- **来源**: dsdcc 1.9.6 适配 (conan-init → G2 conan create)
- **日期**: 2026-09-25

## 问题

`ohc-run.py init-build`/`conan-init` 依据 URL 后缀与注册表推断构建系统。上游 GitHub
归档 URL(`.../archive/refs/tags/v1.9.6.tar.gz`)无构建系统特征时,被推断为
`autotools`,生成的 `conanfile.py` 使用 `AutotoolsToolchain`,而项目实际是 CMake:

```bash
# init-build 输出
ℹ️ 构建系统: autotools
# 生成物 conanfile.py 含
from conan.tools.gnu import Autotools, AutotoolsToolchain
```

对 CMake 项目,G2 `conan create` 必然失败(configure 不存在/行为不符)。

## 根因

构建系统推断只依据 URL 与注册表,未实际检查源码根目录的构建文件
(`CMakeLists.txt` vs `configure` vs `Makefile`)。

## 方案

1. **生成后核验**:查看源码根目录是否存在 `CMakeLists.txt`(CMake 项目的权威标志)。
2. **误判时改模板**:用仓库 `templates/conanfile-cmake.py.tmpl` 手动重写
   `conanfile.py`(CMakeToolchain + cmake_layout),删除 autotools 导入。
3. 同步修正 `conandata.yml` sha256 与 manifest build_system 字段。
4. 重跑 `conan-verify` 直至 G0-G4 通过。

关键改写点:

```python
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
# layout(): cmake_layout(self)
# generate(): CMakeToolchain; tc.variables["BUILD_SHARED_LIBS"] ...
# build(): CMake.configure(); CMake.build()
# package(): CMake.install()
```

## 验证

dsdcc 1.9.6 重写为 CMake 模板后:G1/G0/G2 (conan create)/G3 (系统同名库隔离)/G4
(产物完整性)全部 PASS。

## 适用边界

- 适用:任何 `init-build` 构建系统推断与源码实际不符的配方生成场景;核验标志 =
  源码根目录存在 `CMakeLists.txt`。
- 不适用:项目确有 `configure` 脚本(autotools 模板正确)或纯 Makefile 项目。
- 反例:CMake 项目但含 autotools 兼容层(configure 包装)时,仍需以
  `CMakeLists.txt` 为准。

## 相关条目

- similar_to: E007 (autotools configure 平台识别,面向 configure 阶段而非配方生成)