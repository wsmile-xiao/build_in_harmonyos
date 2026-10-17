# tetraproc 0.9.2 适配笔记

## 基本信息

- 上游：Fons Adriaensen，https://kokkinizita.linuxaudio.org/linuxaudio/
- 源码：https://kokkinizita.linuxaudio.org/linuxaudio/downloads/tetraproc-0.9.2.tar.bz2
  - SHA256：`9116a4df746e62eb06e94e4539ff5bf6f38952334adf3aa82cbd15fdb58126ab`
  - 单一根目录 `tetraproc-0.9.2/`，`strip_root=True` 适用。
- 许可证：GPL-2.0-or-later（source/COPYING）。
- 上游版本与 Conan 包版本一致（0.9.2，无递增）。
- issue 编号：待补（会话与项目文件内无明确 issue）。

## 构建系统分析（W1）

- 纯 C++ 程序项目，无 configure/CMake，`source/Makefile` 提供 all/install/uninstall/clean。
- 产物两个：
  - `tetraproc`：X11/JACK GUI 处理器（运行期需要 display + jackd）。
  - `tetrafile`：命令行 B-format 转换器（只依赖 sndfile + fftw3f，可无头运行）。
- 上游无测试目标：`make -C source check` 报 "No rule to make target 'check'"，
  无上游测试可执行（与 clxclient/clthreads 同类情况，见 test_package/MANIFEST.yml 的
  upstream_zero_evidence）。

## W0 依赖结论

依赖数量：12（全部为链接依赖，无 Python/测试依赖）。

已满足依赖（仓库内已有 Conan 包）：

| 依赖 | 引用 | 用途 |
|---|---|---|
| clthreads | clthreads/2.4.0 | 线程/ITC 支撑库（头文件；须与 clxclient/3.9.2 钉版一致，2.4.2 会在依赖图中冲突） |
| clxclient | clxclient/3.9.2 | X11 C++ 控件库（GUI 部分） |
| jack | jack/1.9.22 | JACK 音频（jclient.cc, `jack/jack.h`） |
| libsndfile | libsndfile/1.2.2 | 音频文件读写 |
| libpng | libpng/1.6.58.3 | K-meter 表盘图片加载（`png.h`） |
| libx11 / libxft / freetype / fontconfig / libxrender / xorgproto | 见 conanfile | X11 工具栈（与 clxclient 3.9.2 配方一致的一组钉版） |

缺失/拆分依赖：

- **无。** 制品仓提供独立的单精度包 `fftw3f/3.3.10`（libfftw3f + libfftw3f_threads，
  armv8 OHOS 预编译二进制，带版本软链）。注意仓库的 `fftw/*` 包是双精度
  （ENABLE_FLOAT=OFF），不能用于本库；单精度必须用 `fftw3f` 包名。
- 依赖数量修正：12 个（上表 11 个 + fftw3f/3.3.10）。

## OHOS 可移植性改造（以 replace_in_file 实现，未用补丁文件）

1. 去除 `CXXFLAGS += -march=native`：编译器/代码生成由 Conan profile 控制。
2. 新增 `PCONFCFL`/`FREETYPE_CFLAGS`/`CONAN_LDLIBS`/`SYSLIBS` 四个 make 变量槽：
   保留 Makefile 自身的 `-DVERSION`/`-DSHARED` 与目标级 `LDLIBS +=`，recipe 通过
   命令行注入 -I/-L，不整体覆盖 CPPFLAGS/LDLIBS。
3. `$(shell pkg-config --cflags freetype2)` → `$(FREETYPE_CFLAGS)`（OHOS 无 pkg-config）。
4. `-lrt` → `$(SYSLIBS)`（默认 -lrt，OHOS 传空：musl 时钟/定时器在 libc，无 librt）。
5. 源码层面仅 `mlockall` 一处系统假设（tetraproc.cc:109，失败仅告警，无需改动）。
6. 无 fork/exec/pthread_cancel/alsa 依赖。

## 打包

- `bin/tetraproc`、`bin/tetrafile`；`share/tetraproc/*.png`（GUI 启动期从编译进二进制的
  SHARED 路径加载，运行期路径以 OHOS 真机验证为准）；`licenses/COPYING`。
- OHOS 下 package 阶段对 bin/ 的 ELF 做 `binary-sign-tool -selfSign` 内容签名
  （同 fftw 配方做法；签名后不可再 strip/objcopy）。
- `package_type = "application"`；test_package 不链接本包，直接消费安装后的可执行文件。

## 本机验证（W4，2026-09 会话）

- `git diff --check`：通过。
- conanfile.py / test_package Python 语法检查（py_compile）：通过。
- YAML 结构检查（manifest.yaml、test_package/MANIFEST.yml）：通过。
- 源码归档 SHA256 复核：与下载文件一致。
- 依赖钉版与仓库现存目录/制品仓逐一核对：全部存在（单精度用 fftw3f/3.3.10）。
- 本机 OHOS 交叉编译 + 链接（fathom-local 的工具链，aarch64-linux-ohos sysroot）：
  - 20/20 个 .cc 全部编译通过（含 `-DCLTHREADS_NO_PTHREAD_CANCEL`，与 clthreads
    配方约定一致；未出现其它告警以外的错误）。
  - `tetrafile` 与 `tetraproc` 两个可执行文件全部链接成功
    （ELF64 / AArch64 / DYN）。
  - 最终链接使用制品仓 fftw3f/3.3.10 预编译包，tetrafile 的 DT_NEEDED 为
    libfftw3f.so.3（SONAME 正确）、libc++_shared、libc。
  - tetraproc 的 DT_NEEDED：libfftw3f、libclxclient、libclthreads、libjack、
    libpng16、libXft、libX11、libc++_shared、libc（libsndfile 走静态包，无 NEEDED，
    与仓库 libsndfile/1.2.2 默认 shared=False 一致）。
  - 验证方式说明：本机无 make，未运行 Makefile 本身；conan create 的完整链路
    留给真机 shadow CI。以上为直接调用与 Makefile 相同 flag 的等价编译/链接验证。
- 制品仓 fftw3f/3.3.10 预编译包（libfftw3f.so.3.6.10 + threads，带 SONAME 软链）
  在本机成功下载并用于最终链接验证；此前用 TEMP 内临时配方（未提交）做的
  链路验证结论一致，最终以 fftw3f/3.3.10 的链接结果为准。
- 本机环境限制备忘：conan build profile 为 Windows 时 `util-macros` 的 validate
  会拒绝（其仅允许 Linux/OHOS）；依赖二进制下载需用 os=Linux 的临时 build
  profile（`--build=never`），CI Linux worker 不受影响。

## 真机 shadow CI 结果（W5，已执行）

隔离 job（`<job>` 占位，避免记录内部路径细节）：job 名 `tetraproc-0.9.2-20261004-r2`，
包路径 `archives/t/tetraproc/0.9.2`，runner exit code = **0**。

| 项 | r1 | r2(终) |
|---|---|---|
| job / run 目录 | tetraproc-0.9.2-20261004（repo-source 缺 ci/，外层失败 exit 127） | tetraproc-0.9.2-20261004-r2 |
| exit code | 1 | **0** |
| L0 / L1 / L4 / L5 | fail/skip | **pass / pass / pass / pass** |
| L1e 破坏性反向验证 | - | **confirmed**（test 真实依赖包产物） |
| L2 | - | skip（CI 内置 --version/--help smoke 非 0，非阻塞；tetrafile 实际可用，见下） |
| test_package | - | **4/4 断言通过**（tetrafile --help 输出 usage banner、exit 1 符合上游；3 张 K-meter PNG 齐全） |

迭代记录（r2 内部共 7 次重跑，每轮根因→解法）：
1. `can't open input file: ci/conan/build_and_test.sh`：repo-source 的仓库缺 ci/ →
   换用含 ci/ 的完整仓库重建 job。
2. `libx11/1.8.13 not resolved`：job conan-home 默认只有 conancenter →
   按成功 job 模式配置 remotes.json（conancenter disabled + ohpcd）。
3. `clthreads/2.4.0 vs 2.4.2 冲突`：clxclient/3.9.2 钉 2.4.0 → 本库改钉 2.4.0。
4. `get() got unexpected keyword 'tetraproc'`：conandata sources 按包名嵌套 →
   source() 改用 `conan_data["sources"]["tetraproc"]`。
5. 链接期 `-L` 全部丢失：重生成补丁时 `$(CONAN_LDLIBS)` 槽位漏掉 → 补回两个链接行。
6. `KeyError: 'CONFIG_SHELL'`：test_package 里 str.format 吃掉 `${CONFIG_SHELL:-}` →
   改字符串拼接。
7. `FileExistsError: runtime-libs`：上一轮残留 → 生成前先清理。

L2 说明（如实）：CI 的 L2 smoke 对 bin/tetrafile、bin/tetraproc 直接跑
`--version/--help` 失败（非阻塞 warn→skip）；test_package 已通过带运行时闭包的
方式验证 tetrafile 可执行且输出正确，tetraproc GUI 需 display+jackd，无法无头运行。

## 下一步

### 本机静态门禁自检结论（真机 CI 自检模板第一部分）

- G0e 根目录白名单：无白名单外杂项（worktree 根的 code/ docs/ 等均为上游跟踪文件）。
- JC 垃圾文件：无（临时 __pycache__ 已清除；无 reports/、ci-metadata.json）。
- L0 逐条核对：conanfile 语法 OK、test_package/conanfile.py + MANIFEST.yml 齐全、
  含真实断言的 test()、无硬编码 remote、无外部 curl、无 run() 内 shell 环境变量。
- G1（conan-verify 配方完整性）：PASS。
- G2（conan create）：本机无法执行——make 不存在（WinError 2），配方解析与
  conandata/补丁流程本身正常；由真机 shadow CI 承担（未把未执行写成通过）。
- L1e 设计说明：test_package 直接运行安装后的 tetrafile 二进制并断言其输出与
  产物结构，破坏产物目录后测试必然失败，不属"假测试"。
- pre_pr_audit：W3 本地 CI 模拟结果（.ci-result.json）缺失，需 shadow CI 后补。

1. 真机空闲窗口内创建隔离 job（勿在 SSH 首连时直接跑重任务）：

   ```sh
   sh "$HOME/bin/ohos-prepare-isolated-conan-job.sh" \
     --user codex --job tetraproc-0.9.2-<timestamp> \
     --package archives/t/tetraproc/0.9.2 \
     --repo-source "$HOME/ohos-users/codex/<existing-job>/repo/build_in_harmonyos"
   ```

2. 传输后核对文件清单（conanfile.py、manifest、notes、test_package 齐全），
   再执行 `sh "$HOME/ohos-users/codex/<job>/run-conan-heavy.sh"`。
3. 记录 L0/L1/L2/L4/L5、exit code、test_package 断言数（4）。
5. tetrafile --help 为无头可跑项；tetraproc GUI 需 display + jackd，
   真机验证以 L2 bin smoke（tetrafile）为准，GUI 启动列为后续人工项。

## 已知限制

- tetraproc GUI 运行期需要 X display 与 jackd，CI/无头环境不可执行，属上游设计。
- GUI 图片加载路径为编译期 `$(PREFIX)/share/tetraproc`（默认 /usr/local），
  OHOS 上的实际部署路径如不同，需要后续确认（不影响 tetrafile）。
