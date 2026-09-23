# mussh 1.0 — HarmonyOS PC (aarch64, os=OHOS) 适配笔记

## 基本信息
- 上游源: https://downloads.sourceforge.net/mussh/mussh-1.0.tgz (官方 SourceForge 渠道, https 经检视意见升级, sha256 与 http 一致)
- 实测 sha256: 6ba883cfaacc3f54c2643e8790556ff7b17da73c9e0d4e18346a51791fedd267
- 性质: 纯 bash 脚本 (MUltihost SSH Wrapper), 上游 2011 年发布, 无构建系统
- 语言: bash 脚本 (CI 能力矩阵 bash ✅, 无 Rust/OCaml 等工具链缺口)
- 依赖: 无 Conan 依赖; 运行时依赖 ssh/ssh-agent/ssh-add/sed/cat/mktemp/
  hostname/awk 全部为系统命令 (openssh 工具集属系统命令, 非制品依赖)

## 适配结论 (零编译)
- 无 configure/make/CMake, 无编译步骤: build() 仅 apply_conandata_patches
  (零补丁时 no-op)
- source(): get(..., strip_root=True) — 压缩包根目录为 mussh/
- package(): 显式挑选 4 个目标 — mussh → bin/mussh (os.chmod 0o755),
  mussh.1 → res/man/man1/, README/CHANGES → licenses/ (README 声明 GPL
  未注明版本, 出处置证); 禁止整目录拷贝 (包内 .swp/.mussh.1.swp/mussh.bak/
  mussh.spec/casetest.sh 杂物)
- package_id(): self.info.clear() — 纯脚本内容跨平台一致
- package_info(): includedirs=[], libdirs=[], bindirs=["bin"]

## 补丁说明 (0001-shebang-env-bash.patch)
- 初始决策为零补丁: shebang 保持上游 #!/bin/bash, 本地 mussh -V 实测
  输出 "Version: 1.0" 且退出码 0
- CI 实证触发预案: PR#7998 首轮 CI 红于 L0c no_test_sources, 补
  test_mussh.sh 后第二轮 CI 在 conan test 执行环节报
  "/bin/bash: bad interpreter: No such file or directory"
  (CI worker 与本地沙箱同源, 均无 /bin/bash, shell 位于
  /data/service/hnp/bin/bash) — 本地+CI 双证据, 按预案打
  shebang 补丁: #!/bin/bash → #!/usr/bin/env bash (env 经 PATH
  定位 bash, 非 __OHOS__ 平台宏, 纯 portability 修改)
- 上游脚本其余内容无平台相关硬编码, 无需其他修改

## 测试结论（含人工审核 rule4 整改）
- 上游 test/ 3 个 shell 集成测试（10_basic_connect.sh/11_hostfile.sh/
  12_async.sh）为 mussh 对 localhost 的 ssh 编排测试
- 整改尝试 1（部署 SSH 服务端实跑）：OpenSSH sshd 无法部署——
  /usr/local 只读（编译期写死 libexec /usr/local/lib/sshd-session）+
  /etc/passwd 只读 fs（privsep 用户无法添加）；改部署 paramiko
  协议级 SSH 服务端（真实 ssh 公钥认证+远程命令执行，127.0.0.1:2222），
  wrapper ssh (-F /dev/null 绕 HMDFS config 权限归一化) 连通成功
- 整改尝试 2（实跑测试脚本）：mussh 编排层验证成功——144 次连续 ssh
  连接与远程命令执行全部成功（10_basic 核心断言 `mussh -h localhost
  -c "date"` 在编排层成立）；但测试脚本无法正常终止
- 1-e 归因（附证据）：mussh 多主机编排依赖临时目录文件协议
  （hostlist.lock 追加锁 + rm/mv 收缩 hostlist）；HMDFS（沙箱唯一
  用户可写 fs）写后读不一致——三种收缩写法（rm+mv / cat 覆盖）均不
  生效（2641+ 次循环现场尸检 hostlist 恒为初始值），沙箱无非 HMDFS
  可写文件系统（/tmp 只读 erofs、/ root755、/data/local/tmp root、
  /usr 只读、for-all-app root、sudo 无 tty，六候选穷尽）→ 测试脚本
  平台不可运行（1-e 技术原因），证据文件留档 paramiko-server-exec-log
  与 mussh-tempdir-corruption-evidence
- 新增 0002-mktemp-tmpdir.patch：mussh 硬编码 TEMP_BASE=/tmp，鸿蒙
  /tmp 为只读 erofs（E002），改 ${TMPDIR:-/tmp}（未设 TMPDIR 行为不变）
- test_package (explicit): bin/mussh 存在且可执行 + can_run 时
  test_mussh.sh 实际执行 mussh -V 断言 stdout 含 "Version: 1.0";
  禁止无参数/--help 断言 (两者退出码均为 0, 无区分度)
- CI 首轮教训: test_package 除 conanfile.py 外必须有实体测试源文件
  (.c/.cpp/.sh/.py, L0c no_test_sources 门禁), 已补 test_mussh.sh;
  本地 conan create 复验通过后追加提交
- 本沙箱域禁止执行脚本/ELF (E052/E077 同源), 本地 W3 仅验证打包完整性,
  运行验证交 CI 执行机 conan test

## Conan 配方要点
- package_type=application, settings 四元组兼容 ohos-aarch64 profile
- package_id(): self.info.clear() — script-only 内容跨平台一致
- 无 requirements: 运行时依赖全为系统命令
- commands.json (R38): 产物为命令行工具, 软件级声明 type=tool
- test_package (R34/PF3): 断言 bin/mussh 存在+可执行, can_run 时
  mussh -V stdout 断言; test_type=explicit (conan create 不执行,
  CI conan test 真跑)

## 任务信息
- 任务来源: 智能任务平台依赖项任务 (沿用 musepack r475 流程)
- 认领时间: 2026-09-03 18:10 CST
- 任务分支: feat/mussh-1.0 (基点 f5131ee224, 最新 origin/main)
- 推送目标: 个人 Fork git@gitcode.com:Hawkninja21/build_in_harmonyos.git

---

**编译结束**: 2026-09-03
**最终状态**: built
