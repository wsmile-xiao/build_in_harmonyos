# exiftags 1.01 适配笔记

## 编译环境
- 构建系统: makefile（纯 Makefile，无 configure 脚本）
- 编译日期: 2026-08-26
- 编译器: clang 15.0.4（鸿蒙 aarch64 工具链）
- 状态: published

## 编译步骤

exiftags 使用纯 Makefile 构建，无 configure 脚本。三个工具 exiftags、exifcom、exiftime 一起编译。

```bash
# 编译（传 CC/CFLAGS 以使用鸿蒙工具链，默认 Makefile 用 CC=cc）
make CC=clang CFLAGS="-fPIC -O2"

# 隔离测试安装（Makefile 的 install 目标 bindir/mandir 可覆盖）
make install prefix=$TEST_PREFIX bindir=$TEST_PREFIX/bin mandir=$TEST_PREFIX/share/man
```

### Makefile 安装路径说明
Makefile 的 install 规则使用 `$(bindir)` 和 `$(mandir)/man1`，其中：
- `bindir=$(DESTDIR)$(prefix)/bin`
- `mandir=$(datadir)/man`，`datadir=$(DESTDIR)$(prefix)`

为避免 DESTDIR 与 prefix 拼接导致路径重复，直接覆盖 `prefix`、`bindir`、`mandir` 三个变量到目标路径。install 规则内部 cp 到 `$(mandir)/man1`，故 mandir 设为不含 /man1 的路径。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | install 默认 DESTDIR+prefix 路径重复 | Makefile 的 datadir=$(DESTDIR)$(prefix)，与 DESTDIR 模式冲突 | 直接覆盖 bindir/mandir 到目标绝对路径，不使用 DESTDIR |
| 2 | 编译警告（非错误） | clang 对老式 C 代码的 abs(unsigned) 等发出警告 | 无害警告，不影响功能，不修改源码 |

## 源码修改

无源码修改。exiftags 1.01 原始源码在鸿蒙 aarch64 上使用 clang 编译通过，仅传 CC/CFLAGS 即可，无需任何 patch。

## 依赖版本

无外部依赖。三个工具仅依赖标准 C 库和 libm。

## 验证结果

```bash
# 编译成功（3 个二进制）
$ ls -la exiftags exifcom exiftime
-rwxrwx--- exifcom   (76224)
-rwxrwx--- exiftags  (170432)
-rwxrwx--- exiftime  (68032)

# L2 smoke test：三个二进制均正常响应
$ ./exiftags -h        → 显示 usage（exit 1，正常行为）
$ ./exifcom            → 显示 usage（exit 1，正常行为）
$ ./exiftime           → 显示 usage（exit 1，正常行为）
```

## 注意事项

- exiftags 是命令行工具（含 3 个可执行文件），需创建 commands.json（R38）
- 无 conan 依赖，requirements() 为空
- Makefile 的 CC 默认为 cc，需在 conanfile build() 中从 Conan toolchain 取 CC/CFLAGS（R33）

## 上游测试用例核查

**结论：exiftags 1.01 上游无测试用例，无需执行上游测试。**

四路交叉验证：
1. 上游 Makefile 仅有 `all`/`clean`/`install` 三目标，无 `check`/`test` 目标
2. 源码包 36 个文件全部为 `.c`/`.h`/`.1`/`.dsp`/`Makefile`/`README`/`CHANGES`，无 test/spec/fixture/sample 命名文件
3. README 无测试说明
4. Homebrew/Debian 第三方打包均未补充上游测试套件

test_package/MANIFEST.yml 已据实声明 `upstream_test_in_build: false`、`upstream_tests: []`。本仓库 test_package/test.sh 为消费者视角功能验证（R34），非上游测试。

---

**编译结束**: 2026-08-26 09:55
**最终状态**: published

## CI 修复记录

### E266: lld 缺 libxml2.so.16 链接失败（修复已推翻，见下）

**现象**：CI Build #31560（Worker CI-042）编译阶段，所有 .o 编译成功，但链接阶段失败。OHOS SDK 自带的 `lld` 链接器是动态链接 ELF，运行时依赖 `libxml2.so.16`，系统默认库搜索路径找不到该库，lld 无法启动，clang 链接报 `error: unable to execute command: No such file or directory`。

**知识图谱命中**：E266（Phase B: 3，severity=3，category=linking/dependency）

**原修复（已推翻）**：在 conanfile.py build() 的 CFLAGS 中追加 `-fuse-ld=/data/service/hnp/bin/ld`，指定 GNU ld 2.45 替代有问题的 lld。

**为何推翻**：GNU ld 不注入 `.codesign` 段，OHOS 内核拒绝执行其产出的二进制，直接导致 #31567 的 Permission denied（详见下条）。本地验证表明 clang 默认 lld 在当前环境可正常链接并注入有效签名，E266 的 libxml2 缺失前提在本机不复存在。修复已回退到 lld 默认链接。

**当前修复**：删 `-fuse-ld`，用 clang 默认 lld。若 CI worker 仍遇 lld 启动失败，正确方向是把 `libxml2.so.16` 放入 ld.so 搜索路径（LD_LIBRARY_PATH 或 hnp lib 目录），而非改用 GNU ld。

**参考先例**：asm6809 2.15、b2sum 20190724、bam 0.5.1 等配方曾用 GNU ld 方案——这些若为库（非可执行 application）则无 .codesign 问题；exiftags 是 application，不可照搬。

**禁止做法**（R5 铁律）：不使用 `ln -sf` 创建软链接覆盖系统库路径。

### CI #31567: 二进制 Permission denied — GNU ld 产出无 .codesign 段（误诊修正）

**现象**：CI #31567 conan create 成功（三二进制打包），但 test_package 运行时报 `Permission denied`。当时误诊为 copy() 未保留执行权限，已在 package() 加 `os.chmod(0o755)` 并重新触发 CI（#31567 二次运行，recipe revision `a2cc4b05`），仍 Permission denied。

**误诊修正**：通过本地复现证伪了 copy() 权限说——
1. recipe revision `a2cc4b05`（带 chmod 的版本）与当前 conanfile.py `conan export` 比对完全一致，证明 CI 确实跑了带 chmod 的版本；
2. CI 日志显示 `Packaged 3 files`，package() 无异常，chmod 代码已执行；
3. 但二进制仍不可执行——chmod 对此无效。

**真实根因**：OHOS 内核拒绝执行缺少有效 `.codesign` 段的 ELF。clang 默认 lld 链接器自动注入该段（二进制可执行）；E266 改用的 GNU ld 不注入该段（二进制 Permission denied）。本地对比验证：
- lld 链接的 hello：含 `.codesign` 段，`rc=0` 可执行 ✓
- GNU ld 链接的 hello（`-fuse-ld=.../ld`）：仅 `.note.ohos.ident`，无 `.codesign`，`rc=126` EACCES ✗
- `binary-sign-tool -selfSign 1` 后签名注入 `.codesign` 但内核仍 EACCES（自签名不被信任）

**修复**：删 `cflags` 中的 `-fuse-ld=/data/service/hnp/bin/ld`，回到 clang 默认 lld 链接。lld 自动注入有效签名，二进制可直接执行。本地 conan create + test_package 验证 4 passed, 0 failed。`os.chmod(0o755)` 保留作冗余保险。

### CI #31563: test.sh 适配非零退出码

**现象**：CI #31563 conan create 成功，但 test_package 失败。exifcom/exiftime/exiftags 无参数时返回 exit 1（usage error），`set -eu` 下管道 `cmd 2>&1 | grep -q` 的 grep 失败导致脚本整体退出。

**修复**：重写 test.sh，移除 `set -e`，用 `$(cmd 2>&1) || true` 捕获输出后 grep 断言，显式 pass/fail 计数，仅断言失败时 exit 1。
