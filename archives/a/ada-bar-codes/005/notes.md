# ada-bar-codes 005 适配笔记

## 编译环境
- 构建系统: custom（GNAT 工程文件 `ada_bar_codes.gpr`，gprbuild/gnatmake -P 构建）
- 编译日期: 2026-08-19
- 编译器: GNAT 13.2.1（OHOS 基础工具链无 Ada 编译器；经调研确认 Harmonybrew core tap 无 gnat/gprbuild 配方，
  故改用 Alpine aarch64 musl gcc-gnat 13.2.1 apk 直接引导（同 argc/1.24.0 的 bottle 下载先例，
  OHOS 为 musl libc，与 Alpine 同族）
- 状态: built（真机预检通过后由 HMBS 统一提交上传）

## 上游信息
- 官方项目: https://ada-bar-codes.sourceforge.io/（SourceForge: ada-bar-codes）
- GitHub 镜像: https://github.com/zertovitch/ada-bar-codes
- 版本: 005（归档 abc_005.zip，bar_codes.ads 内 version 常量 "005"，14-Sep-2024）
- 许可: MIT（版权声明内嵌于 bar_codes.ads 头部）
- 归档 sha256: `15c9774f049e70614d9f6dabf5a7e2f4bc3c0800b86c55910646767e6597932f`
  - 与 Alire bar_codes 5.0.0 发布的 sha512 `c211b27c...` 校验一致，确认是官方归档
- 语言: 纯 Ada 2012，无任何外部依赖（只依赖 Ada 标准库），OS/CPU/编译器无关

## 编译步骤
1. `conan create` 时 `get()` 下载 abc_005.zip（zip 内顶层目录为 `abc/`，strip_root=True）
2. `_ensure_ada_toolchain()`：探测 PATH/harmonybrew/hnp 中 gnatmake/gprbuild；无则引导 Alpine musl GNAT：
   - 用 Python urllib 下载 Alpine v3.20 main aarch64 官方 apk（设备 curl 无 CA bundle，
     与 argc/1.24.0 相同处理：优先指向系统 CA store，无则 unverified TLS 兜底）
   - 校验每个 apk 的 sha256（表内硬编码，来自官方 CDN 实测）
   - 解包到 `~/gnat-toolchain/13.2.1`（tarfile 直接解 gzip tar）
   - 设置 GCC_EXEC_PREFIX / ADA_INCLUDE_PATH / ADA_OBJECTS_PATH / LIBRARY_PATH /
     LD_LIBRARY_PATH（重定位 GCC 子程序、Ada runtime 与共享库）
3. `gprbuild -P ada_bar_codes -XABC_Build_Mode=static -j1`（无 gprbuild 时回退 gnatmake）
   → 产出 `obj/static-lib/libada_bar_codes.a`（静态库）与 `obj/static-obj/*.ali`（Ada 链接信息）
4. `gprbuild -P ada_bar_codes -XABC_Build_Mode=Fast -j1`
   → 产出 `bar_codes_test`（上游测试）与 `bar_codes_demo`（示例）
5. 运行 `./bar_codes_test` 生成条码 PNG，作为上游测试
6. package: 静态库 + `.ali` 文件进 lib/，`.ads` 规格文件进 include/

## 上游测试
- 测试程序: `test/bar_codes_test.adb`（gpr 的 Fast 模式作为 Main 构建为 `bar_codes_test` 可执行文件）
- 覆盖: Code 128、MSI、EAN-13、UPC-A、Data Matrix、QR（4 个纠错级别）共 82 次条码渲染
  - 统计：Test_128 23 次 + Test_MSI 6 次 + Test_EAN13 10 次 + Test_UPCA 1 次 + Test_2D 6×7=42 次 = 82
- 说明：6 个 MSI 样本复用同一文件名，磁盘上实际为 77 个非空 PNG 文件
- 断言方式：任一编码失败抛 `Cannot_Encode` 异常 → 退出码非零；退出码 0 即全部渲染成功
- HMBS 标记：`HMBS_UPSTREAM_TEST_RESULT` 的 discovered/executed/passed 取真机实际生成的 PNG 文件计数

## test_package（消费者冒烟测试）
- `bar_codes_smoke.adb`：Ada 消费者程序，真实调用库 API
  - `Bar_Codes.Fitting (Code_128, "Hello")` → 校验 1D 模块尺寸非空
  - `Bar_Codes.Fitting (Code_QR_Low, "Hello")` → 校验 2D 模块尺寸非空
  - `Bar_Codes_Media.SVG_Bar_Code (Code_QR_Low, 100.0, 100.0, "mm", "Hello")` → 校验 SVG 输出非空
- 编译方式：gnatmake `-I<include>`（.ads 规格）+ `-aL<lib>`（.ali 链接信息）+ `-largs -L<lib> -lada_bar_codes`（静态库）
- 复用主配方引导的 `~/gnat-toolchain/13.2.1` 工具链（同一机器同一 home），环境变量设置与主配方一致
- 3 项断言，全部通过才输出 `HMBS_TEST_PACKAGE_RESULT` 标记

## 遇到的问题与解决方案
| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 真机预检 harmonybrew 安装失败（curl SSL 证书校验失败、brew update 下载 portable-git 失败） | 设备 curl 无 CA bundle（已知问题，argc/agent-browser 先例）；且 Harmonybrew core tap（克隆核验 4733 个 formula）**不含 gnat/gprbuild 配方**，即使 brew 装上 `brew install gnat gprbuild` 也会 formula not found | 弃用 harmonybrew 路径；改为直接用 Python urllib 下载 Alpine aarch64 musl gcc-gnat 13.2.1 官方 apk（含 gcc-gnat/libgnat/libgnat-static/gcc/binutils/gmp/mpfr/isl/mpc1/zlib/libgcc/libstdc++/libgomp/libatomic/musl-dev/jansson/zstd），校验 sha256 后解包到 `~/gnat-toolchain/13.2.1`，用 GCC_EXEC_PREFIX/ADA_*_PATH/LD_LIBRARY_PATH 重定位；GPR 头注释确认 `gnatmake -P ada_bar_codes` 与 gprbuild 等效 |
| 2 | OHOS /tmp 只读（readonly_tmp 诊断） | OHOS 根文件系统只读 | build/test_package 统一使用 HMBS 注入的 TMPDIR/TMP/TEMP（HMBS_TMPDIR/TMPDIR 优先，兜底 ~/tmp/ada-bar-codes），注入 gnatmake 子进程 |
| 3 | 真机预检 `gnatmake: Permission denied`（Error 126，编译阶段） | HMDFS 忽略 chmod()（知识 E046/E087，平台能力 chmod=0）：tarfile.extractall() 解包 Alpine apk 时靠 os.chmod 恢复 tar 头里的执行位，chmod 静默失效，二进制保持 umask 077 创建模式（0600）无执行位；而 HMDFS 上 os.access(X_OK) 又不可靠（返回可执行），shutil.which 找到路径后实际 execve 失败 | 新增 `_repair_exec_bits()`：遍历 `~/gnat-toolchain/13.2.1` 下 usr/bin 与 usr/libexec（cc1/gnat1 所在），对 `stat.S_IMODE & 0o111` 无执行位的普通文件，用 `os.open(tmp, O_WRONLY|O_CREAT|O_TRUNC, 0o755)` 写入内容再 `os.replace` 原子替换（HMDFS 认 open 创建时 mode，同 aribb24 install shim 先例）；在 `_ensure_ada_toolchain()` 复用已有工具链与新建引导两条路径都调用 |
| 4 | 第 2 轮真机预检仍 `gnatmake: Permission denied`（Error 126，同一指纹） | 第 3 条修复未生效：① HMDFS 进程 umask 077 会把 os.open 的 0o755 剥成 0700（只剩 owner 执行位）；② HMDFS 把文件 owner 映射成与进程不同的 UID（E011：文件 owner UID 20001006 vs 进程 UID 20020083），owner 位永远匹配不上 → execve 仍 EACCES；③ 上轮 stat 判断用 `& 0o111`，0700 也含 owner 执行位被判为"已修复"直接跳过，永远不会再重建 | 换策略：`_repair_exec_bits()` 改为 **umask(0) 强制 0o755**（o+x 全用户执行位，非 owner 进程也能 exec）+ 跳过条件改为 `& 0o001`（仅当已有 world-exec 才跳过）+ unlink 后 os.open(O_EXCL, 0o755) 重建（不用 rename）；新增 `_verify_gnat_exec()` 真实执行 `gnatmake --version` 探针，os.access/stat 在 HMDFS 上都不可靠，只有真跑一次才能证明可执行；`_gpr_build()` 兜底绝对路径（which 可能返回 None）；主配方与 test_package 同步修改 |
| 5 | 第 3 轮真机预检仍 EACCES（`[Errno 13] Permission denied`，同一指纹；日志显示 repair 已重建 usr/libexec 下文件为 0o755 但仍失败） | **位置问题而非 mode 问题**：探针证明 mode=0o755（o+x 齐全）仍 execve EACCES。`~/gnat-toolchain`（home 根）位于 OHOS noexec 存储（E257 草稿/djstub 草稿：用户可写位置拒绝直接 exec，仅 /data/service/hnp 可执行；与 shebang 脚本 Permission denied/exit 126 同源）；而 conan build_folder 可执行（argc/1.24.0 的 rust-toolchain 就在 self.build_folder 下解包，cargo.real 直接运行成功） | 新策略：**工具链从 home 根迁移到 `self.build_folder/gnat-toolchain`**——`_GNAT_ROOT` 模块常量删除，改为实例方法 `_gnat_root()`（`os.path.join(self.build_folder, "gnat-toolchain")`）；`_gnat_env` 由 staticmethod 改实例方法；apk 下载缓存移到共享的 `~/.cache/ada-gnat-apks`（home 根只读/写无妨，仅 exec 受限）；test_package 在自己的 build_folder 镜像引导（argc test_package 同款，apk 走共享缓存）；保留 _repair_exec_bits + _verify_gnat_exec 双保险 |

## 源码修改
无补丁。上游纯 Ada 代码不依赖平台 API，无需任何 OHOS 适配修改。

## 依赖版本
- GNAT / gprbuild: Alpine musl gcc-gnat 13.2.1（`~/gnat-toolchain/13.2.1`，含 gprbuild 运行时组件与 gnatmake）
- 库本身无 Conan 依赖（dependencies: []）

## 验证结果
```bash
# 真机预检（由 HMBS 在 HarmonyOS PC aarch64 环境执行）：
conan create . -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
# 上游测试：./bar_codes_test 生成 77 个非空 PNG（82 次渲染）
# test_package：./bar_codes_smoke 3 项断言
```

## 注意事项
- OHOS 无 Ada 编译器，本配方引导 Alpine musl GNAT 到 `~/gnat-toolchain/13.2.1`（同一台真机 home 共享，
  test_package 直接复用；重定位依赖 GCC_EXEC_PREFIX/ADA_INCLUDE_PATH/ADA_OBJECTS_PATH/LD_LIBRARY_PATH）
- 静态库链接需要 `.ali` 文件，已随包发布到 lib/ 目录；Ada 消费者用 gnatmake -aL 指向
- 上游无 tag/release，版本 005 以 SourceForge 官方归档 abc_005.zip 为准（GitHub 镜像无 tag，master 已是 006）
- Alpine apk 的 sha256 已在配方内硬编码（来源：dl-cdn.alpinelinux.org 官方 CDN 实测），下载后严格校验，
  防止镜像内容漂移；设备无 CA bundle 时按 argc/1.24.0 先例回退 unverified TLS（仅针对固定官方镜像）

## 第四轮修复（2026-08-19）：换执行路线 — 真机 loader 显式调用 + 原生 ELF 启动器
- **失败证据**：第 4 轮日志显示工具链已在 `build_folder/gnat-toolchain`（第 3 轮位置）且 usr/libexec 文件已
  重建为 0o755，探针 `gnatmake --version` 仍 `[Errno 13] Permission denied` —— 排除了 mode 与位置两个旧假设。
- **决定性根因（本地取证）**：解包 Alpine gcc-gnat apk 检查 gnatmake 是 aarch64 ELF（非脚本），
  PT_INTERP = `/lib/ld-musl-aarch64.so.1`（本地 Python 解析 ELF program headers 实证）。OHOS 的 musl loader
  不在该路径，直接 execve 一律 EACCES，与 chmod/位置/umask 无关。E257 草稿只覆盖 shebang 脚本；
  djstub 草稿证实"用户存储可执行 OHOS 原生 ELF"（djlink/djstrip 先例）——问题专属于 Alpine musl 二进制的
  PT_INTERP 路径缺失。
- **新方案（第 4 轮，替换前 3 轮"修执行位/换位置"路线）**：
  1. `_find_loader()`：解析已知可执行文件的 PT_INTERP（`/proc/self/exe`=python3、`/data/service/hnp/bin/bash`）
     定位真机原生 musl loader，并用 `[loader, gnatmake, --version]` 逐候选实测验证（显式 loader 调用可绕过
     内核对该 ELF 的 exec 检查，djstub explicit-interpreter-invocation 模式）。
  2. `_install_wrappers()`：用 OHOS clang 编译一个原生 ELF 启动器（djstub 模式，`/proc/self/exe` basename
     解析真实工具路径），复制为 `<root>/wrappers/<tool>`（覆盖 usr/bin 与 usr/libexec/gcc/<triple>/<ver> 全部
     可执行名），每个包装器 `execv(loader, [loader, real_tool, args...])`；PATH 前置 wrappers 目录 +
     GCC_EXEC_PREFIX=wrappers，使 gnatmake→gnat1→as/ld 整条子进程链都经真机 loader 运行。
  3. `_gnat_env()` 的 LD_LIBRARY_PATH 增加 `<root>/lib`（新增 Alpine `musl-1.2.5-r3.apk`，提供
     libc.musl-aarch64.so.1，sha256 `e455c49c...` 本地实测）。
  4. 上游 `bar_codes_test` 与 test_package 的 `bar_codes_smoke` 均为工具链链接产物（同样携带
     `/lib/ld-musl-aarch64.so.1` 解释器），统一改为 `[loader, exe]` 显式启动。
  5. `build()` 去掉 `env="conanbuild"`（该 env 文件是 generate() 时快照，会丢掉激活后的 PATH/GCC_EXEC_PREFIX/
     LD_LIBRARY_PATH），改用当前 os.environ。
- 测试口径不变：上游 77 个非空 PNG / 82 次渲染，test_package 3 项断言，标记格式与计数不变。
- 第 3 轮"build_folder 可执行（argc 先例）"结论被第 4 轮日志证伪：argc 的 cargo.real 是 OHOS 原生 bottle，
  PT_INTERP 指向 OHOS loader，故可执行；Alpine 工具链不满足该前提。

## 第五轮修复（2026-08-19）：loader 发现容错 + 拷贝重建（第 2 次同域修复，非重复）
- **本轮失败证据**：日志已进入 `_find_loader()`，首个候选 `/lib/ld-musl-aarch64.so.1` **在真机上存在**，
  但 `subprocess.run([cand, gnatmake, ...])` 抛 `PermissionError: [Errno 13] Permission denied:
  '/lib/ld-musl-aarch64.so.1'` —— 该 loader 文件存在但**不可执行**（execve 它本身被拒），这也解释
  rounds 1-3 直接 execve gnatmake 为何必 EACCES（内核按 PT_INTERP 加载解释器时因解释器不可执行而拒绝）。
- **上一版（第 4 轮）为何无效**：① `_find_loader()` 探针未捕获 OSError，首个候选 PermissionError 直接
  崩溃，后续候选（包括真正可执行的 loader）根本没被尝试；② 候选来源 `/proc/self/exe`（OHOS SELinux
  大概率拒绝 open）与 `/data/service/hnp/bin/bash`（可能不存在）的 `_elf_interp()` 均返回 None，导致
  固定路径 `/lib/ld-musl-aarch64.so.1` 成为首个被探的候选。
- **本轮修改（主配方 + test_package 同步，仅工作树未提交）**：
  1. 新增 `_probe_loader()`：探针永不抛异常——OSError（EACCES/ENOENT/ENOEXEC）返回 rc=-1 并记录，
     供调用方走拷贝重建分支；每种候选试两套环境：默认（Alpine libc 走 `<root>/lib` LD_LIBRARY_PATH）
     与去掉 `<root>/lib`（让真机自身 /lib 下的 libc.musl-aarch64.so.1 满足 soname）。
  2. 新增 `_copy_loader_candidate()`：对"存在但不可执行"的 loader 文件，读字节 → 校验 ELF magic →
     umask-0 `os.open(0o755)` 重建副本（djstub 原理：新建的 OHOS 原生 ELF 带 o+x 即可从用户存储执行），
     副本放 build_folder（跨预检持久）。
  3. `_find_loader()` 候选来源改为**已验证可执行**的二进制：HMBS_PYTHON3（hmbs 注入的真实 python3 绝对路径）、
     sys.executable、/bin/sh（HMBS_PLATFORM_CAPABILITIES 声明的 shell）、/data/service/hnp/bin 下的
     python3/cmake/make/ninja/bash —— 解析它们的 PT_INTERP 得到的 loader 按构造必然可执行；
     固定路径与 glob 兜底保留。逐候选记录 probe 结果，失败继续下一个。
  4. 新增 `import sys`。
- 测试口径不变（上游 77 PNG / test_package 3 断言）。

## 第六轮修复（2026-08-19）：loader 副本改用无 .so 后缀名 + 对照探针（同指纹第 3 次，换路线）
- **本轮失败证据（决定性转折）**：日志显示 `_find_loader()` 已探到多个候选但全部 execve 被拒：
  - `/system/lib/ld-musl-aarch64.so.1`（真机系统 loader）→ EACCES；
  - round-5 的副本 `.../gnat-loader-ld-musl-aarch64.so.1`（os.open umask-0 0o755 重建）→ 仍 EACCES。
  - 结论：**连 0o755 重建的 OHOS 原生 loader 副本都无法 exec**，问题不在位置、不在 mode、不在二进制来源，
    而在**文件名含 `.so`**（副本保留了源 basename `ld-musl-aarch64.so.1`）。
- **交叉验证（仓库实证）**：djstub 0.7 的启动器（clang 编译、包 bin 内、文件名 `djlink/djstrip/djelfextract`
  无 .so）在 test_package 直接 exec 成功（PR 已合入）；argc/1.24.0 的 bash shim（clang 编译、build_folder 内、
  名 `bash`）真机 probe OK（第 20-22 轮，219 用例通过）。而 Alpine 工具链二进制（gnatmake 等）失败是因为
  内核按 PT_INTERP=/lib/ld-musl-aarch64.so.1 加载解释器时解释器文件不可 exec → 整条 execve EACCES。
- **上一版（第 5 轮）为何无效**：副本 `_copy_loader_candidate` 保留源 basename（含 `.so.1`），仍被 exec 策略
  拒绝；且探针无对照实验，无法区分"用户存储不可 exec"与"loader 文件本身被拒"。
- **本轮修改（主配方 + test_package 同步，仅工作树未提交）**：
  1. `_copy_loader_candidate()` 副本改为**固定无 .so 名 `gnat-ldso-aarch64`**（同时消除 /lib 与 /system/lib
     basename 冲突）；创建后打印 stat mode、副本自身 PT_INTERP 与 e_type 作机器证据。
  2. 新增 `_elf_e_type()`（e_type 2=EXEC/3=DYN）、`_exec_probe()`（通用 exec 探针，永不抛异常）、
     `_copy_file_0755()`（通用 0o755 拷贝）。
  3. `_find_loader()` 开头新增**对照探针**：`/bin/sh -c exit 0`（证明 subprocess exec 可用）与
     `/bin/sh` 的 0o755 无 .so 副本 `gnat-ctl-sh` exec（证明"拷贝的 OHOS 原生 ELF + 0o755 + 无 .so 名"
     在用户存储可执行——djstub/argc 同款机制）；候选日志补充 realpath 与 e_type。
- 若 `gnat-ldso-aarch64` 探针通过：返回该副本作为 loader，wrapper 链（PATH 前置 + GCC_EXEC_PREFIX）
  与 `[loader, exe]` 测试启动照常工作；若连无 .so 副本仍被拒且对照探针显示 sh 副本可执行，则证明
  loader 文件内容被策略拒绝，需另寻 GNAT 来源（届时如实上报）。
- 测试口径不变（上游 77 PNG / test_package 3 断言）。

## 第七轮修复（2026-08-19）：PT_INTERP 重写，内核直接加载系统 loader（换路线，当前生效）
- **本轮判定**：前一轮（round 6）preflight 日志显示 `_find_loader()` 探到 `/system/lib/ld-musl-aarch64.so.1`
  （真机系统 loader）存在，但 `execve` 该 loader —— 无论原始路径、0o755 拷贝、还是去掉 `.so` 后缀名的
  副本 `gnat-ldso-aarch64` —— 全部被拒（EACCES）。即 rounds 4-6 的“显式 loader 调用 + wrapper 链”路线
  依赖“从用户存储 exec 真机 loader”，该前提被真机证据证伪：连 OHOS 原生 loader 副本在用户存储都不能 exec。
- **换路线（round 7，当前工作树/源码状态）**：放弃显式 loader 调用，改为**原地重写 Alpine ELF**：
  1. `_rewrite_elf()`：把每个 Alpine 二进制的 PT_INTERP（`/lib/ld-musl-aarch64.so.1`，24 字节）在 EOF 追加
     设备的实际 loader 路径并回写 program header 的 p_offset/p_filesz/p_memsz（新路径更长故须重定位到 EOF）；
     再把 .dynstr 里 DT_NEEDED 的 `libc.musl-aarch64.so.1` 原地改写为 `libc.so`（等长 NUL 补齐），
     使设备 musl loader 把 libc 映射到自身（与所有 OHOS 原生二进制一致）。
  2. `_device_interp()`：从真实可执行的二进制（HMBS_PYTHON3 / sys.executable / /bin/sh / hnp python3/bash）
     的 PT_INTERP 取 loader 路径，兜底 `/system/lib/ld-musl-aarch64.so.1`（round-6 已证存在）。
  3. 让**内核**在 exec 重写后的 ELF 时直接按 PT_INTERP 加载规范路径上的系统 loader —— 与 python3/clang/make
     等任何原生二进制完全相同的机制，完全绕开“从用户存储 exec loader”这个被证伪的依赖。
  4. `_activate_toolchain()` = `_repair_exec_bits()`（umask-0 0o755）+ `_rewrite_toolchain()`（全树重写）+
     `_ctl_no_pie_probe()`（诊断）+ env + `_verify_gnat_exec()`（真跑 `gnatmake --version` 作为硬门禁）。
  5. 上游 `bar_codes_test` 与 test_package `bar_codes_smoke`（均为 gnatmake 链接产物，携带 Alpine 解释器）
     构建后同样 `_rewrite_elf()` + `_copy_file_0755()` 后直接 exec（round-7 模型）。
- 主配方与 test_package 两侧均已同步为该模型（`_probe_loader()` 均改为 raise 占位，不再走 loader 调用）。
- 本轮仅确认并交接该工作树模型（未在本机真跑 conan）；是否有效由下一次真机预检判定。
- 测试口径不变（上游 77 非空 PNG / test_package 3 断言）。

## 第八轮修复（2026-08-19）：OHOS XPM ELF 签名（换路线，当前生效）
- **本轮失败证据（round 8 preflight）**：`rewrote 81 toolchain ELF files` 之后，
  `ctl no-pie e_type=2` 探针 `exec rc=0`（**真机 clang 原生编译的 ET_EXEC 二进制在
  build_folder 内可正常 exec**），但 `_verify_gnat_exec()` 仍报
  `gnatmake is not executable after PT_INTERP rewrite (...) interp='...' e_type=2:
  [Errno 13] Permission denied`。
- **上一方案（round 7，PT_INTERP 重写）为何无效**：round-8 日志证明 PT_INTERP 重写
  + 0o755 之后，Alpine 二进制 exec 仍被 EACCES；而**同一位置的 OHOS 原生 clang 产物
  （ctl-nopie）exec 正常**。两者差异不在位置、权限位或 loader 路径，而在 ELF 本体：
  知识库 E258（clang/22.1.8）root cause (5) 与 E077 明确——**OHOS XPM 要求 bin/ ELF
  与 lib/*.so 必须经 binary-sign-tool 自签（.codesign + .note.ohos.ident），未签名的
  外来 ELF 一律 exec/dlopen 报 Permission denied**。rounds 4-7 从未做签名，只做了解释器
  与权限修复，故同一指纹反复出现。
- **本轮修改（round 8，主配方 + test_package 同步，仅工作树未提交）**：
  1. 新增 `_sign_tool()`（定位 /data/service/hnp/bin/binary-sign-tool）、
     `_remove_codesign()`（llvm-objcopy 移除旧 .codesign，E077 步骤 1）、
     `_sign_elf()`（binary-sign-tool sign -selfSign 1，随后 byte-identical 0o755 重建
     恢复执行位——签名会把 mode 清零为 000，E077 步骤 4；HMFS chmod 不可靠）、
     `_sign_toolchain()`（遍历工具链 usr/ 下所有 ELF 签名）。
  2. `_activate_toolchain()` 顺序改为：repair → rewrite（PT_INTERP/DT_NEEDED）→
     **sign（签名必须覆盖重写后的最终字节）** → ctl-no-pie 探针 → env → verify。
  3. 上游 `bar_codes_test` 与 test_package `bar_codes_smoke` 在 `_rewrite_elf()` +
     `_copy_file_0755()` 之后同样 `_sign_elf()` 再 exec。
  4. binary-sign-tool 缺失时仅 warning 并继续（工具在 hnp 固定路径，E077 确认存在）。
- 测试口径不变（上游 77 非空 PNG / test_package 3 断言）。

## 第九轮修复（2026-08-19）：签名存活重写——改用 patchelf（section-aware）换路线（当前生效）
- **本轮失败证据（round 9 preflight）**：`rewrote 81 toolchain ELF files` →
  `OHOS-signed 92 toolchain ELF files` → `ctl no-pie exec rc=0` 之后，
  `_verify_gnat_exec()` 仍报
  `gnatmake is not executable after PT_INTERP rewrite (...) interp='' e_type=2:
  [Errno 22] Invalid argument`。
- **上一方案（round 8，binary-sign-tool 签名）为何无效**：round-8 的 `_rewrite_elf`
  把设备 loader 路径**追加在 ELF 文件 EOF**、再手工改写 PT_INTERP program header
  （p_offset/p_filesz/p_memsz）指向该 EOF 偏移。round-9 日志证明该方案被签名破坏：
  `binary-sign-tool sign` 在写 .codesign 时会**重建 ELF 文件**，EOF 处的手工追加字节
  不属于任何 section，重建后即丢失；PT_INTERP 仍指向旧 EOF 偏移，读取结果为空串
  （`interp=''`），内核 exec 因解释器为空报 EINVAL（[Errno 22]，与 round-8 的 EACCES
  不同——说明签名已生效，失败点转移到被破坏的 interp）。
- **本轮修改（round 9，主配方 + test_package 同步，仅工作树未提交）**：
  1. 放弃手工 EOF 追加重写；改用**设备自带 patchelf**（E077 验证的 OHOS ELF 编辑工具，
     参考 /data/service/hnp/bin/patchelf）：`patchelf --set-interpreter <设备loader>`
     修改 PT_INTERP、`patchelf --replace-needed libc.musl-aarch64.so.1 libc.so`
     修改 DT_NEEDED——patchelf 的改动是 **section-aware** 的（更新真实 .interp
     section 与 program header），签名重建 ELF 时随 section 保留，不会丢失。
  2. 新增 `_patchelf_tool()`（探测 patchelf 路径）、`_elf_needed()`（--print-needed
     读 DT_NEEDED 列表，用于幂等判断）、`_patchelf()`（执行器，失败仅 warning）。
  3. `_rewrite_elf()` 重写：仅当文件有 PT_INTERP 且 != 设备 loader 时
     --set-interpreter；仅当 DT_NEEDED 含 libc.musl-aarch64.so.1 时 --replace-needed；
     保持幂等（已改写文件两项都跳过）。
  4. 顺序不变：repair → rewrite(patchelf) → sign(binary-sign-tool) → 探针 → env →
     verify；E077 文档的四步流程即为 patchelf 修改后再签名，签名覆盖 patchelf 后的
     最终字节。
  5. 上游 bar_codes_test 与 test_package bar_codes_smoke 同样走 patchelf + 签名。
- 若 patchelf 缺失或对 Alpine 格式拒绝处理，warning 后继续，verify 会以描述性错误
  暴露真实原因（届时如实上报）。
- 测试口径不变（上游 77 非空 PNG / test_package 3 断言）。

## 第十轮修复（2026-08-19）：gnatmake 直接构建替代 gprbuild/-P 项目文件（换路线，当前生效）
- **本轮失败证据（round 10 preflight）**：工具链激活全部通过（rewrote/OHOS-signed/ctl
  no-pie rc=0），**gnatmake 已能执行**（round 9 patchelf 路线生效），但 build() 报
  `gnatmake: project files are no longer supported by gnatmake; use gprbuild instead`
  → `ConanException: Error 4 while executing`（build() line 804，static 模式构建）。
- **根因**：GNAT 13.2.1 的 gnatmake 已移除 `-P` 项目文件支持（GPR 头注释里
  "gnatmake -P ada_bar_codes" 的等价说法对该版本不再成立）；且 Alpine v3.20
  main/community APKINDEX 中**无 gprbuild apk**（实测仅有 grpc 的无关 libgpr），
  无法通过 apk 引导 gprbuild。旧 `_gpr_build()` 优先 which("gprbuild") 未命中后
  回退 `gnatmake -P ada_bar_codes`，必然失败。
- **本轮修改（round 10，仅主配方，工作树未提交）**：`_gpr_build(mode)` 改为
  **gnatmake 直接构建**，按 ada_bar_codes.gpr 语义复刻两种模式：
  1. static：`mkdir -p obj/static-obj obj/static-lib` →
     `gnatmake -c -D obj/static-obj -Ofast -gnatn *.adb`（编译根目录全部库单元，
     含 bar_codes-encode_* 子单元）→ `ar rcs obj/static-lib/libada_bar_codes.a
     obj/static-obj/*.o`（ar 来自 binutils apk，同样已 patchelf+签名可执行）。
  2. Fast：`gnatmake -Ofast -gnatn -o bar_codes_test -I. -Itest -Idemo -Itools
     test/bar_codes_test.adb`（GPR Main=bar_codes_test.adb，Exec_Dir="." →
     产物落在 source_folder/bar_codes_test，与 _run_upstream_tests 期望一致）。
  3. 编译参数取 GPR Compiler_Fast_Options 的 `-Ofast -gnatn`；严格告警/风格开关
     （-gnatwaC/-gnaty*）为诊断项，不影响正确构建，省略。
  4. package() 期望路径不变（obj/static-lib/libada_bar_codes.a、obj/static-obj/*.ali、
     根目录 *.ads），产物布局与 GPR 一致。
- test_package 无需改动：其编译命令是 gnatmake 直接编译单个 .adb（-I -aL -largs），
  从未使用 -P。
- 测试口径不变（上游 77 非空 PNG / test_package 3 断言）。

## 第十一轮修复（2026-08-19）：工具链共享库 RUNPATH（E186/E266 路线，当前生效）
- **本轮失败证据（round 11 preflight）**：static 构建第一步即失败——
  `gnatmake -c -D obj/static-obj -Ofast -gnatn *.adb` 已能执行（round 9/10 的
  patchelf+签名路线验证有效，gnatmake/gcc 均 exec 成功），但 gcc 驱动 gnat1 时：
  `Error loading shared library : (needed by .../gnat-toolchain/usr/libexec/gcc/
  aarch64-alpine-linux-musl/13.2.1/gnat1)` 与 `Error relocating .../gnat1:
  : symbol not found`（大量重复）→ `gnatmake: "bar_codes-encode_code_128.adb"
  compilation error` → ConanException Error 4。
- **根因（证据链）**：gnatmake/gcc 只需 libc（loader 把 libc.so 映射为自身）故能跑；
  gnat1 额外依赖 libmpfr.so.4/libgmp.so.10/libisl.so.23/libmpc.so.3/libz.so.1/
  libgcc_s.so.1（解包在 <build_folder>/gnat-toolchain/usr/lib 与 usr/lib/gcc/
  aarch64-alpine-linux-musl/13.2.1）。OHOS musl ldso 使用 namespace 机制，
  **LD_LIBRARY_PATH 对非标准路径二进制无效**（知识库 E186 根因、E266 同指纹：
  `Error loading shared library libxml2.so.16: (needed by .../lld)` +
  `Error relocating .../lld: xmlFreeDoc: symbol not found`），loader 只认
  RPATH/RUNPATH 与系统默认路径 → gnat1 找不到其数学库依赖。
- **上一版（round 9/10）为何"不够"**：patchelf --set-interpreter + --replace-needed
  只解决了"内核能否 exec / libc 能否解析"，没有解决"非 libc 共享库能否被 loader
  找到"；LD_LIBRARY_PATH（_gnat_env 已设）在 OHOS namespace 机制下不生效。
- **本轮修改（round 11，主配方 + test_package 同步，仅工作树未提交）**：
  1. 新增 `_elf_has_dynamic()`：解析 program headers 判断 PT_DYNAMIC（patchelf
     --set-rpath 对静态二进制会报错，仅改动态 ELF）。
  2. 新增 `_elf_rpath()`：`patchelf --print-rpath` 读当前 RUNPATH（幂等判断）。
  3. 新增 `_toolchain_rpath()`：返回 `<root>/usr/lib:<root>/usr/lib/gcc/
     aarch64-alpine-linux-musl/13.2.1`（存在才收录）。
  4. `_rewrite_elf()` 追加第 3 步：动态 ELF 且当前 RUNPATH 未含目标目录时
     `patchelf --set-rpath <usr/lib>:<gcc_lib>`（与既有 RUNPATH 合并去重），
     仍在 sign 之前执行（签名覆盖最终字节，E077 patchelf→sign 顺序）。
     工具链所有 ELF（usr/ 下可执行文件与 .so）及新链接的 bar_codes_test /
     bar_codes_smoke 统一走该路径。
  5. `_patchelf()` 超时 120s→300s（gnat1/cc1 体积大，patchelf 慢路径耗时）。
  6. 主配方 `_activate_toolchain()` 在 `_verify_gnat_exec()` 后新增
     `_probe_compile()`：用 gnatmake -c 编译最小 Ada 单元，全链路
     gnatmake→gcc→gnat1 真实走一遍，把任何残留 loader 错误提前暴露在 build()
     之前（下轮日志可直接判定 RUNPATH 修复是否生效）。
- 测试口径不变（上游 77 非空 PNG / test_package 3 断言）。

## 第十二轮修复（2026-08-19）：_elf_has_dynamic 关闭句柄 seek 修复（round-11 代码自身缺陷，当前生效）
- **本轮失败证据（round 12 preflight）**：激活流程进入 _rewrite_toolchain()（repair 完成、
  `device interpreter: /lib/ld-musl-aarch64.so.1` 已打印），随后 build() 崩溃：
  `while calling '_rewrite_elf', line 539 -> if self._elf_has_dynamic(path): ->
  while calling '_elf_has_dynamic', line 357 -> fh.seek(e_phoff) -> ValueError:
  seek of closed file`（ConanException → conan create 退出码 1）。
- **根因**：round-11 新增的 `_elf_has_dynamic()` 实现缺陷——`with open(path,"rb") as fh:`
  块内只读取 64 字节 ELF 头，块退出即关闭文件；后续 `fh.seek(e_phoff)` / `fh.read(...)`
  却在 with 块外执行，对已关闭句柄 seek 抛 ValueError。主配方与 test_package 两处同名
  函数同样缺陷（镜像复制所致）。这是 round-11 引入的实现 bug，RUNPATH 方案本身尚未被
  真机验证（被本 bug 挡在 _rewrite_toolchain 阶段），不属于方案失败，无需换路线。
- **本轮修改（round 12，主配方 + test_package 同步，仅工作树未提交）**：
  1. `_elf_has_dynamic()` 整体解析移入 with 块内：块内读头 → 判 ELF magic/长度 →
     unpack e_phoff/e_phentsize/e_phnum → fh.seek(e_phoff) → fh.read(phdrs)；块外仅做
     PT_DYNAMIC 遍历判断。文件句柄生命周期与所有 I/O 严格一致。
  2. docstring 记录 round-12 失败指纹，防止回归。
- **本地验证**：AST 提取两配方 `_elf_has_dynamic` 函数体，构造 4 个样本（非 ELF /
  无 PT_DYNAMIC 的 ELF / 含 PT_DYNAMIC 的 ELF / 短文件）实测：False/False/True/False，
  不再抛 ValueError；两文件 py_compile 与 AST 均通过。
- 测试口径不变（上游 77 非空 PNG / test_package 3 断言）。

## 第十三轮修复（2026-08-19）：补齐 gnat1 缺失的运行时库实体（mpfr4/isl26/zstd-libs + lib/ 前缀 RUNPATH）
- **本轮失败证据（round 13 preflight）**：激活全通——`rewrote 81 toolchain ELF files`、
  `OHOS-signed 92 toolchain ELF files`、`ctl no-pie exec rc=0`（round-12 seek bug 已修复，
  RUNPATH 已写入，日志可见 `rpath=/usr/lib/../lib:<build>/gnat-toolchain/usr/lib:
  <build>/gnat-toolchain/usr/lib/gcc/aarch64-alpine-linux-musl/13.2.1`）。但 `_probe_compile`
  仍失败：`gnatmake probe compile failed (gnat1 shared-lib load, RUNPATH fix
  insufficient?): rc=4 tail='...gnat1: : symbol not found
Error relocating ...gnat1:
  : symbol not found'`；HMBS 平台诊断提示 [stale_runtime_library]（测试进程加载系统旧库）。
- **根因（本地取证，非猜测）**：下载全部 Alpine apk 解包 + 解析 gnat1/cc1 的 DT_NEEDED：
  - gnat1 NEEDED = `libisl.so.23, libmpc.so.3, libmpfr.so.6, libgmp.so.10, libz.so.1,
    libc.musl-aarch64.so.1`；cc1 相同。
  - **mpfr-dev/isl-dev 只含 .a 与未版本化 .so 符号链接，版本化实体在独立运行时包**
    （Alpine 包命名：`mpfr4-4.2.1-r0.apk` 提供 libmpfr.so.6、`isl26-0.26-r1.apk` 提供
    libisl.so.23；APKINDEX 证实 mpfr-dev 依赖 mpfr4=4.2.1-r0、isl-dev 依赖 isl26=0.26-r1）。
    配方原来只下载了 -dev 包 → **libmpfr.so.6 / libisl.so.23 实体根本不存在**，
    即使 RUNPATH 正确也加载失败（Error relocating 空符号即实体缺失的表现）。
  - **Alpine apk 存在两个 lib 前缀**：绝大多数在 usr/lib（gmp/mpc1/libgcc/binutils...），
    但 **zlib 在 lib/ 前缀**（lib/libz.so.1）、musl 也在 lib/（lib/ld-musl-aarch64.so.1、
    lib/libc.musl-aarch64.so.1）。上一轮 `_toolchain_rpath()` 只含 usr/lib 与 gcc_lib，
    **漏了 `<root>/lib`** → libz.so.1 仍找不到。
  - **zstd CLI apk 不含共享库**：binutils as 的 NEEDED 含 libzstd.so.1，由独立包
    `zstd-libs-1.5.6-r0.apk`（usr/lib/libzstd.so.1）提供，原配方缺。
- **本轮修改（round 13，主配方 + test_package 同步，仅工作树未提交）**：
  1. `_ALPINE_APKS` 新增 3 个运行时包（sha256 均为本地实测）：
     `mpfr4-4.2.1-r0.apk`(1be0b3ca...)、`isl26-0.26-r1.apk`(869b52e2...)、
     `zstd-libs-1.5.6-r0.apk`(accb1881...)，放于对应 -dev/CLI 包前。
  2. `_toolchain_rpath()` 增加 `<root>/lib`（Alpine lib/ 前缀：libz.so.1、musl 库）。
  3. `_gnat_env()` 的 LD_LIBRARY_PATH 同步加入 `<root>/lib`（一致性，虽然 OHOS loader
     忽略 LD_LIBRARY_PATH，RUNPATH 才是生效路径）。
  4. 校验：21 个 apk 条目 sha256 与本地下载逐一比对全部 OK；两文件 py_compile/AST 通过；
     本地解析确认 mpfr4/isl26/zstd-libs 提供 libmpfr.so.6/libisl.so.23/libzstd.so.1 实体。
- 测试口径不变（上游 77 非空 PNG / test_package 3 断言）。

## 第十四轮修复（2026-08-19）：lib/ 前缀 ELF 纳入重写与签名（换路线，消除双 libc）
- **本轮失败证据（round 14 preflight）**：`rewrote 84 toolchain ELF files`、
  `OHOS-signed 95 toolchain ELF files`（round-13 的 mpfr4/isl26/zstd-libs 已生效，
  81→84 / 92→95）、`ctl no-pie exec rc=0`；HMBS 平台诊断打印
  `ct2: needed=libc.so, rpath=<build>/gnat-toolchain/lib:<build>/gnat-toolchain/usr/lib:
  <build>/gnat-toolchain/usr/lib/gcc/aarch64-alpine-linux-musl/13.2.1`（gnat1 的
  NEEDED 已含 libc.so、RUNPATH 三目录已就位）。但 `_probe_compile` 仍失败：
  `gnat1: : symbol not found` / `Error relocating <gnat1>: : symbol not found`，
  rc=4——与 round-13 完全同指纹。
- **上一方案（round 13，"缺 mpfr4/isl26/zstd-libs 实体 + lib/ RUNPATH"）为何无效**：
  round-14 日志证明实体已存在、RUNPATH 已覆盖三目录，且错误中无
  "Error loading shared library" 行（库全部加载成功），失败发生在 gnat1 自身
  重定位阶段——"缺库实体"假设被证伪，必须换根因。
- **根因（本地取证，非猜测）**：下载全部 apk 解包 + pyelftools 分析 gnat1 与依赖库：
  1. gnat1 结构：ET_EXEC、DF_1_NOW(BIND_NOW)、.rela.dyn 1088（1082 GLOB_DAT +
     6 R_AARCH64_COPY[1024]：stdin/stdout/stderr/__gmp_version/__stack_chk_guard/
     __environ）、.rela.plt 518 JUMP_SLOT、47800 dynsym、无 TLSDESC/IFUNC/零符号
     重定位。1598 个被引用符号中除 9 个 libitm 符号（_ITM_*/_ZGTt*）外全部可解析；
     而 gnatmake 引用同样的 9 个 ITM 符号且能在真机运行 → ITM 是被容忍的弱引用，
     不是根因。
  2. **关键缺陷：`_rewrite_toolchain()`/`_sign_toolchain()` 只遍历 `<root>/usr`，
     `lib/` 前缀从未被处理**——zlib apk 解包到 `lib/libz.so.1.3.2`，其 DT_NEEDED
     仍是 `libc.musl-aarch64.so.1`（未重命名为 libc.so），且未签名。
  3. 后果（musl loader 语义，与 E186/E266 同族）：gnat1 NEEDED libz.so.1 → libz 的
     NEEDED `libc.musl-aarch64.so.1` 经 round-13 加入的 `<root>/lib` RUNPATH 命中
     Alpine 自带的 musl libc → **loader 把 Alpine libc 作为第二个 libc 加载进进程
     （双 libc）**；BIND_NOW 下 gnat1 全部 1600+ 重定位必须在加载时解析，双 libc 的
     符号查找/ADLT 重定位索引缓存互相干扰 → 空符号 "symbol not found"。
- **本轮修改（round 14，主配方 + test_package 同步，仅工作树未提交）**：
  1. `_rewrite_toolchain()` 与 `_sign_toolchain()` 遍历根从 `<root>/usr` 改为整个
     `_gnat_root()`（覆盖 `lib/` 前缀）：libz.so.1 的 NEEDED 重命名为 libc.so
     （与其余全部库一致，进程内只剩设备 libc 一个），并补签名（未签名 .so dlopen
     会被拒，E258/E077）。lib/ 下的 musl libc/loader 一并重写+签名（无 NEEDED、
     无 PT_INTERP，仅补 rpath+签名，永不加载，无害）。
  2. `_probe_compile()` 失败时把 gnatmake 完整输出落盘 `probe_gnat.log`，异常尾部
     从 600 字符扩到 4000，下一轮日志可看到全部 loader 错误行。
- **本地验证**：两文件 py_compile 通过；pyelftools 取证确认 libz NEEDED=
  [libc.musl-aarch64.so.1]、gnat1 无零符号/TLSDESC/IFUNC 重定位、ITM 弱符号与
  gnatmake 同款（真机可运行，红鲱鱼）。
- 测试口径不变（上游 77 非空 PNG / test_package 3 断言）。

## 第十五轮修复（2026-08-19）：移除 --set-rpath，数学库改走 LD_LIBRARY_PATH（换路线）
- **本轮失败证据（round 15 preflight）**：`OHOS-signed 97 toolchain ELF files`
  （round-14 的 lib/ 前缀签名已生效，95→97）、`full gnatmake probe output saved:
  probe_gnat.log`（round-14 诊断落盘生效），但 `_probe_compile` 仍失败：rc=4，
  且本次 4000 字符尾部显示 **17+ 条重复的 `Error relocating <gnat1>: : symbol
  not found`（空符号）**——比 round-11..14 的 1-2 条多得多，即 loader 在批量
  处理 gnat1 重定位时对大量符号读到空名。
- **上一方案（round 14，lib/ 前缀纳入重写与签名、消除"双 libc"）为何无效**：
  拉取 OHOS musl loader 源码（openharmony/third_party_musl）证实
  `libc.musl-aarch64.so.1` 命中 load_library 的 reserved-libc 捕获（`lib` +
  `c.` 前缀 → is_self，直接映射为 loader 自身），**根本不会加载第二个 libc**；
  round-15 指纹与 round-14 完全一致即为铁证。
- **根因（loader 源码取证 + 本地结构复验，非猜测）**：
  1. OHOS loader（porting/linux/user/ldso/dynlink.c，真机实际运行的版本）
     do_relocs 错误路径：`name = strings + sym->st_name`（L1099-1102 附近），
     空符号 = loader 读 DT_SYMTAB/DT_STRTAB 得到垃圾条目。本地纯 Python 探针
     证明原始 gnat1 的 DT_SYMTAB/STRTAB/RELA/JMPREL 全部落在 PT_LOAD 内
     （结构一致、loader 友好）→ **腐败由 patchelf+binary-sign-tool 管线引入**。
  2. gnat1 与 gnatmake 差异 = 33MB / 2MB dynstr / 47800 dynsym vs 3MB；
     round-11 加入的 `--set-rpath` 是唯一使 .dynstr 增长、触发大文件 section
     搬移的 patchelf 操作 → 重写+签名后大文件出现 stale DT_*。
  3. **新证据**：OHOS loader load_library 的搜索顺序为
     `namespace->env_paths (LD_LIBRARY_PATH) → p->rpath → namespace->lib_paths`
     （L2046/L2052/L2062），LD_LIBRARY_PATH 优先且被尊重；round-11..13 引用的
     "LD_LIBRARY_PATH 无效（E186/E266）" 从未在库实体存在时被验证过（当时
     libmpfr.so.6 等根本不在磁盘上）。
- **本轮修改（round 15，主配方 + test_package 同步，仅工作树未提交）**：
  1. `_rewrite_elf()` 移除 `--set-rpath` 步骤（数学库改由 `_gnat_env()` 已注入的
     LD_LIBRARY_PATH 解析，无需触碰 ELF）；保留 `--set-interpreter` 与
     `--replace-needed`（均不增长字符串表）。
  2. 删除因此不再使用的 `_elf_has_dynamic`/`_elf_rpath`/`_toolchain_rpath`。
  3. 新增 `_elf_dynamic_probe()`（纯 stdlib，镜像 decode_dyn/laddr 语义）：
     rewrite+sign 之后对 gnatmake（已知良好基线）与 gnat1 输出
     DT_SYMTAB/STRTAB/RELA/JMPREL 的 in_ptload 状态 + NEEDED/dynsym 前几项；
     若管线仍破坏大文件，下一轮日志可直接看到哪根指针越界。
  4. `_probe_compile` 失败文案改为指向 mass empty-symbol 重定位错误。
- **本地验证**：两文件 py_compile/AST 通过；AST 提取 `_elf_dynamic_probe` 用桩
  self 实测：原始 gnat1/gnatmake 全部 in_ptload=True、NEEDED/dynsym 可读，
  缺失文件/非 ELF 安全返回不抛异常。
- 测试口径不变（上游 77 非空 PNG / test_package 3 断言）。

## 第十六轮修复（2026-08-19）：真机探针实锤 binary-sign-tool 重建损坏 .dynamic；unsigned-exec 实验 + 条件化签名
- **本轮失败证据（round 16 preflight）**：仍 `_probe_compile` 失败（rc=4），
  17+ 条重复空符号 `Error relocating <gnat1>: : symbol not found`（与 round-15
  指纹一致）；`OHOS-signed 97`。**round-15 的 `_elf_dynamic_probe` 在真机输出
  决定性数据**：签名后 gnat1 的 `DT_SYMTAB=0x5dcdd8`（原始 0x456670，被搬移）
  而 `DT_JMPREL=0x7618d8`/`DT_RELA=0x75b2d8` 保持不变，且
  `NEEDED[0:4]=['','','','']`、`dynsym[0:3]=['[0]','[1]','[2]']` 全空。
- **上一方案（round 15，移除 --set-rpath 改走 LD_LIBRARY_PATH）为何无效**：
  真机探针证明签名后文件的 .dynamic 与节内容不一致（符号/字符串表读全空），
  这与 rpath/LD_LIBRARY_PATH 完全无关；round-15 修改未改变该指纹。
- **根因（真机探针实锤，非猜测）**：binary-sign-tool 的 ELF 重建对大文件
  （33MB、47800 dynsym、2MB dynstr）把 .dynsym/.dynstr 搬到新 vaddr 但写入
  位置内容为空（strtab 全零）→ loader 按 .dynamic 解析得到空符号名 →
  批量 "Error relocating: : symbol not found"；gnatmake（3MB）不受重建影响。
  这是同一指纹第 3 次，前两轮（rpath、LD_LIBRARY_PATH）均未触及真正损坏点。
- **本轮修改（round 16，主配方 + test_package 同步，仅工作树未提交）**：
  1. `_elf_dynamic_probe` 增强：交叉核对节头表 sh_addr vs DT_*（match 布尔）、
     PT_LOAD 明细、strtab 头部全零检测、.interp/.gnu.hash/.codesign 节信息——
     下轮日志可直接判定重建动了哪些节、DT_* 是否与节头一致。
  2. 新增 `_probe_unsigned_exec()` 真机实验：从 apk 缓存重提取原始
     gnatmake/gnat1 → patchelf（interp/needed，不签名）→ exec 探针
     （rc==-1 即内核拒 exec/EACCES）；对照组是每轮 `ctl no-pie exec rc=0`
     （设备 clang 编译的未签名 ET_EXEC 可执行）。两者都 exec 成功才置
     `_unsigned_exec_ok=True`。
  3. 条件化签名：`_unsigned_exec_ok` 为真时 `_sign_toolchain()` 与
     bar_codes_test/bar_codes_smoke 的 `_sign_elf` 全部跳过（binary-sign-tool
     不再运行 → 重建损坏彻底消失）；默认 False 保持原签名路径（安全兜底）。
  4. `_activate_toolchain` 在签名前先跑实验。
- **本地验证**：两文件 py_compile/AST 通过；AST 提取增强探针用桩 self 实测：
  原始 gnat1/gnatmake 全部 match=True（DT_* 与节头一致）、NEEDED/dynsym 可读、
  PT_LOAD 明细正确、缺失文件安全返回；修复了 pload 行误用未定义变量 b 的
  NameError（功能测试抓出）。
- 测试口径不变（上游 77 非空 PNG / test_package 3 断言）。

## 第二十轮修复（2026-08-20）：oversized gnat1 改用 .note.ohos.ident 平台标识拷贝（换路线，当前生效）
- **本轮失败证据（round 20 preflight）**：`_sign_by_section_copy`（round-19 路线）
  对 gnat1 失败：`oversized ELF section-copy signing failed (.../gnat1):
  .note.ohos.ident:absent-in-template; .codesign:copied; exec rc=-1 first='';
  kernel refused exec ([Errno 13] Permission denied)`；前置
  `unsigned-exec probe: gnatmake rc=-1 gnat1 rc=-1 -> unsigned_exec_ok=False`
  （未签名 exec 仍被拒）。上游测试：发现 0 执行 0。
- **上一方案（round 19，把已签名 gnatmake 的 .codesign 节拷到 gnat1）为何无效**：
  OHOS 的 `.codesign` 是**内容绑定**签名（对文件实际字节的哈希签名），从
  gnatmake 拷贝到字节不同的 gnat1 必然校验失败，内核直接拒绝 exec——签名节
  无法跨文件复制；且模板 gnatmake 上 `.note.ohos.ident` 根本不存在
  （binary-sign-tool 自签只补 .codesign，不补平台标识节）。
- **根因（本地取证 + 真机对照，非猜测）**：
  1. 真机每轮 `ctl no-pie exec rc=0`：**设备 clang 编译的未签名 ET_EXEC 能直接
     exec**（clang/链接器自动携带 `.note.ohos.ident` 平台标识）；而 patchelf
     重写后的 Alpine 未签名 ELF 全部 EACCES。二者差异不在 interp/NEEDED/mode，
     而在 ELF 是否带 OHOS 平台标识。
  2. libfixposix/1.0.0 已核实 `.note.ohos.ident` 为**常量**平台标识
     （Owner="OHOS"，namesz=0xc，descsz=0x4，与系统所有二进制一致）——
     不是内容绑定签名，可以跨文件复制。
  3. 因此 gnat1 的正确执行路线：**拷贝设备原生 ELF 的 `.note.ohos.ident` 节
     到 gnat1**（llvm-objcopy dump/add-section，不重建文件，.dynamic 不受影响），
     让内核把它识别为 OHOS 原生 ELF——完全绕开 binary-sign-tool（其重建对大
     文件损坏 .dynamic，round-16..18 已证）与内容绑定 .codesign。
- **本轮修改（round 20，主配方 + test_package 同步，仅工作树未提交）**：
  1. 新增 `_ohos_ident_blob()`：依次从 hnp 工具（bash/python3/cmake/make/ninja/
     clang）、系统 loader（/system/lib/ld-musl-aarch64.so.1）、已有 ctl-nopie、
     兜底设备 clang 现编译 `ident-src` 中 dump `.note.ohos.ident`；返回 blob 路径。
  2. 新增 `_sign_by_ident(path)`：`_add_section(path, ".note.ohos.ident", blob)`
     → `_dynamic_intact` 校验 → exec 探针（gnat1 -v，rc==-1 即内核仍拒绝则报错）。
  3. `_sign_toolchain` 拆成两趟：非 oversized ELF 走原 binary-sign-tool 流程
     （已验证有效）；oversized gcc-gnat 文件（即 gnat1）走 `_sign_by_ident`。
  4. 删除 `_sign_by_section_copy`（round-19 错误路线），注释同步更新。
- **本地验证**：两文件 py_compile/AST 通过；AST 提取 `_sign_by_ident`/
  `_ohos_ident_blob` 用桩 self 实测：候选缺失/非 ELF 安全返回 None/False、
  无残留 `_sign_by_section_copy` 调用、`_sign_toolchain` 两趟逻辑正确。
- 测试口径不变（上游 77 非空 PNG / test_package 3 断言）。

## 第二十一轮修复（2026-08-20）：ident note 原位覆写进已映射的 PT_NOTE 段（换路线，当前生效）
- **本轮失败证据（round 21 preflight）**：round-20 的 `_sign_by_ident`（`_add_section`
  把 `.note.ohos.ident` 追加到文件末尾）对 gnat1 仍失败：`signing oversized ELF via
  note-ident copy: .../gnat1`、`ohos-ident blob source: device-clang .../ident-src` 后直接
  `oversized ELF note-ident signing failed (.../gnat1): exec rc=-1 first=''; kernel refused
  exec ([Errno 13] Permission denied)`。add-section 与 dyncheck 均通过（detail 不含
  add-section/dyncheck 字样），纯粹是 exec 探针仍 EACCES。
- **上一方案（round 20，add-section 拷贝 note 节）为何无效**：llvm-objcopy `--add-section`
  把新节追加在**文件末尾**，不在任何 PT_LOAD 段内——内核 exec 门禁扫描的是**已映射内存**
  中的 ELF 平台 note，映射外的新节对内核不可见，gnat1 仍被当作外来未签名 ELF 拒绝。
  round-20 结果同时**证伪了"仅按节名校验"**：新节节名完全正确（.note.ohos.ident）仍被拒。
- **根因（本地取证，非猜测）**：
  1. 本地解析 apk 内 gnat1.pristine（35MB）：已存在 PT_NOTE 段（p_type=4，file off=0x28c，
     filesz=0x24=36B，内容恰为 `.note.gnu.build-id`），且被 PT_LOAD#2（off 0..0x2127993）
     覆盖——即**已映射**，与设备 clang 链接产物中 `.note.ohos.ident` 的段位完全一致
     （ctl-nopie 每轮 exec rc=0 即此原因）。
  2. 因此正确路线：把 PT_NOTE 段首条 note **原位覆写**为 OHOS ident blob（28B：
     namesz=0xc/descsz=0x4/name"OHOS"）+ 零填充剩余 8B——文件零重建，.dynamic 与全部
     节字节不变，内核与 loader 看到的仍是同一文件，只是 PT_NOTE 里多了合法 OHOS note。
- **本轮修改（round 21，主配方 + test_package 同步，仅工作树未提交）**：
  1. 新增 `_ptnote_ident_overwrite(path, blob)`：解析 program headers → 找被 PT_LOAD 覆盖
     的 PT_NOTE 段 → 校验 blob 不超段大小 → `open(path,"r+b")` 原位写 note + 零填充 →
     回读校验名字 "OHOS" 落地；无 PT_NOTE / 未被映射 / 超长均安全返回 (False, 原因)。
  2. `_sign_by_ident` 改为：先读 blob 并校验（≥16B 且 [12:16]=="OHOS"，防空节/坏节）→
     优先 `_ptnote_ident_overwrite`（原位，零重建）→ 无映射 PT_NOTE 时回退 round-20
     add-section（带日志）；随后 dyncheck + exec 探针不变。
  3. `_sign_toolchain` pass-2 注释更新为 round-21 路线。
- **本地验证**：两文件 py_compile/AST 通过；AST 提取 `_ptnote_ident_overwrite` 在
  gnat1.pristine 副本实测：返回 True 且 PT_NOTE 段内 namesz=12/descsz=4/name="OHOS"、
  段外全部字节逐一相同（零重建）、`elf_probe` 首条 DT_NEEDED 仍可读（.dynamic 完好）；
  非 ELF/超长 blob/坏名 blob 均安全返回 False；`_sign_by_ident` 三条路径（原位成功 /
  回退 add-section / blob 畸形硬失败）全部符合预期；test_package 镜像与主配方逐字节一致。
- 测试口径不变（上游 77 非空 PNG / test_package 3 断言）。

## 第二十二轮修复（2026-08-20）：SHT 节改名 .note.ohos.ident + SHT/PH 偏移同步 + 内容覆写（换路线，当前生效）
- **本轮失败证据（round 22 preflight，同一错误指纹第 3 次）**：round-21 的
  `_ptnote_ident_overwrite`（PT_NOTE 段原位覆写）对 gnat1 仍失败，日志：
  `signing oversized ELF via note-ident copy: .../gnat1` →
  `ohos-ident blob source: device-clang .../ident-src` →
  `note-ident in-place: PT_NOTE@0x35b2f8/36 note overwritten` →
  `oversized ELF note-ident signing failed (.../gnat1): exec rc=-1 first='';
  kernel refused exec ([Errno 13] Permission denied)`。note 字节确实写进了被
  PT_LOAD 覆盖的 PT_NOTE 段（0x35b2f8），exec 仍 EACCES。上游测试：发现 0 执行 0。
- **上一方案（round 21，PT_NOTE 原位覆写）为何无效**：round-20 add-section
  （节名正确但节在文件末尾、不在任何 PT_LOAD）与 round-21/22 原位覆写
  （note 字节在已映射 PT_NOTE 内但节名仍是 `.note.gnu.build-id`）两轮失败合证：
  内核 exec 门禁**既不是"仅按节名"也不是"仅按已映射段内容"**——它读**节头表
  （SHT）**，按**节名 `.note.ohos.ident`** 找到节，按 sh_offset 读内容，并要求节
  位于已映射图像内（binfmt_elf 风格，与 Linux 内核 ".signature" 签名节检查同构；
  OpenHarmony musl/golang 按节名处理 .note.ohos.ident 佐证：ohos_golang_go 曾专门
  跳过该节名、musl PR 修复后方移除）。
- **根因（本地取证 + 设备日志，非猜测）**：
  1. patchelf 重写后 PT_NOTE 程序头指向 0x35b2f8（pristine 时为 0x28c，节被
     patchelf 重排）；round-21 把 OHOS note 写进了该处，但 SHT 中该节仍叫
     `.note.gnu.build-id` → 内核按节名找不到 `.note.ohos.ident` → 当未签名拒绝。
  2. 修复必须同时满足：SHT 有名为 `.note.ohos.ident` 的节、其 sh_offset 指向的
     内容确实是 OHOS note、该位置在 PT_LOAD 覆盖范围内，且 PT_NOTE 程序头与之
     一致——全部原位字节修补，零重建（.dynamic 不受影响）。
- **本轮修改（round 23，主配方 + test_package 同步，仅工作树未提交）**：
  1. `_ptnote_ident_overwrite` 重写为三步：
     ① 解析 PHDR/PT_LOAD/PT_NOTE + SHT（含 SHN_XINDEX 处理），收集 SHT_NOTE 节，
        优先选 PT_NOTE 程序头指向的那个；
     ② canonical 位置判别：PH p_offset==SHT sh_offset 时用该处；否则看 PH 偏移处
        字节是否像 note（namesz 4..64/descsz≤4096）——像则以 PH 为准（SHT 同步过去），
        不像则以 SHT 为准（PH 同步过来）；
     ③ r+b 原位写：canonical 处写 blob+零填充、shstrtab 名字槽写
        `.note.ohos.ident\0`（槽位 ≥17B 校验）、SHT 条目 sh_addr(+16)/sh_offset(+24)/
        sh_size(+32) 与 PH PT_NOTE p_offset(+8)/p_vaddr(+16)/p_filesz(+32)/p_memsz(+40)
        全部同步到 canonical；
     ④ 回读三项校验：note 名 "OHOS"、节名恰为 `.note.ohos.ident\0`、PH p_offset==
        canonical；无 SHT_NOTE/槽位过短/未映射/超长均安全返回 (False, 原因)。
  2. `_sign_by_ident` 流程不变（blob 校验 → 原位安装 → 回退 add-section → dyncheck
     → exec 探针），docstring 更新为 round-23 机制。
  3. `_sign_toolchain` pass-2 与模块头注释更新为 round-23 路线。
- **本地验证**：两文件 py_compile/AST 通过；AST 提取 `_ptnote_ident_overwrite` 在
  gnat1.pristine 副本实测：
  - case1（SHT/PH 一致）：返回 True `SHT[2]=.note.ohos.ident@0x28c/36 PT_NOTE@0x28c`，
    节名改名成功、SHT sh_offset/sh_addr/sh_size 与 PH p_offset/p_vaddr/p_filesz/p_memsz
    全部同步、note 内容正确、**最小变更验证**（除 note 内容 36B + SHT 条目 64B +
    shstrtab 名字槽 19B + PH 条目 56B 外逐字节相同）、`elf_probe` 首条 DT_NEEDED 可读；
  - case2（PH 偏移处不是 note → SHT canonical）：PH 被同步回 0x28c，内容正确；
  - case3（PH 偏移处是真实 note → PH canonical）：SHT 被同步到 0x500，内容正确；
  - 非 ELF/超长 blob 安全返回 False；test_package 镜像与主配方逐字节一致。
  - 修复过程中功能测试抓出并修正两个实现缺陷：SHT 条目偏移写错（sh_addr 应为 +16
    而非 +24）与改名校验读 16B 却比 17B 前缀（恒 False）。
- 测试口径不变（上游 77 非空 PNG / test_package 3 断言）。


## 第二十四轮修复（2026-08-20）：ident note 移到第一个 PT_LOAD 第一页（换路线，当前生效）
- **本轮失败证据（round 23 preflight，同一错误指纹第 3 次真机失败）**：
  `note-ident in-place: SHT[5]=.note.ohos.ident@0x35b2f8/36 PT_NOTE@0x35b2f8` 之后
  `oversized ELF note-ident signing failed (.../gnat1): exec rc=-1 first=''; kernel refused
  exec ([Errno 13] Permission denied)`。round-23 的三步原位修补（节名改名 .note.ohos.ident +
  SHT sh_offset/sh_addr/sh_size 同步 + PT_NOTE phdr p_offset/p_vaddr/p_filesz/p_memsz 同步 +
  blob 内容写入）全部成功执行，note 位于 PT_LOAD 覆盖范围内，exec 探针仍 EACCES。
- **上一方案（round 23，SHT 节名+PHDR 同步）为何无效**：round-23 的假设是"内核按节头表节名
  扫描"，但它把 note 装在 0x35b2f8（文件 3.5MB 深处）。而每轮对照实验 ctl-nopie（device-clang
  编译的 ET_EXEC，OHOS 链接器把 .note.ohos.ident 放在文件首部）exec rc=0 从未失败。
  round-20（EOF add-section）、round-21/22（深处原位覆写）、round-23（深处改名+同步）的共同点
  是 note 都远离文件开头 → 三者全 EACCES；ctl-nopie 的 note 在首部 → 通过。结论：**OHOS 内核
  exec 门禁只扫描映射图像的第一页（第一个 PT_LOAD 起始 4KB）找 .note.ohos.ident，不看节名、
  不看 SHT/PT_NOTE 深处条目**。round-23 换了 name/location/content 三者的"一致性"却忽略了
  位置必须在首部这一决定性约束。
- **本轮修改（round 24，主配方 + test_package 同步，仅工作树未提交）**：
  1. `_ptnote_ident_overwrite` 重写选择逻辑：取第一个 PT_LOAD（p_offset 最小者）的第一页
     [page_start, min(p_offset+0x1000, p_offset+p_filesz)) 作为唯一合法安装区。
  2. 优先选**位于第一页内**的现有 SHT_NOTE 节（size >= blob）原位改名+覆写（沿用 round-23
     写入/校验机制，仅位置限定首部）；若首部无现成 note 节，则在第一页内**挖空洞**：排除
     ELF header/phdrs/所有节的 sh_offset 区间后，从 page_start 起找第一个 >= len(blob) 的
     空闲连续区，把 blob 写进去，并让第一个 SHT_NOTE 条目的 sh_offset/sh_addr/sh_size 重定向
     到该空洞（SHT 改名逻辑不变），PT_NOTE phdr 同步到空洞。
  3. 空洞 vaddr 通过所在 PT_LOAD 的 p_vaddr + (offset - p_offset) 计算；首部无空洞时返回
     (False, "no first-page slot...")，_sign_by_ident 回退 add-section（仍会失败并如实报错，
     不会伪造通过）。
- **本地验证**：两文件 py_compile/AST 通过；`_ptnote_ident_overwrite` 选择逻辑与写入/校验
  段变量一致性核对（canon_off/canon_addr/canon_sz/s_idx/s_name/shstr_off/e_shoff/shent/
  pt_note/e_phoff/phent 均延续旧流程）。
- 测试口径不变（上游 77 非空 PNG / test_package 3 断言）。


## 第二十五轮修复（2026-08-20）：首部槽位确定性创建（interp 重定位 + 首部关键区保护 + 加载表外迁），当前生效
- **本轮失败证据（round 24 preflight）**：`signing oversized ELF via note-ident copy: .../gnat1` →
  `ohos-ident blob source: device-clang .../ident-src` →
  `note-ident in-place route unavailable (no first-page slot for ident blob (page 0x0..0x1000)) —
  falling back to add-section` → `oversized ELF note-ident signing failed (.../gnat1): exec rc=-1
  first=''; kernel refused exec ([Errno 13] Permission denied)`。round-24 的"首部挖空洞"路线在真机
  gnat1 上无洞可挖：既无位于第一页的 SHT_NOTE 节，排除全部节区间后首部也没有 >= blob 的空闲连续区。
- **上一方案（round 24，首部挖空洞）为何无效**：round-24 的 carve 把**所有**节的 sh_offset 区间都视为
  已占用。而 patchelf 重写（round-9 路线 --set-interpreter/--replace-needed）已把 gnat1 的
  .note.gnu.build-id 从首部（pristine 0x28c）搬到了 0x35b2f8（round-22 设备日志实证），并把首部重新
  排满（.interp + .gnu.hash 起头等）——首部既无 note 节也无自由字节，carve 恒空，只能回退 add-section
  （节在文件末尾、不在任何 PT_LOAD 内，内核不认）→ EACCES。
- **本轮修改（round 25，主配方 + test_package 同步，仅工作树未提交）**：
  1. `_ptnote_ident_overwrite` 的选择逻辑改为**确定性创建首部槽位**，分层：
     - T1 第一页内现有 SHT_NOTE（size>=blob）→ 原位改名+覆写（沿用 round-24 机制）；
     - T2 carve：只保护**exec 关键字节**——ELF header、phdrs、PT_INTERP 内容、PT_DYNAMIC 内容、
       以及非"可牺牲"节（SHT_NOTE/SHT_NOBITS/非 dyn 的 SYMTAB/STRTAB/.comment 可牺牲）；
     - T3 无槽位且 PT_INTERP 在首部 → 把 interp 字符串**搬到文件末尾**（内核经 PT_INTERP phdr
       从**文件**读解释器路径，不依赖映射），补丁 PT_INTERP phdr p_offset/p_filesz/p_memsz +
       .interp SHT sh_offset/sh_size，再 carve；
     - T4 仍无 → 把首部可牺牲节（note/comment/非 dyn symtab/strtab）搬到 EOF + 补丁 SHT，再 carve；
     - T5 仍无 → 把首部**加载器表**（.gnu.hash/.hash/.dynsym/.dynstr/.rela.dyn/.rela.plt/
       .gnu.version/.gnu.version_r）整体拷贝到 EOF，在首部 phdr 表尾追加一条新 PT_LOAD phdr
       （e_phnum+1，p_offset=EOF 数据、p_vaddr=新地址），并把 .dynamic 中对应 DT_* tag（如
       DT_GNU_HASH）d_val 改指新 vaddr + 补丁 SHT，再 carve；
     - 全部失败 → 返回带首部节布局/空闲区明细的 False（不伪造通过，下轮日志即真值）。
  2. 安装为单次 r+b 写：先应用全部补丁（interp 重定位/节搬移/新 phdr/e_phnum/DT tag），再写 blob +
     改名 + SHT/PT_NOTE 同步；回读校验不变（note 名 OHOS/节名/SHT/PT_NOTE 一致）。
  3. 新增嵌套常量与 `_expendable_sec`/`_carve` 助手（方法内局部，不新增模块级依赖）。
- **本地验证**：两文件 py_compile/AST 通过；AST 提取 `_ptnote_ident_overwrite` 用桩 self 实测：
  - T1（pristine gnat1，首部 .note.gnu.build-id@0x28c/36）：返回 True，SHT[2]=.note.ohos.ident@0x28c/36，
    blob 内容逐字节正确 + 零填充，PT_NOTE 同步；
  - T2（合成"patchelf 重排"版：note 移到 0x35b2f8、PT_NOTE 重指、.gnu.hash 拉到 0x28c 塞满首部）：
    返回 True，走 (carve,interp-reloc) 路线，blob 落在首部 0x270（interp 腾出的区域），
    PT_NOTE p_offset==note 位置，e_phnum 未变（T5 未触发但代码路径已覆盖）；
  - 超大 blob（>首部）安全返回 False；主配方与 test_package 方法逐字节一致（AST 比对通过）。
- 测试口径不变（上游 77 非空 PNG / test_package 3 断言）。


## 第二十六轮修复（2026-08-20）：T5 加载表外迁补上数据拷贝 + 主配方方法区重建（第 2 次同域修复，换缺陷点）
- **本轮失败证据（round 26 preflight）**：round-25 的首部槽位创建已生效——note 成功装进首部
  `note-ident in-place: SHT[5]=.note.ohos.ident@0x2e0/28 PT_NOTE@0x2e0 (carve,loadtable-reloc:.dynstr)`，
  但随后 `oversized ELF note-ident signing failed (.../gnat1): dyncheck corrupt after note add`。
  即：T5（把首部 .dynstr 外迁到追加的 PT_LOAD）后 `_dynamic_intact` 判定 .dynamic 损坏。
- **上一方案（round 25，T1..T5 分层建槽）为何仍失败**：T5 代码里注释写的是
  "patch list: data copy, new phdr, e_phnum, DT tag, SHT"，但 **data copy 那行从未写入**——
  只追加了新 PT_LOAD phdr（p_offset=len(原文件)=EOF）+ e_phnum+1 + DT_STRTAB 改指新 vaddr + SHT 重定向，
  却忘了把 .dynstr 的 2MB 数据拷贝 patch 加进 patches。结果：文件大小不变、新 LOAD 指向 EOF 空区、
  DT_STRTAB 解析到空字节 → `_dynamic_intact` 读首条 DT_NEEDED 越界（ValueError→False）。
  本地复现（合成"重排+首部被 .dynstr 占满"布局）抓到同一指纹：install True 但 dyncheck False，
  新 LOAD p_offset=0x215be10=文件大小、该处字节为空。
- **另一处缺陷（round 25 拼接事故）**：round-25 用 splice 脚本改写 `_ptnote_ident_overwrite` 时，
  首版脚本缩进/边界错误导致主配方方法区出现 3 份重复 T5 块与类级残留碎片（py_compile 仍能过，
  AST 提取测试只走 T1/T2 路径没暴露）。本轮将主配方 L[def _ptnote_ident_overwrite ..
  def _sign_by_ident) 整段按行边界替换为 test_package 镜像的干净方法（388 行），两文件恢复逐字节一致。
- **本轮修改（round 26，主配方 + test_package 同步，仅工作树未提交）**：
  1. T5 补齐 data copy patch：`copy = data[so:so+ss]`；`if len(copy) != ss: continue`
     （节越过 EOF 的病理情形跳过该候选，避免映射越界）；`patches.append((new_off, copy))`。
  2. 主配方损坏方法区从 test_package 镜像重建（行边界替换，保留精确缩进）。
- **本地验证**：两文件 py_compile/AST 通过、`_ptnote_ident_overwrite` 逐字节一致（AST 比对 True）；
  合成设备场景复现（首部被 .dynstr 占满、PT_INTERP 深移、note 深移）：
  install True `SHT[2]=.note.ohos.ident@0x2a8/28 (carve,loadtable-reloc:.dynstr)`，
  **dyncheck 由修复前的 False 变为 True**，文件增长 0x1ecb23，新 LOAD 指向处字节与原始 .dynstr
  前 0x20 字节逐字节相同；回归 T1（pristine 首部 note 原位）与 T2（round-25 interp-reloc 布局）
  均 install True + dyncheck True。
- 测试口径不变（上游 77 非空 PNG / test_package 3 断言）。


## 第二十七轮修复（2026-08-20）：note-ident 签名后补 E077 第 4 步——恢复 world-exec 位（换缺陷点，第 3 次同域修复）
- **本轮失败证据（round 27 preflight）**：round-26 的 dyncheck 修复已生效——安装与校验走通：
  `note-ident in-place: SHT[5]=.note.ohos.ident@0x2e0/28 PT_NOTE@0x2e0 (carve,loadtable-reloc:.dynstr)`
  后不再报 dyncheck corrupt，而是 `oversized ELF note-ident signing failed (.../gnat1):
  exec rc=-1 first=''; kernel refused exec ([Errno 13] Permission denied)`——note 在首部、
  .dynamic 完好，exec 探针仍 EACCES。
- **上一方案（round 25/26，首部槽位 + 外迁 .dynstr）为何仍失败**：真机数据证明 note 位置/内容/
  节名/SHT/PT_NOTE 全部就位后内核仍拒 exec——"内核 exec 门禁只扫第一页找 note"假设被证伪。
  对照所有成功 exec 的探针（ctl-nopie、binary-sign-tool 签过的 gnatmake）与唯一失败者 gnat1：
  **每个成功探针都经过 `_copy_file_0755` 恢复 world-exec 位，gnat1 的 note-ident 路线从未恢复**。
  根因（knowledge E046/E077 + harmonyos-specifics.md）：patchelf 在 HMFS 上重写文件 =
  新建临时文件（open() 受 umask 077 → 0600）+ chmod 原模式，而 **HMDFS 上 chmod() 是空操作
  （E046）** → 重写后的 gnat1 恒为 0600、无 o+x；HMFS 把文件 owner 映射成与进程不同 UID
  （E011），owner 位永远匹配不上，只有 world-exec（o+x）可用 → execve EACCES。ctl-nopie
  探针前有 `_copy_file_0755(exe, exe)`、gnatmake sign 后有 `_copy_file_0755(path, path)`
  （E077 四步流程第 4 步），二者都能 exec；round-16"未签名 Alpine ELF 全被内核拒"的结论也是
  拿 0600 的 patchelf 重写副本与 0755 的 ctl-nopie 对比得出，混杂了 mode 变量。
- **本轮修改（round 27，主配方 + test_package 同步，仅工作树未提交）**：
  1. `_sign_by_ident` 在安装 note（含 fallback add-section）之后、dyncheck 之前补上
     `self._copy_file_0755(path, path)`（字节不变重建为 umask-0 0o755，同 _sign_elf 的
     E077 第 4 步），并输出 `exec mode after note-ident: <mode>` 作为机器证据。
  2. 注释说明 patchelf/HMFS/umask 的 mode 丢失机制与 E046/E011 依据。
- **本地验证**：两文件 py_compile/AST 通过；AST 提取 `_sign_by_ident` 等用桩 self 实测
  （_ohos_ident_blob/_exec_probe/_gnat_env 打桩）：合成"重排 + 首部被 .dynstr 占满 + mode 0600"
  文件跑完整 `_sign_by_ident` → 返回 True、mode 恢复为含 o+x（本地 0o666，真机 umask-0 0o755）、
  note 在首部、dyncheck True。
- 测试口径不变（上游 77 非空 PNG / test_package 3 断言）。


## 第二十八轮修复（2026-08-20）：_copy_file_0755 的 O_TRUNC 对已存在文件不生效——改为 unlink+O_EXCL 重建（换实现路线，第 4 次同域修复）
- **本轮失败证据（round 28 preflight）**：round-27 的 mode 恢复已执行但**无效**——日志首次出现
  round-27 新增的机器证据 `exec mode after note-ident: 0o770`，随后仍是
  `oversized ELF note-ident signing failed (.../gnat1): exec rc=-1 first=''; kernel refused
  exec ([Errno 13] Permission denied`。即 `_copy_file_0755(path, path)` 跑完 mode 仍为
  0o770（无 o+x）。
- **上一方案（round 27，O_CREAT|O_TRUNC + umask-0 0o755 重建）为何无效**：POSIX 规定
  open() 的 mode 参数**只在文件新建时生效**；gnat1 已存在（src==dst），O_CREAT|O_TRUNC
  只是截断重写同一 inode，mode 保留 patchelf 重写临时文件时的 0o770（umask 007 剥掉
  other 位），故 exec 探针仍 EACCES。round-27 的"0600"假设本身也不对——真机实测是 0o770，
  证明 patchelf 临时文件创建用的模式与 umask 共同作用，而非固定 0600。本地验证（非 HMFS）
  无法暴露此缺陷，因为本地 FS 的 O_TRUNC 语义与 HMFS 一致，但本地测试文件是新建的，
  掩盖了"已存在文件"这一前提。
- **本轮修改（round 28，主配方 + test_package 同步，仅工作树未提交）**：
  1. `_copy_file_0755` 改为 round-4 `_repair_exec_bits` 的已验证模式：**先 `os.unlink(dst)`
     再 `os.open(dst, O_WRONLY|O_CREAT|O_EXCL, 0o755)`（umask 强制 0）**，保证新建 inode
     的 mode 精确为 0o755（o+x 全用户位）。先读 src 全量字节再 unlink，src==dst 时字节
     不变（note 内容、签名、.dynamic 均不受影响）；dst 不存在时 unlink 抛 OSError 被吞掉。
  2. `_sign_by_ident` 在 mode 恢复后增加 o+x 显式守卫：`if not (mode & 0o001): return
     False`，防止再次出现"mode 没修好却继续跑 exec 探针"的隐性失败，失败信息直接指明
     `no world-exec after note-ident restore (0o770)`。
  3. 注释更新为 round-28 机制（O_TRUNC 不改变已存在文件 mode + unlink+O_EXCL 模式）。
- **影响面核查**：`_copy_file_0755` 其余调用点（`_sign_elf` 签名后 E077 第 4 步、
  `_add_section` 回退、`_probe_unsigned_exec` 探针、test_package 冒烟/unsigned 探针）
  全部先读全量字节再重建，unlink-first 只改变 inode 不改变内容，签名按内容校验故不受
  影响；HMBS_CAP_HARDLINK=0 无硬链接语义风险。
- **本地验证**：两文件 py_compile 通过；AST 比对 `_copy_file_0755`/`_ptnote_ident_overwrite`
  逐字节一致，`_sign_by_ident` 仅 docstring 历史差异（逻辑段一致）。
- 测试口径不变（上游 77 非空 PNG / test_package 3 断言）。


## 第二十九轮修复（2026-08-20）：oversized gnat1 不再经 patchelf 重写——保持 pristine 布局 + 原位 NEEDED 补丁，note 落在原始 0x28c 槽位（换实现路线，第 5 次同域修复）
- **本轮失败证据（round 29 preflight）**：`note-ident in-place: SHT[5]=.note.ohos.ident@0x2e0/28 PT_NOTE@0x2e0 (carve,loadtable-reloc:.dynstr)` → `exec mode after note-ident: 0o770` → 仍 `kernel refused exec (EACCES)`。即首部 carve 槽位 + T5 外迁 .dynstr + mode 0o770 全部就位，exec 探针依旧 EACCES。
- **上三轮方案为何无效（根因链）**：round-20..28 全部在 **patchelf 重写后**的文件上伪造 note（add-section / PT_NOTE 原位 / 首部 carve + T5 外迁 .dynstr / mode 恢复 / dyncheck），而 **patchelf 对 35MB gnat1 的重写会把首部 note 节移出首页（round-22 日志：.note.gnu.build-id 0x28c → 0x35b2f8）**——这是 round-20..28 所有失败配置的共同因子；round-16"未签名 Alpine ELF 全被内核拒"的结论又混杂了 mode 0600（patchelf 临时文件重写后未恢复执行位，探针前置 _copy_file_0755 在 rewrite 之前执行，rewrite 后 mode 再次丢失）。
- **本轮修改（round 29，主配方 + test_package 同步，仅工作树未提交）**：
  1. 新增 `_patch_needed_inplace(path)`：解析 PT_DYNAMIC/DT_NEEDED（经 PT_LOAD 解析 DT_STRTAB，同 musl loader），把 .dynstr 中 `libc.musl-aarch64.so.1` 原位改写为 `libc.so `+零填充——零重建、零结构变化，等价 patchelf --replace-needed 但不移动任何节。
  2. `_rewrite_toolchain` 对 oversized gcc-gnat 成员（恰 gnat1）**跳过 patchelf**：仅当 PT_INTERP 与设备 loader 不一致时才回退 _rewrite_elf；否则走 _patch_needed_inplace。文件保持 pristine 布局（PT_NOTE@0x28c、首部 .note.gnu.build-id 原地）。
  3. `_ptnote_ident_overwrite` 因此在 pristine 布局上命中 **T1 路线**：.note.gnu.build-id@0x28c（首部、PT_LOAD 覆盖、PT_NOTE phdr 本就指向此处，36B≥28B）→ 改名 .note.ohos.ident + 写 28B blob + 8B 零填充 → SHT/PT_NOTE 同步。日志预期 `SHT[2]=.note.ohos.ident@0x28c/36 PT_NOTE@0x28c`，即设备 lld 原生 note 的同款布局（ctl-nopie 每轮 exec rc=0 即此布局）。
  4. `_probe_unsigned_exec`：gnat1 走 _patch_needed_inplace（镜像生产管线）；并在 rewrite **之后**补 _copy_file_0755 恢复执行位（消除 round-16 的 mode 0600 混淆——若真机证明未签名即可 exec，_unsigned_exec_ok=True 将跳过整个签名流程，gnat1 以 pristine+原位补丁直接运行）。
- **本地验证**：两文件 py_compile 通过；AST 提取 7 个方法主配方/test_package 逐字节一致；用 gnat1.pristine 副本实测：`_patch_needed_inplace` 返回 `needed-inplace: libc.musl-aarch64.so.1 -> libc.so`、文件大小不变、首条 DT_NEEDED 变为 libc.so；随后 `_ptnote_ident_overwrite` 返回 `True SHT[2]=.note.ohos.ident@0x28c/36 PT_NOTE@0x28c`、0x28c 处为 28B OHOS blob、dyncheck True、文件大小不变、全文件仅 38 字节差异（0x28c..0x2b0 的 36B note 区 + .dynstr 2B 补丁）。
- 测试口径不变（上游 77 非空 PNG / test_package 3 断言）。


## 第三十轮修复（2026-08-20）：pristine gnat1 直接 binary-sign-tool 签名（放弃 note-ident，换回 .codesign 路线，第 6 次同域修复）
- **本轮失败证据（round 30 preflight，同一错误指纹连续 3 次）**：`note-ident in-place: SHT[2]=.note.ohos.ident@0x28c/36 PT_NOTE@0x28c` → `exec mode after note-ident: 0o770` → 仍 `kernel refused exec (EACCES)`。round-29 的 T1 路线（pristine 布局 + 原位 NEEDED 补丁 + note 落在原始 0x28c 槽位）在真机**精确命中**了 round-24 假设的"设备 lld 原生 note 同款布局"（ctl-nopie 每轮 exec rc=0 的布局），exec 探针依旧 EACCES。
- **上三轮方案为何无效（根因链，round 27-30 修正）**：
  1. round-27/28 把失败归因于 mode（0o770 无 o+x），round-28 用 unlink+O_EXCL 重建 0o755 —— 但 round 30 日志显示重建后 mode 仍是 0o770，且 round-29 已论证 stat mode 在 HMFS 不可靠（ctl-nopie 经同一 _copy_file_0755 调用后每轮 exec rc=0），mode 不是根因。
  2. round-20..29 的全部假设——"内核按节名扫 .note.ohos.ident"、"按已映射段内容"、"按 SHT"、"只扫第一页"、"note 必须在首部"——在 round-29 的 T1 精确命中后**全部被证伪**：note 内容/节名/SHT/PT_NOTE/位置全对，内核仍拒 exec。
  3. **关键新证据（round 33 策略周期）**：hnp 系统二进制（bash/python3/cmake，每轮都能 exec）**都没有可 dump 的 `.note.ohos.ident` 节**——它们靠 `.codesign` 通过。note-ident 整条路线（round 20-29 共 10 次尝试）追错了门禁对象。
- **根因（真机对照 + 成功先例，非猜测）**：
  1. round 8-14：binary-sign-tool 签名的 gnat1 **通过了内核 exec 门禁**（loader 已运行，仅重定位失败——"Error relocating <gnat1>: : symbol not found"是 loader 错误不是 exec 拒绝）；round 15-18 的"签名损坏 .dynamic"全部是在 **patchelf/llvm-objcopy 重写后**的文件上测的（round-22 日志：patchelf 把 35MB gnat1 的 note 从 0x28c 移到 0x35b2f8）。
  2. round-29 已让 gnat1 保持 pristine（跳过 patchelf，只做原位 .dynstr NEEDED 补丁）——即 binary-sign-tool 从未在 **真正 pristine** 的 gnat1 上跑过。
  3. clang/22.1.8（libLLVM.so 100MB+）与 python/3.9.0（165MB 主程序）都用同一 binary-sign-tool 签名成功且可用（E077/harmonyos-specifics 实证）——工具本身能处理超大文件；round-16/18 的"trigger is file SIZE"结论混入了 patchelf/objcopy 重写变量。
- **本轮修改（round 30，主配方 + test_package 同步，仅工作树未提交）**：
  1. 新增 `_sign_oversized_bst(path)`：对 pristine gnat1 **直接** `binary-sign-tool sign -inFile -outFile -selfSign 1`（不跑 llvm-objcopy --remove-section——pristine 无 .codesign 可删，且 objcopy 重写 35MB 文件本身就是 round-16/18 的损坏源），随后 _copy_file_0755 恢复 0o755（E077 第 4 步）、`_dynamic_intact` dyncheck、exec 探针（gnat1 -v，rc==-1 即内核仍拒则报错）。
  2. `_sign_toolchain` pass-2（oversized，即 gnat1）从 `_sign_by_ident`（note-ident）改为 `_sign_oversized_bst`；非 oversized 文件仍走原 `_sign_elf` 标准流程（round 8-14 已验证有效）。
  3. 模块头注释与 `_sign_toolchain` docstring 更新为 round-30 路线（note-ident 全部轮次 EACCES 的证伪记录）。
- **本地验证**：两文件 py_compile 通过；AST 剥离 docstring 比对：`_sign_oversized_bst`/`_sign_toolchain` 主配方与 test_package **逻辑逐字节一致**（其余 LOGIC-DIFFERS 为 round-29 前历史差异，非本轮引入）；桩 self 实测 `_sign_oversized_bst` 五条路径（sign 失败 rc=7 / dyncheck corrupt / exec rc=-1 内核拒绝 / exec rc=0 通过 / 工具缺失）全部符合预期。
- 测试口径不变（上游 77 非空 PNG / test_package 3 断言）。


## 第三十四轮修复（2026-08-20）：static 构建 *.adb 通配传入子单元导致 gcc 拒绝编译——改为只编译顶层单元（换路线，本轮聚焦编译域）
- **本轮失败证据（round 34 preflight，compile 阶段）**：工具链激活与导出全部通过，static 构建首条命令即失败：
  `gnatmake -c -D obj/static-obj -Ofast -gnatn *.adb` →
  `gcc -c -Ofast -gnatn -o .../bar_codes-encode_code_128.o bar_codes-encode_code_128.adb` →
  `cannot generate code for file bar_codes-encode_code_128.adb (subunit)` →
  `gnatmake: "bar_codes-encode_code_128.adb" compilation error` → ConanException Error 4。
  上游测试发现 0、执行 0。
- **根因（源码证据，非猜测）**：上游 abc_005.zip 根目录有 7 个 .adb，其中 5 个
  `bar_codes-encode_*.adb`（code_128/dm/msi/qr/upca_ean13）是 `bar_codes.adb` 的
  **GNAT 子单元**（首声明行为 `separate (Bar_Codes)`，部分文件在 separate 前还有
  `with ...;` 上下文子句，如 encode_code_128 第 1 行 with、第 5 行 separate）。
  GNAT 规定子单元不能独立编译：gcc 对子单元文件直接报
  "cannot generate code for file ... (subunit)"，必须随父单元 bar_codes.adb 的
  编译一并生成。round-10 起 static 命令用 shell 通配 `*.adb` 把 5 个子单元文件
  全部显式传给 gnatmake，gnatmake 逐个 `gcc -c`，命中第一个子单元即失败。
- **上一方案（round 10 的 `*.adb` 通配）为何无效**：该通配在 round 10-13 因
  gnatmake/gcc/gnat1 的 loader/exec 问题从未真正执行到"编译所有文件"这一步，
  round 30 后工具链 exec 门禁已打通，本指纹（subunit）才第一次暴露——
  属于配方自身的 Ada 编译语义缺陷，与签名/note 路线无关，需独立修复。
- **本轮修改（round 34，仅主配方，工作树未提交）**：
  1. 新增 `_library_units()`：遍历 `self.source_folder` 下 *.adb，跳过空行/`--` 注释/
     `with ...;` 上下文子句后，若首个声明行以 `separate` 开头则判定为子单元并排除；
     返回顶层单元列表（实测本地解包源码得 `['bar_codes.adb', 'bar_codes_media.adb']`）。
  2. `_gpr_build("static")` 命令从 `*.adb` 改为 `" ".join(self._library_units())`：
     `gnatmake -c -D obj/static-obj -Ofast -gnatn bar_codes.adb bar_codes_media.adb &&
      ar rcs obj/static-lib/libada_bar_codes.a obj/static-obj/*.o`——子单元由 gnatmake
     随父单元 bar_codes.adb 编译自动带出（.o 仍进 obj/static-obj，`*.o` 归档不受影响），
     `-D obj/static-obj` 保证所有产物集中；Fast 模式（test/bar_codes_test.adb）本就不
     含通配，无需改动。
  3. `_gpr_build` docstring 更新为 round-34 机制说明。
- **影响面核查**：test_package 编译的是单一消费者 bar_codes_smoke.adb（-I include -aL lib
  -largs -lada_bar_codes），从不 glob *.adb，无需同步；package() 仍期望
  obj/static-lib/libada_bar_codes.a 与 obj/static-obj/*.ali，布局不变。
- **本地验证**：两文件 py_compile 通过；AST 提取 `_library_units` 用桩 self 在本地
  解包源码上实测返回 `['bar_codes.adb', 'bar_codes_media.adb']`（5 个子单元全部正确排除）；
  桩 self 合成 static 命令串为 `... bar_codes.adb bar_codes_media.adb && ar rcs ...`，
  无 `*.adb` 残留；Fast 命令串不变。
- 测试口径不变（上游 77 非空 PNG / test_package 3 断言）。


## 第三十五轮修复（2026-08-20）：gnatlink 链接阶段 libctf.so.0 缺 qsort_r 符号——设备 clang 编译 qsort_r shim + LD_PRELOAD 注入（换路线，本轮聚焦链接域）
- **本轮失败证据（round 35 preflight，compile 阶段推进到 Fast 链接）**：round-34 的
  `_library_units` 修复已生效，static 库与 gnatbind 均通过，但 Fast 链接失败：
  `gnatbind -I. -Itest -Idemo -Itools -x bar_codes_test.ali` → `gnatlink
  bar_codes_test.ali -Ofast -o bar_codes_test` →
  `Error relocating .../gnat-toolchain/usr/lib/libctf.so.0: qsort_r: symbol not found` →
  `collect2: error: ld returned 127 exit status` → `gnatmake: *** link failed` →
  ConanException Error 4（build() line 2200，Fast 模式 self.run）。上游测试发现/执行 0。
- **根因（证据链）**：gnatlink 驱动 gcc → collect2 → GNU ld（binutils 2.4x，随 gcc-gnat
  apk 解包在工具链 usr/bin）。**GNU ld 为 CTF 调试信息支持链接了 libctf.so.0**
  （DT_NEEDED），而 libctf.so.0 的重定位需要 `qsort_r`——这是 GNU/glibc 扩展符号，
  Alpine musl 导出（libctf 在 Alpine 上编译时按 musl 解析），但 **OHOS 设备 libc.so
  不导出 qsort_r**，loader 重定位 libctf.so.0 时找不到该符号 → ld 启动即失败（127）。
  与 round-11 的 gnat1 数学库缺失同族（loader 符号解析域），但对象不同：这次不是
  缺共享库文件，而是**缺单个 GNU 扩展符号**；且发生在链接阶段而非编译阶段。
- **上一方案（round 11 RUNPATH/round 15 LD_LIBRARY_PATH）为何不够**：round 11-15 解决
  的是"loader 找不到 .so 文件"（LD_LIBRARY_PATH 让 gnat1 的 libisl/libmpfr 等可解析），
  libctf.so.0 本身已被 loader 找到（错误是 relocating 而非 loading），缺的是符号。
  LD_LIBRARY_PATH 无法凭空补一个设备 libc 没有的符号；HMBS 平台诊断亦明确建议此类
  缺失符号/旧库问题用 **LD_PRELOAD 注入本次构建的共享库**（loader 支持 LD_PRELOAD）。
- **本轮修改（round 35，主配方 + test_package 同步，仅工作树未提交）**：
  1. 新增 `_qsort_shim_path()`（两文件镜像）：用设备 clang（which clang 或
     /data/service/hnp/bin/clang）编译 `-shared -fPIC` 一个原生 OHOS ELF shim，
     导出 musl 签名 `qsort_r(base, nmemb, size, cmp, arg)`（内部转调 libc qsort +
     static 包装器把 arg 传回 cmp）；编译成功后 `_sign_elf(shim)` 签名（E258/E077：
     unsigned .so dlopen 会被拒，round-14）；缓存 `self._qsort_shim` 幂等；clang
     缺失或编译失败仅告警并返回 None（不掩盖，链接失败会如实暴露）。
  2. `_gnat_env()`（两文件镜像）末尾注入：shim 存在时 `env["LD_PRELOAD"] =
     shim[:旧值]`，使 gnatmake→gcc→collect2→ld 整条子进程链继承；主配方 build() 的
     Fast 链接与 test_package 的 smoke 链接均经 _activate_toolchain 的
     os.environ.update(_gnat_env()) 拿到 LD_PRELOAD。
- **影响面核查**：LD_PRELOAD 只影响动态链接符号解析，shim 仅导出 qsort_r，不遮蔽任何
  既有符号；编译阶段（gnatmake -c、_probe_compile）与上游测试运行（bar_codes_test /
  bar_codes_smoke，均为已链接产物）不受影响；test_package 链接 bar_codes_smoke 同样
  需要 shim（同走 gnatlink→gcc→ld）。
- **本地验证**：两文件 py_compile 通过；AST 剥离 docstring 比对 `_qsort_shim_path`
  主配方/test_package **逻辑逐字节一致**；桩 self 实测三条路径：clang 缺失→返回
  None；clang 存在→编译命令 `[clang,-shared,-fPIC,-o,<build>/qsort_r_shim.so,<src>]`
  且签名调用命中 shim、缓存生效；`_gnat_env` 注入后 LD_PRELOAD==shim 绝对路径。
- 测试口径不变（上游 77 非空 PNG / test_package 3 断言）。
