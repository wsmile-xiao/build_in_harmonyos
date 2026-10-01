# Draft: `DRAFT-XMILL-08-CONANDEPS-MISSING-HOST-LIB-SHADOWING`
> Stem: `xmill-0.8-conandeps-missing-host-lib-shadowing` — pairs with the same-stem `.kv`

# 漏写 CMakeDeps，`find_package` 命中宿主同名库：产物被塞进运行期动态依赖，编译器不报错

## 基本信息

- **ID**: DRAFT-XMILL-08-CONANDEPS-MISSING-HOST-LIB-SHADOWING
- **严重度**: 1（编译、conan create、conan-verify 全绿，只有运行期依赖检查能发现）
- **类别**: conan | build-system | cmake | dependency | linking | packaging
- **触发工具**: conan | cmake | clang | ld
- **阶段**: configuration → linking → testing
- **来源**: xmill 0.8 适配（2026-10-01）

## 错误特征

先是一个容易误判的前置症状（`generate()` 完全缺失时）：

```
ERROR: xmill/0.8: Error in build() method
  ConanException: CMakePresets.json was not found in .../b/build/Release/generators
  folder. Check that you are using CMakeToolchain as generator to ensure its correct initialization.
```

补上 `CMakeToolchain` 之后一切"正常"：`conan create` rc=0、`conan-verify` G1–G4 全 PASS。
但 `test_package` 的**运行期依赖断言**立刻失败：

```
[FAIL] [OHOS] T3 no runtime libz.so dependency (static zlib)
$ readelf -d <pkg>/bin/xmill | grep NEEDED
  (NEEDED)  Shared library: [libz.so.1]      ← 不该出现
```

## 根因（一类）

Conan 2 里 `CMakeToolchain` 与 `CMakeDeps` 是**两个独立生成器**：前者产出 toolchain / presets，
后者才产出 `<Pkg>Config.cmake`、`<Pkg>Targets.cmake`。配方只写：

```python
def generate(self):
    tc = CMakeToolchain(self)
    tc.generate()
```

时，构建目录里没有 `ZLIBConfig.cmake`，`CMakeLists.txt` 的 `find_package(ZLIB REQUIRED)`
便去别处找同名包——命中了宿主上另一个 zlib：

```
$ grep ZLIB_DIR <build>/CMakeCache.txt
ZLIB_DIR:PATH=/storage/Users/currentUser/.harmonybrew/lib/cmake/ZLIB
```

（CMake 会从 `PATH` 派生前缀，并搜索 `<prefix>/lib/cmake`；本机 `PATH` 含
`/storage/Users/currentUser/.harmonybrew/bin`。）于是链接了**动态** `libz.so.1`：
静态隔离（R26）失效、包不再自足、产物带上非预期运行期依赖 —— 而编译器一声不吭。

## 修法

```python
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout

def generate(self):
    deps = CMakeDeps(self)      # 必须：生成 <Pkg>Config.cmake / Targets
    deps.generate()
    tc = CMakeToolchain(self)
    tc.generate()
```

加固建议：`CMakeLists.txt` 写 `find_package(ZLIB REQUIRED CONFIG)`，把"配置必须由 Conan 提供"
变成硬约束——模块模式下的 CMake 内置 `FindZLIB.cmake` 会绕过 CMakeDeps 直接找系统库。

## 验证

```
$ conan create archives/x/xmill/0.8 -pr:h=… -pr:b=…       → rc=0
$ readelf -d <pkg>/bin/xmill | grep NEEDED
  (NEEDED)  Shared library: [libc++_shared.so]
  (NEEDED)  Shared library: [libc.so]                     # 再无 libz.so.1
test_package: pass=7 fail=0 skip=0（含 2 项鸿蒙特有断言）
```

## 适用面与检出手段

- 任何用 CMake + Conan 2 的配方，特别是依赖"看起来系统里已有"的公共库
  （zlib / openssl / libpng / sqlite3 / bzip2 / curl）；
- 开发机 `PATH` 上存在其它包管理器前缀（homebrew / harmonybrew / macports）时更易触发，
  且装机环境越"干净"越不容易暴露——不能以"我这台机器没问题"结案；
- 检出手段固定两条：`grep <PKG>_DIR <build>/CMakeCache.txt` 看是否指向本仓之外；
  `readelf -d <bin> | grep NEEDED` 看产物是否多了非预期 `.so`。

## 关联

- `notes.md` §3.5（该缺陷是在第一次 conan create 的 test_package 里被 T3 拦下的）
- 同类：`tng-1.8.2-static-zlib-priv-link-self-contained`（zlib 静态自足性同一主题）
