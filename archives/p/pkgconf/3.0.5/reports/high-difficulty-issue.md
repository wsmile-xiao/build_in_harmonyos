【依赖关系】本任务是 GraalVM Issue #1085 的真实前置依赖。GraalVM 源码构建图中的 gcompat 构建需要 pkg-config 兼容工具；本任务交付 `pkgconf/3.0.5`，解除该依赖链的构建前置阻塞。活动固定为“依赖”，高难度挑战只是本任务的唯一最高标题前缀，不改变依赖活动。

【申请人账号】2301_80739235
【队伍名称】天天开心
【申请日期】2026/08/17
【库名称】pkgconf
【版本】3.0.5
【任务分支】feat/pkgconf-3.0.5
【活动】依赖

## 申请原因

本任务同时申请路径 A、路径 B 和路径 C，并按优先级只使用“高难度挑战”一个标题前缀。

路径 C 的难点不是让一个静态库完成编译，而是保持交付边界、上游测试语义和目标端事务安全同时成立：

1. OHOS/arm64 交付必须安装静态 `libpkgconf.a`，但官方 OOM 测试只有在 shared 被测库边界下才保持上游故障注入语义。因此配方构建隔离的静态交付树和 shared 验证树，后者绝不进入制品。
2. 目标 libc 缺少 `reallocarray` 会让 OOM 与 corpus 测试从清单中静默消失。适配使用默认关闭、只链接测试可执行文件的溢出安全 shim，并从 Meson introspection 硬绑定 33 个顶层测试。
3. 14 个 fixture 套件内部共有 425 个独立用例；上游 runner 可以在顶层返回成功的同时产生嵌套 SKIP。验证器按唯一 `(suite, fixture)` 键重建真实 PASS 映射，禁止把 SKIP 或重复平台执行计为通过。
4. parser/solver corpus runner 对临时文件、短写、close、空 corpus、路径截断和 missing-path 全部失败闭合，并分别绑定 141、3 和 1 个官方输入终态。
5. 目标端需要对五个 ELF 副本进行签名、以对象身份闭合 acquire/publish/cleanup，并在 HUP/INT/TERM、路径替换和提交边界上保存外来对象。完整定向矩阵覆盖普通失败与竞争窗口。
6. 授权 endpoint-215 上，同一精确快照完成唯一一次 controller/runner 启动，runner RC0、26/26 断言通过；释放证明 root process 0、clean scans 2、lock/lease 0。后置 tar 校验器只误拒了合法根目录项，未重跑设备，而是用 48/48 成员与 13/13 哈希做不可变 reconciliation。

完整上游官方库存为 586/586：15 个 API 可执行测试、1 个 OOM 测试、425 个 fixture、141 个 parser corpus 输入、3 个 solver corpus 输入和 1 个 missing-path 负测。构建与测试均以单作业执行。

## 知识库查重情况

提交前在 `knowledge/graph`、`knowledge/drafts`、`knowledge/doc`、`knowledge/operations` 四个范围按精确错误、别名、根因和修复语义查重。未发现覆盖以下六项完整边界的等价条目，结论为 `NO_EQUIVALENT_REUSABLE_KNOWLEDGE`：

- Meson allocator fault injection 的能力探测、符号包装和 shared/static 被测边界；
- 目标 ELF 签名树的 FD/对象身份 acquire、no-clobber publish、信号与 cleanup 原子性；
- 平台条件 fixture 的唯一键库存与真实 PASS 归并；
- 目录根 tar readback 的目录/普通文件分型、证据哈希和 postrelease reconciliation。
- CI Worker 同时缺少 curl 与 Python SSL 时，官方 HTTPS 首选、权威 HTTP 同哈希回退和真实 Conan source 验证。
- Conan profile 提供的 build-tool PATH 仅由 `self.run` 的 `conanbuild` build scope 消费，裸 Python subprocess 无法继承时的 JSON introspection 与失败闭合。

查重查询、四个范围和结论保存在 `reports/knowledge-dedup-result.json`，并在每次 push 前重新绑定 official main。现有 E2147 涉及 Meson 测试清单语义，但不覆盖 Conan build environment 与裸 subprocess 的进程环境边界；E299 只负责源码失败分层，也未覆盖 curl 与 Python SSL 同时缺失时的权威 HTTP 同哈希回退合同。因此本候选使用当前未占用的 E2145-E2150；旧基线查重仅保留为诊断，提交前必须重新校验，本任务不修改任何无关正式条目。

## 可复用说明

本 PR 随软件提交 E2145、E2146、E2147、E2148、E2149、E2150 六组同 stem KV/Markdown 草稿，KV 均含 `draft: true`：

- E2145 可复用于 Meson + GNU ld `--wrap` 的 OOM、capability 与链接边界验证；
- E2146 可复用于需要签名后发布目录树的编译器、代码生成器和命令行工具，覆盖 FD 身份、无覆盖提交、信号和回滚；
- E2147 可复用于顶层成功但内部可能 SKIP 的 fixture runner，提供唯一键库存与多次完整执行去重方法；
- E2148 可复用于设备或远程任务的目录根 tar readback，区分合法目录记录和普通文件，并在已完成 release 后安全闭合主机校验器缺陷。
- E2149 可复用于最小化 CI Worker 同时缺少 curl 与 Python SSL 的 Conan 源码获取，要求官方 HTTPS 保持首选、权威 HTTP 镜像字节同一并由上游 SHA-256 约束。
- E2150 可复用于 profile 通过 `conanbuild` 提供 Meson 等构建工具、但配方用裸 subprocess 做 JSON introspection 的场景，要求统一 `self.run` 环境并保留返回码、JSON 与清单投影失败闭合。

每组草稿都包含触发条件、根因、推荐方案、禁止策略、定向验证和安全边界；不修改正式 graph/doc/index。软件配方、测试、知识草稿与验证报告保持同一 PR 原子范围。

## 当前证据

| 证据 | 结果 |
|------|------|
| 上游官方测试 | 586/586（100%），32 OK + 1 required EXPECTEDFAIL，零失败/跳过 |
| OHOS/arm64 Conan | RREV `8a74e2c45ec826b8181fbca738a4a146`；PID `21b17f8b2bc0e9511e276e3d57a23893067cefe5`；PREV `7dad25c18ecf6400f17f94e2df9542ce` |
| 真机消费者 | endpoint `10.62.215.229:2222`，26/26，controller/runner 1/1，runner RC0 |
| 真机释放 | root process 0，clean scans 2，lock 0，lease 0，postrelease PASS |
| readback | tar SHA-256 `83856bf764a71f75d59755b3c88047337a0b66b6c5fb27e829f33fcb64bbc7fb`，48/48 成员，13/13 证据哈希 |
| 当前输入重绑定 | 未重跑真机；源码、patch、test_package、包命令和消费者字节保持精确，`conandata.yml` 仅增加权威 HTTP 同哈希回退，`conanfile.py` 只修复主包构建后的 Meson introspection 环境；生产方法 13/13，successor 定向矩阵 9/9 |

## 分值说明

本任务满足路径 C 的源代码、工具链/架构、测试规模、执行成本和目标事务证据，也形成路径 B 的六组可复用知识。标题按用户给定优先级只使用 `【高难度挑战】`，不叠加 `【知识库扩展】`、`【积分赛】` 或 `【依赖项】`；最终评分以赛事评审结论为准。
