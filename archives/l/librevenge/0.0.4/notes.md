# librevenge 0.0.4 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-06-29
- 编译器: clang/clang++
- 状态: published

## 编译步骤

1. init-build 下载解压 librevenge-0.0.4.tar.gz
2. 复制系统 automake-1.17 的 config.guess/config.sub 替换原始版本（E007 平台识别）
3. 修补 configure.ac 添加 -Wno-error=shadow（boost spirit headers 触发 -Wshadow 被 -Werror 拦截）
4. 修补 RVNGStringIterTest.cpp 添加 #include <cassert>
5. 修改 configure 中 umask 077→022（HarmonyOS FS 限制，目录权限 drwx--S--- 无法创建文件）
6. autoreconf -fi 重新生成 configure
7. ./configure --prefix=$DEFAULT_PREFIX --enable-static --disable-shared
8. make -j1
9. make install DESTDIR=$TEST_PREFIX
10. make check（通过）
11. conan-init 生成 conanfile.py + conandata.yml + test_package/
12. conan-verify 8 道门禁全部通过
13. finish 标记 published

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | config.guess/config.sub 不识别 aarch64-unknown-linux-ohos | GNU config 不含 OHOS 检测分支 (E007) | 复制 automake-1.17 版本替换 |
| 2 | boost spirit headers 触发 -Wshadow 被 -Werror 拦截 | boost 代码与 librevenge 代码变量名冲突 | configure.ac 添加 -Wno-error=shadow |
| 3 | umask 077 创建目录权限 drwx--S--- | HarmonyOS FS 限制 | 修改 configure 中 umask 077→022 |
| 4 | RVNGStringIterTest.cpp 缺少 #include <cassert> | 源码遗漏头文件 | 添加补丁 0031 |
| 5 | SSL 证书问题导致 Conan 下载失败 | 系统证书链不完整 | 设置 REQUESTS_CA_BUNDLE 和 SSL_CERT_FILE |
| 6 | conandata.yml verify_ssl 无效参数 | Conan 2.x 不支持该字段 | 移除 |
| 7 | test_package CMake 生成器 "Make" 无效 | 默认生成器名错误 | 显式设置 generator = "Unix Makefiles" |
| 8 | CMakeDeps 找不到库 (liblibrevenge-0.0.a) | cpp_info.libs 含 lib 前缀 | 去除前缀 |
| 9 | test_package 找不到头文件 | includedirs 路径不完整 | 添加 include/librevenge-0.0 |

## 源码修改

- patches/0009-configure.ac.patch: configure.ac 添加 -Wno-error=shadow
- patches/0031-src-test-RVNGStringIterTest.cpp.patch: 添加 #include <cassert>
- config.guess/config.sub: build() 中从 automake-1.17 复制替换（非补丁方式）
- configure umask 077→022: build() 中字符串替换（非补丁方式）

## 依赖版本

- boost: 系统预装 (header-only, spirit classic)
- zlib: 系统预装
- automake-1.17: 用于 config.guess/config.sub

## 验证结果

```
conan-verify: PASS (G0-G4 + L2/L4/L5 全部通过)
make check: PASS (1 suite, 1 pass, 0 fail, 0 skip)
功能测试: PASS (55/55, 100% 通过率)
产物: 3 .a (librevenge-0.0.a, librevenge-generators-0.0.a, librevenge-stream-0.0.a) + 31 .h
Conan 包: librevenge/0.0.4@ohpcd/stable
```

## 功能测试结论

librevenge 0.0.4 在鸿蒙平台上通过完整功能验证（55 项测试全部通过），确认可在鸿蒙平台正常使用。

### 测试覆盖
- RVNGString: 字符串操作、UTF-8多字节字符、XML转义、迭代器、比较运算 (13项)
- RVNGStringVector: 向量操作、索引访问、拷贝 (5项)
- RVNGPropertyList: 多类型属性插入(int/bool/double/string)、遍历、删除、序列化 (11项)
- RVNGBinaryData: 数据追加、Base64编解码、缓冲区读取 (8项)
- RVNGStringStream: 内存流读取/seek/EOF检测 (6项)
- RVNGFileStream: 鸿蒙文件系统I/O验证 (5项)
- RVNGSVGDrawingGenerator: SVG端到端生成(矩形/椭圆/文本/多页面) (4项)
- 跨模块集成: BinaryData→Stream、PropertyList+SVG、1000属性压力测试 (3项)

### 发现的注意事项
- drawEllipse 方法需要 svg:cx/cy/rx/ry（中心坐标+半径）属性，而非 svg:x/y/width/height
- 鸿蒙文件系统 I/O 完全兼容，RVNGFileStream 读写/seek/EOF 检测均正常
- UTF-8 多字节字符（如中文）的 len() 计数正确，迭代器遍历正常
- 静态链接后库体积合理：librevenge-0.0.a (433KB) + generators (993KB) + stream (219KB)

## 注意事项

- boost 和 zlib 为系统预装，requirements() 暂为空。当 @ohpcd/stable 版本可用后应添加依赖引用 (R27)
- 32 个补丁中仅 2 个源文件补丁在 conandata.yml 中引用，其余为生成文件快照（R6: 不补丁生成文件）
- drawEllipse API 需要 svg:cx/cy/rx/ry 属性，下游软件需注意此接口约定

---

**编译结束**: 2026-06-29 11:51
**最终状态**: published
