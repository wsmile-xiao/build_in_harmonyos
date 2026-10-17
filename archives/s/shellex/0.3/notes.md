# shellex 0.3 适配笔记

## 编译环境
- 构建系统: makefile（上游纯 Makefile + 子 mk 文件，无 configure）
- 编译日期: 2026-09-19
- 编译器: clang（OHOS aarch64 工具链，经 conan profile `tools.build:compiler_executables` 注入）
- 状态: built
- worktree: `~/qzy/GLM-57-shellex-0.3`，分支 `feat/shellex-0.3`
- CONAN_HOME: `~/tmp/ch/home-glm57-shellex`（复制自 home-zchunk 的 global.conf + remotes.json）

## W0/W0b 与语言预检
- W0 依赖检查：preflight_check.sh shellex/0.3 → 无依赖声明（唯一 C 源文件 preload/main.c 仅依赖 libc/dl），通过。
- W0b 历史经验：归档树无 shellex 历史归档/notes（首适配）。
- 语言预检 lang-preflight：task=cpp，detected=c（主体 preload/main.c，sh 脚本按辅助脚本不计主体），通过。

## 编译步骤
1. `python3 scripts/ohc-run.py init-build shellex 0.3 --url=<官方 tag tarball>`（源码落 `~/tmp/builds/shellex-0.3.work`）
2. 手动编译探针：`make CC=clang SED=sed` → 产物：`preload/shellex_preload.so`（-shared -fPIC）、
   `shellex`（sed 由 shellex.in 生成）、`conf/shellexrc`、`urxvt/shellex`
3. `conan-init shellex 0.3` 生成骨架 → 按纯 Makefile 应用型包改写 conanfile.py：
   package_type=application，build() 显式 `make CC=<conf clang> SED=sed`；
   package() 按上游 install 布局平铺拷贝（bin/shellex、lib/shellex/shellex_preload.so、
   lib/shellex/shellexrc、lib/shellex/conf/、lib/shellex/urxvt/shellex）；
   软件级 commands.json（R38，type=tool）
4. `conan-verify shellex 0.3`（G0-G4/L2/L4/L5 + 消费者测试）

## 上游测试账本（五维，rule4 口径）
| 维度 | 数量 | 说明 |
|---|---|---|
| N_static（上游静态声明） | 0 | Makefile 无 check 目标、无 tests/ 目录（见 test_package/MANIFEST.yml 证据） |
| N_registered | 0 | 同上 |
| N_executed | 0 | 上游无测试可执行 |
| 未执行分类数 | 0 | — |
| N_consumer（新增消费者测试） | 1 | test_package/test.c：①LD_PRELOAD 将真实 shellex_preload.so 注入运行中的 /bin/sh，断言 shell 退出码 0、命令输出正确、loader 无 "Error loading shared library"；②对生成的 shellex 启动脚本 `sh -n` 语法校验（共 4 断言） |

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | OHOS 工具链无 `cc`，上游依赖 make 内建默认编译器 | 上游假设 GNU make 默认环境 | 配方 build() 显式传 `CC=<conan compiler_executables c>` |
| 2 | 上游 install 目标以绝对 PREFIX 在 SYSCONFDIR 建 `ln -s` 符号链接 | 上游面向系统目录布局 | package() 改为按上游布局平铺拷贝文件，跳过系统目录符号链接（conan 包内无意义且 HMDFS 符号链接脆弱） |

## 源码修改

无补丁（patches: {}）。未修改任何上游源文件。

## 依赖版本

无外部依赖（唯一 C 源文件仅用 libc + dlsym RTLD_NEXT）。

## 验证结果

```bash
# conan-verify：G0-G4/L2/L4/L5 全绿（配方验证通过，可标记 built）
python3 scripts/ohc-run.py conan-verify shellex 0.3   # ✅ 配方验证通过
# W3 本地 CI 模拟（finish step 5，与 CI 同源）
python3 scripts/ohc-run.py finish shellex 0.3 built   # ✅ FINISH_EXIT=0
# 消费者测试（conan create 真实执行，reports/conan-create.log）
shellex consumer test: preload library loaded and shell behaved, launcher script syntax OK   # 新增 1/1 通过
# 上游测试：N_static=0（无测试套件），无执行项，未伪报通过率
```

## 路径 A/B 判断

**结论：纯路径 A。** 依据：本次适配未产生可跨仓库复用的新知识——"make 内建 CC=cc 需显式覆盖" 与
"install 的 SYSCONFDIR 符号链接在 conan 包内跳过" 均为本仓库既有惯用法/常识性处理，无新错误模式
（无知识图谱草稿生成需求）；shellex 本体无平台特有适配点（TIOCGWINSZ=0x5413 与 musl 一致，
dlsym(RTLD_NEXT) musl 原生支持）。不满足路径 B 证据门槛，不建知识库扩展 Issue。

## 注意事项

- shellex 包装脚本运行时依赖 urxvt/zsh，非 OHOS 平台组件，包内**不声明也不提供**；核心产物是
  shellex_preload.so（消费者测试覆盖其真实加载路径），启动脚本交付但仅做语法级验证。
- 产物包含 `.so`（非系统同名库，preload 注入用），cpp_info.libdirs 置空，避免被下游误链接。
---

**编译结束**: 2026-09-19 02:33
**最终状态**: built
