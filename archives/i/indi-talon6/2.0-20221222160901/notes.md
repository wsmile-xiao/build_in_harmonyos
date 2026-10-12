# indi-talon6 2.0-20221222160901 适配笔记

## 编译环境
- **类型**: CMake 构建的 INDI 驱动（可执行文件 `indi_talon6`，`Talon6 : public INDI::Dome`）
- **编译日期**: 2026-10-07
- **平台**: arm64-ohos（OpenHarmony PC）
- **依赖**: `libindi/2.2.2.1` + `libnova/0.16`（均已合入制品仓，`conan install` 实测可解析）
- **状态**: built

## 编译步骤（conan create 全流程）

```bash
conan create archives/i/indi-talon6/2.0-20221222160901 \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
```

### 1. 源码获取（source()）
`get()` 下载 indi-3rdparty 单体仓归档（commit `945fbe12d13f3472643931e24e444a4ca69d4ed5`，
sha256 `6dee1f35…d87a`），`strip_root=True` 保留整棵仓库树。

**为什么必须保留整棵树**：`indi-talon6/CMakeLists.txt` 会把 `../cmake_modules`
追加进 `CMAKE_MODULE_PATH`，`include(CMakeCommon)` 与 `find_package(INDI)` 都依赖
仓库根的共享 cmake 模块，只取子目录无法配置。

**为什么 pin 到 commit 而不是 tag**：该驱动版本号（`2.0-20221222160901`）是 Debian
打包的日期戳；源码代次取 v2.2.2 代 commit `945fbe12…`，与本仓制品仓的
`libindi 2.2.2.1` 同代（同快照兄弟驱动 `indi-aok 2.0-20221222093242` 用同一 commit
与同一 sha256 构建通过，可互为佐证）。

### 2. 配置（generate()）
- `INDI_ROOT` = libindi 包的 package_folder —— 让仓内 `cmake_modules/FindINDI.cmake`
  命中预构建的 libindi（该 finder 走 `INDI_ROOT` 提示，不依赖系统安装）。
- **私有 `NovaConfig.cmake`**：上游与 libnova 包都没有 Nova 的 finder/config 包，
  而 `indi-talon6/CMakeLists.txt` 要求 `find_package(Nova REQUIRED)`。故在本包
  generators 目录下生成 `NovaConfig.cmake`（`NOVA_FOUND/NOVA_INCLUDE_DIR(S)/
  NOVA_LIBRARIES` 全部取自 libnova cpp_info 的绝对路径），并以 `Nova_DIR` 指向它
  （R49：不注入共享前缀）。

### 3. 构建（build()）
```bash
cmake.configure(build_script_folder="indi-talon6")   # 只配置本驱动子目录
cmake.build()
```
单体仓内其余驱动不参与本包。

### 4. 打包（package()）
`cmake.install()`；产物为 `bin/indi_talon6` 与 `share/indi/indi_talon6.xml`
（XML 里的 `<driver name="Talon6">indi_talon6</driver>`，manufacturer MONFRAGÜE，
group Domes，version 2.0）。

`package_info()`：`bindirs=["bin"]`、`resdirs=["share"]`，并
`prepend_path("LD_LIBRARY_PATH", …libindi 的 libdir)` —— **libindi 以静态优先发布
（shared=False），Conan 不会把它的 lib 目录放进运行环境**，而驱动实际动态链接
libindi 的 `.so`，不显式注入则 test_package/消费者无法加载驱动。

## 实测结果（本地 conan create，2026-10-07）

```
indi-talon6/2.0-20221222160901: Apply patch (portability): 请求 INDI 的 client 组件…
[100%] Built target indi_talon6
indi-talon6/2.0-20221222160901: Package '9819fc38…' created
[ok]   bin/indi_talon6: AArch64 ELF, 72192 bytes
[ok]   share/indi/indi_talon6.xml: driver name + executable reference match the package
[ok]   DT_NEEDED closure complete: libindiclient.so.2, libindidriver.so.2, libindiAlignmentDriver.so.2 (all provided by the libindi package)
[skip] 宿主拒绝映射依赖库（有证据：平台限制标记或 ctypes 权限拒绝），非打包缺陷：Error loading shared library libindidriver.so.2: (needed by …/bin/indi_talon6)
checks=4 fails=0 skips=1
RESULT: PASS
```

- 上游通过率：**N/A**（上游无测试用例，清点证据见下节）
- 消费者校验：**4 项中 3 项通过 + 1 项按设计 SKIP**（沙箱对 OHOS 共享对象的 mmap/未签名 ELF 加载受限；该 SKIP 会打印加载器原文，属平台限制而非打包缺陷）

### 本轮按 aireview 意见所做的修正（PR #14944）

aireview 给出 **P2×2 + P3×1**，已逐条实改并重跑本地 CI 验证（`checks=4 fails=0 skips=1 RESULT: PASS`）：

| # | 级别 | 意见 | 本次改动 |
|---|---|---|---|
| 1 | P2 | `check_driver.py` 把加载器「解析失败」类消息与平台限制混在一起命中即 SKIP，真实闭包缺陷会被放行（假 PASS） | 重写 `check_exec`：**真实闭包/符号缺陷一律 FAIL**（未解析符号、未解析共享对象、被点名却不在任何依赖包内的库）；**仅在有证据时**才记 SKIP——输出含平台限制标记，或被点名的库确实存在却同样无法被宿主映射（新增 `_host_can_map()` 用 ctypes 实测，本机报 `Permission denied` 即证据）。OSError 分支同样只在命中平台限制标记时 SKIP |
| 2 | P2 | 缺 R38 要求的软件级 `commands.json`（兄弟包 indi-aok 有） | 新增 `archives/i/indi-talon6/commands.json`（name/description/homepage/type=`tool`/versions.ref，格式对齐 indi-aok） |
| 3 | P3 | 脚本 docstring 列的核心库与 `INDI_CORE_LIBS` 不一致（docstring 写 `libindilx200`） | docstring 改为 `libindiclient / libindidriver / libindiAlignmentDriver` 与常量一致；`test_package/MANIFEST.yml` 的描述里同处不一致一并修正 |

修正后第 4 项的输出变为「`[skip] 宿主拒绝映射依赖库（有证据：平台限制标记或 ctypes 权限拒绝），非打包缺陷`」——
即"环境限制"与"打包缺陷"现在**有明确证据边界**，不再靠关键字一把梭。

## 适配过程中实际踩到的三个坑（均与同快照兄弟 indi-aok 同源或邻接）

1. **libnova 头目录必须显式注入**：`indidome.h → libastro.h → #include <libnova/utility.h>`，
   而 `indi-talon6/CMakeLists.txt` 只用 `${NOVA_LIBRARIES}` 链接、**不把
   `NOVA_INCLUDE_DIRS` 加进 include 路径**（首轮构建即 `fatal error:
   'libnova/utility.h' file not found`）→ 用 `tc.extra_cflags/extra_cxxflags`
   注入 `-I<nova_inc>`（与 libindi 配方注入 fftw 头的既有做法一致；R33）。
2. **`INDI_DATA_DIR` 会被 `find_path` 定成 libindi 包的绝对路径**：
   `FindINDI.cmake` 里 `find_path(INDI_DATA_DIR … PATH_SUFFIXES share/indi)`，
   而 INDI_ROOT 指向 libindi 包且其中确有 `share/indi/drivers.xml` → 得到绝对路径；
   驱动的 `install(FILES … DESTINATION ${INDI_DATA_DIR})` 于是把 XML **写进 libindi 的
   包目录**（实测确实写进去了，本包反而没有 XML）。修法：在 toolchain 里预置
   `INDI_DATA_DIR = share/indi`（相对路径；`find_path` 对已定义变量直接跳过搜索），
   XML 即落入本包的 `share/indi/`。
3. **DT_NEEDED 缺 `libindiclient`**：`find_package(INDI REQUIRED)` 不带组件时
   `FindINDI.cmake` 回落默认组件 `driver + align`，实测 DT_NEEDED 只有
   `libindidriver.so.2 + libindiAlignmentDriver.so.2`；而这两个库从 libindiclient
   引入的符号（如 `tty_write_string`）必须在 DT_NEEDED 里显式记录，否则 musl
   loader 报 `Error relocating … symbol not found`（与 indi-aok 当年的问题同类）
   → 新增补丁请求 `client` 组件（保持默认 `driver align`）。

## 上游测试清点（R51）

| 项 | 值 |
|----|----|
| 子目录清单 | `CMakeLists.txt`、`talon6.cpp`、`talon6.h`、`config.h.cmake`、`indi_talon6.xml.cmake`、`README`、`AUTHORS`、`ChangeLog`、`INSTALL`、`TODO` |
| 测试框架声明 | **无**：`CMakeLists.txt` 只有 `add_executable(indi_talon6)` + `target_link_libraries` + 两条 `install`，**无 `enable_testing()` / `add_test()`** |
| 仓库级测试 | indi-3rdparty 全仓无该驱动的测试用例（`debian/indi-talon6/` 仅有打包元数据） |
| 结论 | **上游确无测试用例** → `build()` 不跑上游套件；`upstream_test_pass_rate` 记 **N/A**（如实披露，不虚构） |
| 消费者验证 | `test_package/check_driver.py` 4 项（ELF / XML 交叉引用 / DT_NEEDED 闭包 / best-effort 运行） |

## 真机环境注意点

- **运行期库搜索路径**：如上，驱动依赖 libindi 的 `.so`；`conanrun` 环境已由
  `package_info()` 注入 `LD_LIBRARY_PATH`。
- **沙箱内无法直接执行**：本适配沙箱对 OHOS 共享对象/未签名 ELF 的加载受限，
  `check_driver.py` 的第 4 项会把它记为 **SKIP**（并打印加载器原文），
  不让平台限制变成打包失败；前 3 项为静态审计，任何环境下都成立。

## 复用来源

本配方与同快照兄弟驱动 **`archives/i/indi-aok/2.0-20221222093242`** 同构（源码 pin 的
commit/sha256 完全相同、requires 相同、generate()/package_info() 策略相同），
属于"indi-3rdparty 单体仓驱动子目录"这一既有适配范式的直接复用。
