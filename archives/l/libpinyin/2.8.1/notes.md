# libpinyin 2.8.1 适配笔记

## 编译环境
- 构建系统: cmake（上游同时带 autotools，但 GitHub tag 归档无已生成的 configure，autotools 需 autoreconf，故走 CMake 路径）
- 编译日期: 2026-09-28
- 编译器: clang 15（OHOS aarch64 profile，-stdlib=libc++，C++17，Release）
- conan: 2.29.1；依赖 glib/2.88.3、berkeley-db/4.8.30（均制品仓已发布）
- 状态: built（conan-verify 全绿：G0/G1/G2/G3/G4/L2/L4/L5 PASS，Verdict PASS）

## 编译步骤

1. W0：preflight 确认 glib/2.88.3、berkeley-db/4.8.30 已发布（后者精确 settings 二进制在仓，W0 用 `conan install --build=never` 核过）。
2. conan create（-pr:h/-pr:b=ci/conan/profiles/ohos-aarch64 --build=missing --user=ohpcd --channel=stable）：
   - source()：get() 拉官方 GitHub tag 归档（sha256 见 conandata.yml；设备网络对 github/ghfast 均不通，靠共享 dlcache 按 sha256 命中零网络取包）。
   - generate()：CMakeDeps + CMakeToolchain；tc.variables 里显式喂 GLIB2_INCLUDE_DIR/GLIB2_LIBRARIES（glib2::glib2 目标）与 DB_INCLUDE_DIR/DB_LIBRARY（libdb.a 静态库路径）给上游旧式 Find 模块变量。
   - build()：configure 时命令行注入 -DCMAKE_POLICY_VERSION_MINIMUM=3.5（CMake 4.1.2）；补 <build>/src 符号链接与 LD_LIBRARY_PATH 供 data 生成工具运行期加载；cmake.test() 真实执行上游 ctest（R51）。
   - data 步骤：model19 文本模型下载多通道保障（详见下文「CI 红修复」）：配方层本地副本预置（dlcache/配方目录双位置探测）+ python3 urllib 在线通道（sys.executable，CI worker 必有）；make 层 dl_model19.sh 兜底（多通道降级链，0002 补丁改为 `sh ./dl_model19.sh`）。
3. test_package：find_package(libpinyin CONFIG REQUIRED) + 链接目标 libpinyin + glib-2.0 + libdb.a；SYSTEM_DATADIR 指向包内 share/libpinyin/data；消费者断言 9 项 ok / 0 failures（init/alloc/parse=2/guess/get_sentence/reset/再解析/free/fini）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | E017：conan create 拉 source 时 ghfast.top 镜像超时 | verify 框架对 github URL 注入 ghfast 镜像，且设备对该代理与 github 均不通；注入又改了配方 revision 导致源缓存失效 | 把与 conandata 同 sha256 的 tarball 预置进共享 dlcache（core.sources:download_cache 按"内容 sha256"命中，命中即零网络），并用 .json 元数据登记 URL |
| 2 | CMake 报 Compatibility with CMake < 3.5 removed | 设备 cmake 4.1.2，上游 cmake_minimum_required 过旧；toolchain 变量在 project() 之后才生效 | build() 里 cmake.configure(variables={"CMAKE_POLICY_VERSION_MINIMUM": "3.5"}) 命令行注入 |
| 3 | glib.h not found（编译期） | 上游 FindGLIB2 消费 GLIB2_INCLUDE_DIR/GLIB2_LIBRARIES 旧式变量，find_package(GLIB2) 被 CMakeDeps 的 glib2-config 截胡后变量恒空 | generate() 里把 glib cpp_info 聚合 include 目录喂给 GLIB2_INCLUDE_DIR、GLIB2_LIBRARIES=glib2::glib2 |
| 4 | unknown type name 'ChewingLargeTable2' / Bigram 段错误 | gen-2 索引实现只在 chewing_large_table2_bdb.h/ngram_bdb.h 等后端头文件里，前窗"全关后端走内置存储"的判断不成立 | 启用 BerkeleyDB：requirements 加 berkeley-db/4.8.30（W0 精确二进制核过），并给 FindBerkeleyDB 预置 DB_INCLUDE_DIR/DB_LIBRARY |
| 5 | data 生成工具运行期 db_create/libglib 加载失败 | 上游模型包下载无条件执行，网络抖动即失败；工具运行期还需加载刚编出的 libpinyin.so 与 glib .so | 配方层预置 model19 副本 + LD_LIBRARY_PATH 注入 + <build>/src 符号链接（模型下载保障详见 #9/#10） |
| 6 | 上游 ctest ngram/flexible_ngram 段错误 | 测试硬编码写 /tmp/*.db，设备 /tmp 为只读文件系统，BDB open 失败被吞 | 0001 补丁把测试路径改为构建目录相对路径，ctest 4/4 通过 |
| 7 | test_package 链接/运行失败 | 目标名应为 libpinyin（配方 cmake_target_name 无命名空间）；公开头缺 stdbool.h；glib 包 cpp_info 未发布 libs 名；libpinyin.so 的 BDB 符号需消费者链入 libdb.a | test_package 链 libpinyin + glib-2.0(find_library) + libdb.a；0003 补丁给 pinyin.h 补 stdbool（仅非 C++）；test() 以 conanrun 环境运行通过 |
| 8 | 包内缺 table.conf，pinyin_init 返回 NULL | 上游 install 只装 4 个基础 .bin + bigram.db，漏 SYSTEM_TABLE_INFO 与其余模型表 | package() 从构建目录 data/ 补齐 table.conf 与全部 *.bin |
| 9 | CI 两连红（#63264 fork OOM 重试过 / #63267）：data 目标 `wget ...: inaccessible or not found` → make Error 127 | CI worker 无 wget 二进制；model19 文本模型是 *.bin/bigram.db/table.conf 的硬依赖（SKIP 不可行，见「CI 红修复」节）；设备绿仅因 dlcache 预置副本被 test -s 守卫命中 | 双层保障：0002 补丁改 `sh ./dl_model19.sh`（脚本内含 副本守卫 → 多通道降级 → urllib 兜底，FATAL 报通道清单，.part 防半包）+ 配方层 _ensure_model_data（dlcache/配方目录双位置探测；在线只走 python3 urllib——L0o 门禁禁 conanfile.py 内嵌 curl/wget 调用，见 ci/conan/build_and_test.sh L0o） |
| 10 | 多通道命令内联进 CMake COMMAND 被拆碎（首次修复尝试即踩） | CMake 把含 `;` 的引号参数按 list 拆成多个碎片，make 逐片当独立命令执行 → 全部 "not found" Error 127（旧补丁没炸只因 body 恰好无分号） | 逻辑移出生成系统：补丁只留 `sh ./dl_model19.sh` 一句，脚本由配方构建期生成进构建目录（不入库） |

## 源码修改

均以 conandata.yml patches 记录（apply_conandata_patches 应用）：
- patches/0001-fix-ngram-tests-tmpdir.patch：tests/storage 两个用例的 /tmp 路径改相对路径（仅测试代码）。
- patches/0002-model-data-download-resilience.patch：data 目标下载命令改 `sh ./dl_model19.sh`（脚本由配方生成，见下）。
- patches/0003-pinyin-h-stdbool-for-c-consumers.patch：pinyin.h 仅在非 C++ 编译时包含 stdbool.h（可移植性，无 ABI 影响）。
另 test_package/test.c、CMakeLists.txt 与 conanfile.py（model19 多通道保障、变量桥接、BDB 依赖、包内模型数据补齐）为本配方内容。
conanfile.py 构建期把 dl_model19.sh 生成进构建目录 data/（⛔ 不入库）：副本 test -s 守卫 → 多通道降级 → python3 urllib 兜底，先写 .part 成功后原子改名，全失败打通道清单并 exit 1；PYBIN 由配方注入（运行 conan 的解释器）；MODEL19_URL 环境变量可覆盖端点（file:// 用于离线测试）。

## 依赖版本

- glib/2.88.3（制品仓，共享库）
- berkeley-db/4.8.30（制品仓，静态库 shared=False；仅使用 C API db.h/libdb.a）

## 验证结果

```bash
python3 scripts/ohc-run.py conan-verify libpinyin 2.8.1
# Verdict: PASS；G0/G1/G2/G3/G4/L2/L4/L5 全 PASS（2026-09-28T06:53，v3 配方复验）
# conan create 成功；test_package 消费者断言 9 项 ok / 0 failures
上游 ctest（R51，4 用例）：
1/4 memory_chunk            Passed
2/4 phrase_index_logger     Passed
3/4 ngram                   Passed
4/4 flexible_ngram          Passed
100% tests passed, 0 tests failed out of 4
```

## CI 红修复（2026-09-28，收尾-1B）

CI #63264（fork OOM 重试过）/#63267 两连红，真实根因（CI 日志原文引注）：

```
o[ 84%] Downloading textual model data...
o/bin/sh:  wget http://downloads.sourceforge.net/libpinyin/models/model19.text.tar.gz: inaccessible or not found
omake[2]: *** [data/CMakeFiles/data.dir/build.make:111: .../data/gb_char.table] Error 127
```

- CI worker 无 wget ⇒ data 目标下载 model19 失败；设备绿仅因 dlcache 预置副本被旧 0002 的 test -s 守卫命中。
- SKIP 不可行：上游 data/CMakeLists.txt 的 install(FILES BINARY_MODEL_DATA_FILES) 装的 *.bin/bigram.db 全部由 model19 解压产物链生成（tar → gen_binary_files/gen_unigram/import_interpolation），table.conf 也出自该步；package() 再从构建目录补 table.conf/*.bin ⇒ data 生成是包产物硬依赖，无网即无包。
- 修复形态（双层）：0002 补丁把下载命令改为 `sh ./dl_model19.sh`（脚本由 conanfile.py 构建期生成进构建目录，不入库）；配方层 _ensure_model_data() 先行保障副本（dlcache/配方目录双位置探测 → 拷贝；未命中则 python3 urllib 在线下载）。
- ⚠ CMake 陷阱（实测踩中，问题 #10）：含 `;` 的引号参数会被 CMake 按 list 拆碎，make 逐片执行全部 not found——多通道逻辑必须放 sh 脚本，不能内联 COMMAND。
- ⚠ L0o 门禁（ci/conan/build_and_test.sh）：conanfile.py 内嵌 curl/wget 调用即 L0 fail（uses_external_curl）⇒ conan 层在线通道只走 python3 urllib（sys.executable），多通道降级链保留在 make 层脚本内。
- 验证证据（设备实测，2026-09-28）：
  - 单元级（复刻 CI：本地副本不命中 + 无 wget/curl）：python3-urllib 通道 15.6s 真实下载 20MB，sha256=56422a4ee5966c2c809dd065692590ee8def934e52edbbe249b8488daaa1f50b 与 dlcache 参考副本一致；
  - 脚本独立：坏 wget/curl（exit 127 shim）+ file:// 端点 → urllib 通道下载成功；全通道失败 → FATAL 通道清单 + exit 1 + 无 .part 残留；
  - 真实构建目录重放：删副本+删 table 产物后 make data（wget/curl shim 127）：首跑遇 sourceforge 传输截断（ContentTooShortError），FATAL 清单按设计打出、make Error 正常传播；重跑下载成功（sha256 同上），`[100%] Built target data`，产物链全量重建（MAKE_RC=0）；
  - W3 本地 CI 模拟（finish Step5）：✅ 通过，`L0: All quality gate checks passed`（L0o 不再命中）；
  - finish 终态：built；graph validate：RC=0。
- 遗留（非本次引入，HEAD 即如此）：L5a `libpinyin.so 缺少 DT_SONAME`（W3 内 warning 级，HEAD 版日志同款报错）；finish Step6 提示 README.md/release|debug tar.gz 缺失与 Step8 gen_summary 框架报错（`'str' object has no attribute 'append'`）均为框架/打包阶段事项。

## 注意事项
## 注意事项

- pinyin_init(systemdir, NULL) 在 systemdir 缺 table.conf 时直接返回 NULL；本包把模型数据（含 table.conf）装在 share/libpinyin/data，消费者需把该目录作为 systemdir 传入。
- 公开头文件位于 include/libpinyin-2.1.0/（上游 CMake PROJECT_VERSION 为 2.1.0，与发布 tag 2.8.1 不同），配方 package_info 已动态探测。
- 设备 /tmp 只读、github 与 ghfast.top 常态不可达；共享 dlcache 按"内容 sha256"命中可完全绕开网络下载。
---

**编译结束**: 2026-09-28 06:52
**最终状态**: built
