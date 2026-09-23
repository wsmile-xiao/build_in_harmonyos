# breeze-grub 6.7.2 HarmonyOS 资源包适配

## 范围与来源

用户确认交付资源包。官方源码为 KDE Plasma 6.7.2 发布包，SHA256 见 conandata.yml；保留原始主题内容，不修改引导配置。复用知识 E255、E241。

W0：打包无 requires/tool_requires；已执行仓库依赖预检。远端版本查询返回 `error:system acceleration policy not enabled`，只能记录版本占用尚未核实，不能将该错误解释为版本不存在。W1：起点为 upstream/main `542b245a1266d73d7c4f819faeb4b377cbb80f04`。

语言预检：源码无编译单元，检测为 `other`。按用户确认的资源类型执行 `lang-preflight --lang other` 通过；默认 cpp 的检查不适用于本数据包。

## 上游测试清点（R51）

归档 36 个成员，其中 33 个普通文件、3 个目录。breeze/ 有 23 个资源，LICENSES/ 有 7 份正文，另有 REUSE.toml、mkfont.sh、.gitlab-ci.yml。无 tests/、CMakeLists.txt、Makefile、pytest/CTest 注册或功能测试。上游功能用例数 0；上游 CI 仅引用外部 REUSE 许可证检查，不计作功能测试。没有修改或删除上游测试。

## 配方与补全测试

Conan `package_type=unknown`，settings 四项满足当前 CI，package_id 清除架构/编译器差异。直接安装 23 个资源以及许可证/REUSE，共 31 个文件。未包含 mkfont.sh，因为它是再生字体的作者工具而非运行所需内容。

test_resources.py 为 7 个消费者用例：31 个文件的固定 SHA256/长度和精确清单；12 张 PNG 的块 CRC、解压尺寸及过滤器；3 个 PF2 字体的字符索引/位图边界和必需菜单字符；主题字体与九宫格/进度条资源引用；SVG XML；许可证元数据；Conan 运行环境发现。

C 消费者有 3 个公共用例：读取并校验全部 23 个主题文件；缺失资源拒绝；theme.txt 损坏拒绝。1 个鸿蒙特有用例仅在真实 SDK `__OHOS__` 编译下执行：向 TMPDIR 的空格目录复制完整主题、重命名为 UTF-8 名称、重新逐个校验内容并清理。本机目录权限不依赖 chmod/X_OK 语义。

计数为 10 个公共用例 + 1 个鸿蒙用例，内部逐文件断言不重复计数。HDC 路径核验系统身份、远端退出码和每项完成标记；远端失败不会因 HDC 进程返回零而被当作通过。原生 OHOS worker 路径使用 binary-sign-tool 后执行同一 C 程序。

## 本机环境问题

Windows 现有 SDK profile 的 Ninja 生成器配了 mingw32-make.exe；本次运行用 `-c:h tools.gnu:make_program=<SDK>/native/build-tools/cmake/bin/ninja.exe` 修正。SDK 注入的 --gcc-toolchain 参数在 clang 编译阶段产生 unused-command-line-argument，测试目标仅将该工具链诊断降为警告，保留源代码 -Wall/-Wextra/-Werror。

## 实测记录

Windows Conan 2.29.1 + OHOS SDK 26.0.0/clang 15.0.4 构建成功，11/11 个用例通过：7 个 Python 内容用例在宿主机执行，4 个 C 程序用例在虚拟机执行。目标端完整读取 23 个主题文件，缺失和损坏资源均以非零退出拒绝，鸿蒙 TMPDIR 复制/重命名/重新读取通过。首轮 Linux/WSL Conan 构建也通过通用测试。

本地虚拟机标识 `OpenHarmony-6.0.0.47`，架构 x86_64。资源包无架构差异；不会将 x86_64 实测写成 arm64 PC 原生测试结果。

### 原始本地 CI（W3）

通过 `FinishPipeline.step35_local_ci()` 调用未修改的 `ci/conan/setup.sh` 和 `ci/conan/build_and_test.sh`，隔离 Conan 缓存执行，1/1 包通过、退出码 0。由原始流程生成 `.ci-result.json`，没有手写或修改通过标记。日志 `reports/w3-local-ci.log` 的 SHA256 为 `2177f57a58c3e7e86cdda93466f2ec4bb792e4755b5f61fde8257f1dab3501ba`。

W3 在 WSL 运行，通过本机 OHOS SDK 编译包装器调用 Windows clang，以 HDC 在上述 x86_64 鸿蒙虚拟机执行同一消费者；资源主包没有编译步骤。`JUNK_PR_DIFF` 是本软件全部实际新增文件的 diff；既有 SDL2/tinyxml2/libsodium/bmkdep/pari/boost/libXext 内容不进入本包检查。CI 预下载流程校验官方包，并在结束时自动把临时 file:// 地址恢复为官方 HTTPS，已核验恢复。

L0/L1/L4 通过。资源包没有 bin/lib，L2 为 skip，L5 为 warn；通用 L1e 只破坏 bin/lib/include，所以为 skip。本包自身执行真实资源缺失/损坏的反向测试，弥补该检查的资源目录覆盖范围。没有把不适用的二进制门禁记成已执行通过。

### 额外验证

- 仓库 `tests/run_all.py`：10/11 套件直接通过；`test_v1220.py` 写死 `/data/service/hnp/git.org/git_2.45.2/bin/git`，WSL 不具备该路径。在独立测试进程内将 GITBIN 映射到 `/usr/bin/git` 后，原有 33/33 断言通过；未修改 tests 文件或测试断言。
- 3 个独立破坏性内容验证通过：PNG 数据修改被 CRC 验证拒绝，PF2 截断被字形边界验证拒绝，主题引用不存在字体被语义验证拒绝。这 3 项单独统计，不混入 11 项 Conan 用例。
- 知识图谱 `graph validate` 通过，540 条目，169 个既有警告；没有修改他人知识条目。
- 独立审查未发现阻塞问题，重新比对 31 个源文件 SHA256 和 23 个资源 CRC32/长度均一致。审查证据包含配方和测试源码哈希。
- 仓库 `ohc-run.py conan-verify breeze-grub 6.7.2` 已通过，完整报告为 `reports/conan-verify-report.md`。使用本次 WSL OHOS profile 的绝对路径；验证器自动创建本地 `@ohpcd/stable` 验证引用，仅存在本机缓存，不代表发布。配方状态仍为 built。

## 复现命令

原生 HarmonyOS PC CI（环境须提供仓库要求的 Conan/clang/CMake/binary-sign-tool）：

```sh
conan create archives/b/breeze-grub/6.7.2 \
  -pr:h=ci/conan/profiles/ohos-aarch64 \
  -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing
```

本机 Windows → x86_64 鸿蒙虚拟机，使用当前项目已配置的环境 profile：

```powershell
$env:PATH = "$env:LOCALAPPDATA\OpenHarmony\Sdk\26.0.0\native\build-tools\cmake\bin;" + $env:PATH
$env:BREEZE_GRUB_HDC = (Get-Command hdc).Source
$env:BREEZE_GRUB_HDC_TARGET = '127.0.0.1:5555'
conan create archives/b/breeze-grub/6.7.2 `
  -pr:h=.ohc/profiles/ohos-6-x86_64-sdk26 `
  -pr:b=.ohc/profiles/windows-x86_64-build `
  -c:h=tools.gnu:make_program=C:/Users/ASUS/AppData/Local/OpenHarmony/Sdk/26.0.0/native/build-tools/cmake/bin/ninja.exe `
  --no-remote
```

`.ohc/profiles` 是本地 SDK 配置，不是配方依赖；其他机器应按实际 SDK 路径建立对应 profile。跨编译未配置 HDC 会明确失败。Conan 包状态为 `built`，尚未上传；没有创建、推送 PR。
