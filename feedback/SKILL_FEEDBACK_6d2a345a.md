# SKILL 执行流程反馈报告

## 背景
- 软件：swuniq 0.5；2026-09-25；上游 https://github.com/mterron/swuniq.git，官方 tag v0.5。
- 构建：Makefile/C、OHOS aarch64 静态 CLI；路径 B（基础适配加知识草稿）；补丁 0；Conan 依赖 0（仅系统 libc）。
- 当前：本地 Conan 验证通过，W3 / W4 与远程 CI 分阶段执行，结果以本报告后续记录为准。

## 情况
- init-build：先误传仓库 `.git` URL，init-build 当 tar.gz 下载，手动终止；再从官方 v0.5 codeload tarball 初始化成功。该 tag 头文件已 vendored，无 gitlink。
- conan-init：将 Makefile 错判为 autotools，产物为 library 骨架、空壳消费者和未填的 manifest；人工替换为静态 application 配方及实际 C 消费者用例。
- conan-verify：首次 G1 提示缺少 export_sources 与补丁钩子，补齐后 G2 报 `BadZipFile: File is not a zip file`；依据 `E483` 在 `conandata.yml` 显式设置 tarball 文件名后 G1/G2/G3 通过。引擎当时误命中 E540（工具 PATH，与本错误无关）。
- 实测：上游 make check 1/1；Conan 消费者 1/1，含 OHOS aarch64 ELF 和管道两项窗口行为断言（2/2），x86 主机经 qemu/binfmt 实际运行。新草稿 `knowledge/drafts/E545-draft-0086.kv` 与配套 md；draft-review 与 E483 相似度仅 0.09、建议 create；graph validate 通过（已有存量警告）。
- W3 首跑失败：`[fail] L1e: test passed WITHOUT package artifacts`。正向 create 已 `PASS (2/2)`，根因是 L1e 用单 profile `conan test`，`can_run(self)` 变假导致 `test()` 静默跳过。改为按物理架构原生执行或显式 `qemu-aarch64`，缺执行条件即报错；沉淀草稿 `E550-draft-1C7E`（引擎最近命中 E428，根因不同）。另 finish Step 3 的 G0 clean-verify 对 Makefile-only 包跑 configure 报 exit 127（非阻塞）。
- W4、PR、CI：此报告写入时尚未产生；以工具报告与 PR 状态为准，不预称成功。
- 效率：`.git` URL 类型误用、Makefile 被当 autotools、L1e 与正向 profile 不一致是三处返工；G1/G2/W3 各一次失败与修复，无同类调参死循环。

## 建议
### SKILL 设计改进
`scripts/ohc/init_build.py:410-425` 收到 `--url` 时先拒绝 `.git` 后缀，并提示“此入口只接受压缩包归档、如需子模块先核对 tag gitlink”；避免在 `:89-117` 以 300 秒等待无效仓库下载。

### 模板改进
`scripts/ohc/conan_recipe.py:216` 默认 autotools 模板回退遇 Makefile-only CLI 会产生 configure()/library 类型空壳；为 Makefile CLI 选择真实 application 骨架，`test_package` 应默认执行被测命令而非打印 OK；`:299-302` 的 `sources` 应生成版本键而非无版本字典。

### 自动化补全
`scripts/ohc/conan_recipe.py:145-165` 应检查实际工作源码是否存在 `configure`，仅有 Makefile 时优先 makefile 而非 init-build 的 URL 猜测；`:299-302` 对 codeload `/tar.gz/refs/tags/<tag>` 自动填 `filename`，并计算已经缓存 tarball 的 SHA256；`:380-424` 生成 MANIFEST 后提示并拒绝测试项占位标记进入验证；反馈生成器应把未渲染的构建系统模板变量、未知上游和 0 测试从事实数据中纠正，不要写为既成结果。

### 知识图谱覆盖
新增 E550-draft-1C7E：`ci/conan/build_and_test.sh:1646` 的 L1e 反向 `conan test` 只传 `-pr`，与正向 `-pr:h/-pr:b` 不一致，任何以 `can_run()` 作跳过条件的 test_package 都会被误判空壳；建议 L1e 同时传 `-pr:b`，或模板禁止无 else 的 `can_run()` 跳过。新增草稿 E545-draft-0086 仅针对 **init-build 的 `.git` 仓库 URL** 与按版本核对子模块；已入库 E483/E276 已涵盖 **Conan get() BadZipFile**，禁止重复创建。建议编辑审核后 promote，保持 index 与正式条目由主编维护。

## 作者
- 姓名：nyaco3
- 邮箱：aqjCItYW1QmEJQuF.gcw_XDpqZ8sO@noreply.gitcode.com
- Agent ID：B6A1
- 日期：2026-09-25
- PR：尚未创建，待审计后填写；CI：尚未触发。
