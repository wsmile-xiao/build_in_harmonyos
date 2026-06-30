# cspice 67 适配笔记

## 编译环境
- 构建系统: makefile（自定义 Makefile，非 autotools）
- 编译日期: 2026-06-29
- 编译器: clang 15.0.4
- 平台: HarmonyOS (ohos-aarch64)
- 状态: published

## 编译步骤

1. **源码获取**: NAIF 官网不可达，改用 GitHub 镜像 (arturania/cspice) 下载 60.8MB 源码包
2. **init-build**: 使用 `--no-download` 模式，手动设置 .orig/.work 目录，手动创建 .build-context 文件
3. **编译**: 在源码根目录创建自定义 Makefile，编译全部 2151 个 .c 文件
   ```bash
   cd $BUILD_SRC_DIR
   make CC=clang CFLAGS="-fPIC -O2" -j1
   ```
4. **安装**: `make install DESTDIR=$TEST_PREFIX PREFIX=""`
5. **测试**: 编写 smoke test 程序链接静态库，验证 API 调用正确
6. **Conan 配方**: conan-init 生成骨架，手动修正为自定义构建配方

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | NAIF 官网连接超时 | 网络环境限制 | 改用 GitHub 镜像 arturania/cspice |
| 2 | GitHub 镜像无 Makefile | 该仓库仅包含源码，不含构建脚本 | 在 conanfile.py 的 build() 中动态生成 Makefile |
| 3 | f2c.h 找不到 | CFLAGS 环境变量覆盖了 Makefile 中的 -I./include | 将 INCLUDES 分离为独立变量，不使用 ?= 赋值 |
| 4 | CMakeDeps 找不到库 | 库名 cspice.a 缺少 lib 前缀，CMake 期望 libcspice.a | 重命名为 libcspice.a |
| 5 | Makefile 中 \t 被写入为字面量 | Python save() 中使用转义字符串 | 改用列表 + "\n".join() 生成正确 TAB 字符 |
| 6 | conan create 下载 GitHub 超时 (E017) | 中国大陆网络环境 GitHub 访问不稳定 | 使用 ghfast.top 代理 URL |
| 7 | init-build SSL 证书检查挂起 | 证书下载步骤网络超时 | 手动创建 .build-context 文件继续编译 |

## 源码修改

### 0001-Makefile.patch
- **文件**: Makefile（新增）
- **说明**: 源码包不包含 Makefile，新增自定义 Makefile 用于编译全部 src/*.c 到 libcspice.a 静态库
- **分类**: platform_only（平台适配）
- **内容**:
  - 定义 CC/AR/CFLAGS 变量
  - INCLUDES = -I./include（分离以避免环境变量覆盖）
  - 编译规则: `$(CC) $(CFLAGS) $(INCLUDES) -c $< -o $@`
  - 归档: `$(AR) $(ARFLAGS) libcspice.a $^` + `ranlib`
  - install/check/clean 目标

## 依赖版本

无外部依赖。cspice 是完全自包含的 C 库。

## 验证结果

### make check
```bash
$ make check
Build successful - libcspice.a created
```

### Smoke Test
```bash
$ clang -fPIC -O2 -I./include -o test_cspice_smoke test_cspice_smoke.c lib/cspice.a -lm
$ ./test_cspice_smoke
[TEST1] pi_c() = 3.141592653589793
[TEST2] halfpi_c() = 1.570796326794897
[TEST3] twopi_c() = 6.283185307179586
[TEST4] clight_c() = 299792.458 km/s
[PASS] pi 值验证通过
```

### Conan test_package
```
cspice pi() = 3.141592653589793
test cspice 67: OK
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| lib/cspice.a | 9.5MB | 静态库（2151 个 .o 文件归档） |
| include/*.h | 35 个文件 | 头文件（含 SpiceUsr.h, f2c.h 等） |

## 注意事项

1. cspice 源码包含 f2c 生成的 Fortran-to-C 转换代码，部分文件有 deprecated non-prototype 警告，不影响功能
2. 库名使用 `libcspice.a`（带 lib 前缀）以满足 CMake/Conan 的命名约定
3. 原始 NAIF 包中库名为 `cspice.a`（无 lib 前缀），如需兼容可创建符号链接
4. conandata.yml 中的 URL 使用 ghfast.top 代理以解决中国大陆 GitHub 访问问题
---

**编译结束**: 2026-06-30 15:38
**最终状态**: published
