# mrbayes 3.2.7a — HarmonyOS PC 适配笔记

## 适配要点

- **构建系统**：autotools，官方 release 包内含预生成 `configure`，无需 autoconf/automake
- **可选依赖全部禁用**：readline（`--with-readline=no`）、beagle-lib（`--with-beagle=no`）、MPI（`--with-mpi=no`）；核心功能（贝叶斯 MCMC 分析）不依赖三者
- **x86 SIMD 显式关闭**：`--enable-sse=no --enable-avx=no --enable-fma=no`，armv8 平台无对应指令集
- **补丁 0001**：`src/bayes.c` 在 Unix 命令行解析块内把 GNU 长选项 `--version`/`--help` 归一化为 `-v`/`-h`，兼容 CI L2 冒烟测试（上游仅支持短选项）
- **补丁 0002/0003**：`am-aux/config.guess`（2015 版）不识别鸿蒙 `uname -s = HarmonyOS`，补丁添加 `__OHOS__` libc 检测与 HarmonyOS case 分支（输出 `aarch64-unknown-linux-ohos`）；`am-aux/config.sub` 接受 `linux-ohos*` 三元组
- **补丁 0004**：`configure` 临时目录创建 `umask 077` → `022`（HMDFS 上 0700 目录不可读导致 configure 检测失败，设备实测 E011）
- **HMDFS 规避**：profile 的 `[buildenv] CONFIG_SHELL` 指向存在 getcwd 缺陷的 bash；recipe 在临时构建目录中构建（位于 Conan build 目录的**父级**缓存目录——鸿蒙 `/tmp` 只读，E002；且不能放在 build_folder 之下：basic_layout 的源码目录就在那里，copytree 把源码复制进自身后代会导致无限递归，设备实测），覆盖 `CONFIG_SHELL=/bin/sh`、`SHELL=/bin/sh`，用 `subprocess` + `/bin/sh` 脚本驱动 configure/make，不使用 Conan 的 shell wrapper
- **make -j1**：HMDFS 不支持 mkfifo，make jobserver 无法工作
- **编译器获取（R33）**：`tools.build:compiler_executables` conf → `VirtualBuildEnv`（profile [buildenv]）→ `CC` 环境变量 → 无则抛 `ConanException`，全程无硬编码路径
- **构建内冒烟测试**：`make` 后立即 `./src/mb -v | grep -q '3.2.7a'`，构建失败早暴露
- **包类型 application**：`package_info` 设置 `bindirs = ["bin"]` 并将 bin 目录加入 buildenv/runenv PATH

## 问题与解决方案

| 问题 | 解决 |
|------|------|
| 上游无测试套件 | test_package 补全 consumer 测试：test_mb.sh 真实运行 mb（--version + 4 taxa 完整 MCMC + sump 后验汇总 + stdin EOF 安全），9 项检查 |
| `mb --version` 不支持（上游仅 `-v`） | 补丁 0001-bayes.c.patch |
| HMDFS bash getcwd 缺陷 | 临时构建目录 + /bin/sh（覆盖 profile 的 CONFIG_SHELL） |
| 鸿蒙 `/tmp` 只读 | TMPDIR 重定向到 HOME 下可写目录（与 CI 的 `$HOME/tmp` 惯例一致） |
| 2015 版 config.guess 不识别 `uname -s=HarmonyOS`（"cannot guess build type"） | 补丁 0002/0003（config.guess/config.sub 识别 linux-ohos） |
| configure 在 HMDFS 上 umask 077 建目录不可读 | 补丁 0004-configure-umask-022.patch |
| copytree 无限递归（临时目录落在 basic_layout 源码树内） | 临时目录必须位于 Conan 源码树之外（设备实测后改用 HOME/tmp） |
| HMDFS 不支持 mkfifo | make -j1（单线程） |
| 包类型为 application（无库/头文件） | `package_type = "application"` + `bindirs` + 软件级 commands.json（R38） |

## 验证命令（设备）

```bash
cd /storage/Users/currentUser/build_in_harmonyos
export PATH="$HOME/.local/bin:$PATH"
PROFILE=ci/conan/profiles/ohos-aarch64
conan create archives/m/mrbayes/3.2.7a -pr:h=$PROFILE -pr:b=$PROFILE --build=missing
# 完整 CI 门禁
CI_PACKAGES="archives/m/mrbayes/3.2.7a" zsh ci/conan/build_and_test.sh
```

test_package 输出应包含 9 个 PASS，退出码 0。

## 设备验证记录（2026-08-15）

- `conan create`（conan 2.29.1，ohos-aarch64 profile，clang 15）：✅ 4 个补丁全部 apply，构建 + 打包 + test_package 9/9 PASS
- 完整 CI 门禁 `build_and_test.sh`：✅ 100%（1/1）
  - L0 pass（全部质量门禁）、L1 pass（test_package 真实执行 + L1e 破坏性负向测试确认测试真实依赖包产物）、L2 pass（`mb --version`）、L5 pass（bin/ 有内容）
  - L4 warn（非阻塞）：补丁扫描器在 `0002-config.guess-ohos.patch` 上下文的上游注释 "NetBSD (nbsd) targets" 中命中 "gets" 子串（tar-**gets**），误报，补丁未引入任何 strcpy/sprintf/gets/strcat 代码
- 注意：CI 脚本会就地改写 conandata.yml（镜像回退 + 预下载），验证后需从快照恢复
