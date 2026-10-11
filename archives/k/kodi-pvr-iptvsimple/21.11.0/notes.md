# kodi-pvr-iptvsimple 21.11.0 适配笔记

## 结论

适配成功：本地 `conan create`（profile `ohos-aarch64`）构建 + test_package 全绿
（2 个测试二进制共 25 条断言）。

## 版本映射与源码身份

- 产品版本 `21.11.0` ↔ 上游 tag `21.11.0-Omega`（kodi-pvr/pvr.iptvsimple，
  release commit `fe95755432cd16acfdadac2926780bac088179ac`）。
- 归档 `https://github.com/kodi-pvr/pvr.iptvsimple/archive/refs/tags/21.11.0-Omega.tar.gz`
  SHA256 `377fb3c69d39866c0b3b8a3a7d4c790241b15997b140f45443209c4e44e62418`
  （codeload.github.com 与 gh-proxy 镜像同哈希，官方值）。
- 名称遵循仓库 kodi-* 家族约定（上游项目 id `pvr.iptvsimple` → 包名
  `kodi-pvr-iptvsimple`）。

## 依赖闭包（制品仓已发布，`conan download --only-recipe` 探测通过）

- `pugixml/1.15-r0`（静态，编入模块）。上游 pin 1.14
  （depends/common/pugixml/pugixml.txt），制品仓无 1.14 → 用 1.15-r0
  （同 1.x 系列，插件只用稳定 DOM 子集，源码兼容）。
- `lzma/5.6.2`（XZ Utils，静态 PIC，编入模块）。上游 pin xz-utils 5.4.3
  （depends/common/xz-utils/xz-utils.txt），制品仓用同名 liblzma API 的
  lzma/5.6.2。
- zlib：**链接 OHOS 系统 libz.so**（`FileUtils::GzipInflate` 用 inflate）。
  conan zlib/1.3.1 刻意只出静态非 PIC 归档（系统同名库 R26），无法链入
  aarch64 共享模块；产物 DT_NEEDED=`libz.so`，运行时由 OHOS 加载器解析到
  系统组件 `/system/lib64/platformsdk/libz.so`（test_ohos.cpp 用 dladdr 实测取证）。
- 无外部 curl 依赖：网络/文件访问走 Kodi 宿主 `kodi::vfs` / `kodi::network`。

## 上游测试门禁（NO_UPSTREAM_TESTS，R51 清点证据）

- 源码归档内 `find . -iname '*test*'` 无任何命中，**无 tests/ 目录**；
- `CMakeLists.txt`：无 `enable_testing()`/`add_test()`/CTest 注册（仅
  find_package + addon_version + build_addon）；
- `Jenkinsfile`：单行 `buildPlugin(version: "Omega")`——仅构建；
- `.github/workflows/build.yml`（名为 "Build and run tests"）：唯一 job 是构建
  （checkout xbmc Omega 树 + build add-on）；"Debian package test"（`DEBIAN_BUILD`
  默认关闭）走 xbmc `debian-addon-package-test.sh`（`sudo apt-get build-dep` +
  fakeroot/dpkg 打包冒烟），非测试套件且本环境不可运行；
- `azure-pipelines.yml` / `build-install-mac.sh`：仅构建/辅助脚本。

结论：上游无可在本环境运行的自动化测试套件 → `NO_UPSTREAM_TESTS`。

## 构建方案

1. **Kodi 构建系统缺失**：上游 `find_package(Kodi REQUIRED)` + `build_addon()`
   需要 kodi-addon-dev 发行包（registry 无 kodi 包）→ 仿
   kodi-inputstream-rtmp / kodi-addon-screensaver 自备 `recipe-cmake/CMakeLists.txt`
   （`cmake.configure(build_script_folder="recipe-cmake")`），上游源码零修改。
2. **kodi-dev-kit 头**：xbmc 21.3-Omega 归档 `xbmc/addons/kodi-dev-kit/include/kodi`
   原样内嵌到版本目录 `kodi-dev-kit/kodi`（152 个头文件；归一化掉 `include/`
   路径段以避开仓库 `.gitignore` 的 `archives/**/include/` 规则）。
   核对：`kodi/versions.h` 的 `ADDON_INSTANCE_VERSION_PVR=8.3.0`（min 8.2.0），
   与 21.11.0 插件的 Omega（21.x）PVR 代码一致（源码所有 override 均可解析）。
   不定义 `BUILD_KODI_ADDON` → versions.h 编译进全部版本分支，test_package 可
   在无宿主时断言版本。
3. **上游 find 模块替换**：`Findpugixml.cmake`/`Findlzma.cmake`（pkg-config 风格）
   改为 `find_package(pugixml CONFIG REQUIRED)` / `find_package(lzma CONFIG REQUIRED)`
   + Conan CMakeDeps target。zlib 用系统 `z`。
4. **产物**：单一共享模块 `lib/pvr.iptvsimple.so`（CMake `MODULE` + `PREFIX ""`，
   与 addon.xml 的 `library_linux` 期望名一致），SONAME 显式为
   `pvr.iptvsimple.so`（CI L5a 要求相对 SONAME）。
5. **PVR 版本串**：`addon_version(pvr.iptvsimple IPTV)` 由 addon.xml.in 取
   `IPTV_VERSION=21.11.0`，经 recipe-cmake 的编译定义注入（`STR()` 由
   `kodi/versions.h` 自带，无需自造）。

## 关键坑：OHOS 加载器对产物做整文件完整性校验（本库最大发现）

首轮 test_package 失败：`dlopen` 打包后的 `pvr.iptvsimple.so` 报
`Error loading shared library ...: Permission denied`（EACCES），且**链接**该模块
的测试二进制在进程启动时即失败。定位过程（可复现）：

- 链接器直接输出（`build/Release/pvr.iptvsimple.so`）`dlopen` **成功**；
- `cmake --install` 后的同名文件 `dlopen` **失败**（conan 包内即此文件）；
- 两份文件仅差 230 字节（`cmake --install` 的 RPATH 改写：把构建期 RUNPATH 字符串
  就地清零、并重写部分路径字符串），ELF 头/段/动态表结构一致；
- **单字节翻转实验**：对可加载的链接器输出，在任意位置（含加载器不读取的
  `.debug_*` 节）翻转 1 字节 → `dlopen` 立即 EACCES；把全部差异字节还原 → 恢复可加载。

**根因**：OHOS（musl）加载器对可加载 ELF 做**整文件完整性校验**（链接期记录的完整性
值），任何链接后的文件改动（哪怕未被加载器读取的字节）都会使校验失败，`dlopen`
返回 EACCES。`cmake --install` 的 RPATH 改写在产物上做了就地修改 → 校验失效。

**规避（本配方）**：`CMakeToolchain` 置 `CMAKE_SKIP_RPATH=ON` → 链接器输出不含
RUNPATH，`cmake --install` 不再改写（安装文件与链接器输出逐字节一致）→ 校验通过。
（对照：kodi-inputstream-rtmp 只链静态库，CMake 未植入构建期 rpath，`cmake --install`
不产生改动，故未踩中此坑。）

## test_package 设计

消费者测试为真实编译 + 链接 + 运行，两二进制共 25 条断言（任一失败进程返回非零）：

- `test_kodi_pvr_iptvsimple.cpp`（16 条）：Part 1 契约——`dlopen` 产物并断言
  `ADDONCREATOR` 导出的 `ADDON_Create`/`ADDON_GetTypeVersion`/`ADDON_GetTypeMinVersion`，
  PVR 8.3.0/8.2.0、main 2.0.2/2.0.0、general 1.0.5/1.0.4、未知类型 "0.0.0"
  （对齐 21.3-Omega 头）；Part 2 功能——直接调用产物导出的
  `FileUtils::GzipInflate`/`XzDecompress`（test-only 前向声明），用内嵌 gzip/xz
  样本验证 zlib 与 liblzma 解压路径逐字节正确、对非法输入不产出数据；
  `PathCombine` 构造 POSIX 路径。
- `test_ohos.cpp`（9 条，**鸿蒙特有测试**，`-Wall -Wextra -Werror` 严格编译）：
  `RTLD_NOW` 即时绑定（OHOS/musl 全重定位）；`dlsym("inflate")` + `dladdr` 断言
  zlib 符号解析到 OHOS **系统** libz（实测 `/system/lib64/platformsdk/libz.so`）；
  `dladdr(ADDON_Create)` 断言解析到的模块即打包产物且 PVR API 为 8.3.0/8.2.0。

## 遗留风险

- Kodi 宿主运行时行为未端到端覆盖（设备无 Kodi）：未驱动 `ADDON_Create` →
  `create_instance(ADDON_INSTANCE_PVR)`（`IptvSimple::Initialise` 依赖宿主 settings/
  vfs 接口），真实 M3U/EPG 拉取与播放仍需宿主侧验证。
- addon.xml 的 `@ADDON_DEPENDS@`/`@PLATFORM@`/`@LIBRARY_FILENAME@` 占位符由 Kodi
  宿主安装流程展开，不在本包范围。
- pugixml 1.14→1.15-r0、xz 5.4.3→lzma 5.6.2 的上游 pin 偏差已在配方 docstring
  与本节记录（API 兼容子集）。

## 验证命令

```bash
P=<repo>/ci/conan/profiles/ohos-aarch64
cd archives/k/kodi-pvr-iptvsimple/21.11.0
conan create . -pr:h=$P -pr:b=$P      # 构建 + test_package（25/25 断言通过）
```
---

**编译结束**: 2026-10-10 11:13
**最终状态**: built
