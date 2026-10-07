# libwebp 1.6.0.2 真正执行的正式验证

官方上游版本1.6.0，SHA-256 `e4ab7009bf0629fd11982d4c2aa83964cf244cffba7347ecd39019a9e38c4564`；`.2`为真实更高适配修复后缀，不是上游标签。生产配方恢复官方固定FuzzTest提交及原依赖闭包，并保留ANTLR4.12.0默认原测试。

| 独立事务 | 原上游 | 消费者 | 鸿蒙专项 | 原命令 | 清理 |
|---|---:|---:|---:|---|---|
| libwebp-1.6.0.2-conan-20261006-r005 | 76/76，无skip | 4/4 | 1/1 | 官方ConanVerifier RC0 | 唯一launch1，release/postrelease，自有进程0 |
| libwebp-1.6.0.2-finish-step5-20261006-r001 | 76/76，无skip | 4/4 | 1/1 | 当前官方step35原setup/build_and_test RC0，L0/L1通过 | 唯一launch1，release/postrelease，自有进程0 |

各行有自己完整的源码IDs、参数、输入闭包和回执链，不拼不同run分母。原上游十二个libwebp/FuzzTest参数属性程序与ANTLR原六十四个参数化用例已匹配源清单；不是静态注册数量或仅构建通过。原断言未减少。

当前官方事务：endpoint10.62.201.39:2222，boot `7851bdff-5b32-4d35-bc28-520a25ceaf05`，UID20020084；基线HEAD `3006419400b88a4a103ac8a9e0ed4d42c98b5e8a`，实测candidate tree `3ce7223b35e557189f73e382fac55da84f7cf0b2`。补充真实归档文档不是重测产品变更；提交前合同必须绑定最终stagedtree，不能把基线HEAD当成尚未发生的新PR提交HEAD。

原方法实际生成的`.ci-result.json`精确字节SHA `356ba5a9556143c3c498e4d8e51c77cb40b72205c8bc9e0fae31ff1b63f9ddb0`；原`w3-local-ci.log` SHA `b6cf02d05e27386b18038b674b8beb034f23fa14c85a3ca4de8b8d6ed7c0e18f`。未生成或修改结果字段。独立正式观察 `official-step35-observed.json` SHA `9c44182d456b890bf788d9c0dc151320809ee11c9ce2bf11902f0dfb9c27cd0d`；`upstream-source-cases-observed.json` SHA `10f3be25105582c22a1c8db1c3571a8960e4ea67e8f3487658a3186061a69025`。

鸿蒙专项独立执行真实AArch64/codesign、basename SONAME/NEEDED与实际自有包DSO映射，并实际调用codec无损往返；清单`HARMONY_TEST_COUNT=1`，原日志`HARMONY_TEST_PASS=1/1`。消费者无损RGBA、XMP mux/demux、有损尺寸/alpha、坏码流拒绝四项不替代鸿蒙专项或原上游。

保留的真实失败：未知OS白名单拒绝语言能力、路径型DT_NEEDED装载失败、断联launch0的UNKNOWN、缺os.version配置、codeload归档basename解析，以及正式r004的裸ctest启动失败。每个失败独立归档，已消费run永不重放；当前两个正式成功只来自新run真实执行。

边界：这不是整个官方finish所有阶段、平台CI、Review、发布或提审PASS。新任务/Issue/PR身份尚待真实平台建立，旧#13623 Review/CI不能代替新版本；不合并、不force、不上传制品、不改系统服务/权限。
