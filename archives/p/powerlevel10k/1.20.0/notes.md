# powerlevel10k 1.20.0 适配笔记

## 编译环境
- 构建系统: custom（纯 zsh 脚本，无编译步骤）
- 编译日期: 2026-09-03
- 编译器: 无（纯脚本包，cc/cxx 为空）
- 状态: built（share-only 包 conan-verify G4 预期降级，papirus-icon/theme 先例）

## 软件与版本来源
- 上游: https://github.com/romkatv/powerlevel10k
- 版本: v1.20.0（2024-01-26 发布，为撰写时最新 release）
- tarball: https://github.com/romkatv/powerlevel10k/archive/refs/tags/v1.20.0.tar.gz
- sha256: d8187d44b697b3a37a8c4896678b4380e717cbf2850179529358348780a2d3d7
  （ghfast.top 镜像与 codeload.github.com 双源下载交叉验证，字节一致）

## 打包方案（核心决策：仅打包 zsh 脚本，不带 gitstatusd 守护进程）

powerlevel10k 依赖 gitstatus 子项目（C++ 编写的 gitstatusd 守护进程）加速
vcs 段渲染。本包**只打包 zsh 脚本，不带 gitstatusd 二进制**，理由如下：

1. **tarball 内本就没有二进制**：v1.20.0 发布 tarball 中 `gitstatus/usrbin/`
   与 `gitstatus/deps/` 仅含 `.gitkeep` 占位；gitstatusd 预编译二进制位于
   gitstatus 项目的独立 release assets，不随本 tarball 分发。
2. **源码构建整条 C++ 依赖链不可行**：gitstatusd 需要链接 romkatv fork 的
   libgit2（`gitstatus/deps/libgit2` 子模块，tarball 中为空占位）；该 fork
   未发布到 ohpcd 制品仓（R36：未发布依赖 Hard Fail），从源码构建即引入
   整条 C++ 依赖链，远超纯脚本包适配范围。
3. **JC2 门禁禁止入库二进制**：即使下载官方 release 二进制，也无法随包
   提交到本仓库（无二进制入库先例，JC 拦截）。
4. **降级机制是上游设计内行为**（已实测验证）：
   - `internal/p10k.zsh:4165`：仅当 `GITSTATUS_DAEMON_PID_POWERLEVEL9K`
     已设置（daemon 已由 gitstatus 启动）才走 gitstatus 快路径，否则
     回退 zsh 原生 `vcs_info` 渲染 vcs 段；
   - `gitstatus/gitstatus.plugin.zsh:55-58`：`zmodload zsh/datetime
     zsh/system || return` / `zmodload -F zsh/files b:zf_rm || return` ——
     zsh 模块缺失时插件静默 return，主题继续以 vcs_info 后端工作；
   - 本机 `/usr/bin/zsh`（5.9, aarch64-unknown-linux-musl）恰好缺失
     `zsh/files` 模块，天然触发该降级路径：主题加载 exit 0、`p10k` 函数
     就绪、`_p9k_vcs_info_init`（vcs_info 回退后端）已定义。

## 编译步骤

```bash
# 1. init-build（仓库 scripts/ohc/init_build.py，源码经 ghfast.top 镜像下载
#    至 ~/tmp/builds/，sha256 校验通过，与 .work/.orig 基线一致）
# 2. conan create（-pr:h/-pr:b ci/conan/profiles/ohos-aarch64）
#    - source(): conan get() 下载并解压 tarball（CI 走 gh-proxy 镜像预下载）
#    - build():  pass —— 无编译
#    - package(): 整树复制到 share/powerlevel10k/（上游 install.md 语义：
#      "git clone the repository into your custom themes directory"，
#      整树即安装单元）
# 3. test_package: zsh 布局/语法/加载冒烟测试（14 断言，见下）
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | GitHub 直连下载超时 | 构建机网络策略 | ghfast.top 镜像前缀下载（与 codeload 双源交叉验证 sha256） |
| 2 | `conan download zsh/5.9` 失败（平台策略错误 + API 404） | zsh/5.9 未发布到 ohpcd 制品仓（archives/z/zsh/5.9/ 为旧式 partial 归档，仅 manifest+patches 无 conanfile） | conanfile 不声明 requires("zsh/5.9")（R36 Hard Fail）；test_package 使用系统 /usr/bin/zsh |
| 3 | 本机 zsh 缺 zsh/files 等模块（module_path 指向构建机残留路径） | 系统 zsh 为 musl 构建，模块目录未随包安装 | 恰好触发上游 gitstatus 降级路径（gitstatus.plugin.zsh:55-58 静默 return），vcs_info 后端正常；测试断言据此设计为双后端可接受 |
| 4 | gitstatusd 无法打包 | 见"打包方案"4 条理由 | 仅打包 zsh 脚本，降级机制兜底 |
| 5 | /tmp 只读（E002） | OHOS 平台限制 | 临时文件用 $HOME/tmp；TMPDIR=/storage/Users/currentUser/tmp |
| 6 | 手工 conan create 传相对路径 profile（`-pr:h ci/conan/profiles/ohos-aarch64`）时 profile 被静默替换（os.version 丢失、cppstd=gnu14、libcxx=libstdc++11、conf/buildenv 全丢），test_package 报 `Invalid ID: 'settings.os.version' value not defined` | conan 2.x 对非 `./`、`..` 前缀的相对 profile 参数**优先按名字在 ~/.conan2/profiles/ 下查找**：本机存在 2026-08-25 残留的 `~/.conan2/profiles/ci/conan/profiles/ohos-aarch64`（旧内容，无 os.version/conf/buildenv），遮蔽了同名相对路径；CI 的 build_and_test.sh 用 `$REPO_ROOT` 绝对路径不受影响 | 一律用绝对路径传 profile（与 CI 同款）；建议环境侧清理该残留文件（已记入最终报告） |
| 7 | conan-verify G1 报 `conanfile.py 缺少: 补丁应用调用` | G1 字面检查 `apply_conandata_patches` 调用（仓库惯例：无补丁也保留该 no-op 调用，posh/papirus-icon 先例） | build() 补 `apply_conandata_patches(self)`（patches: {} 下为 no-op） |
| 8 | finish Step3 G0 干净构建验证 `configure 失败 (exit 127)`（非阻塞警告） | G0 无 configure 跳过机制：解压根目录无 `./configure`（纯 zsh 脚本包，上游无 autotools）→ shell 报 127；唯一豁免通道是配方含 `replace_in_file`（运行时修复标记）。posh 0.14.6（tarball 同样无 configure，配方亦无 replace_in_file）finish 时同样 G0 假失败，仍以 built 终态交付 | 记录为框架对非 autotools 包的已知限制：真实构建验证由 conan-verify G2（conan create）+ W3 本地 CI（全绿）承担；不阻塞收尾 |

## 源码修改

无补丁：tarball 源码零修改（`diff -r` 与 .orig 基线比对 = 0 差异）。
gitstatusd 不打包是打包范围决策，非源码修改。

## 依赖版本

- 无 Conan 依赖（运行时仅需 zsh ≥ 5.1；上游 README 声明）
- 测试环境 zsh: /usr/bin/zsh（5.9, aarch64-unknown-linux-musl）
- conan 2.29.1（OHOS 适配版，os=OHOS 有效枚举）

## 验证结果

```bash
# 主题降级加载（test.sh 的核心断言，实测）：
$ GITSTATUS_AUTO_INSTALL=0 zsh -df +m -c 'source .../powerlevel10k.zsh-theme; ...'
rc=0  p10k=1  vcs_info_fallback=1  gitstatus_query=0   # 守护进程缺席 → vcs_info 回退就绪

# zsh -n 语法检查（全部通过）：
powerlevel10k.zsh-theme / internal/p10k.zsh / internal/configure.zsh
/ internal/wizard.zsh / gitstatus/gitstatus.plugin.zsh → SYNTAX-OK

# test_package 冒烟套件：14 断言（8 布局 + 3 语法 + 3 加载）全过，
# 详见 test_package/MANIFEST.yml 与 reports/w3-local-ci.log
```

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py | 配方（application / settings 四属性 / package_id clear / share-only） |
| conandata.yml | 官方 tarball URL + sha256（双源验证） |
| test_package/{conanfile.py,test.sh,MANIFEST.yml} | R34 消费者视角冒烟测试（14 断言） |
| patches/.no-patches-needed | 无补丁标记（源码零修改） |
| manifest.yaml | 版本级元数据（本文件同目录） |
| notes.md | 本文件 |

## 注意事项

- 上游无正式测试套件（无 check/test 目标），本包测试为消费者视角冒烟
  断言（如实记录于 test_package/MANIFEST.yml）。
- 主题启用方式：`source <pkg>/share/powerlevel10k/powerlevel10k.zsh-theme`
  （加入 .zshrc），随后运行 `p10k configure` 生成用户配置。
- 如未来 gitstatus/libgit2 在 ohpcd 发布，可另立版本重新评估打包
  gitstatusd（需同步处理 JC2 二进制入库限制）。
- share-only 包 conan-verify G4 预期降级，manifest 终态 built 属既定
  可接受终点（papirus-icon/theme 先例），勿误判为失败。
---

**编译结束**: 2026-09-03 20:36
**最终状态**: built
