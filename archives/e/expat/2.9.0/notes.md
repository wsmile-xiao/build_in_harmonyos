# expat 2.9.0 HarmonyOS PC 适配笔记

## 源码与构建差异

本版使用上游 `R_2_9_0` 正式发行资产 `expat-2.9.0.tar.xz`，SHA-256 为
`1e6371862cc31999b368c3b89b49994f0677e1bab5f1b2b85ae3741f5d803051`。
归档解包后的 `CMakeLists.txt` 位于源码根目录；此前 2.8.5 配方使用 tag 自动归档，
构建入口位于 `self.source_folder/expat`，不能仅替换版本与哈希。

交叉构建沿用已验证的 OHOS SDK `ohos.toolchain.cmake` 与裸 CMake 构建方式；
原生 OHOS 目标如无 SDK toolchain 文件则使用目标 Clang/CMake。两种路径都保留
`CMAKE_SHARED_LIBRARY_SONAME_C_FLAG=-Wl,-soname,`，避免共享库缺少 SONAME 时把
Conan 包缓存绝对路径写进消费者 `DT_NEEDED`。shared/static 分别由
`EXPAT_SHARED_LIBS` 控制，显式启用 `EXPAT_WITH_GETRANDOM` 与上游测试构建。
目标机签名工具对 ELF 去除旧 `.codesign` 后重新签名；`llvm-objcopy` 失败会中断流程。

## 已有私有验证

- 2026-10-10，在 D 盘隔离 Conan home 中，Windows→OHOS 交叉 `conan create`
  对 shared 与 static 分别退出 0；对应原始日志为
  `cross-conan-a687.log` 和 `cross-conan-static-a689.log`。当前消费者源码对已安装的
  shared/static 包又分别完成 Conan 消费者编译与链接（a694/a695，退出 0）；
  交叉模式未运行目标 ELF，也未重新编译库。
- 授权目标 `10.62.201.39:2222` 上的独立私有运行显示 Expat 2.9.0 上游 runner
  `100%: Checks: 5196, Failed: 0`；shared 与 static 消费者各 2/2，退出 0。
  输入、签名、传输回读和运行原始证据记录在工作区
  `expat-2.9.0/target-a690/evidence.json`。这次运行使用交叉产物，不是原生
  Conan create。
- 2026-10-12，在目标两个全新私有根 `a705`（shared）与 `a706`（static），
  对本候选分别执行原生 `conan create`，两次均退出 0。每次上游 runner 均输出
  `100%: Checks: 5196, Failed: 0`；已安装包消费者在目标实际编译、链接和运行，
  shared 输出 `dlopen libexpat.so and parse ok`，static 输出
  `static link and parse ok`。官方源码、七份候选文件及私有 profile 均精确传输并由
  独立 SSH 会话逐字节回读。原始日志分别为
  `target-native-conan-a705/create.log`（31,403 字节，SHA-256
  `30422edd207d57cf50fba6520e17d365c481bc3c8eac94ce48e1e08a1ce46a5a`）与
  `target-native-conan-a706/create.log`（30,714 字节，SHA-256
  `52a8086f83c4047610cb41dacee095f2ea41181ccb4952f3aeac7c58ce349bd6`）；
  原始退出码文件均为 `0`。这是私有原生 Conan 验证，不是正式 W3 或平台 CI。

## 提交前待完成

- 按官方流程取得真实 W3 回执，再创建软件 PR 并等待平台 CI。
  当前无正式 W3、软件 PR、平台 CI 或积分。
- Conan 曾在候选 `test_package` 生成临时脚本与 ELF。提交只选
  `conanfile.py`、`conandata.yml`、本 `manifest.yaml`、本 `notes.md`，以及
  `test_package/conanfile.py`、`test_package/test.c`、`test_package/MANIFEST.yml`。

本笔记只引用上述私有原始记录；正式运行的测试数与结论应以其新日志为准。
