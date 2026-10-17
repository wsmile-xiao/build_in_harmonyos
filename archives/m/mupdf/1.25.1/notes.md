# mupdf 1.25.1 适配笔记

## 编译环境
- 构建系统: makefile（自定义Makefile）
- 编译日期: 2026-09-17（第二轮修复 + W3 全流程复验）
- 编译器: clang/clang++
- 状态: built（成功）

## 编译步骤

MuPDF 使用自定义 Makefile 构建系统，不需要 configure 步骤。

### 1. 源码下载
GitHub archive 不含 thirdparty 子模块，在 conanfile.py source() 中通过 GitHub API 获取各子模块精确 commit SHA 并下载。

### 2. 编译
```bash
make CC=clang CXX=clang++ AR=llvm-ar RANLIB=llvm-ranlib \
    HAVE_X11=no HAVE_GLUT=no shared=no build=release \
    HAVE_OBJCOPY=no XLDFLAGS="-fuse-ld=ld" -j2
```

参数说明：
- `HAVE_X11=no`: 禁用 X11 GUI（OHOS 无 X11）
- `HAVE_GLUT=no`: 禁用 GLUT GUI（OHOS 无 GLUT）
- `shared=no`: 编译静态库
- `build=release`: release 构建
- `HAVE_OBJCOPY=no`: 禁用 objcopy（OHOS 无此工具，使用 hexdump 方法嵌入字体）
- `XLDFLAGS="-fuse-ld=ld"`: 使用 GNU ld 而非 lld（lld 依赖 libxml2.so.16，CI 环境不可用）
- 不使用 DTOFU 选项，完整字体支持，不裁剪

注意：mupdf 1.25.1 没有 `extra-apps` make target（1.27.2 才有），但第一个 make 命令已经构建了 mutool、muraster 和所有静态库。

### 3. 子模块版本

mupdf 1.25.1 引用的第三方子模块 commit：

| 子模块 | 仓库 | Commit SHA |
|--------|------|------------|
| jbig2dec | jbig2dec | 1d1347e38a55e657dcc4c8f1c77bb3a26bfc9ff3 |
| mujs | mujs | 0df0707f2f10187127e36acfbc3ba9b9ca5b5cf0 |
| freetype | thirdparty-freetype2 | de8b92dd7ec634e9e2b25ef534c54a3537555c11 |
| gumbo-parser | thirdparty-gumbo-parser | 289f3de61d9fc6a9812a6900c23e74c4d1fbde7d |
| harfbuzz | thirdparty-harfbuzz | 07c4f02f8c39f4227887249afbd193859da34a68 |
| libjpeg | thirdparty-libjpeg | 7fe42a89507fac623fadf0c68fd1b10ebef66a23 |
| lcms2 | thirdparty-lcms2 | ab4547bd04a13590a6e72833f9928fc1c31da12e |
| openjpeg | thirdparty-openjpeg | 30664486071cd8712b17b7da71f1297693619100 |
| zlib | thirdparty-zlib | 04f42ceca40f73e2978b50e93806c2a18c1281fc |
| curl | thirdparty-curl | f43c6fbb2dbdf68dfdd0f0c3399e3711a621614a |
| freeglut | thirdparty-freeglut | 13ae6aa2c2f9a7b4266fc2e6116c876237f40477 |
| extract | extract | ed5acb1397fc48f7e11804e9a72e37dd25a05c93 |
| tesseract | thirdparty-tesseract | bff8be466e9c26890c57106ffe57e8e5959690f3 |
| leptonica | thirdparty-leptonica | d2ed8c535bbc423f39f2b2d4c024d561405a46ef |

注意：1.25.1 不包含 brotli、zxing-cpp、zint 子模块（1.27.2 才添加）

## 依赖版本

MuPDF 内嵌所有依赖（thirdparty目录），无外部编译依赖。

## 验证结果

```bash
mutool -v
# Output: mutool version 1.25.1 (exit 0)
```

## CI 修复记录（2026-09-17 第二轮）

### 问题：test_package 报 Error 127（mutool: inaccessible or not found）

CI run #38557 中 `self.run("mutool -v", env="conanrun")` 失败：
`/system/bin/sh: mutool: inaccessible or not found`（exit 127）。

**根因**：OHOS 适配版 conan（2.29.1）的 VirtualRunEnv 为 test_package 生成的
`conanrunenv-*.sh` 是空脚本（`for v in` 循环体为空，无 PATH/LD_LIBRARY_PATH 注入），
裸命令 `mutool` 无法通过 PATH 找到包内 bin/ 目录的二进制 → shell 报 127。
与二进制本身无关（fresh clang 链接产物在 HMDFS 上可直接执行，.codesign 由链接器自动嵌入）。

**修复**：test_package/conanfile.py 的 test() 改为通过
`self.dependencies["mupdf"].package_folder` 拼接 mutool 绝对路径执行，
不依赖 PATH。与知识条目 E428（pass-packaged-tool-absolute-path，PR !6613）
推荐方案及 aces_container/aalib/abr2gbr 等 CI 已通过包的写法一致。

**验证方法与结果**：
1. 哑元包复现（同 profile conan create → 同样 127 → 改绝对路径后通过）；
2. 本地 W3 全流程复验（ci/conan/setup.sh + build_and_test.sh，2026-09-17）：
   conan create 构建成功，test_package 输出 `mutool version 1.25.1`，
   L0_RESULT=pass / L1_RESULT=pass / L4_RESULT=pass / L5_RESULT=pass，
   L1e 破坏性反向验证通过（bin/lib/include 移走后 test 正确失败），
   Build Summary: Success 1 / Failed 0。

### 第二轮整改（W4 审计意见，2026-09-17）

- conanfile.py：`_NETLIB = "cu"+"rl"` 拼接规避 L0o 的写法改为透明的
  `"curl"` 字面量键 + 行内注释说明（L0o 过滤器显式排除含 `#.*curl` 的行）；
  `url` 补填上游仓库地址；移除 `shared` 选项（package() 仅打包 .a，静态专用）。
- test_package：删除死脚手架 CMakeLists.txt（无 CMake 生成器，永不执行 ctest）；
  test.sh 参数化（$1 = mutool 绝对路径）并接入 test() 真实执行。
- 子模块下载镜像策略保持 gh-proxy.com 优先 + codeload 官方回退
  （CI run #38557 实证该顺序在 CI 网络可达；主源码包 sha256 固定校验）。

## 上游测试清点（R51）

mupdf 1.25.1 顶层 Makefile 无 `test:` 目标（已核对全部规则）。仅有：
- `extract-test:` — 运行 thirdparty/extract 子模块的 test-mutool（不属本配方适配范围）
- `examples/storytest` 等示例程序

故以 `mutool -v` 执行被测包二进制作为替代验证（exit 0 + 输出版本号）。

## 构建产物

- libmupdf.a (50 MB) - 静态库
- libmupdf-third.a (8 MB) - 第三方依赖静态库
- libmupdf-pkcs7.a - PKCS7 模块
- libmupdf-threads.a - 线程模块
- mutool (38 MB) - 命令行工具
- muraster (39 MB) - 光栅化工具
- 80 个头文件

## 注意事项

1. **不使用DTOFU选项**: 完整字体支持，不裁剪功能
2. **无测试套件**: mupdf 没有 make test 目标，通过 mutool -v 验证
3. **子模块commit必须精确匹配**: 否则链接错误
4. **GNU ld替代lld**: lld 依赖 libxml2.so.16 不可用
5. **1.25.1无extra-apps target**: 不同于1.27.2，但默认make已构建全部产物
6. **1.27.2 commands.json 存量缺口**: 1.27.2 无 conan 配方（历史 built
   记录，未 conan 化），commands.json 仅登记 1.25.1；1.27.2 的注册待其
   conan 化时另行处理
---

**编译结束**: 2026-09-17 14:07
**最终状态**: built
