# boost1.84-wserialization 1.84.0 适配笔记

## 组件定位

Boost.Wserialization 是 Boost.Serialization 的宽字符（wchar_t）archive 扩展：
`text_wiarchive/text_woarchive`、`xml_wiarchive/xml_woarchive` 及其 polymorphic
包装。上游以 `libboost_wserialization` 发布，链接依赖 `libboost_serialization`。

本包以独立包名 `boost1.84-wserialization` 归档（积分赛任务 6079），与
`boost/1.84.0` 元包并行维护。

## 编译环境
- 构建系统: 手动 clang++ 编译（b2 在 OHOS 不兼容，E068）
- 编译日期: 2026-09-05
- 编译器: clang/clang++ 15.0.4 (aarch64-unknown-linux-ohos)
- 状态: built

## 源集定义（上游 libs/serialization/build/Jamfile.v2）

| 段 | 文件数 | 归属 |
|---|--------|------|
| SOURCES（窄字符核心） | 33 | libboost_serialization |
| SOURCES_HAS_STD_WSTREAMBUF | 2（xml_oarchive, utf8_codecvt_facet） | libboost_serialization（musl 有 std::wstreambuf，直接编译） |
| WSOURCES（宽字符） | 11 | libboost_wserialization |

合计 46 个 .cpp，全部编译成功（0 失败）。

## 编译命令

```bash
# conan create（W3 验证）等价的手动命令
clang++ -std=c++17 -stdlib=libc++ -O2 -DNDEBUG -fPIC \
  -I<boost_root> \
  -DBOOST_ALL_NO_LIB -DBOOST_SYSTEM_NO_DEPRECATED \
  -DBOOST_SP_NO_PTHREAD_SETCANCELSTATE \
  -c libs/serialization/src/<src>.cpp -o <obj>
llvm-ar rcs libboost_serialization.a <35 objs>
llvm-ar rcs libboost_wserialization.a <11 objs>

# 消费者测试（宽字符往返）
clang++ ... test_wserialization.cpp \
  libboost_wserialization.a libboost_serialization.a -o test_wser && ./test_wser
# → text_woarchive/text_wiarchive round-trip OK (id=42)
# → xml_woarchive/xml_wiarchive round-trip OK
# → boost_wserialization: all wide-char archive round-trips OK (rc=0)
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 26 个源文件报 `use of undeclared identifier 'pthread_setcancelstate'` | OHOS musl 无此 API；sp_thread_sleep.hpp 在 BOOST_HAS_PTHREADS 下直接调用 | 应用 0001 补丁（加 BOOST_SP_NO_PTHREAD_SETCANCELSTATE 特性检测宏守卫，R8 合规）+ 编译期 -D 注入 |
| 2 | b2 无法构建 | Boost.Build SHELL 执行机制在 OHOS 失败（E068） | 手动 clang++ 编译 Jamfile.v2 定义的源集，llvm-ar 打包 |
| 3 | 链接测试二进制运行时缺 libc++_shared.so | 交叉编译产物需 OHOS libc++ 运行时 | LD_LIBRARY_PATH 指向 sysroot；conan test_package 由 Conan 运行环境自动处理 |

## 源码修改
仅上游头文件补丁 0001（与 boost/1.84.0 配方完全相同的补丁）；未修改其他源码。

## 依赖版本
- 无 conan 依赖（boost 序列化不依赖 zlib；zlib 仅 iostreams 需要）
- 运行时依赖：libc++（OHOS sysroot）
