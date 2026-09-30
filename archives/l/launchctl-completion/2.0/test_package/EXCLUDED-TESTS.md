# EXCLUDED-TESTS.md — launchctl-completion 2.0 上游测试排除说明

## 结论：NOT_APPLICABLE / NO_UPSTREAM_TESTS（上游零测试，无可排除对象）

本文件不是"逐条排除理由"清单，而是**零测试上游的判定证据链**（沿用
lazycontainer-0.0.1 先例范式）：上游从未有过测试套件，因此既无 NOT_RUN
对象（NOT_RUN 语义是"有测试但被跳过"），也无从移植。

## 判定证据（三证据，均可独立复核）

判定基于对 v2.0 tag（commit 9dd7a322db986105507f04b86c87d62e7a797584，
tarball sha256 990499494562cedf361482c5bf9f89b3a8b6a8aee92fda4e1eadaacb96688ecd）
的完整清单审计：

1. **归档全清单仅 2 个文件**：`LICENSE`（1069 B，MIT）与
   `launchctl-completion.sh`（29855 B，713 行）。无 tests/、test/、spec/
   目录，无任何 `*_test.*` / `*-test.*` / `test_*` 文件。
   （配方的 `build()` 对解包树做文件集合 + SHA256 机读复核，审计点唯一。）
2. **无任何测试入口**：无 Makefile（上游连构建系统都没有）、无
   run_tests.sh / tox.ini / pytest.ini / package.json / Cargo.toml 等
   任何测试 runner 配置。
3. **无 CI 配置**：无 `.github/`（workflows）、无 `.gitlab-ci.yml`、
   无 `.travis.yml`。交叉印证：GitHub Releases 的 v2.0 无任何附件
   （assets: []），Homebrew homebrew-core formula 的 `test do` 块仅做
   "source 后 `complete -p launchctl`"断言——即上游生态自己也将
   "加载注册成功"作为该包唯一可验证行为，与本冒烟 Check 3 同构。

## 与 OHOS 适配点的对应关系（冒烟为何这样设计）

上游零测试时没有可移植的测试对象，断言对象替换为"适配动作本身做对了没"：

| 冒烟检查 | 对准的适配决策 |
|---|---|
| ① bash >= 5.3 | 脚本用 `compgen -V`（bash 5.3 新增）与 `local -n`（4.3+）→ requires("bash/5.3")，端到端验证依赖包内 bash 真的被用到 |
| ② bash -n 语法 | 数据包忠实原则：不改上游源码，语法门禁证明安装件完整可用 |
| ③ complete -p 逐字断言 | 复刻 Homebrew test 块：source 加载 + complete 注册成功 |
| ④ _launchctl2 在册 | 补全函数真被定义（而非静默半加载） |
| ⑤ 静态一级补全 44 项 + 关键成员 | 纯 builtin 路径冒烟：OHOS 无 launchctl/dscl 数据源也能完成静态子命令补全；COMP_CWORD=1 分支先于脚本内一切外部命令返回，不写 /tmp |
| ⑥ 安装路径 | Homebrew 同款：share/bash-completion/completions/launchctl 改名放置 |
| ⑦⑧ SHA256 逐字节一致 | E241 固定输出精确比对：安装件 = 上游原件（数据保真） |
| ⑨ 机读证据文件在场 | 审计链可机读复核（本文件 + UPSTREAM-TESTS-EVIDENCE.json） |

## 功能面诚实披露（不属测试排除，属运行期限制）

- `launchctl` 本体在 OHOS 不存在：`complete -F` 注册无害，仅在用户
  手敲 `launchctl <TAB>` 时触发。
- 动态数据源（`launchctl list`、`dscl . -list /Users`、`/Library/Launch*`
  glob、可选 `fd`/`segment_dumper`）缺失：对应补全分支产出空集；
  脚本第 97/102/107 行的 `launchctl list` 调用无 stderr 守卫，
  补全 `list <TAB>` 等场景会有 command-not-found 噪声一行。
  按**数据包忠实原则不修改上游内容**，此为已知并接受的功能限制。
