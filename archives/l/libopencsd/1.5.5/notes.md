# libopencsd 1.5.5 适配笔记

## 编译环境
- 构建系统: makefile（自定义 Makefile：decoder/build/linux/makefile + unix_common/makefile.common，无 configure）
- 编译日期: 2026-09-17
- 编译器: clang/clang++（OHOS CI: /data/service/hnp/bin/clang，aarch64-linux-ohos；本地验证: macOS apple-clang）
- 状态: built

## 编译步骤

源码来自官方发布 tarball（Linaro/OpenCSD v1.5.5，GitHub 官方 release，SHA256 见 manifest）。
源码根为 `OpenCSD-1.5.5/`，库源码在 `decoder/` 下（source/ + include/ + tests/ + build/）。

1. 工具链注入（R33）：makefile.common 用 `MASTER_CC=$(CROSS_COMPILE)gcc` 等默认值，
   以 make 命令行变量覆盖注入 OHOS 工具链（取值自 Conan conf `tools.build:compiler_executables`）：
   ```bash
   make MASTER_CC=<cc> MASTER_CXX=<cxx> MASTER_LINKER=<cxx> MASTER_LIB=<ar> -j1
   ```
2. 构建（含库与测试程序，产物在源码树内）：
   ```bash
   cd decoder/build/linux && make ...        # libopencsd.a/.so、libopencsd_c_api.a/.so
   cd decoder/build/linux && make tests ...  # trc_pkt_lister 等 7 个测试程序
   ```
3. OHOS 特例——测试可执行文件签名（HarmonyOS 内核只 exec 带 .codesign 段的 ELF）：
   ```bash
   llvm-objcopy --remove-section .codesign <bin>
   binary-sign-tool sign -inFile <bin> -outFile <bin> -selfSign 1
   ```
4. 上游测试套件：61 个场景由适配驱动逐场景执行并检查 rc==0（详见"验证结果"）。
5. 打包：libopencsd.so* / libopencsd.a / libopencsd_c_api.so* / libopencsd_c_api.a → lib/；
   decoder/include/opencsd/** → include/opencsd/（C API 与 C++ API 头文件齐全）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | init-build 的"嵌套源码检测"把 decoder/build/linux 误当源码根 | 检测启发式按含 makefile 的最深目录判定，OpenCSD 的 makefile 位于 build 子目录 | 手动重建源码树：解压 tarball 保留完整 OpenCSD-1.5.5 结构为 .orig/.work |
| 2 | 本机 macOS 链接 .so 报错（ld64 不认 -soname / -Wl,-z,defs） | ld64 与 GNU ld/lld 链接参数差异 | 仅 macOS 本地验证时：SONAME_FLAG=-install_name、PLATFORM_LDFLAGS=（置空）；OHOS/CI 保持上游默认（lld 支持） |
| 3 | 本机 macOS 经 bash 脚本运行时 dyld 找不到 libopencsd.so.1 | 沙箱运行时对 DYLD_* 环境变量的传递行为异常，LC_RPATH 不被检索 | 测试驱动器用 Python subprocess 直接 exec 二进制并注入 DYLD_LIBRARY_PATH（OHOS/Linux 用 LD_LIBRARY_PATH），不再依赖 bash 脚本内的环境变量 |
| 4 | 上游测试脚本不传播失败码（"Done : Return N" 仅 echo） | 上游脚本设计为冒烟式 | 适配驱动逐场景执行并检查 rc==0，任何非 0 即失败，形成 61/61 通过记录 |
| 5 | 官方 Savannah 源 tar.gz 404 | 该库官方发布在 GitHub（Linaro/OpenCSD），Savannah 上的 libopencsd 是另一个同名小项目 | 源码 URL 改用官方 GitHub release tarball |
| 6 | 本机无 /data/service/hnp OHOS 工具链 | 工具链仅存在于远程 CI worker | 本地用 default profile（macOS 原生）跑通 conan create / conan-verify（W3）；ohos-aarch64 真机交叉验证依赖远程 CI（未伪造结果） |

## 依赖版本

- 编译依赖：无（纯 C++11/POSIX）
- 本机验证工具链：apple-clang（Xcode）/ make / ar
- CI 工具链：OHOS SDK clang 15（aarch64-linux-ohos）+ lld + llvm-ar + binary-sign-tool

## 验证结果

上游测试清点（R51，统一口径：按上游脚本逐条命令行场景计数）：
- run_pkt_decode_tests.bash: 24（15 解码 + range-limit + badopcode×2 + init-short-addr + TPIU + C-API + frame-demux + mem-buffer×2）
- run_pkt_decode_tests-ete.bash: 36（26 解码 + src_addr_n×3 + multi_session×7）
- run_capi_test.bash: 1（C-API 全快照，命令与主脚本 C-API 场景相同）
- 上游合计: **61**

适配后测试（PR 表格口径）：
- 单元测试: 0 / 集成测试: 61（不变，本地 macOS 全部通过 61/61）/ 其他: 0
- 鸿蒙特有测试: 1（test_ohos.sh：A1 AArch64 ELF64 校验 + A2 SONAME=libopencsd.so.1 + A3 dlopen+版本校验，3 断言）
- 适配后合计: **62**（较上游 +1）

本地 macOS 原生验证（conan default profile）：
```bash
conan create ... # G1-G4 全 PASS（见 .ci-result.json）
# 上游 61 场景：TOTAL=61 PASSED=61 FAILED=0
# test_package：consumer 3 断言 + test_ohos A3(dlopen) 通过
```

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py | Conan 配方：makefile 构建 + 工具链注入 + OHOS 签名 + 61 场景测试驱动 + 打包 |
| conandata.yml | 官方源码 URL + SHA256 |
| test_package/ | L1 消费者测试 + 鸿蒙特有测试（ELF/SONAME/dlopen） |
| manifest.yaml（软件级/版本级） | 归档元数据与适配知识沉淀 |

## 注意事项

- libopencsd 为纯 C++11/POSIX 库，无外部依赖，无平台特定代码需补丁；OHOS 适配点集中在
  ① make 变量工具链注入（R33）② 测试可执行文件签名（exec 前提）③ 上游 61 场景的驱动化运行。
- 动态库（.so）无需签名即可作为 DT_NEEDED 在 exec 时加载，因此打包产物不需要签名；
  CI worker 对用户目录 .so 的 dlopen 存在平台限制（ref: E502），dlopen 链验证保留在本机 default profile 执行并在远程 CI 复核。
- 测试驱动器只镜像上游脚本声明的命令（含 -src_addr_n/-multi_session/-aa64_opcode_chk 等变体），
  不改变断言语义（rc==0）；C-API 场景被 run_capi_test.bash 单独声明一次，按脚本逐条计数。

## 对话记录

### 对话 #1
- 2026-09-17：完成 libopencsd 1.5.5 鸿蒙适配。查重通过（origin/upstream 均无 libopencsd 分支）；
  确认官方源为 GitHub Linaro/OpenCSD v1.5.5（Savannah 上的 libopencsd 是同名小项目，非本库）。
  W0：纯 C++11/POSIX，零外部依赖。R51 清点：上游 61 个测试场景（run_pkt_decode_tests.bash 24 +
  run_pkt_decode_tests-ete.bash 36 + run_capi_test.bash 1，按脚本逐条命令行场景计数）。
  本地 macOS 原生构建 + 测试驱动 61/61 通过；conan create 全绿（构建 + test_package consumer 3 断言 +
  dlopen 链验证）；W3 本地 CI exit 0（L0/L1/L4 PASS、L2 skip、L5 因 macOS Mach-O 无 DT_SONAME 报 fail，
  平台属性，OHOS CI 上由 lld -soname 满足）。conan-verify default profile G1-G4 全 PASS；
  ohos-aarch64 真机交叉验证依赖远程 OHOS CI（本机无 /data/service/hnp 工具链，未伪造结果）。
  OHOS 适配点：make 变量工具链注入（R33）+ 测试可执行文件 binary-sign-tool 签名 + 61 场景驱动化执行。

## 发现与知识

- ✅ 自定义 Makefile 项目（makefile.common 用 MASTER_CC=$(CROSS_COMPILE)gcc 默认值）在 OHOS 上以命令行变量 MASTER_CC/MASTER_CXX/MASTER_LINKER/MASTER_LIB 覆盖注入 clang 工具链（取值自 Conan conf tools.build:compiler_executables），无需改上游 makefile（ref: E540）。
- ✅ OHOS 测试可执行文件必须 binary-sign-tool 签名才能被 exec：llvm-objcopy --remove-section .codesign 后 binary-sign-tool sign -selfSign 1（ref: E077）；动态库（.so）无需签名即可作为 DT_NEEDED 在 exec 时加载。
- ✅ CI worker 对用户目录下共享对象的 dlopen 存在平台限制（ref: E502）：exec-time NEEDED 加载是受支持路径，故鸿蒙特有测试 A3 在 OHOS 侧以 consumer 的 exec 时加载（DT_NEEDED 解析）为验证主体，dlopen 链验证保留在本机 default profile 执行并在远程 CI 复核。
- ✅ macOS 本机验证时 ld64 不认 -soname/-Wl,-z,defs：仅 darwin 分支以 SONAME_FLAG=-install_name、PLATFORM_LDFLAGS= 覆盖；OHOS CI（lld）保持上游默认以生成 DT_SONAME（ref: DRAFT-libopencsd-1.5.5-macos-ld64-soname）。
- ✅ 上游无正式测试框架：3 个 bash 脚本声明 61 个命令行场景且不传播失败码，适配驱动逐场景执行并检查 rc==0，形成可复核的 61/61 通过记录（ref: E265）。

---

**编译结束**: 2026-09-17 22:27
**最终状态**: built
