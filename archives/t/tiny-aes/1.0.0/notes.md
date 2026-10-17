# tiny-AES-c 1.0.0 — OHOS 适配笔记

## 概述

tiny-AES-c 是一个用 C 编写的小型、可移植的 AES 实现，支持 128/192/256 位密钥与
ECB、CTR、CBC 三种工作模式，无任何外部依赖。整个库只有两个文件：`aes.c` 与公共头
`aes.h`（`aes.hpp` 是把它包进 `extern "C"` 的 C++ 包装）。本次为路径 A 基础适配：
**库源码与上游测试零修改，零补丁**。

- 上游：https://github.com/kokke/tiny-AES-c（tag `v1.0.0`）
- 源码：GitHub tag 归档 `tiny-AES-c-1.0.0.tar.gz`
- SHA-256：`61fd99ac95df30e9ab39d6cdd41e88909b2eaf9b9806f23aa235485ac0bed2fd`
- 许可证：The Unlicense

### 源码与版本口径

- 归档下载后按 workflow 要求做了 magic 校验（`1f 8b` gzip）与顶层目录核对
  （`tiny-AES-c-1.0.0/`），排除“停放页/HTML 冒充归档”。
- 内容与 Git 历史交叉核对：`v1.0.0` 的标签提交为
  `e72b6eff0884673997d0ca6385169bbd9b31936d`（2019-02-01，Merge pull request
  #124），把 tarball 解压树与 `git clone --branch v1.0.0` 的工作树做
  `diff -r --exclude=.git` 无内容差异。
- 说明：任务卡与上游 tag 都是 `1.0.0`，但上游仓库属于“长期 master 维护、几乎不发
  版本”的类型，`v1.0.0` 是唯一的 release tag，仓库内无 `project(... VERSION)`
  之类的版本声明。因此本包按 tag 内容对齐，不做版本号改写。

## 构建方案

- 构建入口：仓库根 **raw `Makefile`**，只构建所需目标。
  - `make aes.a` → 静态库（上游 `lib` 目标即 `ar rcs aes.a aes.o`）
  - `make test` → 上游测试：依次以 AES128、AES192、AES256 三种配置
    `make clean` + 重建 `test.elf` + 真实执行
- 产物命名：上游归档名是 `aes.a`，Conan 约定为 `libtiny-aes.a`，因此在
  `build()` 内用 `rename()` 改名；`shared=True` 时用同一份 `-fPIC` 目标文件直接
  链接出 `libtiny-aes.so`（带 `-Wl,-soname,libtiny-aes.so`）。
- 编译参数：沿用上游 Makefile 的 `-Wall -Os -c`，追加 `-fPIC`，再拼上
  profile 的 `tools.build:cflags`。注意：**命令行传入 `CFLAGS` 会覆盖 Makefile
  内的 `CFLAGS += -DAES192=1` / `-DAES256=1`**，所以库产物的宏集合由 recipe
  显式决定，而 `make test` 不传 `CFLAGS`，保留上游自身的三种配置切换。
- 工具解析：`CC`/`AR` 先取 profile 的 `tools.build:compiler_executables`，缺失时
  回退到“与 `CC` 同目录”的 `llvm-ar`（绝对路径优先）。这一条是有依据的：CI worker
  的 PATH 很短，裸 `llvm-ar` 不保证可解析（同类失败形态见 workflow 记录的 meson
  `Unknown linker(s): [['llvm-ar']]`）。
- 并行度：`make -j1`（上游 Makefile 本身串行，无并行目标）。

## 为什么不使用上游的 CMakeLists.txt

上游同时提供 `CMakeLists.txt`，但在本仓库不可用，三点都实测确认：

1. `cmake_minimum_required(VERSION 2.8.12)`：设备 CMake 为 4.1.2，直接拒绝
   （`Compatibility with CMake < 3.5 has been removed`）。
2. `target_include_directories(tiny-aes PRIVATE tiny-AES-c/)`：`tiny-AES-c/`
   子目录在 release tarball 布局中不存在（只在 master 的旧布局里存在）。
3. 没有任何 `install` 规则，无法产出 Conan 需要的 `include/` + `lib/` 结构。

因此按“上游 raw Makefile 为主构建入口”处理。

## 平台判定（为什么零补丁）

- `aes.c` 只 `#include <stdint.h>` 和 `<string.h>`；全库没有任何 `#ifdef` OS、
  `__linux__`、字节序或架构分支，也没有系统调用、文件系统或线程依赖。
- `prescan` 结论：`findings: []`（0 命中），构建系统识别为 `cmake` + `make`，
  `has_tests: true`。
- `lang-preflight` 结论：`task=c`、`detected=cpp`，判为兼容族（C/C++）继续。检测
  证据里的“主体占比 c 33%”来自 release tarball 内含 `CMakeLists.txt`、`conanfile.py`、
  `test_package/conanfile.py` 等非 C 文件与 `test.cpp`；主体语言由库本体
  `aes.c`(572 行) + `aes.h`(90 行) 决定，属 workflow 说明的统计口径噪声，
  不影响判定。

## 设计决策：不把密钥长度/模式暴露为 Conan 选项

上游自带的 `conanfile.py` 把 `AES128/AES192/AES256` 与 `CBC/ECB/CTR` 都做成了
选项，本包**刻意不提供**这些选项，原因是它们与打包头文件之间存在静默 ABI 错配：

- 这些宏写在 `aes.h` 里且默认固定为 `#define AES128 1`（192/256 行是注释掉的），
  同时它们决定 `struct AES_ctx` 的布局（`RoundKey[AES_keyExpSize]`：AES128 为 176、
  AES192 为 208、AES256 为 240；`Iv[16]`）。
- 若把它们做成 Conan 选项，消费方只要用默认头文件（AES128 布局）编译、却链接到
  按 `AES256` 构建的库，就会得到结构体大小不一致的静默错配：编译链接全部成功，
  运行时栈/堆越界。上游配方恰好存在这个缺陷。
- 本包因此固定为上游默认配置（AES128 + CBC/ECB/CTR 全开），并在 `README.md`
  写明需要其他密钥长度时的正确做法（自行编译 `aes.c` 或另建目标配置的版本目录）。

## 遇到的问题与解决方案

1. **相对路径 profile 被 `$CONAN_HOME` 下的陈旧副本静默覆盖（高收益）**
   - 现象：`conan create ... -pr:h=ci/conan/profiles/ohos-aarch64`（相对路径）在
     “Computing necessary packages”阶段报
     `ERROR: There are invalid packages: tiny-aes/1.0.0: Invalid: 'settings.os.version' value not defined`，
     而报错前打印的 Host/Build profile 段里 `compiler.libcxx=libstdc++11`、
     `compiler.cppstd=gnu14` 且**没有 `os.version`**，与仓库内 profile 文件
     （`libc++`、`c++std 17`、`os.version=6.0`）完全不符。
   - 根因：`conan/internal/api/profile/profile_loader.py` 的
     `ProfileLoader.get_profile_path()` 对非绝对、且不以 `./`/`..` 开头的参数，
     **先**拼 `$CONAN_HOME/profiles/<参数>`，命中即用，仅在未命中时才回退到 cwd。
     本机存在陈旧副本
     `$CONAN_HOME/profiles/ci/conan/profiles/ohos-aarch64`（缺 `os.version`、
     cppstd/libcxx 为旧值），于是仓库内的 profile 被静默旁路。
   - 处置：本任务所有 conan 命令一律使用**绝对** profile 路径（与 CI 的
     `build_and_test.sh` 用 `$REPO_ROOT/ci/conan/profiles/$PROFILE` 一致），
     错误消失且 settings 与仓库文件一致。已写入反馈文件。

2. **消费者测试自身的向量配对被自检发现（库无问题）**
   - 现象：首轮 `test_package` 共 **15** 项断言，其中 2 项失败
     （13 条 `ok -` + 2 条 `FAILED -`，末行 `FAILED: 2 assertion(s) failed`，
     退出码 1），`FIPS-197 C.1 AES-128 ECB` 的实测密文为
     `8df4e9aac5c7573a27d8d055d6e4d64b`。该版尚无下述 F.1.1 两向断言，
     故总数是 15 而非最终的 17。
   - 根因：测试把 **FIPS-197 附录 C.1 的密文**（对应密钥
     `000102…0f`）与 **SP 800-38A 的示例密钥** `2b7e1516…3c` 配了对。
     用 OpenSSL 3.6.4 复算可确认 `8df4e9aa…` 正是
     （key=`2b7e…3c`, pt=`00112233…eeff`）的正确结果——即**库是对的，是测试写错了**。
   - 修复：为两组向量分别引入各自的密钥，C.1 用 `000102…0f`，并额外加入
     SP 800-38A F.1.1（key `2b7e…3c`，pt `6bc1 bee2…172a` → `3ad77bb4…ef97`）
     的正反两向断言。这样两套“密文—密钥”配对都被锁定，混用密钥会被直接抓住。
   - 该自检也说明断言不是自洽式假绿：期望值来自公开发布的标准向量。

3. **`make: jobserver mkfifo: ...: Operation not permitted`（设备噪音）**
   - CMake 以 `-- -j20` 调 make 时设备无法创建 jobserver fifo，仅打印噪音，
     构建与测试结果不受影响；与 workflow 记录的 jobserver 噪音同源。

## 验证结果

### 上游测试（同一份上游源码与上游测试，零修改）

- 入口：`make CC=clang LD=clang AR=llvm-ar test`（原始 Makefile，未打补丁）
- 统计单位：`test.c` 的验证例程 × `make test` 的密钥长度构建配置 = 6 × 3
- `TOTAL=18  PASS=18  FAIL=0  SKIP=0  NOT_RUN=0`
- 取数命令：`make test | grep -c 'SUCCESS!'` → `18`；`| grep -c '^Testing AES'` → `3`
- 不计入：`test_encrypt_ecb_verbose()`（void 演示函数，无比较、无返回值）；
  6 个例程的 `main()` 返回值为其求和，任一不符即 `make test` 非零退出。

### 输出正确性的独立核对（非自洽证据）

上游 `test.c` 内嵌的期望值已用 **OpenSSL 3.6.4** 独立复算：AES128 配置下
`test_encrypt_ecb_verbose()` 打印的 4 个分组密文与 OpenSSL ECB 输出逐字节一致
（`3ad77bb4…ef97`、`f5d3d585…baaf`、`43b1cd7f…0688`、`7b0c785e…5dd4`），
设备上库的实际输出与之相同。即“通过”来自真实 AES 正确性，而不是上下游同源的
自洽比较。

### Conan 干净构建与 `test_package`

- 实跑命令（`conan-verify` 采信轮，profile 必须绝对路径，原因见前文“问题 1”）：

  ```sh
  conan create <repo>/archives/t/tiny-aes/1.0.0 \
    -pr:h=<repo>/ci/conan/profiles/ohos-aarch64 \
    -pr:b=<repo>/ci/conan/profiles/ohos-aarch64 \
    --build=missing --user=ohpcd --channel=stable
  ```

  结果：PASS（引用形态即 `tiny-aes/1.0.0@ohpcd/stable`，与包内证据一致）。
- `build()` 内上游测试同样在设备执行：`18 SUCCESS / 0 FAILURE`，三种配置日志齐全。
- `test_package`：静态库 17/17 断言通过；`shared=True` 变体同样 17/17 通过，且
  消费者二进制 `readelf -d` 显示 `NEEDED libtiny-aes.so`——即运行时由加载器真实
  解析并加载动态库，不是静态链接冒充。
- 打包完整性：`shared=True` 时包内 `lib/libtiny-aes.so` 与 build-tree 副本
  `sha256=4892c9e15831e204bc74406ffd0a981cd43eed6622f2ab5a8fecdd6d64990664`
  字节一致（无 `.dynstr` 改写破坏 `.codesign` 的已知问题），`SONAME=libtiny-aes.so`、
  `NEEDED` 仅 `libc.so`、`FLAGS: BIND_NOW`、`.codesign` 段保留、`Type=DYN`(AArch64)。

## 本次为路径 A 基础适配

未修改上游库源码与上游测试，无补丁，无新增鸿蒙专有测试框架；消费者测试为
Conan `test_package` 必需项，覆盖公开发布的 AES 标准向量与库自身语义。
