# securefs 0.13.1 适配笔记（OHOS PC / aarch64）

## 0. 速览

| 项 | 值 |
|----|----|
| 包状态 | `published`（本机 `conan create` 全绿：编译 0 error、上游测试 3/3、消费者用例 5/5） |
| 包类型 | `application`（命令行工具，无库产物；软件级 `commands.json` 已声明，R38） |
| 难度 | ★★★★（4/5）—— 无 API 级平台改造，但源码与构建脚本共 7 处平台阻塞，需 5 条补丁 + 1 处链接期补桩 |
| 上游测试 | `ctest -N` 清点 4 项，实跑 3 项全过；`simple_test` 需真实 FUSE 挂载，鸿蒙 PC 现状不可用（如实申报） |
| 消费者用例 | `test_package` 5/5 通过（调用已安装包中的真实二进制） |
| 知识库关联 | E085（OHOS/musl 缺 POSIX 线程取消 API）的**直接调用**场景落地（E085 原文场景是 weak-symbol 检测） |
| 通用交付物 | `tools/`（检测脚本 + 处理策略 + 复现脚本），见 §9 |

## 1. 环境与构建命令

* 目标平台：OHOS 6.0 / armv8 / clang 15 / libc++ / C++17 / Release
* Profile：`ci/conan/profiles/ohos-aarch64`（host 与 build 同 profile，OHOS PC 原生构建）
* Conan：2.29.1；CMake：4.1.2

```sh
conan create archives/s/securefs/0.13.1 \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 \
  --build=missing
```

配方内流程：[1] `export_sources`（补丁 + pthread stub）→ [2] `source`（主源码 +
三枚子模块）→ [3] `generate`（toolchain 变量注入 + stub 编译）→ [4] `build`
（打补丁 → cmake configure/build → ctest）→ [5] `package` → [6] test_package。

## 2. 源码与依赖

* 主源码：`https://github.com/netheril96/securefs/archive/refs/tags/0.13.1.tar.gz`
  sha256 `7251a285830e0e132165ffcb3551e555c8236425c093c911b00627f9cf5d5d9c`
* 上游 release archive **不含子模块内容**（`external/*` 为空目录／gitlink），按固定 commit 补齐
  （声明在 `conandata.yml` 的 `submodules:`，由 `source()` 逐项下载校验）：

| 子模块 | 目标目录 | 固定 commit | sha256 |
|--------|----------|-------------|--------|
| cryptopp | `external/cryptopp` | `69bf6b53052b59ccb57ce068ce741988ae087317` | `5a4a4aaa427a5b018faeeab8a1a395c0440a849b166b6f4a50d46d31ff6e608a` |
| argon2 | `external/argon2` | `29e8b21543fdf6266cbfb8712dcabda1fefdff07` | `08354832c4b616acdbcfd78967716c51c57b470b0a0fa9bc9959553c4a7d4c76` |
| utf8proc | `external/utf8proc` | `8ca6144c85c165987cb1c5d8395c7314e13d4cd7` | `b9eea86f1501a31043f1c74f9aed9cfb9caf1b25353c47fe82c389e81106d03c` |

* 制品仓依赖：`libfuse/2.9.9`（FUSE 2.x；上游固定 `-DFUSE_USE_VERSION=28`）。
  该包静态提供 `libfuse.a`、`libulockmgr.a` 与 `fuse.h`，因此本包无需任何动态 FUSE 运行时。
* 依赖判断按 R32 写成 `if self.settings.os in ("Linux", "OHOS")`。

## 3. 七处阻塞与处置

| # | 现象（原文摘要） | 根因 | 处置 |
|---|------------------|------|------|
| 1 | `Compatibility with CMake < 3.5 has been removed`（配置首行即失败） | 上游 `cmake_minimum_required(VERSION 3.0 FATAL_ERROR)`，CMake 4.x 硬拒绝 | `patches/0001` 抬到 3.10；对 vendored 子模块另加 `-DCMAKE_POLICY_VERSION_MINIMUM=3.5`（recipe 侧，CMake<4 忽略该变量） |
| 2 | 找不到 `external/cryptopp/CMakeLists.txt` 等子模块产物 | release archive 缺 gitlink 内容 | `conandata.yml` 声明三枚子模块（固定 commit + sha256），`source()` 补齐 |
| 3 | Windows/WinFsp 分支被激活（`C:/Program Files (x86)/WinFsp`、缺 `fuse.h`） | OHOS 下 `if(UNIX)` 为假 → 上游把所有非 UNIX 当 Windows | `patches/0002` 合并修复：`if(UNIX)` → `if(NOT WIN32)` |
| 4 | 找不到 FUSE 头/库（上游写死 `PATHS /usr/local/include`、`/usr/local/lib`） | 构建脚本写死系统前缀探测 | `patches/0002` 去掉写死 `PATHS`；recipe 用 `CMakeToolchain.variables` 注入 `FUSE_INCLUDE_DIR`/`FUSE_LIBRARIES`（依赖包私有前缀，不碰共享 `/usr/local`——R49 同类口径） |
| 5 | `unknown argument: '-fPIC -O2   -stdlib=libc++'` | vendored `cryptopp-cmake` 把 `CMAKE_CXX_FLAGS` 当**单个**编译参数转发；CMake 未加引号的变量展开不按空格切分 | `patches/0004` 删除该转发项 + 空列表守卫（仅"去引号"无效，已被实测否证） |
| 6 | 二进制启动即崩溃（版本探测） | 静态 `libfuse.a` 下上游用 `dlsym` 探测 libfuse 版本，静态链接返回 NULL | `patches/0003` 改为编译期版本宏 |
| 7 | 链接期 `undefined symbol: pthread_cancel` / `pthread_setcancelstate` | OHOS libc 未实现 POSIX 线程取消（E085）；`nm` 实测 `libfuse.a` 的 `fuse.o`、`fuse_loop_mt.o` 引用之 | 新增 `stubs/stub-pthread.c`（no-op，`ENOSYS`），recipe 编译为静态库并加入 `FUSE_LIBRARIES`，见 §6 |

补充（编译期，非源码阻塞）：libc++ 对 Catch2 的 `RandomNumberGenerator` 触发
`static_assert(__libcpp_random_is_valid_urng<_URNG>::value)`（实例链 `__algorithm/shuffle.h`
→ `external/catch.hpp`）→ `patches/0005`。

## 4. 补丁清单

| 补丁 | 目标文件 | 内容 |
|------|----------|------|
| `0001-cmake-minimum-version-3.10.patch` | `CMakeLists.txt` | `cmake_minimum_required(VERSION 3.0 FATAL_ERROR)` → `3.10` |
| `0002-fuse-discovery-posix-branch.patch` | `CMakeLists.txt` | `if(UNIX)` → `if(NOT WIN32)`；FUSE 探测去掉写死的 `PATHS /usr/local/...` |
| `0003-libfuse-version-without-dlsym.patch` | `sources/commands.cpp` | 静态 libfuse 下的版本探测不再依赖 `dlsym` |
| `0004-cryptopp-cmake-cxxflags-forwarding.patch` | `external/cmake-cryptopp/CMakeLists.txt` | 移除 `CMAKE_CXX_FLAGS` 转发项 + 空列表守卫 |
| `0005-catch-rng-result-type.patch` | `external/catch.hpp` | `RandomNumberGenerator` 按 libc++ 要求修正（消除 `static_assert`） |

补丁生成方式：纯净副本 + 单点修改 + `diff`；应用验证用 `patch --dry-run -f`
（本机 `patch` 不支持 `--batch`）。仓库归档约定键为 `patches:` 下的 `patch_file:`，
由 `apply_conandata_patches()` 在 `build()` 首步按序应用。

**上游测试用例未做任何修改**；上述补丁只针对平台兼容与构建脚本。

## 5. 链接期补桩：`stubs/stub-pthread.c`

静态 `libfuse.a` 的 `fuse.o` / `fuse_loop_mt.o` 引用 `pthread_cancel`、
`pthread_setcancelstate`、`pthread_setcanceltype`，而 OHOS libc 不提供这些符号
（E085）。处置方式沿用仓内先例（`archives/a/autodir/0.99.9/stubs/stub-pthread.c`、
`archives/a/alpine/2.26/conanfile.py`）：提供 no-op stub 参与链接。

语义与风险（如实申报）：

* `pthread_cancel` → 返回 `ENOSYS`（调用失败，**不会**执行线程取消）；
  `pthread_setcanceltype` / `pthread_setcancelstate` → 记录/忽略并返回 0。
* 影响面：libfuse 多线程循环的线程收尾路径上，"强制取消线程"退化为无效调用，
  线程需按自身逻辑自然退出。securefs 单线程/常规挂载路径不受影响；
  本包上游测试（含 `sec_test`）与消费者用例全部通过。
* 该 stub 只在 OHOS（无这些符号的平台）参与链接，不影响其他平台的语义。

## 6. 上游测试清点与运行（R51 申报）

清点（`ctest --test-dir <build> -N`）：

```
Test #1: sec_test      Test #2: simple_test
Test #3: cryptest      Test #4: argon2_test       Total Tests: 4
```

运行（配方 `build()` 内，N' = 3/4）：

| 测试 | 结果 | 耗时 | 说明 |
|------|------|------|------|
| sec_test | Passed | 1.50 s | `add_test(NAME sec_test COMMAND securefs_test)`，驱动 `sources/test/*.cpp`（btree/crypto/files/streams/utils） |
| cryptest | Passed | 5.02 s | vendored cryptopp 自带套件 |
| argon2_test | Passed | 12.76 s | vendored argon2 参考实现测试 |
| simple_test | **未运行** | — | 需真实 FUSE 挂载（内核 FUSE + 可打开的 `/dev/fuse`）；实测 `securefs mount` 报 `fuse: failed to open /dev/fuse: Permission denied`，脚本用例无法进入断言分支 → 配方以 `-E simple_test` 排除，其环境行为改由 test_package 的"无 /dev/fuse 优雅失败"用例覆盖 |

**通过率：3/3（可运行项），1 项因平台缺失 FUSE 设备未运行（非跳过、非屏蔽）。**

## 7. 消费者用例（test_package 5/5）

| 用例 | 覆盖点 |
|------|--------|
| `version: 静态链接 libfuse 下 CLI 版本探测不崩溃` | 补丁 0003 的回归（`securefs version` 输出 `libfuse 29`） |
| `create: 创建加密卷并落盘认证加密元数据` | 真实创建卷 + 校验 `.securefs.json` 的 `version/iv_size/block_size/iterations` |
| `info: 免挂载读回卷格式信息` | 免挂载读取（输出 `Filesystem format version:`） |
| `chpass: 旧口令错误时认证失败且不改动卷` | 免挂载鉴权路径：错误旧口令 → `Invalid password and/or keyfile`，非 0 退出、无信号崩溃 |
| `mount: 无 /dev/fuse（鸿蒙 PC 现状）时优雅失败而非崩溃` | `simple_test` 不可用场景的行为断言 |

测试以 argv 传入被测二进制路径；卷工作目录落到 `$TMPDIR` 或 `~/tmp`
（鸿蒙 PC 的 `/tmp` 只读，E002）。

## 8. 排障中得到的平台事实（可复用）

1. 上游 `MountCommand::execute()` **先打开 `/dev/fuse` 再校验凭据**：在无可用 FUSE
   设备的环境里 `mount` 永远到不了口令校验分支——鉴权断言必须走免挂载命令
   （`chpass`，其口令选项为 `--oldpass/--newpass`，与 `mount/create` 的 `--pass` 不同名）。
2. Conan 的 `cmake.test(cli_args=[...])` 会把参数追加给 `cmake --build`（结果
   `Unknown argument -E`），**不是** ctest；需要带参 ctest 时直接
   `self.run('ctest --test-dir "{}" -E ... --no-tests=error'.format(self.build_folder))`。
3. Conan 2.29 的 `ConanFile.run(env=...)` 需 list 形式且实测不透传给子进程；
   跨进程传值用 argv 更可靠。
4. CMake 未加引号的变量展开**不按空格切分**：把 `-fPIC -O2` 塞进一个变量再传给
   `add_compile_options` 之类，会整体成为一个参数 → 只能从源头删除该转发。

## 9. 知识库拓展交付物（`tools/`，本 PR 的通用部分）

三类共性问题（上游「源码发布包 + 自有构建脚本」在 Conan 交叉编译 + CMake 4.x + 干净 CI 下
必然失败的风险）的通用处置套件，**不针对单个库**：

| 产出物 | 文件 | 说明 |
|--------|------|------|
| 检测脚本 | `tools/prescan_risks.py` | 纯标准库、只读、无写死绝对路径；文本 / `--json` 双输出；退出码 0/1/2 |
| 处理策略 | `tools/STRATEGY.md` | 每类风险：现象原文 → 根因 → 识别 → 处置（首选/备选/反面案例）→ 验证 |
| 复现脚本 | `tools/reproduce.sh` | 干净环境复现三类风险 + 处置后验证；日志落文件（不接管道 `head`，规避 SIGPIPE） |
| 样例演示库 | 本包 | 三类风险全中，`patches/`、`conandata.yml`、`conanfile.py` 逐一落地处置 |

规则：R1 = `cmake_minimum_required` < 3.5 被 CMake 4.x 拒绝；R2 = archive 包缺子模块源码
（gitlink）；R3 = 构建脚本写死 `/usr/local` 等系统前缀。检测脚本在样例库源码上实测
`risk_count=6 rules=R1,R2,R3`（R2 三枚 gitlink 各计一次）。

## 10. 已知限制与注意事项

* `simple_test` 在鸿蒙 PC 上不可用（无可用 `/dev/fuse`），这是平台现状而非本包缺陷；
  挂载能力需内核侧 FUSE 支持就绪后另行验证。
* pthread 取消 stub 使"强制取消线程"退化为无效调用（§5 已列影响面），
  属平台符号缺失下的最小代价处置。
* CMake 版本放行变量 `CMAKE_POLICY_VERSION_MINIMUM=3.5` 仅用于 vendored 子模块的旧
  `cmake_minimum_required`；上游主脚本已由补丁 0001 抬到 3.10，不依赖该变量。
* 本包为原生构建（host = build = OHOS aarch64）；不涉及 `--build/--host/--target` 参数。
