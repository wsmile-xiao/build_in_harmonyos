# libmusicbrainz5 5.1.0-git20150707 适配笔记

## 编译环境
- 构建系统: cmake（上游 `cmake_minimum_required(VERSION 2.6)`）
- 编译日期: 2026-09-17
- 编译器: clang/clang++ 15.0.4（OHOS SDK / `/data/service/hnp/bin`）
- CMake: 4.1.2
- Profile: `ci/conan/profiles/ohos-aarch64`（os=OHOS, os.version=6.0, arch=armv8）
- 状态: published

## 版本说明

版本号 `5.1.0-git20150707` 对应 **Debian 源包 `libmusicbrainz5` 的 `5.1.0+git20150707-N`**
（当前 sid/forky 为 `-12`）。上游 `metabrainz/libmusicbrainz` 在 `release-5.1.0`
（2014-11-13）之后**未再发布 release**，各发行版遂改用 git 快照打包。

- 快照来源: 上游 2015-07-07 当日 master HEAD = commit `97f98a6e04d6ae0bc7c1a7f8003e25b6c364d59b`
  （"Merge pull request #9 from sebastinas/split-c-interface"，2015-07-07T19:17:08Z）
- 官方源码 URL: `https://github.com/metabrainz/libmusicbrainz/archive/97f98a6e04d6ae0bc7c1a7f8003e25b6c364d59b.tar.gz`
- SHA256: `15ea1bf5a01ba2e5f0f1f3eb6ac5d281711df09cbdf4ddfad67783b57a2dd048`（两次独立下载字节一致）

**与 release-5.1.0 的关键差异**（决定了历史补丁需重新适配）:
1. `src/CMakeLists.txt` 将原单一 `musicbrainz5` 库拆为两个：
   `musicbrainz5cc`（C++ 源）+ `musicbrainz5`（C 接口 `mb5_c.cc`），
   并新增 `libmusicbrainz5cc.pc`；
2. 该拆分导致 `src/CMakeLists.txt` 的 `ADD_CUSTOM_COMMAND` 位置相对
   release-5.1.0 下移一行（`*.inc` 依赖所在 hunk 的上下文行号变化）；
3. C API 为纯函数式（`mb5_query_new` 等），无 `mb5_metadata_new` 构造函数，
   亦无 `MB5_VERSION_MAJOR` 宏。

## 编译步骤

```bash
# 1. 依赖（均已发布到 ohpcd 制品仓，W0 通过）
conan download libxml2/2.15.3.1 -r=ohpcd      # exit 0
conan download neon/0.34.0 -r=ohpcd           # exit 0

# 2. 配方验证（内含 conan create 干净构建）
python3 scripts/ohc-run.py conan-verify libmusicbrainz5 5.1.0-git20150707
# → G0/G1/G2/G3/G4 + L2/L4/L5 全 PASS，exit 0
```

`conanfile.py` 关键配置：
- `generate()`: `BUILD_SHARED_LIBS`（`shared` 选项驱动）+ `CMAKE_INCLUDE_PATH` /
  `CMAKE_LIBRARY_PATH` 注入 libxml2/neon 搜索路径
- `build()`: `cmake.configure(cli_args=["-DCMAKE_POLICY_VERSION_MINIMUM=3.5"])`
  + `LD_LIBRARY_PATH` 按「SDK 优先、Conan 依赖追加」顺序注入

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `Error loading shared library libxml2.so.16` + `xmlFreeDoc: symbol not found`（链接阶段） | OHOS SDK 的 `lld` 自身依赖 SDK `llvm/lib` 下的 `libxml2.so.16`（ABI 2.14.0）。构建期把 Conan libxml2 的 lib 目录**前置**到 `LD_LIBRARY_PATH` 后，lld 加载到同名但 ABI 不同的 `libxml2.so.16`（2.16.1.3），符号解析失败 | `LD_LIBRARY_PATH` 顺序改为：SDK `llvm/lib` **前置**（`prepend_path`），Conan 依赖 lib 目录**追加**（`append_path`）。知识条目 E120/E132/E266 |
| 2 | `CMake Error at CMakeLists.txt:1 (cmake_minimum_required): Compatibility with CMake < 3.5 has been removed` | 上游 `cmake_minimum_required(VERSION 2.6)`，CMake 4.1.2 已移除 <3.5 兼容模式；且 `CMAKE_POLICY_VERSION_MINIMUM` 必须**先于** CMakeLists 第 1 行生效，写在 CMakeToolchain 变量里太晚 | `cmake.configure(cli_args=["-DCMAKE_POLICY_VERSION_MINIMUM=3.5"])` 以命令行 `-D` 传入。知识条目 E103 |
| 3 | 补丁 `0002-remove-glob-dependency.patch` 应用失败：`hunk no.1 doesn't match source file at line 36` | 历史补丁基于 release-5.1.0 的行号（`@@ -36,7 +36,7 @@`）。20150707 快照因 `_sources_cc`/`_sources_c` 拆分，`ADD_CUSTOM_COMMAND` 下移至 36 行，`*.inc` 依赖在 40 行，上下文不匹配 | 用 `diff -u` 从 20150707 真实源码重新生成补丁（hunk header 改为 `@@ -37,7 +37,7 @@`），并保留 `copy_if_different` 后的双 tab 缩进 |
| 4 | `apply_conandata_patches()` 报错位置在 `generate()` | 补丁应在源码就绪后立即应用 | 移入 `source()`（`get()` 之后） |
| 5 | test_package 编译报 `use of undeclared identifier 'MB5_VERSION_MAJOR'` / `'mb5_metadata_new'` | 误按其他发行版 API 假设编写用例；本版本 C API 为纯函数式，无该宏与构造函数 | 改按真实头文件 `mb5_c.h` 与上游 `tests/ctest.c` 用法编写：`mb5_query_new` / `mb5_query_get_version` / `mb5_query_delete` |
| 6 | 上游 `mbtest` 退出码 134（SIGABRT） | 上游演示程序硬编码访问 `musicbrainz.org`，服务端要求 Bearer/Digest 认证，程序未捕获 `CAuthenticationError` | 非适配缺陷（上游测试的环境依赖）。详见 `reports/upstream-test-report.md` |
| 7 | W3 L5 门禁报 `soname_gate_failed`：两个 `.so` 缺少 `DT_SONAME` | 上游 CMakeLists 虽设置了 `SOVERSION`，但在 OHOS 工具链下 CMake **未生成 `-soname` 链接参数**（`link.txt` 中无相关 flag），产物 `DT_SONAME` 为空 | 补丁 0003 显式注入 `LINK_FLAGS "-Wl,-soname,libXXX.so"`，本地 `readelf -d` 验证得到 `SONAME [libmusicbrainz5.so]` / `[libmusicbrainz5cc.so]`（**不带版本号**：上游 install 只产出 `libX.so`，无 `.so.N` 符号链接链，若 SONAME 带版本号运行期加载器会找不到文件——该失败已实测复现） |
| 8 | 上游 ELF 的 `NEEDED` 含相对路径（`../src/libxxx.so`，见 `tests/`、`examples/` 可执行文件） | 上游 CMake 在链接这些可执行文件时把库名解析为相对路径并写入 `NEEDED` | 不影响安装后的库产物（`lib/*.so` 的 NEEDED 均为干净裸名）；从 `build/tests/` 目录内运行可正常解析 |

## 源码修改

补丁 3 个（均在适配层，不改上游行为语义）：

1. **`patches/0001-xmlGetLastError-const.patch`**（portability）
   `src/xmlParser.cc` 两处：`xmlErrorPtr error = xmlGetLastError();`
   → `const xmlError *error = xmlGetLastError();`
   —— 兼容 libxml2 2.15.x 起 `xmlGetLastError()` 返回 `const xmlError *` 的签名变化。

2. **`patches/0002-remove-glob-dependency.patch`**（build_fix）
   `src/CMakeLists.txt` 的 `ADD_CUSTOM_COMMAND` 中 `DEPENDS ... cinterface.xml *.inc`
   → 去掉 `*.inc`。`make` 不展开 glob 通配符，会把字面量 `*.inc` 当作目标名，
   报 `No rule to make target '*.inc'`。

3. **`patches/0003-set-shared-library-soname.patch`**（portability）
   `src/CMakeLists.txt` 在 `TARGET_LINK_LIBRARIES` 前插入两条
   `SET_TARGET_PROPERTIES(... LINK_FLAGS "-Wl,-soname,libmusicbrainz5.so")` /
   `... "-Wl,-soname,libmusicbrainz5cc.so"` —— OHOS 工具链下 CMake 未按上游的
   `SOVERSION` 生成 `DT_SONAME`，导致下游链接器无法按 SONAME 寻址。
   SONAME 取**不带版本号**的实际文件名（上游 install 无 `.so.N` 符号链接链）。

> 三个补丁均不含平台宏（符合 R8 / PF5）。

## 依赖版本

| 依赖 | 版本 | 来源 | 说明 |
|------|------|------|------|
| libxml2 | 2.15.3.1 | ohpcd 制品仓（shared=True） | XML 解析；上游 `FindLibXml2.cmake` 仅搜系统路径 |
| neon | 0.34.0 | ohpcd 制品仓（shared=False） | HTTP 客户端；上游 `FindNeon.cmake` 仅搜系统路径 |
| expat | 2.8.2 | 传递依赖（neon → expat） | |
| zlib | 1.3.1 | 传递依赖（neon → zlib） | |

## 验证结果

```bash
$ python3 scripts/ohc-run.py conan-verify libmusicbrainz5 5.1.0-git20150707
  ✅ G1: PASS   （配方完整性）
  ✅ G0: PASS   （预构建风险评估）
  ✅ G2: PASS   （conan create 干净构建）
  ✅ G3: PASS   （系统同名库隔离 R26）
  ✅ G4: PASS   （产物完整性）
  ✅ L2/L4/L5   （smoke test / 安全扫描 / 产物基线）
✅ 配方验证通过: libmusicbrainz5 5.1.0-git20150707
```

`conan create` 中 test_package 实际执行输出：
```
libmusicbrainz5 (test package): Running test()
libmusicbrainz5 client version: libmusicbrainz5-v5.1.0
test_musicbrainz5: OK (C++ API + C API roundtrip)
```

## 交付物

| 文件 | 说明 |
|------|------|
| `conanfile.py` | Conan 配方（CMake 构建，neon + libxml2 依赖） |
| `conandata.yml` | 源码 URL/SHA256 + 3 个补丁声明 |
| `patches/0001-xmlGetLastError-const.patch` | libxml2 2.15.x `const xmlError*` 兼容 |
| `patches/0002-remove-glob-dependency.patch` | 移除 `*.inc` 字面 glob 依赖 |
| `patches/0003-set-shared-library-soname.patch` | 显式设置共享库 `DT_SONAME`（OHOS 工具链未按 SOVERSION 生成） |
| `test_package/conanfile.py` | 消费者测试驱动 |
| `test_package/test_musicbrainz5.cpp` | C++/C API 消费者视角用例 |
| `test_package/MANIFEST.yml` | 上游测试来源声明（L0e） |
| `reports/conan-verify-report.md` | G0-G4 门禁报告 |
| `reports/upstream-test-report.md` | 上游测试执行报告（R51） |
| `reports/upstream-ctest.log` / `upstream-mbtest.log` | 上游测试原始输出 |
| `reports/upstream-build-attempt-*.log` | 构建尝试日志（含首个错误） |

产物（包内）：
- `lib/libmusicbrainz5.so`（C API）
- `lib/libmusicbrainz5cc.so`（C++ API）
- `lib/pkgconfig/libmusicbrainz5.pc`、`libmusicbrainz5cc.pc`
- `include/musicbrainz5/*.h`（含构建期生成的 `mb5_c.h`）

## 注意事项

1. **`LD_LIBRARY_PATH` 顺序敏感**：OHOS SDK 的 `lld` 依赖 SDK 自带 `libxml2.so.16`。
   任何把 Conan libxml2 lib 目录前置到 `LD_LIBRARY_PATH` 的做法都会破坏 lld 链接，
   表现为 `Error loading shared library libxml2.so.16` / `symbol not found`。
2. **`CMAKE_POLICY_VERSION_MINIMUM` 必须走命令行 `-D`**：写在 CMakeToolchain 变量中
   对 `cmake_minimum_required` 检查无效。
3. **上游测试需联网且需认证**：`tests/ctest`、`tests/mbtest` 均硬编码线上服务地址，
   无法作为离线回归；本适配以 test_package 消费者用例为准。
4. **上游 ELF 使用了相对路径 `NEEDED`**：`tests/*` 与 `examples/*` 可执行文件的
   `NEEDED` 条目记录为 `../src/libmusicbrainz5.so`（相对路径），须从 `build/tests/`
   目录内运行才能解析；此为上游 CMake 行为，不影响安装后的库产物。

## 知识沉淀

本次适配的 4 个真实问题中，3 个已有知识库条目覆盖，**无新增条目**；
仅 1 项为通用模式的新增（以通用命名提交，不绑定本库）：

| 问题 | 知识库归属 |
|------|-----------|
| lld 加载 ABI 不兼容的 `libxml2.so.16`（`LD_LIBRARY_PATH` 顺序） | **已有** E120（含 `forbid_1: LD_LIBRARY_PATH=.*libxml2`）/ E132 / E266 |
| CMake 4.x 拒绝 `cmake_minimum_required(<3.5)`，`CMAKE_POLICY_VERSION_MINIMUM` 注入方式 | **已有** E103（正式条目）+ DRAFT-E321（已明确"切勿用 tc.variables，应用 cache_variables"） |
| 上游 `FindLibXml2.cmake`/`FindNeon.cmake` 仅搜系统路径 | **已有** E216 |
| OHOS 平台 CMake 链接项目内库用相对路径而非 SONAME | **已有** E207 / E274 |
| `ADD_CUSTOM_COMMAND` 的 `DEPENDS` 中 `*.ext` 字面通配符 → `No rule to make target` | **新增** `DRAFT-cmake-add-custom-command-depends-glob-literal`（通用 CMake/Make 模式，含补丁 hunk 行号须对目标源码重生成的实操要点） |

---

**编译结束**: 2026-09-17 18:38
**最终状态**: published
