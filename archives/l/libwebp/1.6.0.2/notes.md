# libwebp 1.6.0.2 整改记录

上游源码仍为官方 1.6.0；`.2` 是递增的真实适配修复身份，不是虚构上游标签。原 1.6.0.1 已由其他 PR 合入，本候选不覆盖其已发布配方。

## 实际问题与修复

- 原配方未启用 `WEBP_BUILD_FUZZTEST`。本候选恢复官方固定 FuzzTest 提交及其四项原始源码依赖，启用全部十二个原 libwebp 程序；同时保留 ANTLR 默认上游测试。不把注册清单当作执行数。
- ANTLR 的编译器／操作系统白名单在 HarmonyOS 上误报 C++17 不支持。只在原白名单未识别的 Clang 分支执行真实 C++17 编译和链接能力探测；不伪装 Linux、不预置探测成功、不降低语言标准。正式补丁已由官方 `refresh-patch --auto` 生成，并在新原始源码副本精确重放到已验证字节。
- 原生 CMake 的未知系统规则没有 ELF SONAME／运行时链接参数，导致构建工具以相对路径 DT_NEEDED 加载 Abseil 失败。OHOS toolchain 显式设置真实 ELF SONAME、RPATH 和 RPATH_LINK 参数；保留原依赖闭包及工具执行。
- 编译器链接包装器对即将被原 CMake post-build 发现逻辑执行的 ELF 完成实际代码签名；签名不等于测试通过。
- 独立消费者覆盖无损精确往返、XMP mux/demux、有损 RGBA 和坏输入四项语义；鸿蒙专项单独验证 AArch64、真实 `.codesign`、basename SONAME／NEEDED 以及实际映射命名空间。正式 verifier r005 同 run 消费者4/4、鸿蒙1/1通过；现行官方本地 CI r001 也独立执行这五项且通过，不拼跨 run 的分母。
- 原 Python 裸名称 `ctest` 在目标 `posix_spawn` 路径不被解析，r004 正式 create 在原十二项通过后真实失败；仅从原 CMakeCache 的 `CMAKE_CTEST_COMMAND` 绑定唯一绝对可执行文件，原参数、时限和六十四项 ANTLR 用例保持不变。

## 已保留的失败

r001：C++17 白名单 configure 失败；r002：完整原生构建在语法生成器运行时因路径型 NEEDED 失败；r003：传输 SSH MAC 错误，真实 launch=0，没有目标结果，独立核对任务根不存在后退役为 UNKNOWN。全部旧事务和原始证据保留，永不重放。

## 当前状态

探索 r004 同一事务原生全量构建 RC0，原上游76/76、零失败、零跳过，只保留为探索证据。新正式 r005 实际官方 ConanVerifier RC0，原上游76/76、消费者4/4、鸿蒙专项1/1，同 run 源码 IDs／参数、哈希、WAL／完整回执链均独立核验。

现行官方 `FinishPipeline.step35_local_ci()` 在全新 r001 真实执行原 setup.sh 与 build_and_test.sh，RC0，原上游76/76、消费者4/4、鸿蒙专项1/1、L0/L1全部通过；原方法实际生成 `.ci-result.json` 与原日志，其 SHA-256逐字节核对后导出，未手工构造或改写结果。当前新专项目录/清单/固定marker已实际覆盖。`reports/official-step35-observed.json` SHA-256 `9c44182d456b890bf788d9c0dc151320809ee11c9ce2bf11902f0dfb9c27cd0d`；`reports/upstream-source-cases-observed.json` SHA-256 `10f3be25105582c22a1c8db1c3571a8960e4ea67e8f3487658a3186061a69025`。r005与r001分别release/postrelease、自有进程0，永不重放。

该结果只证明实际执行的正式阶段，不冒称整个finish、平台CI或新PR PASS。真实1.6.0.2任务14927已一次导入并领取，账号2301_80739235，分支fix/libwebp-1.6.0.2，API原始assigned与页面已领取一致。软件唯一OPEN Issue3565已纠正为本修复身份，旧PR双向关联已权威回读为空。新PR尚未创建；当前最终元数据候选的PRE_CREATE、POST_CREATE及完整HEAD平台Review/CI仍须按真实阶段执行，旧#13623结果不能代替新版本。四项HD因果重判均false，路径A+B、唯一【知识库扩展】前缀，精确分类观察SHA `70077810f1f1276a1a4cca3d01b9a48fdf81b0191d1ef7593e816dd9952c4d2b`，分类还须绑定本次最终元数据候选，不以数量或时长自设高难阈值。

## 最终状态（本地实际阶段）

正式Conan、本地官方CI、原测试、消费者和独立鸿蒙专项已完成。元数据和身份收尾不修改上述已测试的十二项运行输入；知识草稿对及六节正文随同候选提交。这个结束标记仅关闭本地构建记录，不代表整个finish、平台Review/CI、PR创建或提审已经完成。
