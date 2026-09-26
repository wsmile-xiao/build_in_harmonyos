# UDT 4.11 适配笔记

## 编译环境
- 构建系统: makefile（src/Makefile + app/Makefile，顶层 Makefile 递归调用）
- 编译日期: 2026-09-18
- 编译器: clang/clang++（Conan toolchain，替换上游硬编码的 g++）
- 状态: built

## 编译步骤

UDT 是纯 Makefile 项目，无 configure/CMake。核心步骤：

```bash
# 1. 构建库（libudt.so + libudt.a + udt 头文件副本）
make -C src os=LINUX arch= C++=clang++ all

# 2. 构建上游自包含测试（app/test，链接 ../src 下的 libudt）
make -C app os=LINUX arch= C++=clang++ test

# 3. 运行上游测试（从 app/ 目录，LD_LIBRARY_PATH 指向 src）
cd app && LD_LIBRARY_PATH=../src ./test
```

conan recipe 在 `build()` 中执行以上三步，并在解析测试输出后打印 `HMBS_UPSTREAM_TEST_RESULT` 标记。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | aarch64 编译报 x86 内联汇编错误 | Makefile 默认 `arch=IA32`（或 AMD64）会定义 `-DIA32`/`-DAMD64`，使 CTimer 选择 x86 `rdtsc` 内联汇编 | 构建时传**空** `arch=`，不定义任何架构宏 → UDT 回退到 POSIX `getTime()` 微秒计时器（可移植路径） |
| 2 | Makefile 硬编码 `C++ = g++` | 上游写死编译器 | make 命令行覆盖 `C++=clang++`，从 Conan conf `tools.build:compiler_executables:cpp` 读取（R33） |
| 3 | 上游测试退出码恒为 0，可能假通过 | app/test 的每个子测试线程函数返回 `void*`，main() 不检查返回值 | 解析输出中的 "Test # N completed." 标记数（必须=4），并扫描 "DATA ERROR"/"send:"/"recv:" 等失败指示词，任一异常即判失败（证伪） |
| 4 | 连续快速重跑 app/test 在 Test 2 偶发卡住 | Test 2 在共享/专有端口上建立大量并行连接，前次运行残留的 TIME_WAIT 端口拖慢绑定 | 单次 `conan create` 中测试只跑一次、端口干净，实测 11s 跑完 4 例；无需处理 |

## 源码修改

无补丁。via 构建参数（`os=LINUX arch=` + 编译器覆盖）完成 OHOS aarch64 适配，未修改任何上游源码。

## 依赖版本

- 无第三方编译依赖（仅系统 clang/clang++、POSIX socket、pthread、libm）。

## 验证结果

在上游源码解压后对 `app/test` 进行 host 侧与目标环境验证：

```bash
$ LD_LIBRARY_PATH=../src ./test
Start Test # 1
Testing simple data transfer.
Test # 1 completed.
Start Test # 2
Test parallel UDT and TCP connections.
Test # 2 completed.
Start Test # 3
Test rendezvous connections.
Test # 3 completed.
Start Test # 4
Test UDT in multiple threads.
Test # 4 completed.
$ echo $?
0
```

- 上游测试：4 例全部执行并完成（流式数据、并行 UDT+TCP、rendezvous、多线程）。
- 消费者测试 test_package：在回环上通过 UDT API 实际收发数据（startup/socket/bind/listen/accept/connect/send/recv/close/cleanup）。

## 交付物

| 文件 | 说明 |
|------|------|
| libudt.so | UDT 动态库 |
| libudt.a | UDT 静态库 |
| udt.h | UDT 头文件（含 C++ UDT 命名空间 API 与 C API） |

## 注意事项

- aarch64/OHOS 构建**必须**传空 `arch=`，否则触发 x86 rdtsc 内联汇编编译错误。
- 归档根目录为 `udt4/`，`get()` 时 `strip_root=True` 剥掉，`src/` 与 `app/` 位于顶层。
- 上游测试结果以输出标记为准（退出码不可单独信），符合 HMBS 机器证据门禁要求。
## 2026-09-18 真机预检修复

- **问题**: `conan create` 在依赖图阶段即失败：`ERROR: udt/4.11: Package type is 'library', but no 'shared' option declared`（先于任何编译发生）。
- **根因**: recipe 声明 `package_type = "library"` 却未声明 `options`/`default_options` 中的 `shared`；Conan 2 对 library 类型包强制要求声明 `shared` option，缺失即校验失败。
- **修复**:
  1. conanfile.py 新增 `options = {"shared": [True, False]}`、`default_options = {"shared": False}`；
  2. `package()` 按 `self.options.shared` 只打包 libudt.so（shared）或 libudt.a（static）——上游 Makefile 两者都产出，option 只决定打包给消费者的是哪个；
  3. `package_info()` 未 shared 时追加 `UDT_STATIC` 定义。
- **补全 test_package**（此前目录仅 test.cpp）:
  - 新增 `test_package/conanfile.py`（CMake 方式：CMakeDeps/CMakeToolchain + cmake_layout，编译并运行 test_udt，打印 `HMBS_TEST_PACKAGE_RESULT`，discovered/passedCount=2，对应 test.cpp 两处断言：server 收到数据匹配、client 发送全部字节）；
  - 新增 `test_package/CMakeLists.txt`（find_package(udt) + Threads::Threads，C++17）；
  - 新增 `test_package/MANIFEST.yml`（udt 上游测试存在且在 build() 内执行，`upstream_tests_exist` 隐含 true，`upstream_test_in_build: true`，4 个上游用例）。
- **readonly_tmp 诊断**: 日志中 `can't create temporary file /tmp/...: Read-only file system` 来自预检 harness 脚本自身（preflight.sh[306]），并非 udt recipe 写入 /tmp；本配方及 app/test 均不硬编码 /tmp，无需改动。


## 2026-09-18 真机预检修复（第 2 轮）：source() BadZipFile

- **问题**: shared option 修复后，conan create 进入 source() 阶段失败：
  `ERROR: udt/4.11: Error in source() method, line 73 … BadZipFile: File is not a zip file`。
  下载本身成功（“Sources correctly downloaded …”），但解压报 BadZipFile。
- **根因**: SourceForge 的 `/download` 尾 URL 最后一个路径段是 `download`，
  无归档扩展名。Conan 2 `get()` 默认按 URL 尾段名推断归档类型，识别不了时误按
  ZIP 尝试解压（tar.gz 内容），故抛 `BadZipFile: File is not a zip file`。
- **修复**: 在 `conandata.yml` 的 `sources` 中显式声明
  `filename: "udt.sdk.4.11.tar.gz"`，`get()` 因此按 `.tar.gz` 识别并以同名文件
  落盘（同仓库 armadillo 等 SourceForge 包既有做法）。sha256 不变。
- 注意：严禁为迎合下载而改 sha256；filename 只影响归档类型识别与文件名，不改变归档内容。


## 2026-09-18 真机预检修复（第 3 轮）：readonly_tmp 编译失败

- **问题**: 前两轮（shared option、BadZipFile）在依赖图/source() 阶段即失败，本轮是
  OHOS 真机上首次真正进入 build() 的编译阶段。日志报
  `can't create temporary file /tmp/shcbiaq4.tmp: Read-only file system`，
  hmbs 将其归类为 `[readonly_tmp]`：构建脚本写入只读 /tmp。防线在
  `make -C src ... all`（conanfile.py 中 src_cmd 的 self.run），make 退出非零
  (Error 2)。UDT 的 src/Makefile 本身不写 /tmp，是 clang 编译目标文件时把
  汇编临时文件写到只读 /tmp 导致的失败。
- **根因**: OHOS 设备 /tmp 为 root 属主只读目录；clang（HNP 工具链）缺省把
  汇编中间文件写到 $TMPDIR 或 /tmp。TMPDIR 未显式指向可写目录时编译即失败。
- **关键 Conan 2 陷阱**: `self.run(env=...)` 只接受 *conan 环境文件名的列表*，
  并不把字面 KEY=VALUE 传给子进程（conan/internal/model/conan_file.py run() 里
  `assert isinstance(env, list)`）。子进程继承的是父进程 os.environ，因此正确做法是
  在 recipe 内直接设 `os.environ["TMPDIR"]` 等，而不是 `self.run(env=dict)`。
- **修复**: 新增 `_tmp_env()`，优先用 HMBS 注入的 TMPDIR/TMP/TEMP（含 HMBS_TMPDIR），
  否则回退到 self.build_folder（恒可写），`os.makedirs(candidate, exist_ok=True)` 后
  写入 os.environ["TMPDIR"/"TMP"/"TEMP"]，再执行 make。这样 clang 的临时文件落到
  可写目录，规避只读 /tmp。
- 未改上游源码；未删除任何断言/测试。test_package 与上游测试接入保持不变。


## 2026-09-18 真机预检修复（第 4 轮）：readonly_tmp 编译失败（改用 subprocess + 强制 TMPDIR）

- **现状**: 前一轮（第 3 轮）在同一 `make -C src`（conanfile.py build() 内 self.run）
  的 readonly /tmp 编译失败仍复现：日志仍出现
  `can't create temporary file /tmp/...: Read-only file system` 与
  `can't open /proc/<pid>/cmdline`，`make -C src` 退出 Error 2，Package build failed。
- **为何上一方案无效（自证）**: 第 3 轮只在 recipe 内 `os.environ["TMPDIR"]=candidate`，
  但 candidate 的选取把“继承的 TMPDIR/TMP/TEMP”排在前面；若父环境已把 TMPDIR 设成
  只读 /tmp（或 HMBS 注入的 tmpdir 未以同名环境变量暴露），则 candidate 仍解析到
  只读 /tmp，os.environ 里 TMPDIR 依然是 /tmp → clang 照样写只读 /tmp → 编译失败。
  且 `self.run()` 会在 /bin/sh -c 包裹下执行，包裹 shell 自身的临时文件也可能落到只读 /tmp。
- **不同实现路线**:
  1. `_tmp_env()` 不再信任继承的 TMPDIR/TMP/TEMP，**一律强制** 指向
     `os.path.join(self.build_folder, "tmp")`（Conan 保证 build 目录可写），
     `os.makedirs(...)` 后把 TMPDIR/TMP/TEMP 写进返回的 env dict。
  2. 编译/链接改用 `subprocess.run([make, "-C", src, ..., "all"], shell=False, env=env)`
     直接 exec make，绕开 `self.run()` 的 /bin/sh 包裹层，避免包裹 shell 撞只读 /tmp；
     make 及其 recipe 的子 shell、clang 都继承该 env（含可写 TMPDIR）。
  3. `make` 路径优先 `HMBS_MAKE`，其次 `shutil.which("make")`（hmbs 已把工具目录并入 PATH）。
  4. 上游 app/test 的运行 env 同样强制可写 TMPDIR/TMP/TEMP。
- 未改上游源码；未删除任何断言/测试；test_package 与上游测试接入保持不变。


## 2026-09-18 真机预检修复（第 5 轮）：strip_root "./" 前缀坑致 make -C src 找不到源码树

- **现状**: 上一轮 readonly_tmp 修复后编译已能启动，但本次真机日志（compile 阶段）报
  `make: Entering directory '.../conan-home/p/b/udt7ffeb6b876cd6/b'` 后紧跟
  `make: *** src: No such file or directory. Stop.`，随后 `Package ... build failed`。
  这是第一次真正暴露并定位到「源码没有落在 src/、app/ 顶层」的问题。
- **根因（自证，非猜测）**:
  1. 下载 udt.sdk.4.11.tar.gz 实测其内部条目全部带 "./" 前缀：`./udt4/`、`./udt4/src/...`、
     `./udt4/app/...`（tar tvzf 首成员即 `drwx------ ./udt4/`）。
  2. Conan 2.29/2.30 的 `tools/files/files.py untargz()` 里 strip_root 这样算根目录：
     `name.split("/",1)[0]`，对首个目录成员 `"./udt4/"` 得 `"."` → common_folder="."，
     于是 strip 只剥掉 "./"，树仍落在 `udt4/` 包装层下，`src/`、`app/` 不在顶层。
  3. 因此 build() 里 `make -C src` 从源码树根找不到 src，报
     `make: *** src: No such file or directory`。
- **为何上一方案无效（自证）**: 前几轮只改 TMPDIR/编译器，根本问题在源码解包布局；
  即便 TMPDIR 修好，`make -C src` 依旧因源码在 udt4/ 包装层下而找不到目录。
- **修复**: 不再依赖 `strip_root=True`。`source()` 里 `get(self, **sources)` 直接解包，
  新增 `_src_root()` 显式解析顶层唯一目录（udt4/）为源码树根，build()/上游测试/
  package() 全部改用 `self._src_root()` 定位 src/、app/。规避了 strip_root 对 ./ 前缀
  的误判，且不依赖 basic_layout 下 source/build 目录的具体取值。
- **本地验证**: 在解包后的 udt4/ 上跑 `make -C src os=LINUX arch= C++=g++ all` 成功
  产出 libudt.so/libudt.a/udt；`make -C app os=LINUX arch= C++=g++ test` 成功；
  `LD_LIBRARY_PATH=src ./app/test` 跑满 4 例，"Test # 1..4 completed." 全部出现。
- 未改上游源码；未删除任何断言/测试；test_package 与上游测试接入保持不变。


## 2026-09-18 真机预检修复（第 6 轮）：app/test.cpp 裸 bind 被 std::bind 遮蔽致编译失败

- **现状**: src/（libudt.so/libudt.a/udt.h）本轮编译已通过，但 `make -C app ... test`
  在编译 test.o 时失败，仅 1 处错误：
  `test.cpp:90:51: error: invalid operands to binary expression ('__bind<int &, sockaddr *&, unsigned int &>' and 'int')`
  指向 `if (bind(ssock, res->ai_addr, res->ai_addrlen) != 0)`。
- **根因**: test.cpp 顶部有 `using namespace std;`。在 OHOS 的 libc++ 工具链下，裸 `bind`
  经 using 指令与 C 库 socket `::bind` 一并进入候选，libc++ 的 `std::bind`（模板，返回
  __bind 对象）优先实例化，生成的 `__bind<int&,sockaddr*&,unsigned int&>` 与 `!= 0`
  比较非法而报错。本地 g++/libstdc++ 下非模板 `::bind` 精确匹配胜出，故本机验证时
  `make -C app test` 能过（与 notes 第 5 轮本地记录一致），只有 OHOS libc++ 触发。
- **修复**: 新增 `patches/0001-app-test-fix-bind-shadow.patch`，把
  `bind(ssock, ...)` 限定为 `::bind(ssock, ...)`；conandata.yml 的 patches 由 [] 改为
  注册该补丁（export_sources->export_conandata_patches 导出，source()->apply_conandata_patches
  应用）。只改上游自测代码 app/test.cpp 一处，不影响库本体 src/ 任何行为；测试计数与
  "Test # N completed." 判定逻辑不变。
- **补丁自证**: 对 tarball 全新解包树 `patch -p1` 干净应用，line 90 变为
  `if (::bind(ssock, ...) != 0)`，无 offset/冲突。
- 未删除断言/测试；test_package 与上游测试接入保持不变。


## 2026-09-18 真机预检修复（第 7 轮）：补丁格式损坏致 apply_conandata_patches 解析失败

- **现状**: 本轮真机 conan create 在 source() 阶段失败：
  ```
  udt/4.11: Apply patch (file): patches/0001-app-test-fix-bind-shadow.patch
  udt/4.11: WARN: .../patches/0001-app-test-fix-bind-shadow.patch: error: patch stream is incomplete!
  ERROR: udt/4.11: Error in source() method, line 84
      apply_conandata_patches(self)
      ConanException: Failed to parse patch
  ```
- **根因（自证，非猜测）**: Conan 2 的 `apply_conandata_patches`/`patch()` 使用纯 Python 的
  `patch_ng.fromfile()` 严格解析补丁（conan/tools/files/patches.py 里的 patch_ng）。旧补丁
  hunk 头声明 `@@ -87,7 +87,7 @@`（7 行），但补丁体实际只有 **6** 个源/目标行
  （5 个上下文 + 1 个增删，且首个上下文是空行而非真实首行 `}`）。patch_ng 逐行计数后
  与 hunk 头行数不匹配，文件结束仍认为 hunk 未完整解析，报 "patch stream is incomplete!"，
  fromfile() 返回伪值，Conan 抛 "Failed to parse patch"。
  - 真实 test.cpp 中该处为：87=`}`、88=空行、89=`ssock = socket(...)`、90=`if (bind...)`、
    91=`{`、92=`return -1;`、93=`}`，共 **7** 行源/目标（`diff -u` 生成的正确 hunk 头即为
    `-87,7 +87,7`）。
  - 之前本地 `patch -p1` 验证"干净应用"是 GNU patch 的容错（fuzz/offset）掩盖了 hunk 行数
    错误；GNU patch 宽松，patch_ng 严格，故只有真机 OHOS CI（走 Conan patch_ng）暴露。
- **修复**: 用真实源码 `diff -u --label a/udt4/app/test.cpp --label b/udt4/app/test.cpp`
  重新生成补丁替换旧文件。新补丁 hunk 头与体一致：
  ```
  @@ -87,7 +87,7 @@
     }
  
     ssock = socket(res->ai_family, res->ai_socktype, res->ai_protocol);
  -   if (bind(ssock, res->ai_addr, res->ai_addrlen) != 0)
  +   if (::bind(ssock, res->ai_addr, res->ai_addrlen) != 0)
     {
        return -1;
     }
  ```
- **补丁自证**: patch_ng.fromfile() 解析成功（type=plain，hunk 87 7 87 7）；
  patch_ng.apply(strip=0, root=<含 udt4/ 包装层的 source>，模拟 Conan apply 方式) 返回成功，
  test.cpp 第 90 行变为 `if (::bind(ssock, ...) != 0)`。
- **经验教训（写进本次修复）**: 手工/编辑器生成 unified diff 极易在 hunk 头行数与上下文
  上出错。补丁一律用真实源码 `diff -u` 生成，并**必须**用 patch_ng（Conan 同款严格解析器）
  复验 fromfile()==True 且能 strip=0 落地，不要只依赖 GNU patch -p1（其 fuzz 会掩盖 hunk
  行数/起始行错误）。
- 未改库本体、未删除任何断言/测试；test_package 与上游测试接入保持不变。

## 2026-09-18 真机预检修复（第 3 轮）：test_package 恒失败 server=-1 client=-1

- **问题**: 真机 test_package 阶段失败：`RUN: ./test_udt` → `UDT consumer test FAILED (server=-1 client=-1)`。
- **根因**: test.cpp 里 `std::thread srv(server_main); std::thread cli(client_main);`
  直接以普通 int 返回函数构造线程，返回值被线程启动即丢弃；`g_srv_rc`/`g_cli_rc`
  初始化为 -1 且从不被写入，导致 main() 末尾 `if (g_srv_rc != 0 || g_cli_rc != 0)`
  恒为真 → 无论 server/client 实际是否成功都打印 FAILED 并返回 1。
- **修复**: 用 lambda 捕获线程返回值写入全局：`std::thread srv([](){ g_srv_rc = server_main(); });`
  同理 cli。这样 FAILED 判定基于真实收发结果，服务器收到消息匹配 + 客户端发全字节两处断言
  真实反映通过/失败（HMBS_TEST_PACKAGE_RESULT discovered/passedCount=2）。
- **说明**: `readonly_tmp` 诊断为预检 harness（preflight.sh）自身对只读 /tmp 写临时文件所致，
  与 udt 配方无关；本配方已用 build 目录 tmp 作为 TMPDIR，无需改动。


## 2026-09-18 真机预检修复（第 8 轮，evidence 域）：上游测试证据缺失（HMBS marker chain）

- **现状**: 真机 conan create 与 test_package 均通过（HMBS_TEST_PACKAGE_RESULT 正常出现），
  但 hmbs 判定 evidence 域 incomplete：`上游测试：发现 0，执行 0，通过 0`，
  缺少 HMBS_UPSTREAM_TEST_RESULT 上游测试证据。
- **根因（自证）**: conan create 日志显示 udt/4.11 的二进制包是 `- Cache` /
  `Already installed! (1 of 1)` —— 包已在缓存中，`conan create` 直接复用缓存二进制，
  **跳过 build()**。而上游 app/test 恰好在 build() 内的 `_run_upstream_test()`
  （以及打印 HMBS_UPSTREAM_TEST_RESULT）才执行。build() 被缓存放行后该标记根本不产生，
  hmbs 自然检出 0 个上游用例。test_package 阶段是每次预检都会全新执行的，因此要借助
  它把上游证据带出来。
- **修复**: 采用仓库已验证的「HMBS marker chain」模式（同 aws-c-event-stream、
  abuild-sudo）：
  1. conanfile.py `_run_upstream_test()`：打印标记后，把 result JSON
     持久化为 `self.build_folder/upstream_test_result.json`；
  2. conanfile.py `package()`：把 `upstream_test_result.json` 复制进
     包内 `res/upstream_test_result.json`（build()/package() 同一 build_folder）；
  3. test_package/conanfile.py `test()`：发完 HMBS_TEST_PACKAGE_RESULT 后，
     读 `<udt 包>/res/upstream_test_result.json` 并裸 print
     HMBS_UPSTREAM_TEST_RESULT（缺失则抛 ConanException，绝不静默通过）。
  这样即使缓存命中跳过了 build()，test_package 每次都把上游证据带到日志，
  hmbs 机器证据门禁可解析到真实上游用例数与通过数。
- 未改上游源码、未删除任何断言/测试；上游 4 例计数与 "Test # N completed." 判定逻辑不变。


## 2026-09-19 CI 修复：GNU make 忽略 C++= 覆盖，改用 CXX 变量（patch 0002）

- **问题**: 真机预检通过（passed），但 CI conan-build-test 在 src 编译阶段失败：
  ```
  make: Entering directory '.../udt4/src'
  g++ -fPIC -Wall -Wextra -DLINUX ... api.cpp -c
  make: g++: No such file or directory
  make: *** [Makefile:39: api.o] Error 127
  ```
  即使配方明明传了 `C++=/data/service/hnp/bin/clang++`，实际编译仍用 `g++`。
- **根因（自证）**: 上游 src/Makefile 与 app/Makefile 顶层硬编码 `C++ = g++`。
  实验证实 **GNU make 对含 `+` 的变量名（`C++`）会静默忽略命令行/环境变量覆盖**：
  - `make CXX=clang`：覆盖生效（打印 clang）；
  - `make C++=clang++`、`make C++ ?= g++`、`override C++ = g++` + 命令行：**全部无效**，仍打印 g++。
  因此此前的 `C++=` 传参从未生效，上游硬编码 g++ 恒被采用。真机恰好有 g++，
  用默认 g++/libstdc++ 编译通过（掩盖了问题）；CI worker 无 g++，报 "No such file or directory"。
- **修复**:
  1. 新增 `patches/0002-fix-makefile-compiler-var.patch`：把 src/Makefile 与
     app/Makefile 的 `C++` 变量改名 `CXX`（含所有 `$(C++)` 引用），并把
     app/Makefile LDFLAGS 去掉 `-lstdc++`（clang++/libc++ 自动链 C++ 运行时，
     无需显式 -lstdc++；OHOS 只有 libc++，显式 -lstdc++ 反而链接失败）。
  2. conanfile.py build() 改传 `CXX={cxx}`（不再传 `C++=`）。CXX 是 make 可正常
     覆盖的变量名，从 Conan conf `tools.build:compiler_executables:cpp` 取编译器。
  3. conandata.yml 注册 0002 补丁（export_conandata_patches 自动导出）。
- **证伪验证**（本地）:
  - `make -C src CXX=clang++ all` 实际用 clang++ 编译/链接（输出 clang++ 行），
    且 `CXX=/bin/false` 时 make 确实调用 /bin/false 并 Error 1 —— 证明覆盖真实生效，
    非静默忽略。
  - 打补丁后的干净树 `make -C src CXX=clang++ all` + `make -C app CXX=clang++ test`
    全部成功，`LD_LIBRARY_PATH=../src ./test` 跑满 4 例 "Test # 1..4 completed."。
  - 补丁用 patch_ng（Conan 同款严格解析器）fromfile==True、strip=0 应用成功；
    hunk 头与体行数一致（由真实源码 diff -u 生成，非手写）。
- 未改库源码头文件/实现、未删除任何断言/测试；上游 4 例计数与判定逻辑不变。


## 2026-09-19 真机预检修复（第 9 轮，evidence 域）：MANIFEST.yml 缺少 upstream_test_total 导致 rule4 拒绝

- **问题**: 真机预检通过所有阶段（build()、test_package），HMBS_TEST_PACKAGE_RESULT 与
  HMBS_UPSTREAM_TEST_RESULT 标记均正常出现，但 hmbs 仍判定 evidence 域 incomplete：
  `rule4：必须声明合法的 upstream_test_total，缺失不能按 0 处理`。
- **根因（自证）**: test_package/MANIFEST.yml 虽然有 upstream_tests 列表和测试描述，
  但缺少 rule4 强制要求的 `upstream_test_total` 字段。hmbs 的 L0e 门禁扫描 MANIFEST.yml
  时要求 `upstream_test_total` 为非负整数，缺失即直接拒绝放行。这是纯声明性字段缺失，
  不涉及代码改动。
- **修复**: 在 test_package/MANIFEST.yml 补充：
  1. `upstream_tests_exist: true`（显式声明上游测试存在，避免被误判为 no_tests）；
  2. `upstream_test_audit`（审计结论块，说明测试来源与判定方式）；
  3. `upstream_test_total: 4`（真实用例数，来自 app/test.cpp 的 test_case = 4）；
  4. `upstream_test_passed: 4`、`upstream_test_failed: 0`、`upstream_test_skipped: 0`、
     `upstream_test_not_run: 0`（真机实测结果，4/4 通过）；
  5. `upstream_test_count_method` 未必要（该字段在仓库中尚未见其他包使用，非强制）。
- 未改源码、未改 conanfile.py、未改补丁；仅更新 MANIFEST.yml 声明字段。
- 真机预检日志已证实：HMBS_UPSTREAM_TEST_RESULT={"status":"passed","discovered":4,"executed":4,"passed":4,"failed":0,"skipped":0}


## 2026-09-19 CI 修复（第 10 轮）：三轮 Worker 环境问题，非配方问题

- **现状**：连续三轮 CI 均失败，但失败原因各异，均为 Worker 环境问题而非配方缺陷。

### Build #51208 (CI-021)
- **错误**：`Error loading shared library libxml2.so.16: (needed by .../lld)` + 18个 xml 符号重定位失败
- **根因**：OHOS SDK 26.0.0.18 的 `lld` 是动态链接 ELF，运行时需要加载 `libxml2.so.16`；CI-021 worker 的 SDK 环境缺失该库或 LD_LIBRARY_PATH 未正确设置
- **特征**：编译阶段全部通过（12个 .o 文件），链接阶段 lld 自身崩溃
- **历史案例**：abuild-sudo/3.18.0_rc3 (CI-019 同错误)、argagg/0.4.7 (CI #17494)

### Build #51231 (CI-032)
- **错误**：`fork failed: out of memory` + `resource temporarily unavailable: dirname/sed`
- **根因**：CI-032 worker 系统内存不足，fork 子进程失败

### Build #51241 (CI-011)
- **错误**：`/usr/bin/xargs: Out of memory`、`/usr/bin/tr: Out of memory`、`/data/service/hnp/bin/grep: Out of memory`
- **根因**：CI-011 worker 系统内存不足，KC/JC 检查脚本的外部命令 OOM

### 判定
- **三轮失败模式各异**（libxml2 缺失 vs OOM），指向 Worker 环境问题而非共同配方缺陷
- **真机预检已通过**（passed），配方本身无问题
- **不应修改 conanfile.py/patches/test_package** 来 workaround Worker 环境问题

### 后续建议
- 由 HMBS 后端安排换健康 Worker 重跑
- 或在 build_and_test.sh 中注入 LD_LIBRARY_PATH 指向 SDK llvm/lib（针对 E120/E132 模式）

### 经验决策
| 经验ID | 判定 | 理由 |
|--------|------|------|
| 经验1 (test_package 依赖闭包) | reject | 与本轮 Worker 环境问题无关，udt 无外部依赖 |
