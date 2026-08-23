# osm2pgsql 2.3.1 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-08-19
- 编译器: clang/clang++ (HarmonyOS aarch64)
- 状态: built

## 编译步骤

在 HarmonyOS PC 真机（c1.sermc.net:20222，aarch64）预检目录内执行:

```
conan create osm2pgsql/2.3.1 -pr:h ohos -pr:b default -o "&:shared=False" --build=missing
```

- host profile `ohos`: arch=armv8, build_type=Release, compiler=clang 15, cppstd=17, os=OHOS, os.version=6.0
- 依赖从 OHPCD/ConanCenter 解析；bzip2、lua 在本机从源码构建（--build=missing），其余复用预编译包
- `conanfile.py` 的 `build()` 在 configure/build 后执行 `ctest -L NoDB --output-on-failure`
  （在 CMake build root 即 `self.build_folder` 下、以 `env="conanrun"` 运行），随后 `package()` 调用 `cmake.install()`。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 链接阶段 __cxa_* 等 C++ runtime 符号未定义 | CMake 用 C 编译器驱动（clang）链接，OHOS 上不会自动链接 libc++/libc++abi | generate() 中设置 `CMAKE_EXE_LINKER_FLAGS=-lc++ -lc++abi` |
| 2 | 源码 include `<lua.hpp>`，Conan lua/5.4.8 只装 C 头文件 | lua 包不含上游 C++ wrapper | 补丁 `0001-add-lua-hpp-shim.patch` 在 src/ 提供 lua.hpp shim |
| 3 | FindOsmium.cmake / CMakeLists 用 module-mode find_package(EXPAT/BZip2/ZLIB/Lua/PostgreSQL) | CMakeDeps 只定义 imported target，不填旧式 *_INCLUDE_DIR/*_LIBRARY 变量 | generate() 显式设置各 dep 的 include/lib 变量及 PostgreSQL_ROOT、CMAKE_LIBRARY_PATH |
| 4 | ctest 在错误目录运行报 "No such file" `.../build/Release/build/Release` | `build_root = join(self.build_folder, self.folders.build)` 把路径拼重复（self.build_folder 已是 CMake build root） | 改为 `cwd=self.build_folder` |
| 5 | 手动跑 ctest 报 32/32 failed "Error loading shared library libexpat.so.1/libpq.so.5" | 未注入 conanrun 运行环境（LD_LIBRARY_PATH 缺依赖共享库目录） | 配方用 `env="conanrun"` 提供运行库路径；真机上 source conanrunenv 后 32/32 全过 |

## 源码修改

- `patches/0001-add-lua-hpp-shim.patch`：新增 `src/lua.hpp`（extern "C" 内含 lua.h/lauxlib.h/lualib.h），
  使 include `<lua.hpp>` 的源码不改动即可编译。

## 依赖版本

- libpq/18.1
- boost/1.90.0.4
- lua/5.4.8
- nlohmann-json/3.11.2
- zlib/1.3.1.1.1
- bzip2/1.0.8
- expat/2.8.2.1

## 上游测试套件执行（真机实测）

- 上游注册 62 个 ctest 二进制（源码 374 个 Catch2 TEST_CASE）。
  其中 32 个 NoDB 标签为纯单元测试，无需 PostgreSQL 服务器即可运行。
- 真机执行 `ctest -L NoDB --output-on-failure` → **32/32 通过**，
  合计 **256 个 test cases / 2203 个 assertions 全部通过**。
- 剩余 30 个二进制（test-middle、test-output-*、test-pgsql*、test-pgsql-capabilities…）
  依赖活动 PostgreSQL 服务器 + pg_virtualenv / tablespace fixture，HarmonyOS 未提供，未执行。
  对应 DB 依赖 test cases 114 个（源码计数 374-260）。
- **证伪验证**：故意不加运行库路径手动跑 ctest，32/32 全部 Failed，确认 harness 能抓到失败；
  加回 conanrun 环境后 32/32 全过。exit 0 不等于真跑，此处以 ctest 失败/通过计数为准。

## 验证结果

```bash
# test_package（conan create 自动执行）
osm2pgsql --version   # -> osm2pgsql version 2.3.1 / Build: Release ...
default.style verified

# 上游 NoDB ctest
ctest -L NoDB --output-on-failure
# 32/32 tests passed, 0 failed  (256 test cases / 2203 assertions)
```

## 注意事项

- 上游总 test cases 374（源码），其中 DB 依赖 114 个未能在 HarmonyOS 执行；
  通过率口径按真机实际执行的 NoDB 子集（256/256）填写，并在 PR 正文如实注明
  DB 相关测试未运行及原因。
- PR 正文「上游测试用例通过率」数字必须出自本 notes 记录的真机实测，不估算不编造。
- 内部真机/命令细节不进 PR 正文，仅在 notes.md 保留。
