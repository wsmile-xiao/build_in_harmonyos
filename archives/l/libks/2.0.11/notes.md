# libks 2.0.11 编译笔记

## 编译开始

**时间**: 2026-06-03 17:25
**源码**: ~/builds/libks-2.0.11.tar.gz (已存在)

## 编译过程

### 1. cmake 配置

**命令**:
```bash
cd ~/builds/libks-2.0.11.work/build
cmake .. -DCMAKE_INSTALL_PREFIX=$HOME/usr/local -DCMAKE_BUILD_TYPE=Release -DOPENSSL_ROOT_DIR=$HOME/usr/local
```

**问题1**: cmake 找不到 OpenSSL
- **原因**: OpenSSL pkg-config 文件 (openssl.pc, libssl.pc, libcrypto.pc) 指向旧路径 `~/tmp/test-install-openssl-1.1.1w`
- **解决**: 修复三个 pkg-config 文件的 prefix 为 `$HOME/usr/local`

**问题2**: cmake 找不到 LibM
- **原因**: HarmonyOS 中 libm 集成在 libc 中，FindLibM.cmake 模块找不到 math.h 和 libm.so
- **解决**: 修改 cmake/FindLibM.cmake，直接创建空的 LIBM::LIBM 接口库

### 2. make 编译

**命令**:
```bash
make -j4
```

**问题3**: 找不到 libatomic
- **原因**: HarmonyOS 中没有 libatomic 库
- **解决**: 修改 CMakeLists.txt 第 567 行，移除 atomic 库链接

**编译结果**: 成功 (100%)

### 3. make install

**命令**:
```bash
make install DESTDIR=$HOME/tmp/test-install-libks-2.0.11
```

**安装结果**: 成功
- 库文件: libks2.so (192KB, stripped)
- 头文件: libks2/*.h
- pkgconfig: libks2.pc

### 4. 预编译包制作

**手动打包步骤**:
1. 收集依赖库到 lib/external/
2. Strip 符号 (llvm-strip)
3. ELF 签名 (ohc-run.py sign-elf)
4. 创建 tar.gz 包

**产物**: libks-2.0.11-ohos-aarch64.tar.gz (3.7MB)

## 编译结束

**时间**: 2026-06-03 17:35
**状态**: built
**产物路径**: ~/archives/l/libks/2.0.11/packaging/libks-2.0.11-ohos-aarch64.tar.gz

## 最终状态

**状态**: built