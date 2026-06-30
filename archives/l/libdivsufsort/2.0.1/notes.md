# libdivsufsort 2.0.1 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-06-29
- 编译器: clang 15.0.4 / clang++ 15.0.4
- 状态: built

## 编译步骤

1. **源码下载**: GitHub 直连超时，改用 codeload.github.com 镜像下载
2. **init-build**: `ohc-run.py init-build libdivsufsort 2.0.1 --url=... --no-download`（源码已手动下载解压）
3. **cmake 配置**:
   ```bash
   cd $BUILD_SRC_DIR && mkdir build && cd build
   cmake .. -DCMAKE_INSTALL_PREFIX=$DEFAULT_PREFIX -DBUILD_SHARED_LIBS=OFF -DCMAKE_POLICY_VERSION_MINIMUM=3.5
   ```
4. **编译**: `make -j1` — 生成 libdivsufsort.a + 5个示例程序
5. **安装**: `make install DESTDIR=$TEST_PREFIX` — 安装到 staging 区
6. **测试**: 运行示例程序 + 链接测试全部通过
7. **conan-init**: 生成 conanfile.py + conandata.yml + test_package/
8. **conanfile.py 修复**: 从 Autotools 模板改为 CMake 模板，补充 sha256
9. **conan-verify**: 8道门禁全部通过（G0-G4 + L2/L4/L5）
10. **finish**: 状态 built（conan-verify 通过，缺少 test-report 已补充）

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | GitHub 直连下载超时 | github.com 网络不可达 | 改用 codeload.github.com 镜像下载 |
| 2 | CMake 配置失败 | CMake 4.x 移除了对 cmake_minimum_required < 3.5 的兼容 | 添加 -DCMAKE_POLICY_VERSION_MINIMUM=3.5 |
| 3 | conan-init 生成 Autotools 模板 | init-build 误检测构建系统为 autotools | 手动重写 conanfile.py 为 CMake 工具链 |
| 4 | conandata.yml sha256 占位符 | conan-init 未自动计算 sha256 | 手动填入实际值 9164cb6044... |
| 5 | G2 conan create 首次失败 | CMAKE_POLICY_VERSION_MINIMUM 通过 tc.variables 设置无效 | 改用 tc.cache_variables 作为 -D 参数传递 |
| 6 | finish 降级为 built | 缺少 test-report.md 和 .staging-verified | 补充真实测试报告和 staging 验证标记 |

## 源码修改

无源码修改，无补丁。

## 依赖版本

无外部依赖。

## 验证结果

### 示例程序测试
```bash
$ ./examples/suftest /tmp/suftest_input.txt
sufcheck: Done.                          # ✅ 通过

$ ./examples/bwt input.txt bwt.txt       # ✅ 通过
$ ./examples/unbwt bwt.txt unbwt.txt     # ✅ 还原内容正确
$ ./examples/sasearch "world" input.txt sa.txt  # ✅ 找到位置 6
```

### 静态库链接测试
```bash
$ clang -I$STAGING/include test.c $STAGING/lib/libdivsufsort.a -o test
$ ./test
Suffix array of "banana": 5 3 1 0 4 2    # ✅ 正确
divsufsort: OK
```

### conan-verify 8道门禁
- G0 预构建风险评估: ✅ PASS
- G1 配方完整性: ✅ PASS
- G2 conan create 干净构建: ✅ PASS
- G3 静态链接验证: ✅ PASS
- G4 产物完整性: ✅ PASS
- L2 smoke test: ✅ PASS
- L4 安全扫描: ✅ PASS
- L5 产物基线: ✅ PASS

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| lib/libdivsufsort.a | 35750 bytes | 静态库（AArch64） |
| include/divsufsort.h | 5442 bytes | 头文件 |
| lib/pkgconfig/libdivsufsort.pc | - | pkg-config 文件 |

## 注意事项

- CMake 4.x 需要 `-DCMAKE_POLICY_VERSION_MINIMUM=3.5` 参数
- conanfile.py 中该参数必须用 `tc.cache_variables` 而非 `tc.variables`
- 库名为 divsufsort（非 libdivsufsort），cpp_info.libs = ["divsufsort"]
- GitHub 直连不可达时可用 codeload.github.com 镜像
---

**编译结束**: 2026-06-30 11:51
**最终状态**: published
