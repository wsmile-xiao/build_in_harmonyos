# precomp 0.4.7 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-09-04
- 编译器: clang/clang++（OHOS 设备原生，musl + libc++）
- 状态: built

## 软件概况

precomp（上游仓库名 precomp-cpp，软件自称 precomp）是命令行预压缩器：
扫描文件中已压缩流（deflate/zlib/gzip、bZip2、GIF、JPG、MP3、ZIP、PDF、
SWF、MIME Base64、LZMA），解出内层数据写入 .pcf 容器，使更强压缩器
（xz/7z）再压时总压缩比更优；`precomp -r` 无损还原（位对位一致）。
单二进制 CLI（package_type=application）。

- 上游：https://github.com/schnaader/precomp-cpp tag v0.4.7
- sha256: b4064f9a18b9885e574c274f93d73d8a4e7f2bbd9e959beaa773f2e61292fb2b
- License: Apache-2.0（仓库根 LICENSE 文件确认；README Credits 另列
  vendored 组件：packJPG v2.5k / packMP3 v1.0g / bZip2 1.0.6 /
  zLib 1.2.11 / GifLib 4.1.4 / liblzma (XZ 5.2.3) / preflate v0.3.5）
- CMake ≥3.2，C++11（CMAKE_CXX_STANDARD 11），C99
- 唯一外部依赖 find_package(Threads)（pthread，musl 自带）→ 零 conan
  requirements；bzip2/zlib/giflib/liblzma/packjpg/packmp3/preflate 全部
  vendored 于 contrib/ 编进二进制（CMakeLists 的 BZIP_SRC/ZLIB_SRC/
  GIF_SRC/PACKARI_SRC 等变量直接引用 contrib 源文件）
- Windows 头（windows.h/conio.h/io.h）都在平台守卫内；dlltest.cpp 为
  Windows-only 不参与构建

## 编译步骤

探索构建（工作目录 $TMPDIR/builds/precomp-0.4.7.work）：

```bash
cd build
cmake .. -DCMAKE_BUILD_TYPE=Release \
  -DCMAKE_POLICY_VERSION_MINIMUM=3.5 \
  -DCMAKE_SYSTEM_NAME=Linux -DCMAKE_SYSTEM_PROCESSOR=aarch64
make -j4
```

配方构建等价于上述命令（CMakeToolchain 注入相同 cache 变量，见
conanfile.py generate()）。上游 CMakeLists 无 install() 规则，
package() 手动布局 bin/precomp。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | CMake 4.x 拒绝配置：Compatibility with CMake < 3.5 has been removed | 上游 cmake_minimum_required(VERSION 3.2) | 注入 -DCMAKE_POLICY_VERSION_MINIMUM=3.5（配方 generate() cache_variables），不改上游文件 |
| 2 | if(UNIX) 分支不生效，代码走 Windows 路径（windows.h/conio.h） | 本机 cmake 自动探测 CMAKE_SYSTEM_NAME=HarmonyOS，CMake 对该系统名不设 UNIX 变量（实测 UNIX 为空），-DUNIX/-DLINUX/C99/Threads 全不生效 | 配方注入 CMAKE_SYSTEM_NAME=Linux + CMAKE_SYSTEM_PROCESSOR=aarch64（原生构建，musl/libc++，无 Linux 专有 API；abcmidi 同款先例）→ UNIX 分支正常，Threads::Threads 链接成功 |
| 3 | conan-verify L2 冒烟（--version/--help 探测 rc）失败：precomp 把长选项当输入文件名，exit(1) | 上游无 GNU 风格长选项；无参/usage 路径均 exit(1) | precomp.cpp 参数解析处新增 --version/--help 处理（见源码修改节），L2 探测 rc=0 |
| 4 | `-r` 还原默认输出名 = PCF 头内原文件名，输出已存在时交互式询问覆盖（脚本化卡死风险） | 上游交互设计 | 测试/脚本一律 `-r -o<输出名>` 显式指定（-o 与文件名间无空格，error 10） |

## 源码修改

补丁 0001-precomp.cpp.patch（refresh-patch --auto 生成，
+15/-1），仅改 precomp.cpp 三处：

1. `bool help_requested = false;`（与 long_help 等布尔量同组声明）
2. 参数解析循环 `if (argv[i][0] == '-')` 开头（input_file_given 检查后）
   新增：`--version` → exit(0)（版本横幅在 main 启动时已打印）；
   `--help` → 置 help_requested/long_help/valid_syntax=false 后跳出循环
   走 usage 打印路径
3. usage 打印块末尾 `exit(1)` → `exit(help_requested ? 0 : 1)`，
   使 --help 按惯例 rc=0；其余 usage 路径（语法错误）行为不变

不改任何既有开关行为。CMakeLists.txt 零修改（平台问题全部经配方
cache 变量解决）。

## 依赖版本

- 零 conan 依赖（requirements() 为空）
- vendored（编进二进制）：bzip2 1.0.6 / zlib 1.2.11 / giflib 4.1.4 /
  liblzma (XZ Utils 5.2.3) / packJPG v2.5k / packMP3 v1.0g / preflate v0.3.5
- pthreads：musl libc 提供（Threads::Threads）

## 验证结果

```bash
# 探索构建产物冒烟（$TMPDIR/builds/precomp-0.4.7.work/build/precomp）
./precomp --version          # rc=0，横幅 "Precomp v0.4.7 Unix 64-bit"
./precomp --help             # rc=0，"Usage: precomp [-switches] input_file"
# 弱压缩 round-trip（gzip level 1，~115KiB 词级文本）
./precomp -oout.pcf sample.txt.gz     # rc=0，"Recompressed streams: 1/1"
./precomp -r -orestored.txt.gz out.pcf  # rc=0
sha256sum sample.txt.gz restored.txt.gz  # 一致（位对位还原）
# 压缩增益：gzip(pcf)=16168 < gzip(orig)=23168（核心价值主张实测成立）
```

test_package 断言（test_precomp.py，5 项）：
--version rc=0 横幅 / --help rc=0 usage / 预压缩 rc=0 且 1/1 流 /
还原 sha256 字节一致 / gzip(.pcf) < gzip(原文件)。

## 注意事项

- `-o` 与文件名之间不能有空格（error 10）
- 压缩增益断言的输入构造要点：弱压缩（gzip level 1）+ 中等熵内容
  （词级随机文本 ~115KiB）；高重复内容或极小文件会被 pcf 元数据
  开销吞掉增益
- precomp 退出码语义：0=成功、1=各类错误、2=无流可解（批量场景有用）
- 上游 CI 情况：无自动化测试（仅 appveyor Windows 构建冒烟）

## 对话记录

### 对话 #1: if(UNIX) 平台分支失效
- 问：探索构建时为何代码走 Windows 路径（windows.h/conio.h 缺失风险）？
- 答：本机 cmake 自动探测 CMAKE_SYSTEM_NAME=HarmonyOS，CMake 无该平台模块
  → UNIX 变量为假。解法：配方 generate() 注入 CMAKE_SYSTEM_NAME=Linux +
  CMAKE_SYSTEM_PROCESSOR=aarch64（E092；abcmidi 同款先例），原生构建无
  Linux 专有 API，UNIX 分支（-DUNIX、Threads::Threads）恢复生效。

### 对话 #2: CMake 4.x 拒绝 cmake_minimum_required(3.2)
- 问：configure 报 "Compatibility with CMake < 3.5 has been removed"？
- 答：CMAKE_POLICY_VERSION_MINIMUM=3.5 经 CMakeToolchain.cache_variables
  注入（-D 命令行在任何 CMakeLists 解析前生效；tc.variables 写 toolchain
  文件无效，见 DRAFT-E321-cmake4-policy-version-minimum）。

### 对话 #3: L2 冒烟 --version/--help rc=1
- 问：conan-verify L2 探测失败（上游把长选项当输入文件名，exit 1）？
- 答：precomp.cpp 补丁新增 GNU 长选项（E503 jshn 同款先例）：--version
  直接 exit(0)（横幅启动时已打印）；--help 置 help_requested 后走既有
  usage 打印路径，exit(help_requested ? 0 : 1)。

### 对话 #4: 补丁被编辑器空白清理污染
- 问：refresh-patch 生成 +50/-36 的巨大补丁？
- 答：编辑工具对 8320 行 precomp.cpp 做了全文件尾随空白清理，混入大量
  无关 diff。还原 orig 基准后改用 python 字节级 replace 精确重做 3 处
  功能修改 → 干净补丁 +15/-1。

## 最终状态

- 编译: 成功（conan create PASS，包 ID 6b129b068851896169fae42d399fa922d239ce8a）
- 测试: test_package 5/5 断言通过（round-trip sha256 字节一致 + 压缩增益成立）
- 验证: conan-verify 8 门禁 PASS；verify-build 质量报告 PASS
- 打包: precomp-0.4.7-ohos-aarch64.tar.gz (1093KB) + debug 包
- 状态: built
- COMPLETED
---

**编译结束**: 2026-09-04 12:18
**最终状态**: built
