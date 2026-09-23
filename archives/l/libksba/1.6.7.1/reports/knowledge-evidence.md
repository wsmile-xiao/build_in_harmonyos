# libksba 1.6.7.1 知识升级证据报告

## 候选结论

在 OHOS Conan Autotools 构建中，`configure` 的 conftest、编译、测试临时文件和 `DESTDIR` 安装必须落在同一设备本地可执行 staging。仅加 `--host` 或继续使用 Conan/HMDFS 缓存不能证明目标程序可执行；libksba PR #8621 的后续实现把这些生命周期统一到本地目录后，在 Buildbot 46796（任务 #41174）完成配置、构建、`make check`、安装和消费者测试。

## 事实与证据

| ID | 事实 | 证据 |
|---|---|---|
| EVID-01 | 早期构建出现 `configure: error: cannot run C compiled programs`；补加 `--host` 后仍失败 | PR #8621 的 #41169/#41171 评论与 config.log 摘录 |
| EVID-02 | 修复提交将源码、构建和 `TMPDIR` 迁移到 `/data/storage/el2/base/cache/libksba-*`，设置 OHOS musl build/host、依赖脚本路径并按 configure→make→make check→install 执行 | PR HEAD `4bbae1b2a8e6120b9992aab55f51c2ce67de87c9` 的 `conanfile.py` 及补丁 |
| EVID-03 | Buildbot 46796 的 7 个步骤全部 success，任务 #41174 success，耗时 411 秒 | https://ohpcd.atomgit.com/ci/build/46796 |
| EVID-04 | 上游测试 7/7，消费者 test_package 1/1 | PR #8621 当前正文及 #41174 成功摘要 |

## 版本与边界

- 来源 PR：[#8621](https://atomgit.com/OpenHarmonyPCDeveloper/build_in_harmonyos/merge_requests/8621)，原标题为 `【依赖项】fix(libksba): 1.6.7.1 补齐 OHOS Conan 配方`。
- 知识来源/被验证提交：`4bbae1b2a8e6120b9992aab55f51c2ce67de87c9`。
- 目标：HarmonyOS PC/aarch64 OHOS Worker，Conan 2，libgpg-error 配置脚本可用。
- 上游源码：`https://gnupg.org/ftp/gcrypt/libksba/libksba-1.6.7.tar.bz2`，SHA256 `cf72510b8ebb4eb6693eef765749d83677a03c79291a311040a5bfd79baab763`。
- 未覆盖：独立真机复验、其他架构、非 musl 组合，以及 `ksba-config` 在不同安装前缀下的重定位；补丁 `0004-src-ksba-config.patch` 含固定 `/storage/Users/currentUser/usr/local` 值。

## 去重与增量

E064 已描述通用 conftest 执行失败，E060 已描述 HMDFS/权限边界；本候选新增的是 Conan 配方中设备本地源码/build/TMPDIR/DESTDIR 的组合生命周期、依赖配置脚本传播和 `make check` 闭环。另有同包同版本普通 PR，但本次不新建重复 PR，直接原位升级 #8621。

## 交付检查

- 成对草稿：`knowledge/drafts/DRAFT-libksba-1-6-7-1-device-local-autotools-staging.kv`、`.md`。
- 报告、草稿和 PR 正文使用同一来源提交、CI 任务和测试分母。
- 历史失败与当前成功分开标记；未将旧日志冒充当前 HEAD 重跑。
- 文档提交后需回读远端文件与最终 HEAD，并再运行中央 `draft-review`。
