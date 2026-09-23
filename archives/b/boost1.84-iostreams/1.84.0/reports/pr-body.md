## PR 信息
- **三方库名称**：boost1.84-iostreams（Boost.Iostreams 组件拆分包，Debian libboost-iostreams1.84 模式）
- **上游版本**：Boost 1.84.0（boost_1_84_0）
- **上游仓库地址**：https://github.com/boostorg/iostreams（发行 tarball 来自 https://www.boost.org/users/history/version_1_84_0.html）
- **适配路径**：路径 A（基础适配）
- **使用知识库**：openharmony-compile-agent（E068 Boost.Build 不兼容、E002 /tmp 只读、boost1.84-atomic/log 组件包先例）

---

## 测试用例对比
### 上游库测试用例统计
上游 `libs/iostreams/test/Jamfile.v2` 测试注册共 **56 个条目**（2026-09-06 实测核对，构建源码 sha256 与上游 boost-1.84.0 tag 一致）。口径说明：56 = `test-iostreams` 53 行（52 个测试调用 + 1 个 rule 定义行）+ `compile-fail-iostreams` 2 行（1 个测试调用 + 1 个 rule 定义行）+ `test-suite` 汇总声明 1 行；**其中真实测试目标注册 53 个**（52 个 run 型调用 + 1 个 compile-fail 型调用）：

| 测试类型 | 上游注册数 | 说明 |
|----------|-----------|------|
| 无条件注册 | 45 | 44 个 run 型（43 个平台通用测试：array/auto_close/buffer_size/close/code_converter(+utf8 源)/combine/compose/component_access/copy/counter/deprecated_file_descriptor(+宏)/direct_adapter/dual_seekable/example/execute/file/file_descriptor/filtering_stream/finite_state_filter/flush/grep(+regex)/invert/line_filter/mapped_file/newline/null/operation_sequence/path/pipeline/read_nonblocking/regex_filter(+regex)/restrict/seekable_file/seekable_filter/sequence/slice/stdio_filter/stream_offset_32bit/stream_offset_64bit/stream_state/symmetric_filter/tee/wide_stream + windows_pipe）+ 1 个 compile-fail 型（deprecated_file_descriptor_fail） |
| 条件注册（后端可用性门控，本包已启用该后端） | 4 | `if ! $(NO_BZIP2)` → bzip2_test；`if ! $(NO_ZLIB)` → write_failure/gzip/zlib_test（`ac.check-library` 系统库探测，依赖存在才真构建） |
| 条件注册（后端可用性门控，本包未启用该后端） | 2 | `if ! $(NO_LZMA)` → lzma_test；`if ! $(NO_ZSTD)` → zstd_test |
| 条件注册（环境变量门控） | 2 | `if $(LARGE_FILE_KEEP)` / `if $(LARGE_FILE_TEMP)` → large_file_test 两个变体（默认不设即不注册） |
| **合计（条目口径 56 = 真实测试目标 53 + 2 个 rule 定义行 + 1 个 test-suite 汇总行）** | **56** | 其中 windows_pipe_test 虽无条件注册但带 `<build>no <target-os>windows:<build>yes`，非 Windows 平台上游自身不构建 |

### 本配置生效测试集（真实测试目标 53 → 48 的推导）
本包后端配置：**zlib/1.3.1 + bzip2/1.0.8 已启用**（conan requires + zlib.cpp/gzip.cpp/bzip2.cpp 编入 + 链接）；**lzma/zstd 未启用**（未引入 liblzma/libzstd 依赖，同元包口径）；目标平台 OHOS（非 Windows）；LARGE_FILE_TEMP/KEEP 未设。

| 排除项 | 数量 | 原因（上游条件/平台门控，非适配删减） |
|--------|------|------|
| windows_pipe_test | 1 | Windows-only（`<build>no <target-os>windows:<build>yes`），非 Windows 平台上游 b2 自身就不构建 |
| lzma_test / zstd_test | 2 | NO_LZMA/NO_ZSTD 变量语义，需系统 liblzma/libzstd；本包后端裁剪决策未引入该依赖 |
| large_file_test ×2 | 2 | 需 LARGE_FILE_TEMP/KEEP 环境变量（上游条件测试，未设即不注册执行） |
| **真实测试目标 53 − 5 = 实际执行 48** | | **已启用后端（zlib+bzip2）的条件测试 bzip2_test/gzip_test/zlib_test/write_failure_test 全部真跑**（含在 48 项内） |

### 适配后测试用例统计
| 测试类型 | 适配后用例数 | 与上游对比 | 说明 |
|----------|-------------|-----------|------|
| 单元测试 | 48 | 上游真实测试目标 53 中本配置生效的 48 项全部执行 | 上游 48 项测试（47 run + 1 compile-fail）全部在配方 build() 中手动编译并真实运行（b2 在 OHOS 不兼容 E068，绕过 b2 用 clang++ 直编直跑），48/48 通过 |
| 集成测试 | 0 | 不变 | — |
| 鸿蒙特有测试 | 1 | 新增 | test_package 下游消费冒烟（find_package(boost1.84-iostreams COMPONENTS iostreams) → boost1.84-iostreams::iostreams，覆盖 gzip/zlib/bzip2 三压缩 round-trip + file_descriptor 管道 + mapped_file） |
| **合计** | **49** | **+1** | |

---

## 上游测试用例修改说明
### 是否存在对上游测试用例的修改？
- [x] **否**，未修改上游任何测试用例
- [ ] 是，存在对上游测试用例的修改

（说明：上游测试源文件零改动，原样编译运行。仅因 b2 构建系统在 OHOS 不兼容（E068，Boost.Build SHELL 执行机制失败），改为手动 clang++ 编译同一批测试源文件并直接运行可执行文件；deprecated_file_descriptor_test 按上游 Jamfile 分别以带/不带 BOOST_IOSTREAMS_USE_DEPRECATED 宏两种配置编译（run 型 + compile-fail 型），与上游 test-suite iostreams 等价。）

---

## 补全测试用例说明
### 上游是否存在无测试用例，适配后补全的情况？
- [x] **否**，上游已有测试用例覆盖
- [ ] 是，补全

---

## 验证结果
- 编译状态：通过（conan create -pr ohos-aarch64：5 TU 编译 → libboost_iostreams.a 打包 → test_package 构建签名运行全通过，exit code 0）
- 上游测试用例通过率：48/48（100%，本配置生效全集；上游真实测试目标 53 项、Jamfile 条目 56 项，未执行 5 项均为条件/平台门控，见上方"53→48 推导"表）
- 新增测试用例通过率：1/1（100%）

上游测试运行证据（conan create 日志，OHOS aarch64 本机）：
```
boost1.84-iostreams/1.84.0: [upstream-tests] TOTAL 48: 48 passed / 0 failed
（47 run 型全部 rc=0：array/auto_close/buffer_size/close/code_converter/combine/
 compose/component_access/copy/counter/deprecated_file_descriptor(+宏)/
 direct_adapter/dual_seekable/example/execute/file/file_descriptor/
 filtering_stream/finite_state_filter/flush/grep(+regex)/invert/line_filter/
 mapped_file/newline/null/operation_sequence/path/pipeline/read_nonblocking/
 regex_filter(+regex)/restrict/seekable_file/seekable_filter/sequence/slice/
 stdio_filter/stream_offset_32bit/stream_offset_64bit/stream_state/
 symmetric_filter/tee/wide_stream/write_failure/bzip2/gzip/zlib）
boost1.84-iostreams/1.84.0: [upstream-tests] PASS deprecated_file_descriptor_test.cpp (compile-fail expectation, rc=1)
```
（bzip2/gzip/zlib/write_failure 4 项为本包已启用压缩后端对应的上游条件注册测试，真跑通过）
test_package 运行证据：
```
gzip round-trip OK (40 bytes compressed)
zlib round-trip OK (28 bytes compressed)
bzip2 round-trip OK (45 bytes compressed)
file_descriptor + gzip pipeline OK
mapped_file source OK
boost1.84-iostreams 1.84.0: gzip/zlib/bzip2 + file_descriptor + mapped_file OK
```

---

## 补充说明
- **形态选型**：独立裁剪编译（方案 A）。boost/1.84.0 元包的 iostreams 段只编了 4 个 TU 且漏带上游 Jamfile（libs/iostreams/build/Jamfile.v2 line 120）要求的 BOOST_IOSTREAMS_USE_DEPRECATED 宏（deprecated 构造/open 重载符号缺失，deprecated_file_descriptor_test 链接失败实证）、且无 bzip2 后端；本组件包补齐 5 TU（file_descriptor/mapped_file/zlib/gzip/bzip2）+ 宏 + bzip2/1.0.8 依赖。元包同版本 revision 已冻结无法修订，组件包独立演进（R37）。选型详情见 1.84.0/notes.md。
- **压缩后端**：zlib/1.3.1 + bzip2/1.0.8（Conan requirements，制品仓在库 W0 已验证），组件 requires 声明传递链接——下游链接 boost1.84-iostreams::iostreams 自动带上 libz/libbz2（Debian libboost-iostreams1.84 同款模式）。**后端裁剪决策**：lzma/zstd 未启用（需 liblzma/libzstd 依赖，上游按系统库存在与否条件编入，同元包口径；对应上游条件测试 lzma_test/zstd_test 因此不在本配置生效集内，后续有需求可加依赖递增版本号）。
- **源码**：与元包同源（官方 boost_1_84_0.tar.gz，SourceForge + archives.boost.io 双镜像，sha256 a5800f40...5724 已实测校验）。
- **补丁**：继承元包 0001-ohos-pthread-cancel-fix.patch（sp_thread_sleep.hpp 的 pthread_setcancelstate 在 OHOS musl 不可用，以 BOOST_SP_NO_PTHREAD_SETCANCELSTATE 特性检测宏守卫，R8 合规非平台宏）。iostreams TU 经 smart_ptr 头链触及该文件（本地实测不带 patch 编译报错）。
- **CMake 包名**：组件包用独立 cmake_file_name（boost1.84-iostreams），避免与元包 "Boost" 的 CMakeDeps 生成文件在同工程共存时互相覆盖（同 atomic/log/wave/timer 先例）。
- **已知限制**：b2 构建系统在 OHOS 不可用（E068 已知技术障碍），上游测试以手动编译运行方式等价执行；上游测试的 boost_unit_test_framework/filesystem/regex 三个辅助库仅在 build() 测试阶段编译，不入 package 产物。
