# clinfo 3.0.23.01.25 适配笔记

## 编译环境
- 构建系统: makefile（纯 Makefile，无 autotools/cmake/meson）
- 编译日期: 2026-08-15
- 编译器: clang/clang++（OHOS 工具链 /data/service/hnp/bin/clang）
- 状态: built（待真机预检）

## 上游信息
- 上游仓库: https://github.com/Oblomov/clinfo
- 版本 tag: 3.0.23.01.25（2023-01-25）
- 源码包: https://github.com/Oblomov/clinfo/archive/3.0.23.01.25.tar.gz
- sha256: 6dcdada6c115873db78c7ffc62b9fc1ee7a2d08854a3bccea396df312e7331e3
- 许可证: CC0-1.0
- 说明: clinfo 是纯 C 命令行工具，枚举系统中所有 OpenCL 平台/设备的全部已知属性，
  常用于验证 OpenCL 环境配置是否正确。

## 编译步骤

```bash
# 1. 下载 clinfo 源码 + vendor OpenCL-Headers（官方 KhronosGroup 归档 v2024.05.08）
#    + vendor OpenCL-ICD-Loader（官方 KhronosGroup 归档 v2024.05.08，真机无系统 libOpenCL）
# 2. 编译（配方内执行，OHOS 分支）
#    a. cmake 构建 vendored ICD loader（共享库）→ loader-build/libOpenCL.so.1.2
#       cmake -S OpenCL-ICD-Loader -B loader-build -DCMAKE_BUILD_TYPE=Release \
#             -DENABLE_OPENCL_LAYERS=OFF -DBUILD_TESTING=OFF \
#             -DOPENCL_ICD_LOADER_HEADERS_DIR=<src>/OpenCL-Headers \
#             -DCMAKE_POLICY_VERSION_MINIMUM=3.5
#    b. make 链接 clinfo，LDFLAGS 经环境变量传入（避免 shell 吃 $$ORIGIN）
#       LDFLAGS="-L<loader-build> -Wl,-rpath,'$$ORIGIN'"
#       make CC=<clang> CFLAGS="-O2 -std=c99 -Wall -Wextra" CPPFLAGS="-I<src>/OpenCL-Headers" -j1
# 3. OHOS 下对 clinfo 与 libOpenCL.so.1.2 做 ELF 自签
#    /data/service/hnp/bin/binary-sign-tool sign -inFile <f> -outFile <f> -selfSign 1
# 4. package: bin/clinfo + bin/libOpenCL.so.1（libOpenCL.so.1.2 重命名，rpath $ORIGIN 同目录寻库）
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | OHOS 系统无 OpenCL 头文件 (CL/cl.h) | OHOS 默认不带 OpenCL 开发头 | 配方 source() 中 vendor KhronosGroup/OpenCL-Headers 官方归档（v2024.05.08），CPPFLAGS 指向之 |
| 2 | clinfo 可执行文件在 HarmonyOS 上无法运行 | HarmonyOS 内核要求 ELF 代码签名 | 编译后用 binary-sign-tool 自签（-selfSign 1），先 llvm-objcopy 剥旧 .codesign 段 |
| 3 | 上游 CFLAGS 含 `-g -pedantic -Werror` | clang-15 下 -Werror 可能误报失败 (E063) | 配方传入 CFLAGS 去掉 -pedantic -Werror，保留 -O2 -std=c99 -Wall -Wextra |
| 4 | 真机链接失败 `ld.lld: error: unable to find library -lOpenCL` | OHOS 系统没有 libOpenCL（ICD loader），clinfo 链接 `-lOpenCL -ldl` 找不到库 | 配方 vendor KhronosGroup/OpenCL-ICD-Loader v2024.05.08，OHOS 分支先用 cmake 构建共享库 libOpenCL.so.1.2，再以 `LDFLAGS="-L<loader-build> -Wl,-rpath,'$$ORIGIN'"` 链接 clinfo；打包时把 libOpenCL.so.1.2 重命名为 libOpenCL.so.1 放入 bin/（rpath $ORIGIN 同目录寻库），两者均 ELF 自签。上游无平台时容错 CL_PLATFORM_NOT_FOUND_KHR，输出 "Number of platforms: 0" 并正常退出 |
| 5 | 真机预检 build() 报 `ConanException: 'tools.build:compiler_executables:c' does not exist in configuration list` | `tools.build:compiler_executables:c` 不是 Conan 2.30 的合法 conf 键（子键写法不存在，与 bam/zlib/lolcode 等既有配方一致） | 改为读 dict 型 conf：`self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)` 后取 `["c"]`，缺省回退 `clang` |
| 6 | 预检日志含 `/tmp/shhbvmdd.tmp: Read-only file system` | 该行来自 hmbs 自身 preflight.sh 包装脚本（ksh heredoc 临时文件），非配方/补丁硬编码（grep 确认 clinfo 目录无 /tmp/mktemp/tempfile），conan create 继续执行未受影响 | 不改配方；失败根因实为第 5 项 conf 键错误（退出码 1 来自 ConanException） |

## 上游测试审计（无测试）

- **审计结论**: clinfo 3.0.23.01.25 上游没有任何测试。
- 依据:
  1. 官方 tarball 解包仅含 src/*.c/.h、man1/clinfo.1、Makefile、Makefile.win、LICENSE，
     无 tests/、test/ 等任何测试目录或测试源文件；
  2. Makefile 仅 all/clean/install/sparse 四个目标，无 check/test 目标；
  3. 上游 CI（Travis/AppVeyor）只做编译构建，不运行测试；
  4. 单文件诊断工具，上游 13 年历史中从未包含测试套件。
- 处理: test_package/MANIFEST.yml 声明 `upstream_tests_exist: false` + 完整审计说明；
  hmbs 上游测试结果输出 `status:"no_tests"`、`discovered:0`、`executed:0`。

## 依赖版本

- OpenCL-Headers: v2024.05.08（vendor，官方 KhronosGroup 归档，sha256 3c3dd2...）
- OpenCL-ICD-Loader: v2024.05.08（vendor，官方 KhronosGroup 归档，sha256 eb2c9fde...）
- 运行期: 打包的 libOpenCL.so.1（rpath $ORIGIN 同目录寻库），无需系统 ICD loader

## 验证结果

```bash
# 真机预检（由 hmbs 在 HarmonyOS aarch64 真机执行）
# conan create . -pr=ci/conan/profiles/ohos-aarch64
# 预期:
#   - 编译通过，clinfo 自签成功
#   - test_package: clinfo --version 输出 3.0.23.01.25；clinfo -l 正常枚举
#   - HMBS_TEST_PACKAGE_RESULT: discovered=2, passedCount=2
#   - HMBS_UPSTREAM_TEST_RESULT: status=no_tests (discovered=0, executed=0)
```

## 2026-08-15 修复轮：补充 HMBS_UPSTREAM_TEST_RESULT 标记

- 问题: 真机预检 evidence 阶段报 incomplete，原因「缺少 HMBS_UPSTREAM_TEST_RESULT
  上游测试证据」——test_package 2/2 PASS 已有，但上游测试证据标记从未输出。
- 根因: 上游无测试（MANIFEST.yml 已声明 upstream_tests_exist: false + 完整审计），
  但标记须由配方显式输出；此前 test_package/conanfile.py 只跑 test_clinfo.sh，
  未 print 任何 HMBS_* 标记，conanfile.py build() 也无审计 grep 机器证据。
- 修复（对齐已过门禁的 aribb24/1.0.4 先例）:
  1. test_package/conanfile.py test(): 真实运行 test_clinfo.sh 之后裸 print()
     输出 HMBS_TEST_PACKAGE_RESULT（discovered=2, passedCount=2）与
     HMBS_UPSTREAM_TEST_RESULT（status=no_tests, framework=none,
     discovered/executed/passed/failed/skipped 全 0，含具体 reason）。
  2. conanfile.py build() 末尾调用 _audit_upstream_tests(): 对真实源码树
     Makefile 执行审计 grep（TESTS/check_PROGRAMS/check-local/^test:/^check:）
     + ls tests/ 目录，conan create 日志留机器证据。
  3. 审计依据复核: 上游 tag 3.0.23.01.25 源码树（GitHub API 拉取）确认仅
     Makefile/Makefile.win/src/*/man1/* 等，无 tests/ 目录；Makefile 仅
     all/clean/install/sparse 目标，无 check/test 目标。
- 状态: 未提交，等待 hmbs 下一轮真机预检验证。

## 注意事项

1. **OpenCL 头文件必须 vendor**：OHOS 系统不带 CL/cl.h，缺少则编译直接失败。
2. **ELF 签名不可省略**：未签名二进制在 HarmonyOS 上无法执行，test_package 会因
   无法执行而失败。libOpenCL.so.1.2 同样需要签名。
3. **test_package 用 bash 启动**：OHOS /system/bin/sh 不能 exec ELF 二进制 (R5)，
   test() 中显式使用 CONFIG_SHELL/bash 执行 test_clinfo.sh。
4. **真机无系统 libOpenCL**（`-lOpenCL` 链接失败）：必须 vendor
   OpenCL-ICD-Loader 并在配方内构建；cmake 构建参数参考仓库
   opencl-icd-loader/v2024.05.08 的既有经验（ENABLE_OPENCL_LAYERS=OFF、
   OPENCL_ICD_LOADER_HEADERS_DIR 指向 vendor 头文件、CMAKE_POLICY_VERSION_MINIMUM=3.5）。
5. **LDFLAGS 经环境变量传入 make**：`$$ORIGIN` 需写成 make 转义形式；直接拼进
   self.run 命令串会被外层 shell 二次展开，务必通过 os.environ["LDFLAGS"] 传递。
6. **打包寻库**：clinfo 链接时带 `-Wl,-rpath,'$ORIGIN'`，bin/ 下必须存在
   libOpenCL.so.1（真实文件，非符号链接），动态加载器按 SONAME 查找。
