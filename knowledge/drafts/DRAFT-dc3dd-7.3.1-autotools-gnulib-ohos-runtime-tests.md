# DRAFT-dc3dd-7.3.1-autotools-gnulib-ohos-runtime-tests - old Autotools + gnulib CLI on OHOS

- 贡献者: AtomCode (GLM-5.2) / OpenHarmonyPCDeveloper 适配线程
- 状态: draft，仅作为路径 B / B 类难度候选材料提交评审
- 来源事件: dc3dd 7.3.1 HarmonyOS PC 适配，Shadow CI 多轮定位后完成构建、打包、test_package 与上游文件成像/哈希脚本验证
- 关联提交: `feat/dc3dd-7.3.1-codex` 分支适配结果；最终提交号以 PR 分支为准

## 知识类型与提升边界

本草稿属于“老 Autotools + 捆绑 gnulib + HarmonyOS/musl libc 能力差异 + 真机上游功能测试补位”的组合型经验。它面向路径 B / B 类候选沉淀，不分配正式 E 编号，也不声明已经获得 B 类认定；是否提升为正式知识、是否计入 B 类难度，以维护者和赛事评审结论为准。

dc3dd 不是单一编译开关问题。一次完整适配连续暴露并解决了配置、编译、链接、文档生成、打包、消费者验证、上游功能测试七个面的问题，且每个面都有可迁移到其他老 GNU/gnulib CLI 包的判断规则。

## 触发场景

适用于具备以下特征的包：

- 上游是老 Autotools 发布包，内含生成好的 `configure`、`Makefile.in` 和 gnulib 代码。
- 构建目标是单个或少数 CLI，可通过 Conan `package_type = "application"` 打包。
- 源码使用 gnulib 的 stdio helper，如 `freadahead.c`、`freadptr.c`、`freadseek.c`、`fseterr.c`。
- 上游 `make check` 不覆盖真实功能脚本，或者测试脚本需要设备端可写目录、fixture、信号/中断行为。
- 构建时试图禁用 `help2man`、`makeinfo` 等文档工具，但上游 `man` 目录仍有生成或安装规则。

## 问题模型

dc3dd 7.3.1 在 HarmonyOS PC 上不是一次失败，而是一条逐层展开的问题链：

1. **旧 config.guess/config.sub 不认识 OHOS**
   - `config.guess` 无法识别 HarmonyOS 内核名。
   - `config.sub` 不接受 `aarch64-unknown-linux-ohos`。
   - Autoconf 2.61 的临时目录默认 `umask 077` 在 HMDFS 构建目录下可能制造后续访问问题。

2. **gnulib stdio helper 假设可访问 libc 私有 FILE 结构**
   - `freadahead`、`freadptr`、`freadseek`、`fseterr` 依赖 glibc/BSD 等公开或半公开内部字段。
   - HarmonyOS 的 libc 行为更接近 musl，`FILE` 对调用方是不透明对象，不能靠 `_IO_read_ptr`、结构字段或私有标志位补丁硬读写。
   - 可复用处理方式是：对可降级查询函数返回安全保守值；对 `fseterr` 这类必须设置错误位的函数，使用公开 API 和 fd 级 fallback，避免猜测内部结构。

3. **`pthread_cancel` 缺失不能用空 stub 糊过去**
   - dc3dd 的主线程在退出时取消 signal handling thread。
   - OHOS 目标环境没有可直接链接使用的 `pthread_cancel` 路径，链接阶段暴露 undefined symbol。
   - 本例可复用的关键点不是“随便 return 0”，而是看线程角色：该线程处于信号等待路径，可用 `pthread_kill(signal_thread, SIGINT)` 唤醒 `sigwait`，再 `pthread_join` 回收，保持生命周期闭环。

4. **`HELP2MAN=/bin/true` 不等于文档规则全部安全**
   - release 的 `man` 规则会直接调用捆绑 Perl `man/help2man`，并依赖 `Locale::gettext`。
   - 即使 configure 传入 `HELP2MAN=/bin/true`，顶层 `make` 仍可能进入 `man` 子目录触发 Perl 依赖。
   - dc3dd 的可复用处理是只构建代码目录 `lib` 和 `src`，打包时复用 release 已带的 `man/dc3dd.1`，避免生成时依赖目标环境的 Perl 模块。

5. **上游真实测试不等于 make check**
   - 该 release 的功能脚本位于 `tests/`，但未接入默认 `SUBDIRS` / `make check`。
   - `tests/test-hashing.sh` 覆盖大量 MD5/SHA-1 fixture。
   - `tests/test-file-imaging.sh` 覆盖文件成像、分片、多个输出、校验输出、pattern、错误参数和中断路径。
   - 设备端还要处理 `/tmp` 不可写、release ZIP 缺少 `test_data/reference_images/ref-pat.img`、高速存储导致上游固定 `sleep 1` 中断竞态等测试环境问题。

## 推荐处理模式

1. **先把 Autotools 平台识别和 HMDFS 权限问题稳定住**
   - 补 `config.guess` / `config.sub` 的 `linux-ohos` 识别。
   - 对老 Autoconf 生成脚本中的 `umask 077` 做 HMDFS-safe 调整。
   - configure 通过指定 shell 执行，避免 release 脚本可执行位在传输/解压后不可靠。

2. **gnulib stdio patch 要按函数语义分类**
   - 只读缓存信息的 helper：OHOS/musl 分支返回保守值或禁用不可达内存指针路径。
   - 设置错误位的 helper：优先使用公开 API 或 fd fallback，不直接写 `FILE` 内部字段。
   - patch 必须保留其他 libc 原分支，避免把 Linux/glibc 行为回退。

3. **线程取消 fallback 要保留 joinable lifecycle**
   - 先读线程函数，确认是否有协作退出点、信号等待点、条件变量或事件循环。
   - dc3dd 这类 signal handling thread 可用 `pthread_kill(..., SIGINT)` 唤醒，再 `pthread_join`。
   - 禁止定义假 `pthread_cancel()` 返回成功，因为这会让线程继续运行，后续资源销毁可能出现挂起或竞态。

4. **文档生成规则不要只看 configure 参数**
   - 审计 `Makefile.am` / `Makefile.in` 的 `SUBDIRS`、`man` 目标和 `install` 规则。
   - 如果 release 已带手册页，优先构建代码目录并在 `package()` 中复制已发布文档。
   - 如果 release 不带手册页，再考虑清空 `man_MANS` 或提供真正可用的 host-side `help2man`。

5. **CLI 包消费者测试必须验证包内二进制**
   - `package_info()` 声明 `bindirs = ["bin"]`。
   - `test_package` 运行安装后的 `dc3dd`，覆盖版本、编译默认 hash、文件成像、分片输出和 pattern 生成。
   - 对系统可能也存在同名工具的 CLI 包，推荐用依赖元数据拼绝对路径；dc3dd 目标环境未发现系统同名遮蔽，但该策略可复用。

6. **上游功能脚本要单独记录环境调整**
   - 明确写出是否执行了官方脚本、执行数量和跳过原因。
   - 设备端只改临时测试副本，不把 fixture 合成、路径替换、sleep 调整提交到源码。
   - release 缺 fixture 时，必须标注“合成 fixture”，不能宣称完整官方 fixture 验证。

## B 类难度候选依据

本适配可作为 B 类候选的理由不是补丁数量本身，而是问题链覆盖面与验证闭环：

- **问题面跨度大**：configure 平台识别、HMDFS 权限、gnulib/musl libc 兼容、pthread lifecycle、Perl man rule、Conan packaging、上游运行测试全部参与。
- **失败演进有可复用诊断价值**：r2 暴露 `fseterr` 后进入 `pthread_cancel`，r3 暴露 `Locale/gettext.pm`，r4 才形成可交付构建链。
- **补丁不是简单平台宏绕过**：`fseterr` 和 `pthread_cancel` 都需要理解上游语义，避免伪成功或行为改变。
- **测试不是 smoke-only**：除 `test_package` 外，真机还跑了 532 个 MD5、523 个 SHA-1 fixture，`test-file-imaging.sh` 29 个结果阶段通过。
- **边界记录完整**：device imaging / damaged-device imaging 需要真实设备路径和权限，已明确延期；release 缺官方 pattern fixture 已标注合成验证。

## 与已有知识的差异

- 与 E020 / E429 的关系：既有条目覆盖 musl `FILE` opaque 或 `sizeof(FILE)`，本草稿强调 gnulib stdio helper 的函数级语义分类，尤其是 `fseterr` 需要设置错误位，不能只用“返回 0”解决。
- 与 E085 / E127 / E513 的关系：既有条目覆盖 pthread cancel 缺失和 joinable thread lifecycle，本草稿给出 signal-waiting thread 的具体变体，即用应用已有 `sigwait` 信号路径唤醒并 join，而不是创建通用 signal handler。
- 与 E289 的关系：既有条目覆盖 `HELP2MAN=true` 后安装缺失 man 页，本草稿触发点是构建阶段直接进入捆绑 Perl `help2man` 且缺 `Locale::gettext`，可用“只构建代码目录 + 复用 release 手册页”处理。
- 与 coreutils-sha512sum 草稿的关系：同属 GNU/gnulib 单工具打包，但 dc3dd 的重点不是 `BUILT_SOURCES`，而是老 gnulib libc 兼容、线程取消和设备端功能脚本验证。

## 禁止做法

- 禁止把 `pthread_cancel` 定义为空 stub 或宏替换成 0。
- 禁止直接访问、强转或猜测 `FILE` 私有布局。
- 禁止把 `HELP2MAN=/bin/true` 当成文档规则已处理完成。
- 禁止只跑 `dc3dd --version` 就宣称 CLI 功能通过。
- 禁止把远端临时测试副本的 fixture 合成和 sleep 调整提交为上游源码补丁。
- 禁止把需要块设备路径和权限的 destructive/device-node 测试写成已通过。

## 已验证样例

- 库: `dc3dd/7.3.1`
- 构建系统: Autotools release tarball/zip with bundled gnulib
- 适配动作:
  - 8 个版本内补丁覆盖 config、HMDFS umask、gnulib stdio helper、pthread cancellation fallback。
  - Conan recipe 禁用 NLS/hdparm，显式构建 `lib` 与 `src`，手动打包二进制和 release 手册页。
  - `test_package` 验证版本、hash 默认项、文件成像、分片输出和 pattern 生成。
- 真机结果:
  - `conan create` r4 通过 build/package/test_package。
  - `test-hashing.sh` 532 MD5 + 523 SHA-1 fixture，0 mismatch。
  - `test-file-imaging.sh` 29 个结果阶段通过。

## 证据来源

- 配方与补丁: `archives/d/dc3dd/7.3.1/conanfile.py`、`archives/d/dc3dd/7.3.1/patches/`
- 验证记录: `archives/d/dc3dd/7.3.1/manifest.yaml`
- 适配说明: `archives/d/dc3dd/7.3.1/notes.md`
