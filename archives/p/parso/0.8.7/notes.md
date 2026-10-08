# parso 0.8.7 适配记录（候选）

## 固定输入与范围

- 使用 PyPI sdist `parso-0.8.7.tar.gz`，401824 字节，SHA-256
  `eaaac4c9fdd5e9e8852dc778d2d7405897ec510f2a298071453e5e3a07914bb1`。
- PyPI 元数据声明 `Requires-Python: >=3.6`，无运行时依赖；pytest 和
  fixtures 随 sdist 提供，仅用于上游测试。
- 竞赛任务 #9319 的平台语言标签为 `cpp`，固定源码主体为 Python。本适配按
  人工竞赛入口继续并披露语言差异；不修改标签，不声称存在通用豁免或保证积分。

## 包装方案

配方只安装上游 `parso` Python 模块、Python 版本 grammar 文本、类型标记和
原许可证，通过 Conan run environment 暴露 `PYTHONPATH`。保留完整上游
`LICENSE.txt`，其中也记录 `pgen2` 与 tokenizer 文件的 PSF 来源说明。不把
测试、文档或构建工具作为运行时依赖。消费者检查包来源、语法解析/代码往返、
grammar 数据和错误恢复。

主机 smoke 已从固定 sdist 验证 0.8.7 可加载 Python 3.8 grammar、保留简单
函数源码并对无效语法报告错误。将模块、grammar 资源和类型标记按候选配方目录
复制到临时包布局后，消费者检查为 4/4；这不是 Conan 生成的包。固定 sdist
(SHA-256 `eaaac4c9fdd5e9e8852dc778d2d7405897ec510f2a298071453e5e3a07914bb1`)
的完整上游 pytest 使用主机 Python 3.11.0rc2 执行；第二次全量运行捕获到
`1989 passed in 9.73s`。这是对上游 sdist 的主机测试，不是 OpenHarmony 目标机
测试，也不是对 Conan 包运行的上游 suite。该测试与原始候选补丁
`6986452ed5c1854a194ab4039d0d6af096ded5f552aa873ac321e3b38490a6ea` 使用同一
固定源归档；目标 Conan 包由 H1 W3 consumer 4/4 独立验证。

## H1-001 OpenHarmony 验证（历史候选）

- 固定原始 sdist 和补丁分别为 401824 字节 / SHA-256
  `eaaac4c9fdd5e9e8852dc778d2d7405897ec510f2a298071453e5e3a07914bb1`，以及
  SHA-256 `6986452ed5c1854a194ab4039d0d6af096ded5f552aa873ac321e3b38490a6ea`；
  H1 回读摘要一致，受测树 SHA-256 `45f650ef25bcf83de6f1d9655f8892b542b064ed`。
- H1 aarch64 / Python 3.12.9：官方 `setup.sh` 和定向
  `build_and_test.sh archives/p/parso/0.8.7` 均 rc 0；其中真实 Conan create
  构建了 `parso/0.8.7` 包，消费者 4/4 场景通过，L1e 负向依赖检查通过。
- 门禁结果：L0、L1、L4、L5 pass；L2 因纯 Python 包没有 `bin/` 跳过。
- 目标机上游 pytest 未运行：目标 Python 3.12.9 缺少 pytest
  (`No module named pytest`)。主机的 1989/1989 只代表主机测试结果。
- 对 H1-001 这份历史候选，当时没有运行官方 `finish` 或远端 CI。此记录不表示 H1-003 状态。

## H1-002 历史 finish 结果

H1-002 固定补丁 SHA-256 为 `1f5fac5984cb941949f4bec00eff65512f0daa9a1e2c6456d3298ed11aac93eb`，固定 sdist SHA-256 为 `eaaac4c9fdd5e9e8852dc778d2d7405897ec510f2a298071453e5e3a07914bb1`。finish RC 1；当轮 G0 未找到构建上下文原包、G1 缺 Conan patch hooks，但 W3 RC 0、真实 Conan consumer 4/4。H1-002 的原始结果保持历史，不由后续结果覆盖。

## H1-003 当前候选验证

- H1-003 固定十文件候选补丁 SHA-256 为 `4f0c72395913379c44970651142ad98f07c85842d8791ec0f64594632423cb5a`，树 `ae42d0f66b91463a1acf9fc2c3637a5d4d679faf`，提交 `b1e6ec9efd5426e8a413657df02d1d02abf1de5a`；固定 sdist 的 401,824 字节 / SHA-256 `eaaac4c9fdd5e9e8852dc778d2d7405897ec510f2a298071453e5e3a07914bb1` 与前两轮相同。
- OpenHarmony aarch64 / Python 3.12.9 上 G0、G1、真实 Conan create/package/test_package、W3 均通过；四个唯一消费者场景 4/4，L1e 负向依赖检查通过。G0 用固定 sdist，执行注册补丁、configure、make 和 make install，安装树包含一个 `lib` 项。
- 官方 finish 仍返回 RC 1，报告失败步骤为 `step5b, step8`。`step5b` 的全局知识完整性检查指出与 parso 无关的 E219/E253 缺 `root_cause`、E305 缺 `root_cause` 和 `rec_approach`；parso 条目检查通过，本任务没有新增知识条目。
- `step8` 的旧提交预检要求 `packaging/` 和 `.staging-verified`；固定框架 R19/R20 将此旧 package-builder、tar 和 staging 路径列为废弃。finish 的 `finalize-archive` 另报 RC 2 警告，涉及 legacy packaging/release/debug tar。实际 RC 与失败项如实保留；不运行旧 builder，不造 tar 或 marker，也不宣称官方豁免。
- finish 在私有 clone 自动重写全局 `SUMMARY.md`，造成目录统计及无关条目大范围变化，并生成额外反馈文件；这些文件不属于本任务十文件候选，不纳入贡献差异。
- 目标机上游 pytest 未运行：设备 Python 3.12.9 没有 pytest。主机固定 sdist 的 1989/1989（Python 3.11.0rc2）不代表目标机上游测试。
- 任务 #9319 的平台语言标签为 `cpp`，固定上游源码为 Python。候选披露该差异，不修改平台标签，不主张普遍豁免或保证积分；资格仍待官方入口核实。

### 对话 #9319

状态：H1-003 真机验证已完成，H1 输入补丁绑定 G0/G1/Conan/W3 结果；finish RC 1 的全局/旧门禁结果另行披露。最终候选已通过独立 W4，准确候选摘要和审阅范围见 `reports/audit-result.json`。未运行远端 CI，未推送/创建 PR；Python 源码与 `cpp` 标签的资格仍待正式核验。
