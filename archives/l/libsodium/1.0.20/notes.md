# libsodium 1.0.20 HarmonyOS PC 移植说明

## 移植范围

- 上游版本：1.0.20
- 官方源码：`https://download.libsodium.org/libsodium/releases/libsodium-1.0.20.tar.gz`
- 目标系统：HarmonyOS 6.0 PC
- 构建系统：Autotools
- Conan 引用：`libsodium/1.0.20`
- 默认产物：静态库

## 适配内容

1. 为上游 `build-aux/config.guess` 增加 HarmonyOS `uname` 识别，并让
   `config.sub` 接受 `linux-ohos`。交叉构建的 `--build` 和 `--host` 由
   Conan 根据构建机与 HarmonyOS SDK 目标自动生成。
2. `configure`、编译和打包全部在构建主机执行，目标机只运行生成的测试
   程序，因而不依赖 HarmonyOS HMDFS 执行 Autotools 脚本。
3. Conan 构建固定以单任务方式编译库和全部上游测试程序；`test_package`
   从消费者视角编译、链接公开 API 测试，交叉构建时需另行将程序送到
   目标机运行。
4. HarmonyOS 当前仅提供已验证的静态库；选择 `shared=True` 时配方会明确
   拒绝该配置，避免发布未经目标机运行验证的动态库。
5. HarmonyOS CI 的 HMDFS 会对 `umask 077` 创建的 Autoconf 临时目录发生
   UID 映射，导致 `config.status` 无法访问 `subs1.awk`。配方在运行
   `configure` 前将该临时目录掩码调整为 `022`，对应知识库 E114。

## 测试范围

- 上游测试：`test/default` 中由 Automake 登记的 80 个测试目标。
- 消费者测试：7 个断言，覆盖初始化、版本、secretbox 往返、篡改拒绝和
  安全清零。
- 2026-09-08 在 HarmonyOS 6.0 x86_64 PC 虚拟机上，上游测试 80/80
  通过，消费者测试 7/7 通过。
- WSL 中使用 Conan 2.29.1 完成 `libsodium/1.0.20` 静态包创建，并从该包
  成功编译消费者测试程序；目标机运行结果同上。
- 使用同一套 HarmonyOS SDK 对 arm64-v8a（Conan `armv8`）完成库、80 个
  上游测试程序和消费者测试程序的交叉编译；arm64 本轮仅做编译验证。
- 动态库未形成可在目标机验证的稳定产物，因此本版本不支持 HarmonyOS
  `shared=True`。
- 使用真实 `configure` 和受控 `mktemp` 模拟 HMDFS UID 映射：修复前稳定
  复现 `subs1.awk: Permission denied`，修复后完整生成全部 Makefile。

## 复现命令

准备 Conan 2 的构建与目标 profile。构建 profile 使用 Linux/GCC；目标
profile 必须让 Conan 的 `arch` 与编译器 `--target` 成对匹配。以下示例中
`<SDK>` 替换为 HarmonyOS SDK 的 `native` 目录。

PC 虚拟机 profile：

```ini
[settings]
os=OHOS
os.version=6.0
arch=x86_64
compiler=clang
compiler.version=15
compiler.libcxx=libc++
compiler.cppstd=17
build_type=Release

[conf]
tools.build:compiler_executables={"c": "<SDK>/llvm/bin/clang --target=x86_64-linux-ohos --sysroot=<SDK>/sysroot", "cpp": "<SDK>/llvm/bin/clang++ --target=x86_64-linux-ohos --sysroot=<SDK>/sysroot"}
```

arm64 profile：

```ini
[settings]
os=OHOS
os.version=6.0
arch=armv8
compiler=clang
compiler.version=15
compiler.libcxx=libc++
compiler.cppstd=17
build_type=Release

[conf]
tools.build:compiler_executables={"c": "<SDK>/llvm/bin/clang --target=aarch64-linux-ohos --sysroot=<SDK>/sysroot", "cpp": "<SDK>/llvm/bin/clang++ --target=aarch64-linux-ohos --sysroot=<SDK>/sysroot"}
```

创建包时明确区分目标与构建 profile：

```bash
conan create archives/l/libsodium/1.0.20 \
  -pr:h=<ohos-target-profile> -pr:b=<linux-build-profile> --build=missing
```

Conan 交叉构建执行 `make check -j1 TESTS=`，用于编译而不在构建机误运行
80 个目标程序。目标机验证时，把 `test/default` 的可执行文件及同名 `.exp`
文件发送到可执行目录，并逐一检查退出码和输出；消费者程序也同样发送执行：

```bash
hdc -t <target> file send <test-program> /data/local/tmp/libsodium-tests/
hdc -t <target> file send <test-program>.exp /data/local/tmp/libsodium-tests/
hdc -t <target> shell chmod 755 /data/local/tmp/libsodium-tests/<test-program>
hdc -t <target> shell 'cd /data/local/tmp/libsodium-tests && ./<test-program>'
```

仓库级预检命令如下；在 Windows 上应从能够读取 POSIX 目标 profile 的
WSL/CI 环境执行 Conan 步骤：

```bash
python scripts/ohc-run.py conan-verify libsodium 1.0.20
python scripts/ohc-run.py finish libsodium 1.0.20
python scripts/ohc-run.py graph validate
```
