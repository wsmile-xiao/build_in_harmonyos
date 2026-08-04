# fcheck 2.7.59 HarmonyOS 前置适配记录

## 状态

- 分支：`feat/fcheck-2.7.59`
- Issue：[#1690](https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos/issues/1690)
- 当前状态：`built`（本机前置与真机单包验证通过）
- 范围：新增软件级 `archives/f/fcheck/commands.json` 与版本目录 `archives/f/fcheck/2.7.59/`。

## W0 依赖检查

- Debian source `fcheck_2.7.59-27.dsc` 声明 `Build-Depends-Indep: perl`；fcheck 主体是 Perl 脚本。
- 2026-07-31 复查：`conan list 'perl/*' -r=ohpcd` 可见 `perl/5.42.2`。
- `conan download 'perl/5.42.2' -r=ohpcd --only-recipe` 成功。
- `conan list 'perl/5.42.2:*' -r=ohpcd` 可见 OHOS/armv8 binary，settings 为 `os=OHOS os.version=6.0 arch=armv8 compiler=clang compiler.version=15 compiler.libcxx=libc++ compiler.cppstd=17 build_type=Release`。
- 结论：fcheck 已声明 `perl/5.42.2` 运行时依赖；不再阻塞于 Perl 未发布。

## 源码与构建系统

- 来源：Debian authoritative source mirror。
- URL：`https://deb.debian.org/debian/pool/main/f/fcheck/fcheck_2.7.59.orig.tar.gz`
- sha256：`93c88330173f3f5b21814d6a1b0821875d5714e5b03d0b57c44269cf8d27ae25`
- 源码内容：`fcheck`、`fcheck.cfg`、`README`、`install`、`license`。
- 构建系统：无编译步骤，纯 Perl application。
- 官方上游测试套件：未发现 `make check`、测试目录或可枚举测试用例，因此上游测试用例通过率记为 `0/0（N/A）`。
- 可运行上游检查：使用 `perl -c fcheck` 作为上游脚本语法检查；真机 `conan create` 已执行并通过。
- 消费者测试：使用自动模式创建 baseline 数据库并重复校验。

## 配方策略

- `package_type = "application"`。
- `requirements()` 声明 `self.requires("perl/5.42.2", headers=False, libs=False, run=True)`，通过 Conan `VirtualRunEnv` 为 build/test 提供 Perl。
- 安装 upstream script 到 `share/fcheck/fcheck.pl`。
- 安装 package-local sample config 到 `share/fcheck/fcheck.cfg`，默认只指向当前目录和 `./fcheck.dbf`，并排除 baseline 文件自身，避免默认扫描系统根目录或因数据库自增触发误报；签名命令使用上游可解析的 `Signature` 键。
- 安装 `bin/fcheck` Perl launcher：使用当前 Perl 解释器执行脚本，并在未显式传 `-f` 时注入 package-local sample config；空参时默认执行 `-af <package config>`。
- `test_package/test.sh` 使用 `fcheck -acf <cfg>` 创建 baseline、`fcheck -af <cfg>` 校验，并覆盖包内默认配置下的裸 `fcheck` 执行。上游非自动模式不会写 `END Directories` 分隔符，第二次读取会报 `Malformed database no ending delimiter line for Directories`，因此测试必须走配置中的 `Directory` 自动模式。
- 补丁只包含：
  - shebang 改为 `/usr/bin/env perl`
  - 默认配置文件从 `/usr/local/admtools/conf/fcheck.cfg` 改为相对 `fcheck.cfg`
  - Debian 的 empty-directory bugfix
  - 移除现代 Perl 废弃的 `$[` 赋值
  - 改进数据库不可写错误信息

## 本机验证

已通过：

```sh
python -m py_compile archives/f/fcheck/2.7.59/conanfile.py archives/f/fcheck/2.7.59/test_package/conanfile.py
git apply --check --unsafe-paths -p1 archives/f/fcheck/2.7.59/patches/0001-ohos-portability.patch
git diff --check -- archives/f/fcheck/2.7.59
conan inspect archives/f/fcheck/2.7.59
conan download perl/5.42.2 -r=ohpcd --only-recipe
conan create archives/f/fcheck/2.7.59 --user=ohpcd --channel=stable -s:h os=OHOS -s:h os.version=6.0 -s:h arch=armv8 -s:h compiler=clang -s:h compiler.version=15 -s:h compiler.libcxx=libc++ -s:h compiler.cppstd=17 -s:h build_type=Release --build=fcheck/* -r=ohpcd
```

OHOS host `conan create` 结果：

- 源码下载成功。
- Conan patch 应用成功。
- 依赖图包含 `perl/5.42.2`。
- 从 ohpcd 下载 Perl OHOS/armv8 binary：package id `6b129b068851896169fae42d399fa922d239ce8a`。
- package() 产物生成成功：`bin/fcheck`、`share/fcheck/fcheck.pl`、`share/fcheck/fcheck.cfg`、README/install/license。
- test_package 布局检查通过；`test_package/test.sh` 是 L0c 可见的真实消费者测试源文件。
- `conanrunenv-armv8.sh` 中 `PATH`、`PERL`、`PERL5LIB` 已由 `perl/5.42.2` 注入。
- runtime 测试因 Windows 本机 host=OHOS 不能执行目标 Perl 被跳过；真机已覆盖 baseline create + verify。

本机未通过项目 `ci/conan/build_and_test.sh`：Windows 环境未发现 `zsh`。真实 fcheck runtime 需在 OHOS 原生环境或 shadow CI 执行。

## 真机验证

2026-07-31 通过 SSH 进入共享 OHOS 真机后，在隔离 job 中运行单包 runner。

- 远端 job：`/storage/Users/currentUser/ohos-users/codex/fcheck-2.7.59-20260731`
- 通过 run：`/storage/Users/currentUser/ohos-test-runs/codex-fcheck-fcheck-2.7.59-conan-targeted-r3q-20260731-191552-20260731-191552-16959`
- 命令：`zsh ci/conan/build_and_test.sh archives/f/fcheck/2.7.59`
- 结果：exit code `0`，`Build Summary: Total 1, Success 1, Failed 0`
- 门禁：`L0_RESULT=pass`、`L1_RESULT=pass`、`L4_RESULT=pass`、`L5_RESULT=pass`
- 已按 CLI 工具规则补齐软件级 `archives/f/fcheck/commands.json`，声明 `type: tool`。
- 说明：`L2_RESULT=skip`，因为 CI 的 L2 直接执行 `bin/fcheck --version/--help`，没有加载 Conan `VirtualRunEnv` 中的 Perl；该项为非阻塞，真实 runtime 已由 `test_package` 在 `conanrun` 环境中通过。
- 注意：首次远端隔离 `CONAN_HOME` 缺少 OHOS settings，已通过复制真机全局 `$HOME/.conan2/settings.yml` 到 job `CONAN_HOME/settings.yml` 修复；正式 CI 应先跑 `zsh ci/conan/setup.sh`。

2026-07-31 AI review 修复后复测：

- 命令：`zsh ci/conan/build_and_test.sh archives/f/fcheck/2.7.59`
- 远端环境补充：共享真机 `/tmp` 不可写时需设置 `TMPDIR=$OHOS_JOB_BASE/work/tmp`、`TMPPREFIX=$OHOS_JOB_BASE/work/tmp/zsh`，避免 zsh here-doc 临时文件创建失败。
- 结果：exit code `0`，`Build Summary: Total 1, Success 1, Failed 0`
- 门禁：`L0_RESULT=pass`、`L1_RESULT=pass`、`L4_RESULT=pass`、`L5_RESULT=pass`
- L0k：`commands.json valid (type=tool)`。
- test_package：显式配置 `baseline create/verify` 通过，包内默认配置下裸执行 `fcheck` 通过。

过程中修正过的失败：

- `Invalid setting 'OHOS'`：隔离 Conan settings 过旧/缺失 OHOS 枚举。
- `Malformed database no ending delimiter line for Directories`：测试脚本改为 `-a` 自动模式后通过。

## 下一步 shadow CI / PR

单包验证命令：

```sh
zsh ci/conan/setup.sh
CI_PACKAGES="archives/f/fcheck/2.7.59" zsh ci/conan/build_and_test.sh
```

shadow CI 定向命令：

```sh
/path/to/run-ohos-shadow-ci.sh archives/f/fcheck/2.7.59
```

真机前置检查建议：

```sh
command -v perl
perl -v
conan list 'perl/*' -r=ohpcd
```

PR 前建议命令：

```sh
git add archives/f/fcheck/2.7.59
git commit -m "feat(fcheck): 2.7.59 编译完成"
```
