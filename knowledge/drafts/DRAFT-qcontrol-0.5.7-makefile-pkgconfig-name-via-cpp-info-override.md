# qcontrol 0.5.7：Makefile 里硬编码 pkg-config 模块名与 conan 生成的 .pc 名不一致——第二条修法是「用 cpp_info 覆写 make 变量 ＋ 短路探测」，不新增 .pc

> 同 stem 机器可读件：`DRAFT-qcontrol-0.5.7-makefile-pkgconfig-name-via-cpp-info-override.kv`

## 场景

qcontrol 0.5.7（QNAP/Synology 外设守护进程，裸 Makefile 型上游）适配 HarmonyOS PC。它链接 Lua，但**不走 `PKG_CHECK_MODULES`**，而是在 Makefile 里直接把模块名写进 shell 调用来问 pkg-config 要 flags（`Makefile:9-11`：`pkg-config --cflags lua5.1` / `--libs lua5.1`，另有 `-lpthread`；`Makefile:13` 还有一条 `libsystemd-daemon` 条件探测）。

## 现象（实测原文）

```text
No package 'lua5.1' found
```

```sh
conan install --requires=lua/5.1.5 -g PkgConfigDeps     # 生成的 .pc 名是 lua-5.1
PKG_CONFIG_PATH=<build folder> pkg-config --exists lua5.1 ; echo rc=$?
#   rc=1，stderr: No package 'lua5.1' found
PKG_CONFIG_PATH=<同上> pkg-config --cflags --libs lua-5.1
#   -DLUA_USE_POSIX -DLUA_USE_DLOPEN -I…  以及  -L… -llua -ldl -lm
```

⇒ 依赖本身完全可用，**卡点纯粹是"上游问的名字"与"发布件生成的 .pc 名字"不一致**。这类差异在 lua/tcl/tk/GLib 子模块系里很常见（横杠、前缀、`-2.0`/`-3.0` 后缀都可能中招）。

## 根因

conan 的 `PkgConfigDeps` 按被依赖包 `cpp_info` 的**别名/包名**生成 `.pc` 文件与文件名，不会去迎合某个下游上游 Makefile 里写死的历史名字。凡上游把 `pkg-config <name>` 写进**编译/链接规则的命令行**（而不是 configure 期的 `PKG_CHECK_MODULES`），就没有 `PKG_CONFIG_PATH` 之外的地方可以"预置答案"，于是构建期直接失败。

## 修复（本包采用：0 补丁、0 新增 .pc）

`build()` 里绕开 pkg-config，改为**直接用 `cpp_info` 的值覆写 Makefile 的那两个变量**，并把上游的条件探测短路掉：

```sh
make CFLAGS="<由 self.dependencies['lua/5.1.5'].cpp_info 拼出的 cflags>" \
     LIBS_DYNAMIC="<cpp_info.system_libs + shared_libs 拼出的链接串>" \
     PKG_CONFIG=false
```

三条硬性注意（都是实测换来的）：

1. **参数一律来自 `cpp_info`**（R33），不自己拼编译开关、不写死宿主路径。
2. **覆写前必须先看清该变量在规则里怎么用**。同族反例：skewer 0.2.2 的 `CXXFLAGS?=-c` 里 `-c` 是编译规则的命脉，覆写它会把每条编译变成链接，症状是 `ld.lld: error: undefined symbol: cFQ::readRecord(tag_REC*)`。只有"纯参数拼接型"的变量才可覆写。
3. **上游 `-g` 要一并去掉**：本包实测它会把构建机绝对路径（`/storage/…`）写进产物，与"产物内无宿主路径"的平台断言直接冲突。

## 备选（既有条目的路）与取舍

`DRAFT-ohos-pkgconfig-name-alias`（来源 zeitgeist/1.0.4）的处方是**在 `generate()` 里按上游期望的名字补一份 alias `.pc`**。两条路的分工：

| 情况 | 选哪条 |
|---|---|
| 上游还读 `--modversion`、或同一模块名在多处被查、或想保留上游自己的版本校验语义 | 补 alias `.pc`（保留探测路径不动） |
| 上游只取 `--cflags/--libs`，且希望零补丁、零新增文件 | 本条（`cpp_info` 覆写 ＋ 短路探测） |

选本条的**代价必须写明**：短路掉探测 = 删掉了上游的版本约束与"探到才启用"的特性判定。本包就是靠 `PKG_CONFIG=false` 关掉了 `libsystemd-daemon` 探测 ⇒ systemd 通知特性在 OHOS 上**未启用**，这一点在 `notes.md` 里如实申报，不能当成已通过。

## 验证

```sh
bash ci/scripts/preflight_check.sh qcontrol/0.5.7
python3 scripts/ohc-run.py conan-verify qcontrol 0.5.7      # 期望 G1/G2/G3 全 PASS（本包实测 Verdict PASS）
sh test_package/test_ohos.sh                                # 25 条平台断言含 NEEDED 集合 / .codesign / 无宿主绝对路径
```

消费者测试合计 **45/45 通过**（行为 20 ＋ 平台 25，跳过 0、失败 0；上游静态测试数 0，三条实测证据）；`conan create` 日志含 10 条真实 clang 编译行与 `Calling build()` → `Package built`（不是 `- Cache` 命中的绿）。**链接完整性由 NEEDED 断言兜底**，这是对"绕过 pkg-config"的代价补偿。

## 反例与未证事项

- ⚠ 本窗曾推断"`cpp_info` 的 libs 会漏 `-lm`、`-ldl`"，**实测证伪**：`lua-5.1` 的 `Libs` 本身就带 `-ldl -lm`。⇒ 既不要盲信"pkg-config 一定给全"，也不要盲信"cpp_info 一定漏"，一律以产物 `NEEDED` 断言为准。
- 本条不覆盖 configure/meson/cmake 型上游（它们有各自的 cache 变量 / `-Dxxx=...` 可预置，走 alias `.pc` 或直接传 flag 更稳）。
- qcontrol 的守护模式 socket 承载物问题属另一条目（**E461**，`AF_UNIX` 文件套接字被文件系统矩阵拒绝 → abstract namespace），⛔ 不要与本条混谈，也不得把 E461 的既有结论当新知识申报。
