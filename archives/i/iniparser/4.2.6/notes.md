# iniparser 4.2.6 适配笔记

## 基本信息

- **软件**: iniparser 4.2.6（INI 文件解析库，纯 C，零外部依赖）
- **上游**: https://github.com/ndevilla/iniparser（tag v4.2.6）
- **目标平台**: HarmonyOS PC (aarch64, musl libc, clang 15.0.4)
- **构建系统**: CMake (>= 3.18)
- **适配人**: 2404_87638649
- **日期**: 2026-09-05
- **分支**: feat/iniparser-4.2.6

## 历史归档核验（W0b）

main 仓库已有 2026-05-25 的旧格式归档（仅 manifest.yaml + notes.md，无 conanfile.py，
非 Conan 体系产物，制品仓 conan list iniparser/* 确认为空——首次 Conan 化适配）。
历史 notes 的关键结论逐项核验：

| 历史结论 | 本次核验结果 |
|---|---|
| cmake 构建，"System is unknown" 警告不阻塞 | ✅ 复现一致，忽略即可 |
| BUILD_TESTING=ON 需 git clone Unity | ✅ 复现一致，CI 环境无 ruby/网络不可控，配方中关闭 |
| dictionary_dump 测试失败（"返回 NULL"） | ⚠️ **根因修正**：实为 OHOS libc tmpfile() 对 /data/local/tmp 返回 EACCES（知识条目 E272 同源），注入 tmpfile-shim 后 7/7 全过，非库缺陷 |
| SSL 证书问题需手动下载 | ✅ 复现一致（本次用 ghfast.top/gh-proxy 双镜像下载并校验 sha256 一致） |

## 环境语义可迁移性核验

- 历史命令在 CI 环境可执行性：cmake/clang/make 均 CI 能力矩阵 ✅ 项
- 上游测试的 ruby 依赖是 CI ❌ 项 → 测试不在 conan build() 中集成（见 test_package/MANIFEST.yml 说明），由 test_package 补全

## 适配过程

### Step 1: 源码获取

- GitHub 直连超时，ghfast.top / gh-proxy.com 双镜像下载，sha256 双源一致：
  `a0bd370713a744b1fa8ec27bba889ebf9dbd43060ec92e07fbe91fb43e3cb3ac`
- ⚠️ 源码包内含悬空符号链接 `compile_commands.json -> build/compile_commands.json`，
  OHOS 上 tar 解压报 Permission denied、HMDFS 硬链接/copytree 跟随链接失败，
  解压后需先 `rm -f compile_commands.json`（或忽略 tar 的 settime 错误）

### Step 2: 语言预检（R47）

`lang-preflight --lang c`：detected=c（源文件 8 个：c:7 python:1，主体 88%）✅ 通过

### Step 3: 编译验证（本机探索）

```
cmake -DCMAKE_BUILD_TYPE=Release -DCMAKE_C_COMPILER=clang \
      -DBUILD_TESTING=OFF -DBUILD_EXAMPLES=OFF -DBUILD_DOCS=OFF
make -j4           # libiniparser.so + libiniparser.a 均成功
make install DESTDIR=...  # staging 安装布局正确（lib/include/lib/cmake/lib/pkgconfig）
```

产物：`libiniparser.a`（默认配方产物）、`libiniparser.so`（shared 选项）

### Step 4: 上游测试执行（W0b 历史踩坑比对 + 补充）

上游 test/ 需要 `BUILD_TESTING=ON`：FetchContent 克隆 throwtheswitch/unity +
ruby 生成 test runner。本机具备 ruby，已完整执行：

```
ctest: 100% tests passed, 0 tests failed (2/2)
  test_iniparser:  23 Tests  0 Failures 0 Ignored  PASS（316 断言）
  test_dictionary:  7 Tests  0 Failures 0 Ignored  PASS（34 断言）
```

**关键发现——test_dictionary 失败根因**：直接运行时 `test_dictionary_dump` 失败
（"Expected 'empty dictionary\n' Was NULL"）。根因是 OHOS libc `tmpfile()` 硬编码
尝试系统临时目录（/data/local/tmp）返回 EACCES（无 shell 权限），get_dump 辅助函数
拿到 NULL。这与知识条目 E272（arm-none-eabi-binutils ctf-compressed 同源问题）一致。
按 E272 方案构建 tmpfile-shim.so（mkstemp 到 TMPDIR + unlink + fdopen + FD_CLOEXEC）
LD_PRELOAD 注入后 **30/30 全过**。

历史归档（2026-05-25）将此记录为"dictionary_dump 返回 NULL，已知问题"——本次修正：
非库缺陷，是平台 tmpfile() 权限问题，测试注入 shim 后全绿。

### Step 5: Conan 配方

- `conanfile.py`：CMake recipe，零依赖，`shared` 选项（默认 False 静态），
  BUILD_TESTING/EXAMPLES/DOCS 全关（ruby/doxygen CI 不可得）
- `package_info`：`libs=["iniparser"]`，cmake_file_name/target_name/pkg_config_name 齐全
- `test_package/`：R34 消费者 API 往返测试（18 断言，真实调用
  iniparser_load/getstring/getint/getboolean/set/getnsec/getsecname/getsecnkeys/freedict）

### Step 6: conan create / verify

见 `.ci-result.json` 与 reports/（W3/W4 产物）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | GitHub 直连下载超时 | 网络环境 | ghfast.top + gh-proxy 双镜像下载，sha256 双源比对一致 |
| 2 | tar 解压 compile_commands.json 报 Permission denied | 源码包内悬空符号链接 + OHOS 文件系统 | 解压后 `rm -f compile_commands.json`；探索构建不受影响 |
| 3 | init-build .work 目录创建失败 | HMDFS 硬链接跟随悬空符号链接 EPERM | 手动准备 .orig（清理悬空链接）后重跑 |
| 4 | test_dictionary_dump 失败 | OHOS libc tmpfile() → /data/local/tmp EACCES（E272） | tmpfile-shim.so LD_PRELOAD（mkstemp 到 TMPDIR），30/30 全过 |
| 5 | 上游测试无法进 conan build() | 依赖 ruby + FetchContent git clone（CI 无 ruby） | 本机全量执行记录于本笔记 + test_package 等价断言补全 |

## 源码修改

**无补丁**。上游源码零修改完成适配（悬空符号链接清理属于解压操作，不修改源码内容）。

## 验证结果汇总

```
上游测试（本机，tmpfile-shim 注入）: 30/30 用例通过（350 断言）
  - test_iniparser:  23/23（316 断言）
  - test_dictionary:  7/7（34 断言）
test_package（CI，OHOS conan create）: 18 断言全过
conan create (aarch64-linux-ohos): PASS
```

## 依赖版本

无外部依赖（纯 C 标准库）
---

**编译结束**: 2026-09-05 01:31
**最终状态**: built
