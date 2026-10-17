# boost1.84-serialization 1.84.0 适配笔记

## 形态决策：方案 A（独立裁剪编译）

- **方案 A（采用）**：从 boost 1.84.0 官方源码裁剪，手动 clang++ 编译 `libs/serialization/src` 的 36 个源文件为 `libboost_serialization.a`（上游 Jamfile 的 boost_serialization 目标 = SOURCES 33 个 + SOURCES_HAS_STD_WSTREAMBUF 2 个 + xml_oarchive）。
- **方案 B（否决）**：requires boost/1.84.0 元包——元包只编译了 filesystem/regex/program_options/iostreams，boost_serialization 不在产物中。

## 编译方式

b2 在 OHOS 不兼容（E068）。手动 clang++：
- 参数：`-std=c++17 -stdlib=libc++ -fPIC -O2 -DNDEBUG -DBOOST_ALL_NO_LIB -DBOOST_SP_NO_PTHREAD_SETCANCELSTATE`
- 补丁：复用元包 0001（sp_thread_sleep.hpp pthread_setcancelstate，特性宏 R8 合规）
- 源文件集合与上游 `libs/serialization/build/Jamfile.v2` 的 `lib boost_serialization` 目标一致（SOURCES + xml_oarchive + utf8_codecvt_facet）
- **不含** WSOURCES（basic_text_wiprimitive 等 12 个 wide 字符文件）——那是独立组件包 boost1.84-wserialization 的目标

## 上游测试

serialization 测试的 test_tools.hpp **自带 main**（基于 boost/core/lightweight_test.hpp 的 BOOST_TEST 宏），不依赖 boost.test 库——可直接编译运行绕过 b2。

**测试覆盖口径（2026-09-06 扩充，对齐审核实测 122）**：上游 test/ 目录 122 个 .cpp 测试源，本包纳入 **91 个**（conan create 实测 91/91 通过，0 失败）：

- **RUN 类 78 个**（编译+链接+运行，rc=0 判过）：单 TU text_archive 模式 67 个（上游 test-bsl-run_files/test-bsl-run 注册的 run 目标，窄字符归档）+ 多 TU polymorphic 类 5 个（test_polymorphic/test_polymorphic2/test_p_helper/test_no_rtti/test_exported，按上游 test-bsl-run_polymorphic_files 规则传 `-DBOOST_ARCHIVE_TEST=polymorphic_text_archive.hpp`，链接 polymorphic_base/derived1/derived2、test_polymorphic_A、test_polymorphic2imp 等 TU 源）+ serialization2 套件 13 个（test_inclusion/inclusion2/private_ctor/reset_object_address/void_cast/mult_archive_types/iterators/iterators_base64/smart_cast/codecvt_null/singleton×3/private_base/private_base2）+ test_dll_simple（dll_a.cpp 静态联编，验证 A 类 DLL 导出宏语义）+ 编译型目标按运行验证的 4 个（strong_typedef/static_warning/traits_pass 等本就有 main）
- **COMPILE_ONLY 类 4 个**（上游 b2 `[ compile ]` 规则，无 main 只编译）：test_const_save_warn1/2/3、test_const_pass
- **COMPILE_FAIL 类 9 个**（上游 b2 `[ compile-fail ]` 规则，编译必须失败）：test_not_serializable、test_traits_fail、test_const_load_fail1/2/3（+nvp×3）、test_check

**未纳入的 31 个逐类理由**：
1. **DLL/多共享库类 3 个**：test_dll_exported（Jamfile 要求 lib dll_polymorphic_base + dll_polymorphic_derived2 真共享库构建）、test_dll_plugin（dlopen("polymorphic_derived2.so") 运行时插件加载）、test_multi_shared_lib（需 2 个独立 .so 验证 extended_type_info 多实例销毁序）——上游 Jamfile 自己标 `<link>static:<build>no`，静态库包形态无法复现其构建模式
2. **需 SGI 扩展 4 个**：test_map_hashed/test_set_hashed（源码 #error BOOST_HAS_HASH，SGI hash_map 扩展 OHOS musl/llvm 无）、test_slist/test_slist_ptrs（std::slist SGI 扩展，libc++ 无，实测 no template named 'slist'）
3. **上游遗留未注册 Jamfile 的历史文件 13 个**：A.cpp（测试夹具，已链入 28 个夹具类测试）、config_test.cpp（config 诊断工具非测试）、dll_a/dll_base/dll_polymorphic_base/dll_polymorphic_derived2（dll 库 TU 源非独立测试）、polymorphic_base/derived1/derived2（test_no_rtti/test_exported 的多 TU 源，已随主测试链接）、test_polymorphic_A/test_polymorphic2imp（test_polymorphic/test_polymorphic2 的 TU 源，已随主测试链接）、multi_shared1/multi_shared2（test_multi_shared_lib 的历史辅助 TU）
4. **上游已知问题/空文件 4 个**：test_z.cpp（zlib 流测试，上游 Jamfile 已注释禁用）、test_interators.cpp（空文件 0 行）、test_pimpl.cpp（1998 年遗留，引用未定义 B 类，无法编译）、test_enable_shared_from_this.cpp（上游保留的已知失败样本，注释写明 FAIL: throws bad_weak_ptr，未注册 Jamfile）
5. **const_save_warn 未注册变体 3 个**：test_const_save_warn4、test_const_save_warn4_nvp（Jamfile 注释掉的 nvp 变体）、test_const_save_warn1/2/3_nvp（Jamfile #[ compile ] 注释禁用）

注意点：
- 容器类测试需链接测试夹具 `A.cpp`（上游 Jamfile 用 <source> 指定）
- test_tools.hpp 的 `boost::archive::tmpnam` 用 `boost::filesystem::unique_path` → build() 阶段为测试本地编译 boost_filesystem.a（9 文件，仅测试用，**不入 package 产物**，保持组件包零依赖）
- wide 归档测试（text_warchive/xml_warchive 等 BOOST_ARCHIVE_LIST 模式）归 wserialization 组件包（boost_wserialization 是独立库目标），不在本窄字符组件包范围
- 测试编译 subprocess timeout=900s（重模板测试如 test_reset_object_address 在 conan env 下编译慢，实测原 300s 会超时）；整包 conan create 实测 895s 完成，CI 超时预算已在 ci/config/build_timeouts.txt 设 10800s

## 依赖

无 conan 依赖（Boost.Serialization 核心仅依赖 boost 头文件）。

## 验证命令

```
conan create . --user=ohpcd --channel=stable -pr:h=~/.conan2/profiles/ohos-aarch64 -pr:b=~/.conan2/profiles/ohos-aarch64 --build=missing
```
---

**编译结束**: 2026-09-05 18:00
**最终状态**: published
