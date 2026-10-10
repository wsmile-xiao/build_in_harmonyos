# DRAFT-12592: Conan application 包型剥离 cpp_info 与 meson lib 前缀匹配坑（服务器双形态包）

- **ID**: `DRAFT-12592-ohos-conan-application-pkgtype-strips-cppinfo`
- **触发工具/阶段**: conan | cmake | cmakedeps — test_package / packaging
- **严重度**: 2（🟡 中等）
- **类别**: conan, packaging, test_package, portability, ohos
- **来源**: isc-kea 3.0.3 适配（feat/isc-kea-3.0.3，OHOS PC aarch64，2026-10-08）

## 错误特征

```
# 第一次 test_package 失败（编译期）：
fatal error: 'asiolink/io_address.h' file not found

# 第二次 test_package 失败（cmake configure 期）：
CMake Error at generators/cmakedeps_macros.cmake:81 (message):
  Library 'kea-asiodns' not found in package.  If 'kea-asiodns' is a system
  library, declare it with 'cpp_info.system_libs' property

# 切 library 包型后（conan 解析期，秒级失败）：
ERROR: isc-kea/3.0.3: Package type is 'library', but no 'shared' option declared

# 生成数据侧证据（test_package/build/*/generators/）：
set(isc-kea_INCLUDE_DIRS_RELEASE )      ← 空
set(isc-kea_LIBS_RELEASE )              ← 空
set(isc-kea_LIB_DIRS_RELEASE ".../lib") ← 正常
```

## 场景

`isc-kea`（ISC Kea 3.0.3）交付**双形态**产物：五个服务器守护进程
（`bin/kea-dhcp4` 等）+ 23 个可链接的 `libkea-*.so` + `include/kea` 公共头。
test_package 要求消费者侧 `find_package(isc-kea)` + 链接 + API 断言——
这正是服务器件区别于纯工具件的验证面。

## 根因（三层递进，均为实测踩坑）

1. **application 包型剥离消费者侧 cpp_info**：Conan 对
   `package_type="application"` 的包，CMakeDeps 生成数据里 include dirs 与
   libs 置空（BIN_DIRS/LIB_DIRS 保留）。`find_package()` 成功但编译期
   `'asiolink/io_address.h' file not found`。
2. **meson 产物 lib 前缀**：`_is_packaged_lib` 以裸名（`kea-dhcp.so`）匹配
   meson 真实产物（`libkea-dhcp.so.109.0.0`），永不命中 → `lib/` 从未
   打包。修完包型后 configure 期报
   `Library 'kea-asiodns' not found in package`（conan_package_library_targets
   在 lib/ 里找不到 `libkea-asiodns.so`）。
3. **library 包型的硬性要求**：`package_type="library"` 必须声明 `shared`
   选项，否则 conan 解析期直接报错。

## 推荐方案（实测配方形态）

```python
# 1) 双形态包用 library 包型 + shared 选项：
package_type = "library"
options = {"shared": [True, False], "tests": [True, False]}
default_options = {"shared": True, "tests": True}

# 2) meson 产物匹配带 lib 前缀，cpp_info.libs 用裸名：
def _is_packaged_lib(self, name):
    if name.endswith(".symbols"):       # meson SHSYM 中间产物
        return False
    return any(name == "lib{}.so".format(lib)
               or name.startswith("lib{}.so.".format(lib))
               for lib, _ in self.kea_libs)

def package_info(self):
    self.cpp_info.libs = [lib for lib, _ in self.kea_libs]   # 裸名
    self.cpp_info.includedirs = [os.path.join("include", "kea")]
```

快速复核命令（失败时不用重建，直接查生成数据）：

```bash
grep "INCLUDE_DIRS_RELEASE\|LIBS_RELEASE" \
  test_package/build/*/generators/<pkg>-*-data.cmake
```

## 验证

- 修复后 `conan create` exit 0：test_package 三类验证全过
  （`find_package` + 链接编译；`test_isc_kea` PASS——IOAddress/Element API
  断言；`test_ohos_platform` PASS——OHOS ABI/dlopen 检查；五守护进程
  `-v` 实跑 rc=0 输出 `3.0.3`）。
- 干净重跑（`conan remove` 后全流程）数字完全一致。
- 仓内先例对齐：`mysql-8.4`（binaries + mysqlclient）同为 `library` 包型。

## 限制

- library 包型会把包计入下游依赖图，纯工具件不适用（那是 application
  包型的正确场景）。
- shared 库在 OHOS 的运行期解析（`libc++_shared.so` 的 LD_LIBRARY_PATH）
  是独立坑，不在此条范围。
