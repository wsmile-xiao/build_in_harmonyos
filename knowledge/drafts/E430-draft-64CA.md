# E430 — Conan 2.29 AutotoolsToolchain 不向 CPPFLAGS/LDFLAGS 下发依赖的 -I/-L

## 错误特征
```
checking for main in -lX11... no
configure: error: X11 library is required
```
伴随（SIZEOF 探测静默失败）：
```
config.h: #define SIZEOF_UNSIGNED_INT 0
config.log: ./conftest: Error loading shared library libX11.so.6  (exit 127)
```

## 触发条件
- 构建系统: autotools（`AutotoolsToolchain`）
- 阶段: configure
- 工具链: Conan 2.29.1；上游 configure.ac 直接 `AC_CHECK_LIB`/`AC_CHECK_HEADER`
  探测依赖（而非 pkg-config）

## 根因分析
`conan.tools.gnu.AutotoolsToolchain`（Conan 2.29）生成的
`conanautotoolstoolchain.sh` 中 `LDFLAGS` 为空、`CPPFLAGS` 仅含 defines，
不含依赖的 `-I`/`-L`（那是 `AutotoolsDeps` 的职责，但两者不自动组合）。
`AC_CHECK_LIB([X11], main)` 链接探测必然失败。若上游还用 `AC_CHECK_SIZEOF`
（编译**并运行** conftest），依赖共享库不在 `LD_LIBRARY_PATH` 时 conftest
退出 127，`SIZEOF_*` **静默**变 0——比硬报错更危险。

## 解决方案

### 推荐方案（explicit-flags-in-generate）
在 conanfile.py 的 `generate()` 显式拼装：
```python
toolchain = AutotoolsToolchain(self)
environment = toolchain.environment()
cpp, ld, run = [], [], []
for dep in self.dependencies.host.values():
    cpp += ["-I" + os.path.join(dep.package_folder, d) for d in dep.cpp_info.includedirs]
    ld  += ["-L" + os.path.join(dep.package_folder, d) for d in dep.cpp_info.libdirs]
    run += [os.path.join(dep.package_folder, d) for d in dep.cpp_info.libdirs]
environment.define("CPPFLAGS", " ".join(cpp))
environment.define("LDFLAGS", " ".join(ld))
for p in run:
    environment.append_path("LD_LIBRARY_PATH", p)   # conftest 需要运行
toolchain.generate(env=environment)
```
配合 `PkgConfigDeps` 时还要把其生成目录加进 `PKG_CONFIG_PATH`
（否则 configure 报 `Package 'xcb', required by 'x11', not found`）。

### 禁止做法
- ❌ 只加 `LD_LIBRARY_PATH` 不加 `CPPFLAGS/LDFLAGS`（运行期解决不了链接期探测）
- ❌ 手改 `conanbuild.sh`（generate 产物会被重新生成覆盖）

## 验证
```bash
conan create archives/w/wmnd/0.4.18 -pr:h=ci/conan/profiles/ohos-aarch64 \
  -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing --user=ohpcd --channel=stable
# 实测：checking for main in -lX11... yes；SIZEOF_UNSIGNED_INT=4 / SIZEOF_UNSIGNED_LONG=8；rc=0
```

## 关联条目
- 相关: E429（conftest 运行期还受 SELinux 域限制）
