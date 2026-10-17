# libid3tag 0.16.3 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-05-21
- 编译器: clang/clang++
- 状态: published

## 编译步骤

1. **init-build**: 使用 --no-download 手动下载 tarball（Debian pool mirror，Savannah SSL/超时不可用）
2. **CMake configure**:
   ```bash
   mkdir -p build && cd build
   cmake -DCMAKE_INSTALL_PREFIX=$DEFAULT_PREFIX \
         -DBUILD_SHARED_LIBS=ON \
         -DCMAKE_POLICY_VERSION_MINIMUM=3.5 \
         ..
   ```
3. **Build**: `make -j1` — 成功，仅有指针类型警告（char/unsigned char 混用）
4. **Install (DESTDIR)**: `make install DESTDIR=$TEST_PREFIX` — 安装 libid3tag.so, id3tag.h, id3tag.pc, cmake configs
5. **Tests**: `ctest` — 无测试套件；编写 C 测试程序进行真实验证（9 项测试、67 断言，全部 PASS），详见 `reports/test-report.md`
6. **Verify**: G1-G4 全部 PASS
7. **Package**: libid3tag-0.16.3-ohos-aarch64.tar.gz (258KB)
8. **Local install**: `make install` — 安装到 ~/usr/local
9. **Finish**: published

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | Savannah 下载超时/404 | Savannah 镜像在当前环境不可达 | 使用 Debian pool mirror: ftp.debian.org |
| 2 | SSL 证书验证失败 | 系统缺少 CA 证书 | 使用 install-ca-certs.py + SSL_CERT_FILE 环境变量 |
| 3 | CMake 兼容性错误 | cmake_minimum_required(3.1) 与 CMake 4.x 不兼容 | 添加 -DCMAKE_POLICY_VERSION_MINIMUM=3.5 |
| 4 | init-build 误判为 autotools | 项目只有 CMakeLists.txt，无 configure | 手动更新 manifest.yaml build_system=cmake |
| 5 | G0 clean-verify 失败 | clean-verify 只支持 autotools ./configure | 创建 hints/configure.sh cmake wrapper；G0 已手动验证通过 |

## 源码修改

无补丁，无源码修改。

## 依赖版本

- zlib/1.3.1（预装于 ~/usr/local）

## 验证结果

```bash
# pkg-config 验证
pkg-config --modversion id3tag  → 0.16.3
pkg-config --libs id3tag        → -L/storage/Users/currentUser/usr/local/lib -lid3tag -lz
pkg-config --cflags id3tag      → -I/storage/Users/currentUser/usr/local/include

# 文件验证
ls ~/usr/local/lib/libid3tag*   → libid3tag.so (182656 bytes)
ls ~/usr/local/include/id3tag.h → id3tag.h (10650 bytes)
ls ~/usr/local/lib/pkgconfig/id3tag.pc → id3tag.pc
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| libid3tag-0.16.3-ohos-aarch64.tar.gz | 258KB | 预编译包（含 .so, .h, .pc, cmake configs） |
| libid3tag-0.16.3-ohos-aarch64-debug.tar.gz | 45KB | debug 符号包 |

## 注意事项

- libid3tag 0.16.3 使用 CMake 构建系统，不是 autotools
- G0 clean-verify 需要 hints/configure.sh wrapper 支持 CMake
- 编译产物只有 .so（共享库），无 .a（静态库）
- 原始下载 URL Savannah 不可用，需用 Debian mirror 替代
- CMake 需要添加 -DCMAKE_POLICY_VERSION_MINIMUM=3.5 才能兼容

---

**编译结束**: 2026-05-21 16:56
**最终状态**: published

---

## Conan 2 recipe 适配 (2026-09-02)

### 新增文件
- `conandata.yml` — 官方源码 URL (Debian pool) + SHA256
- `conanfile.py` — Conan 2 recipe (CMakeDeps + CMakeToolchain)
- `test_package/` — 消费者侧测试 (CMakeLists.txt, conanfile.py, test.c, MANIFEST.yml)

### 零 patch 声明
无源码补丁。两个构建细节在 recipe 内处理（非源码 bug，不构成 patch）：
1. `CMAKE_POLICY_VERSION_MINIMUM=3.5` — CMake 4.x 与 `cmake_minimum_required(3.1)` 兼容
2. `replace_in_file(ZLIB::ZLIB → zlib::zlib)` — 上游 CMakeLists 的目标名与 Conan CMakeDeps 生成名不一致，属 Conan 集成细节

### test_package 断言清单 (18 项)
tag 创建 → TIT2 frame 挂载 → UTF-8 编码设置 → UCS-4 字符串添加 → 两遍 render → query/parse 回读 → findframe → UTF-8 duplicate 比对 → ID3 magic 校验

### 上游测试核验
上游 tarball 无 tests/ 目录、无 enable_testing()/add_test()、无 check target；官方 CI (Codeberg) 仅执行 configure/build/install。**上游无正式测试套件**，test_package 为唯一运行时验证。

### 验证证据 (OHOS AArch64)
- compiler: clang 15.0.4 `--target=aarch64-unknown-linux-ohos`
- library: ELF64 AArch64 (`elf64-littleaarch64`)
- test binary: `ELF shared object, 64-bit LSB arm64, dynamic (/lib/ld-musl-aarch64.so.1)`
- conaninfo: `os=OHOS, arch=armv8, compiler=clang`
- scoped CI: `CI_PACKAGES="archives/l/libid3tag/0.16.3" CONAN_PROFILE="ohos-aarch64-local"` → L0/L1/L4/L5 全 pass，18 断言全 PASS
