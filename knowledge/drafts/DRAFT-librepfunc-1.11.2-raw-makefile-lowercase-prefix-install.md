# DRAFT-librepfunc-1.11.2-raw-makefile-lowercase-prefix-install：raw makefile 小写 `prefix=` 安装变量导致 CMakeDeps "Library not found in package"

> Contributor: pc2-34 | Status: Draft | Updated: 2026-09-27
> Source: librepfunc 1.11.2 适配（task librepfunc-1.11.2-r01-bootstrap-and-adapt-pc2-34-20260927T091120Z）
> 对应：`knowledge/drafts/DRAFT-librepfunc-1.11.2-raw-makefile-lowercase-prefix-install.kv`

## 现象

`conan create` 主包构建成功，但 test_package 阶段 `find_package(librepfunc)` 失败：

```text
CMake Error at .../cmakedeps_macros.cmake:81 (message):
  Library 'repfunc' not found in package.  If 'repfunc' is a system library,
  declare it with 'cpp_info.system_libs' property
```

同时包内实际产物落点在 `usr/lib` 而非包根 `lib/`：

```text
install -m 644 librepfunc.a .../p/usr/lib
install -m 644 repfunc.h .../p/usr/include
```

## 根因

手写 Makefile 的 install 目标用**小写** `prefix ?= /usr` 变量展开目录：

```makefile
prefix ?= /usr
libdir   = $(prefix)/lib
includedir = $(prefix)/include
```

Make 变量名大小写敏感。Conan 配方若传**大写** `PREFIX=$package_folder`（或 `PREFIX=`）：
- 大写 `PREFIX` 与 Makefile 中的小写 `prefix` 是**两个不同变量**；
- 大写赋值对小写变量零影响 → `prefix` 保留默认 `/usr`；
- 于是 `make install DESTDIR=$package_folder` 把产物装到
  `$package_folder/usr/lib`、`$package_folder/usr/include`。

CMakeDeps 默认在包根 `lib/` 下生成 `-L` 与 target，找不到
`usr/lib/librepfunc.a` → test_package 配置阶段即报
"Library 'repfunc' not found in package"。

## 修复

package() 中用**小写** `prefix=`（空值直接使包根成为安装根）：

```python
def package(self):
    self.run("make install-static CXX=... DESTDIR={} prefix=".format(self.package_folder))
```

- `prefix=`（小写、空）→ `libdir = /lib` → `DESTDIR/lib/librepfunc.a`，包根即
  libdir，CMakeDeps 正常找到；
- 大写 `PREFIX=` 一律无效，必须与小写 Makefile 变量名匹配；
- shared/static 分别走上游 `make install` / `make install-static` 目标；
- 若上游 Makefile 把 pkgconfigdir 硬编码为 `/usr/lib/pkgconfig`，仅 .pc 落在
  `usr/lib/pkgconfig` 属无害辅助元数据，不阻塞。

## 验证

`make install-static ... prefix=` 后：

- 包内 `find $package_folder -name 'librepfunc*'` → `lib/librepfunc.a`（包根）；
- `conan create ... -pr:h=ohos-aarch64` → G1/G2/G3/G4 全 PASS；
- W3 本地 CI（build_and_test.sh）JC/KC/L0–L5 全绿；
- test_package ctest 断言 UpperCase/IntToStr/IntToHex/Trim 4 项通过。

## 适用边界 / 反例

- ✅ 上游 Makefile install 规则基于小写 `prefix ?= /usr` 展开目录
- ✅ raw makefile（无 configure/cmake/meson 生成）库
- ❌ configure 生成的 Makefile（autotools 会接收 `--prefix`，变量名由 configure
  保证一致）→ 不受此坑影响
- ❌ 上游 install 用大写 `PREFIX ?= /usr/local`（罕见）→ 则必须传大写
- ❌ 靠 `cpp_info.libs = ["librepfunc"]`（带 lib 前缀）或伪造 `libdirs=["usr/lib"]`
  掩盖落点错误 → 掩盖根因，CI L0 会反查

## 查重关系

- similar_to: E392（raw makefile Conan 三陷阱：BadZipFile / compiler_executables /
  make cwd）——本条目补充 install 阶段 prefix 变量大小写维度
- similar_to: E316（SONAME 实体缺失）、E277（vendored 依赖）——同属打包落点/
  库查找域，机制不同