# assimp 6.0.5 编译笔记（HarmonyOS PC · 标准 Conan cmake）

## 定位
- 产出动态 libassimp.so，供 dlopen 及作依赖。

## 关键适配
- （填：系统识别 / umask / 子包 / zipfs / 签名等）

## 状态
built（CI conan create + test 通过）

## conan 化要点

conan 化（该目录原有一份别人手工编译的存档笔记，已保留并并入附录）。zlib 走制品仓现有的纯静态包（只有 libz.a），故静态嵌入 libassimp.so —— 与上游 wheel 链 libz.so.1 不同但功能等价。test_package 11 条断言：内存喂 OBJ 解析、网格/面/顶点数、逐点坐标与包围盒对账、错误路径。

---

<details>
<summary>本目录原有的手工编译笔记（保留，未改动）</summary>

# assimp 6.0.5 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-05-29
- 编译器: clang/clang++
- 状态: built

## 编译步骤

本次编译使用 GNU ld.bfd 链接器替代 OHOS SDK 的 lld 链接器，解决 libxml2.so.16 加载问题。

1. 创建链接器 wrapper：
   ```bash
   mkdir -p $HOME/tmp/ld-wrapper
   cat > $HOME/tmp/ld-wrapper/ld.lld << 'EOF'
   #!/bin/sh
   exec /data/service/hnp/bin/ld.bfd "$@"
   EOF
   chmod +x $HOME/tmp/ld-wrapper/ld.lld
   ```

2. 配置 CMake（使用 -B 选项指定链接器）：
   ```bash
   cmake .. \
     -DCMAKE_BUILD_TYPE=Release \
     -DCMAKE_INSTALL_PREFIX=/storage/Users/currentUser/usr/local \
     -DCMAKE_C_COMPILER_FLAGS="-B $HOME/tmp/ld-wrapper -fPIC -O2" \
     -DCMAKE_CXX_COMPILER_FLAGS="-B $HOME/tmp/ld-wrapper -fPIC -O2" \
     -DCMAKE_EXE_LINKER_FLAGS="-L/storage/Users/currentUser/usr/local/lib -B $HOME/tmp/ld-wrapper" \
     -DCMAKE_SHARED_LINKER_FLAGS="-L/storage/Users/currentUser/usr/local/lib -B $HOME/tmp/ld-wrapper" \
     -DASSIMP_BUILD_M3D_EXPORTER=OFF \
     -DASSIMP_BUILD_M3D_IMPORTER=OFF \
     -DASSIMP_BUILD_USD_IMPORTER=OFF \
     -DASSIMP_BUILD_VRML_IMPORTER=OFF \
     -DASSIMP_HUNTER_ENABLED=OFF
   ```

3. 编译和安装：
   ```bash
   make -j4
   make install DESTDIR=$TEST_PREFIX
   make install
   ```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | OHOS SDK lld 无法加载 libxml2.so.16 | lld 链接器与 OHOS SDK 动态库加载机制不兼容 | 创建 ld.lld wrapper，使用 GNU ld.bfd 替代 |

## 源码修改

无源码修改，使用标准 cmake 配置。

## 依赖版本

- zlib (系统预装)
- clang 15.0.4
- cmake 4.1.2

## 验证结果

```bash
# pkg-config 验证
pkg-config --modversion assimp
6.0.5

# 库文件检查
ls -lh /storage/Users/currentUser/usr/local/lib/libassimp.so
-rwxrwx--- 1 20001006 file_manager 12M 2026-05-29 19:09 libassimp.so

# 链接器信息
readelf -p .comment libassimp.so
OHOS (dev) clang version 15.0.4
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| assimp-6.0.5-ohos-aarch64.tar.gz | 13M | 预编译包（包含 libassimp.so、头文件、pkg-config） |

## 注意事项

1. **链接器问题**：OHOS SDK 的 lld 链接器可能无法加载某些动态库（如 libxml2.so.16），需要使用 GNU ld.bfd 替代。解决方案是创建 wrapper 目录，使用 -B 选项指定链接器路径。
2. **CMake 构建系统**：assimp 使用 CMake，G0 干净构建验证脚本默认尝试运行 ./configure 会失败，这是正常的。
3. **禁用特性**：编译时禁用了 M3D、USD、VRML 等导入导出器，减少编译依赖和大小。
---

**编译结束**: 2026-05-29 19:12
**最终状态**: built

</details>
