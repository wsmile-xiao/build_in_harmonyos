**DRAFT-libncursesw-6.6-build-path-archiver - OHOS 原生编译通过后静态归档找不到 ar**

OHOS 原生配方即使通过绝对路径调用 Clang 编译所有对象，也不代表 `make` 的独立归档工具 `ar` 可被找到。这份草稿补充 E540 所述 runner 工具路径问题：配方要保留调用方的 PATH 并合成 Conan 构建环境，目标机 profile 仍须独立提供可执行的归档器；二者不可互相替代。设置 `AR=llvm-ar` 的基本方法已由 E012 记录，不作为本次新发现。

**身份与当前结论**

| 字段 | 内容 |
|---|---|
| 草稿与状态 | `DRAFT-libncursesw-6.6-build-path-archiver`；真机证据已取得，待维护者审核，不是正式 E 条目 |
| 建议去向 | 补充 E540 的配方局部 PATH 覆盖和静态归档器边界，不申报新模式 |
| 贡献者 | Windrel，来源提交作者 `<windrel@users.noreply.gitcode.com>` |
| 来源与本次交付 PR | [GitCode !10433](https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos/merge_requests/10433)，精确分支 `feat/libncursesw-6.6_p20260516` |
| 提取方式 | 新适配过程中，从同一提交的失败/成功真机运行提炼 |
| 包与上游 | `libncursesw/6.6_p20260516`；ncurses 6.6，`https://invisible-mirror.net/archives/ncurses/ncurses-6.6.tar.gz`；SHA-256 `355b4cbbed880b0381a04c46617b7656e362585d52e9cf84a67e2009b749ff11` |
| 知识来源提交与被验证提交 | `ecce6bcdd8093895839faffe9a13051d8576d1e3`；失败/首次成功的相同中间提交 `2b07bb5f62850b7f72d49daffc2f0202761f9b55` |
| 更新日期 | 2026-09-16 |

本次已在目标机确认编译与归档工具可独立失效；最终 `ecce6bcdd` 的隔离运行通过 L0/L1/L2/L4/L5。没有单变量实验能证明保留 PATH 一项改动就足以修好 `ar`：从失败到成功还调整了设备本地 profile 和工具入口。官方 `/data/service/hnp/bin` 环境及其他设备的结果不在本次结论内。

**1. 触发与失败签名**

| 条件 | 本次实际值 | 作用 |
|---|---|---|
| 运行域 | 用户授权的 arm64 HarmonyOS 真机，隔离 shadow CI | 原生执行配置、编译与归档，无交叉运行替身 |
| 编译器与 SDK | Clang 15.0.4，HarmonyBrew OHOS SDK 26.0.0.18_2，Conan 2.29.1，GNU make 4.4.1 | 编译器由 profile 中绝对路径找到，不依赖 `ar` 是否存在 |
| 仓库 profile 与目标环境 | 仓库标准 profile 引用 `/data/service/hnp/bin`；该设备以隔离 profile 覆盖为 HarmonyBrew/LLVM 路径 | 此设备运行不代表未修改的标准 profile 在本设备可用 |
| 上游输入 | ncurses 6.6 的 `make -j1 SHELL=/bin/sh`，第一份 `libncursesw.a` 静态归档 | 将 C 编译器和静态归档器分别用到 |

失败记录：`$HOME/ohpc-ci-shadow/runs/2b07bb5f6285-20260916T141029Z-51777/logs/build_and_test.log` 第 801-815 行：

```text
ar unknown ../lib/libncursesw.a ...
make[1]: ar: No such file or directory
make[1]: *** [Makefile:1010: ../lib/libncursesw.a] Error 127
make: *** [Makefile:131: all] Error 2
```

KV 签名 `(?m)^ar unknown \.\./lib/libncursesw\.a[^\n]*\nmake\[1\]: ar: No such file or directory` 命中此失败样本；成功日志中对应位置执行 SDK `llvm-ar -curvU ../lib/libncursesw.a`，不含该签名。`install` 缺失的 E174 错误没有前面的 ncurses 归档命令，也不应命中。日志前面多条绝对路径 `clang ... -c ... -o ...` 已成功，不应误报为 C 源码/Clang 失败。

**2. 根因与排除项**

`archives/l/libncursesw/6.6_p20260516/conanfile.py` 最初照搬 `ncurses/6.6` 的固定 PATH，只有 HNP、`usr/local` 和系统目录，不保留设备调用方注入的 HarmonyBrew 及任务专用工具目录。后续配方改为纳入 `os.environ.get("PATH", ...)`，合成 `AutotoolsToolchain`、`VirtualBuildEnv`，并从 `CONFIG_SHELL`、HNP Bash、可发现的 Bash 中选择可执行 configure shell；最终提交还禁止用 `/bin/sh` 冒充 GNU Bash，检查 `gawk` 而不是任意 `awk`。

上述配方变化解决的是**路径保留与所选构建工具的语义**，不能直接证明其修复了日志中的缺失 `ar`。失败 run 的设备隔离 profile 虽有绝对路径 Clang，但未让有效构建环境找到归档器；其工具预检只列 `sed/rm/expr/make/awk/clang/clang++` 和 shell，不包含 `ar`，因而 `OHOS_BUILD_TOOLS=8/8` 并非归档工具已经就绪。相同提交的成功 run 额外在设备隔离 profile 指定 SDK `llvm-ar` 为 `AR`、设置 `RANLIB/NM/STRIP`，并提供工具入口；最终日志中的归档命令已解析为绝对路径 `llvm-ar`。同时变化的 profile 与工具入口必须和配方变更分开表述。

| 竞争解释 | 实际检查 | 结论 |
|---|---|---|
| 编译器不存在或对象编译失败 | 失败日志第 786-800 行成功调用 SDK Clang 编译对象 | 已排除，失败发生在下一步归档 |
| GNU make 不存在 | 两次运行均进入 `make[1]` 的同一归档目标 | 已排除 |
| 缺少 ncurses 上游源文件 | 成功 run 的相同提交完成 86/86 上游程序构建与完整 `make check` | 对所验证源码已排除 |
| 仅修配方 PATH 即能恢复 `ar` | 未做独立单因素对照；成功 run 同时切换设备 profile/工具入口 | 未证实，不能如此宣称 |

**3. 最小修复及验证契约**

1. 配方中在显式前置已知工具目录时保留进入配方的 PATH，再叠加 `AutotoolsToolchain` 和 `VirtualBuildEnv`，不要把 profile/runner 提供的目录直接覆盖掉。选择可执行的 GNU Bash 运行 configure，保持构建步骤明确用 `/bin/sh`。
2. 对当前 HarmonyBrew 真机的隔离 profile，显式设置 `AR=<SDK>/native/llvm/bin/llvm-ar`、相配套的 `RANLIB/NM/STRIP` 及 GNU 工具路径；对标准 HNP CI 维持仓库既有 profile，不在库中写入这台设备的私有路径。
3. 运行时确认有效环境下 `ar` 或显式 `AR` 确实可执行，并检查日志是否在 `libncursesw.a` 处调用 SDK `llvm-ar`；`OHOS_BUILD_TOOLS=8/8`、单独 `clang --version` 均不能替代此检查。归档工具缺失不能通过跳过 `make check` 或删掉静态库目标掩盖。

实现来源：`ecce6bcdd8093895839faffe9a13051d8576d1e3` 的配方，仓库外隔离 profile/工具入口仅在该真机的任务工作区，不把它写为已提交实现。未验证可独立替换此方案的回退。目标机的复验入口是：

```sh
sh "$HOME/bin/run-ohos-shadow-ci.sh" archives/l/libncursesw/6.6_p20260516 --repo "$HOME/ohos-users/device-b/libncursesw-f531e409" --try-lock
```

runner 将固定提交归档进新工作目录，覆盖工作副本中的 Conan profile 为目标机任务专用 profile，再运行仓库检查及 `conan create`；复验前须核对 checkout HEAD、profile 的 `AR` 及结果中的 `commit`，不可直接把普通仓库 profile 用于这台没有 HNP 工具目录的设备。

**4. 验证矩阵与证据范围**

| ID | 类型 | 提交与输入 | 实际结果 | 日志和 SHA-256 |
|---|---|---|---|---|
| EVID-01 | target-executed | `2b07bb5f62850b7f72d49daffc2f0202761f9b55`，隔离 profile 尚未显式供应归档器；`run-ohos-shadow-ci.sh archives/l/libncursesw/6.6_p20260516 --try-lock` | Clang 编译通过，`ar: No such file or directory`，L1 fail，后续层未执行 | 真机 `$HOME/ohpc-ci-shadow/runs/2b07bb5f6285-20260916T141029Z-51777/logs/build_and_test.log`，`9dadb113b4415b5eb29a70dc4d38f274c9915c5d6a479296b7d4bf6cc03bd27f` |
| EVID-02 | target-executed | **相同 HEAD**，调整设备隔离 profile 与工具入口后同一 runner | SDK `llvm-ar` 打包静态库；L0/L1/L2/L4/L5 pass，86/86 程序编译、完整 `make -j1 check`、8/8 消费者工作流 | 真机 `$HOME/ohpc-ci-shadow/runs/2b07bb5f6285-20260916T142420Z-64228/logs/build_and_test.log`，`d97a00395bd4b5ea4f9cf41a829d3c64870fdc36d61b014aec3f7efe419f6c66` |
| EVID-03 | target-executed | 最终 `ecce6bcdd8093895839faffe9a13051d8576d1e3`，保持同一设备隔离工具链；要求真实 GNU Bash/Gawk | L0/L1/L2/L4/L5 pass；`OHOS_BUILD_TOOLS=8/8`、86/86 上游程序、完整 `make check`、27/27 消费者断言、2899 条 terminfo 安装记录 | 真机 `$HOME/ohpc-ci-shadow/runs/ecce6bcdd809-20260916T144447Z-21138/logs/build_and_test.log`，`ea97a57105d6a4ed11658bc3fe56d2b8373ee141ff82d6cd1b96505bcc48edc9`；`gate-results.txt`，`85c402454bff4b4b9407873cc93c53675978a8cf6df358d597f4ad77bb19d2bf` |
| EVID-04 | target-executed，会话记录未独立归档 | 最终 `ecce6bcdd` 真机上额外触发 `shared=True` 与隔离副本缺 terminfo 两项负测 | `shared=True` 返回码 6，提示 `Invalid configuration: libncursesw is packaged statically to avoid shadowing system libncursesw.so.6`；缺 terminfo 返回码 1，提示 `FAIL: newterm with packaged terminfo` | 本次 SSH 会话原始 stdout 摘录；尚无独立留存的负测日志文件与 SHA-256；不能说它们包含在 EVID-03 的构建日志中 |

精确 runner 位于目标机 `$HOME/bin/run-ohos-shadow-ci.sh`，目标 checkout 为 `$HOME/ohos-users/device-b/libncursesw-f531e409`。EVID-01/02/03 日志只在授权设备上通过 SSH 访问，不是仓库内附件；EVID-04 目前只有会话摘录。若审查者无法访问该设备，须先按项目允许方式附上脱敏日志或由维护者重跑，不能仅凭 run ID 声称公开可审计。`2b07bb5f6285` 到 `ecce6bcdd` 除知识文件外还改了配方的 Bash/Gawk 校验，因此不能把 EVID-02 说成最终 HEAD 的 run。

**测试统计**

| 层和单位 | 库存 | 通过 | 失败 | 跳过 | 未执行 | 注意 |
|---|---:|---:|---:|---:|---:|---|
| 上游 `test/programs` 编译目标 | 86 | 86 | 0 | 0 | 0 | 是程序目标数，不是上游运行测试用例数；完整 `make -j1 check` 已执行，但其独立用例库存未由该入口提供 |
| 已安装包消费者工作流 | 8 | 8 | 0 | 0 | 0 | 2 个直接消费者、1 个 config 脚本、5 个 `.pc` 模块；内部断言 27/27，与此行有重叠，不能相加 |
| 边界负测 | 2 | 2 | 0 | 0 | 0 | `shared=True` 返回码 6，缺 terminfo 返回码 1，均为预期拒绝；见 EVID-04 的会话摘录，原始负测日志仍待归档，不把预期非零返回码记为失败 |

现有源包相同版本下的 `ncurses/6.6` 已有同等 86 程序、六路元数据链接跟踪、消费者测试和随包 terminfo；本草稿**不把这些复用内容算作新知识**，只用最终运行证明其未因新包名而退化。未验证其他设备 GNU 工具版本、官方 HNP worker 的最终构建或复杂交互终端行为。

**5. 已有知识与后续自检**

| 已有材料 | 已覆盖 | 此次增量与建议 |
|---|---|---|
| `knowledge/graph/E540.kv` | runner PATH 缺 `/data/service/hnp/bin` 会让 `make` 不可见，HNP profile 的绝对 CC/CXX 仍可能让早期步骤通过 | 同一根因族的**补充**：配方局部覆盖 PATH 与缺失 `ar` 是独立于编译器、`make` 的后续门槛；补录准确 Error 127、同 HEAD 对照和 profile 边界 |
| `knowledge/graph/E012.kv` | 缺 GNU `ar` 的 OHOS SDK 应设置 `AR/RANLIB/NM/STRIP` 为 LLVM 版本 | `AR=llvm-ar` 是已知修复，直接复用、不计新知识；本次补充的是配方 PATH 作用域、前置检查漏检 `ar` 及与设备隔离 profile 联动的真实运行证据 |
| `knowledge/drafts/opencsg-1.8.2-shadow-ci-isolated-job-hnp-toolchain-path.kv` | 隔离 job 缺 HNP `cmake` 导致 Error 127 | 同为工具路径，仍以 E540 为正式关联，不重复创建隔离 runner 模式 |
| `knowledge/drafts/DRAFT-autotools-toolchain-vars-empty-vs-unset.kv` | 已导出空串 `AS/AR` 让 configure 默认值不生效 | 本次 `ar` 根本不可执行，不是已导出空串导致的汇编探针假失败 |
| `knowledge/drafts/DRAFT-libcaca-0.99.beta20-autotools-ohos-shell-and-deps-env.kv` | configure Bash 语义与 Conan 依赖 env 的传递 | 本草稿不重复发明 Bash/Conan env 模式；只强调归档器的后期能力门槛 |
| `archives/n/ncurses/6.6/`、terminfo 草稿与 E028 | 静态库/metadata/terminfo 既有实现及系统 so 冲突 | 没有新的可独立知识机制，保留在本包的适配结果中 |

检索了 `knowledge/graph/`、`knowledge/drafts/` 与 `archives/n/ncurses/6.6/` 中的 `ar`、`PATH`、`VirtualBuildEnv`、`ncursesw6-config`、`terminfo`、`E540`、`E012`。建议草稿合入 E540 的增量边界，E012 的 LLVM ar 方案只交叉引用；若维护者判断仍重复，则只保留为适配案例。预审启发式对本草稿给出的 `create` 只说明正则字面词相似度低，不能凌驾于 E012/E540 的人工去重。KV 与本文同名、字段均独占一行；来源 PR !10433 已核对，最终 PR HEAD 必须另记，草稿提交不能自引用。当前状态：可作为待审补充候选，仍需核对本次回填提交到达远端及官方 CI 与 AI review 结果。
