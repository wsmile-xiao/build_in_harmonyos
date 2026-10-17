# librtpi 1.0.0 OHOS 适配笔记（前置适配 + 真机实测）

> 2026-09-19 已在真机（LAN 10.62.178.77，HongMeng 内核 1.12.0）完成单包
> conan create 实测：**构建/打包/test_package 全部跑通**；内核 PI futex
> 探针给出明确结论——mutex PI 可用，condvar PI 重排队 ENOSYS（见 §8）。

## 1. 软件概述

- 名称：librtpi — Real-Time Priority Inheritance Library
- 版本：1.0.0（上游官方 release tag）
- 功能：在 glibc pthread 之上提供功能正确的优先级继承（PI）互斥锁与条件变量
  （基于优先级的唤醒顺序），提供 C API 与 C++ 绑定（`rtpi/mutex.hpp`、
  `rtpi/condition_variable.hpp`）。
- 许可证：LGPL-2.1-only
- 上游主库：https://gitlab.com/linux-rt/librtpi （README "Source" 声明）；
  备份镜像 github.com/linux-rt/librtpi（无 tag）；作者开发库
  github.com/dvhart/librtpi（含同一提交 f68a846e，未打 tag）。

## 2. W0 依赖发布检查

配方 `requirements()` 为空——librtpi 无任何第三方库依赖，仅依赖平台 libc/pthread。
preflight_check.sh 对空依赖配方将直接通过（本机为 Windows 环境，脚本对无依赖
场景的结论明确）。

平台级依赖逐项核实（2026-09-18 真机只读探测，SSH 非交互 + shadow PATH）：

| 依赖项 | 真机状态 | 证据 |
|---|---|---|
| pthread（create/once/atfork/mutex） | ✅ libc.so 提供 | `llvm-nm -D libc.so` 有符号 |
| `<linux/futex.h>` | ✅ sysroot 提供 | `usr/local/sysroot/usr/include/linux/futex.h` 存在 |
| `FUTEX_LOCK_PI` 常量 | ✅ 可用 | `clang -fsyntax-only` 通过 |
| pthread 取消族（setcancelstate 等） | ❌ 不存在 | `llvm-nm -D libc.so` 无符号（E127 实测复核） |
| 内核 PI futex 实现（FUTEX_LOCK_PI 等系统调用） | ❓ 未知 | 真机为 HongMeng 内核 1.12.0，`/proc/config.gz`、kallsyms 不可读；**test_package 阶段 2/3 即为运行时探针** |
| autotools（autoconf/automake/libtoolize/m4） | ❌ 缺失 | 两个工具目录均无（影响构建系统选型，见 §3） |

结论：无未发布的第三方依赖，W0 通过，无需拆分依赖库。

## 3. 源码与构建系统分析

上游 1.0.0 tag 归档（顶层目录 `librtpi-1.0.0/`）内容：

- `configure.ac` + `Makefile.am`（root/src/tests），**无生成的 configure 脚本**，
  上游 CI（.github/workflows/c-cpp.yml）执行 `autoreconf --install`；
  `configure.ac` 还使用 autoconf-archive 的 `AX_CXX_COMPILE_STDCXX_11` 宏。
- 源码仅 2 个 C 编译单元：`src/pi_mutex.c`、`src/pi_cond.c`（+ 内部头
  `pi_futex.h`、`rtpi_internal.h`），库 version-info 1:0:0（soname librtpi.so.1）。
- 可选特性：`--disable-cancellation`（上游提供，默认开启）。
- 上游测试 45 个注册程序（见 §5）。

**构建系统选型：CMake 包装（偏离上游 autotools，理由与证据如下）**

1. 真机/CI 镜像无 autoconf/automake/libtoolize/m4（§2 表格），`autoreconf`
   无法执行；CI 能力矩阵明确可用的等价工具是 cmake/ninja。
2. 仓库内先例：abiword-plugin-* 系列在能跑 autoreconf 的环境跑
   `autoreconf -fi`；libminini/1.5（2026-09-15 合入）对无构建系统上游直接
   用配方驱动编译。librtpi 介于两者之间：有构建系统但工具链缺失，且库极小
   （2 个 C 文件 + 4 个头文件），CMake 包装可 1:1 复刻上游安装布局。
3. 上游源码零修改：CMakeLists.txt 由配方 `export_sources` 导出（新增文件走
   export_sources、修改文件走 patches 的仓库惯例，参照 abiword-plugin-clarisworks）。
   因此 `patches/` 为空。
4. 映射关系：`--disable-cancellation` → `RTPI_ENABLE_CANCELLATION=OFF`；
   libtool `-version-info 1:0:0` → CMake `VERSION 1.0.0 SOVERSION 1`；
   `nobase_include_HEADERS` → 两条 `install(FILES ... DESTINATION include[/rtpi])`。

## 4. OHOS 适配结论

1. **编译可行性（已验证）**：纯 C + pthread + `<linux/futex.h>`，OHOS
   sysroot 三者齐备；musl 不提供 `__MUSL__` 宏、librtpi 也不依赖 glibc 专有
   接口（它绕过 glibc pthread mutex，直接用 PI futex 系统调用自行实现 PI）。
2. **cancellation 必须关闭（E127）**：`ENABLE_CANCELLATION` 路径调用
   `pthread_setcancelstate/pthread_setcanceltype`，OHOS musl libc 无这些符号
   （实测复核）。配方在 `os=OHOS` 时自动关闭该选项并输出 warning——这是上游
   原生支持的配置（glibc-tests 的 Makefile.am 专门维护了关闭分支），非 stub。
3. **PI futex 内核支持：已实测，部分可用**（详见 §8）：真机内核为
   HongMeng 1.12.0，无法读内核配置。test_package 探针实测结论：
   - `FUTEX_LOCK_PI`/`FUTEX_UNLOCK_PI`：**可用**（阶段 2 双线程竞争锁通过）；
   - `FUTEX_WAIT_REQUEUE_PI`/`FUTEX_CMP_REQUEUE_PI`：**ENOSYS（errno 38）**，
     condvar API 在该真机不可用（阶段 3 探测输出 UNSUPPORTED 标记）。
   属内核能力缺口，非配方缺陷；mutex 半边 API 功能完好可交付。
4. **已知 API 限制（上游自身设计，非适配裁剪）**：`RTPI_MUTEX_ROBUST`、
   `RTPI_MUTEX_ERRORCHECK` 在 1.0.0 中被注释未实现；锁不可递归（返回 EDEADLOCK）。
5. **失败先查**：`futex` 相关失败先看 errno（ENOSYS=内核缺失、EINVAL=参数/
   标志不支持）；`pthread_setcancelstate` 链接失败说明 cancellation 开关未生效。

## 5. 上游测试清点（R51 第 1 步）

`tests/Makefile.am` 注册（`make check`，均在 cancellation 开启的默认配置下计数）：

| 套件 | 数量 | 内容 |
|---|---|---|
| 顶层 | 4 | test_api、tst-cond1、tst-condpi2.sh、tst-condpi2-cpp.sh |
| glibc-tests/ | 22 | tst-cond1~25 子集 + tst-cond-except（cancellation 关闭时 17） |
| libstdc++-tests/ | 19 | 移植自 libstdc++ 的 mutex/condition_variable 回归测试 |
| **合计** | **45** | （cancellation 关闭配置：40） |

- 上游 `make check` 需要先 `autoreconf && configure && make`——真机无
  autotools，**本轮配方 build() 未集成 make check**（裁剪理由如上）；
  45 个测试中 tst-condpi2 还依赖线程优先级设置（sched_setscheduler，真机
  普通用户可能无权限）。若真机验证通过且有需要，可后续以手工命令逐套运行。
- 第 2 步（真机实测）已于 2026-09-19 完成（§8）；第 3 步（PR 回填通过率）
  随 PR 提交回填。

## 6. test_package 设计（R34 实质测试）

`test_rtpi.c` 以消费者身份链接 librtpi（CMakeDeps/CMakeToolchain 集成），
6 阶段约 23 处断言：

1. alloc/init/trylock/unlock（无竞争 CAS 快路径，任何内核可过）；
2. 双线程竞争 lock/unlock → 强制 `FUTEX_LOCK_PI`/`FUTEX_UNLOCK_PI` 慢路径；
3. **condvar 能力探测**：无信号者 timedwait 200ms——`ETIMEDOUT`=内核支持
   PI 重排队（继续阶段 4/5）；`ENOSYS`=内核未实现（打印 UNSUPPORTED 标记
   后跳过 condvar 功能阶段，exit 0）；其他返回值硬失败；
4. condvar timedwait + signal → 强制 `FUTEX_WAIT_REQUEUE_PI`/
   `FUTEX_CMP_REQUEUE_PI` 重排队路径（signal 用法遵循上游 tst-condpi2：
   不要求持锁，mutex 参数仅指定重排队目标）；
5. 无信号者 timedwait 1 秒 → 返回 ETIMEDOUT（同时验证超时不悬挂）；
6. destroy/free 生命周期。

阶段 2 即 mutex PI 探针；阶段 3 即 condvar PI 探针。设计动机：内核缺口
（ENOSYS）是平台事实而非包缺陷，硬失败会让包永远无法交付且不增加信息；
显式标记 + 其余异常照常失败，既保住 R34 实质性，又不掩盖真 bug。

## 7. 本机已完成的验证（2026-09-18）

- 源码下载与校验：GitLab canonical tag 归档两次独立下载 sha256 一致
  （`7115cbdd…`），内容与 API 归档逐字节一致（diff -r）。
- W0：无第三方依赖（见 §2），平台级依赖逐项真机核实。
- 真机只读探测：工具链、sysroot 头文件、libc 符号（§2 表格）。
- 配方静态验证：`conan export` 解析 + Lint 通过（无警告/错误），test_package
  结构完整（conanfile.py/test_rtpi.c/CMakeLists.txt/MANIFEST.yml）。
- 不可行项：本机为 Windows，`validate()` 正确拒绝 `os=Windows`
  （librtpi 仅 Linux 族）；无 WSL，无法本机交叉验证 PI futex 行为。

## 8. 真机实测结果（2026-09-19，LAN 10.62.178.77）

入口：`ohos-test-runner.sh --user gcw --mode smoke --try-lock --path /data/service/hnp/bin
--workdir $HOME/build_in_harmonyos -- zsh ci/conan/build_and_test.sh archives/l/librtpi/1.0.0`
（`CI_PACKAGES=archives/l/librtpi/1.0.0`；源码经 Conan 备份缓存
`CONAN_CORE_SOURCES_DOWNLOAD_CACHE` 预置，sha256 校验通过）。

**conan create（构建+打包+test_package）**：

| 项 | 结果 |
|---|---|
| conan create（构建+打包） | ✅ librtpi.a + 4 头文件 + LICENSE |
| test_package 3/3 消费者程序 | ✅ test_rtpi（6 阶段 API 冒烟+内核探针）、consumer_checks（错误路径/PSHARED）、consumer_cpp（C++ 绑定） |
| Build Summary | Total: 1, Success: 1, Failed: 0；L0 pass / L1 pass / L2 skip(纯库) / L4 pass / L5 pass |
| 内存安全 | 全程 jobs=1，未触发 OOM |

**上游测试实跑（R51 第 2 步，真机手工编译执行，源码零修改）**：

- 可执行子集 19 项：test_api、顶层 tst-cond1、glibc-tests 17 项（对应
  --disable-cancellation 上游分支）。编译环境 shim（不改测试源码）：
  glibc `<error.h>`、`M_PERTURB`、test_api 的 `main(int, char*)` 签名别名。
- **通过率 7/19（36.8%）**：PASS = test_api + tst-cond9/16/18/19/20/21
  （不触发内核重排队路径的用例）；FAIL 12 项全部为 condvar 用例触发
  `FUTEX_WAIT_REQUEUE_PI` → ENOSYS（errno 38），无其他失败原因。
- 未执行 22 项的逐项原因：libstdc++-tests 19 项依赖 GNU libstdc++ 内部
  头文件（bits/c++config.h、ext/typelist.h），OHOS 使用 libc++ 无法编译；
  tst-condpi2.sh / tst-condpi2-cpp.sh 2 项需 sched_setscheduler 线程优先级
  特权；glibc-tests 取消分支 5 项（cancellation 开启配置专属，本包按 E127
  使用上游关闭分支）。

**平台结论**：HongMeng 内核 1.12.0（该真机）实现了基本 PI futex
（LOCK_PI/UNLOCK_PI），未实现 PI 重排队族（WAIT_REQUEUE_PI/CMP_REQUEUE_PI）。
librtpi 的 mutex API 功能完好（含竞争路径）；condvar API 运行期返回 ENOSYS。

**过程踩坑记录**：
1. 首跑 `cmake: not found`（Error 127）——真机 `$HOME/usr/local/bin/cmake`
   及 `aarch64-unknown-linux-ohos-clang` 包装器被并行任务删除（共享前缀
   污染，E524 同类）；改用 `/data/service/hnp/bin` 工具链（runner `--path`
   / profile compiler_executables 同源）解决。
2. `liblibrtpi.a` 双前缀——CMake 对 `add_library(librtpi)` 自动加 lib 前缀，
   与 `cpp_info.libs=["rtpi"]` 错位；`OUTPUT_NAME rtpi` 修复。
3. `build_and_test.sh` 位置参数在该 runner 链路未生效——**必须用
   `CI_PACKAGES` 环境变量**；误触发的全仓扫描（260 包）已立即终止并按单包重跑。
4. 上游测试直跑需注意：clang++ 会把 `.c` 按码当 C++ 编译（sys_futex/gettid
   报错）——库源码须先用 C 编译器出 .o；真机 `/tmp` 只读，clang 与 shell
   heredoc 都需要 TMPDIR/TMPPREFIX 指向可写目录。

## 9. 下一步：shadow CI / PR

前置：worktree `D:\harmonyos\worktrees\librtpi`，分支 `feat/librtpi-1.0.0`
（真机单包验证已完成，见 §8；以下为复现命令与合入步骤）。

1. **真机单包复现**（走隔离 runner；必须 `CI_PACKAGES` 环境变量，勿用位置参数）：
   ```sh
   export CI_PACKAGES="archives/l/librtpi/1.0.0"
   export CONAN_CORE_SOURCES_DOWNLOAD_CACHE=$HOME/tmp/librtpi/bkcache  # 预置源码备份
   ohos-test-runner.sh --user gcw --lib librtpi --task librtpi-<ts> --mode smoke \
     --try-lock --path /data/service/hnp/bin --workdir $HOME/build_in_harmonyos -- \
     zsh ci/conan/build_and_test.sh archives/l/librtpi/1.0.0
   # exit 75 = 锁忙；结果在 $HOME/ohos-test-runs/<RUN_DIR>/logs/
   ```
2. **shadow CI 单包验证**：
   ```sh
   CI_PACKAGES="archives/l/librtpi/1.0.0" zsh ci/conan/build_and_test.sh
   # 确认 Build Summary Total: 1，L0/L1 pass，L2 对纯库可 skip，L5 产物在 lib/、include/
   ```
3. **推分支 + PR**：
   ```sh
   git fetch origin && git rebase origin/main
   git push https://gitcode.com/gcw_6YxinkyD/build_in_harmonyos.git feat/librtpi-1.0.0
   ```
   PR 标题 `feat(librtpi): 1.0.0 编译完成`；描述三要素见 §10；PR 中必须
   如实写明 condvar ENOSYS 平台缺口（引用 §8 证据）。
4. **跑通后可选：上游完整测试**（需先解决 autotools 缺失或手工编译 tests/）：
   ```sh
   clang -std=c11 -I src tests/test_api.c src/pi_mutex.c src/pi_cond.c -lpthread -o test_api && ./test_api
   ```

## 10. 常见合入问题自查

- 软件与目录名 `librtpi`、版本 `1.0.0`，单包单分支单 PR。
- 仅新增 `archives/l/librtpi/` 下文件与 1 个 librtpi 相关知识草稿；未动
  SKILL/references/templates/scripts/ci/index.tsv/SUMMARY.md。
- 官方 HTTPS 源 + 固定 sha256（GitLab 官方 tag 归档，字节稳定已验证）。
- 纯库交付，无 `commands.json`（R38）；无 patch 文件（上游零修改）。
- `test_package` 非空壳：实际链接库并调用公开 API（PF3/R34）；
  ENOSYS 能力探测语义已在 MANIFEST.yml 与 §6/§8 说明。
- `manifest.yaml` 状态已更新为 `built`（真机实测通过，含平台限制说明）。
