# libwebp 1.6.0.2 真正执行的正式验证

## 当前权威：2026-10-12 r008

本轮唯一事务 `libwebp-1.6.0.2-finish-step5-20261012-r008`：官方 step35、干净 Conan create 真实 RC0；原测试76/76（FuzzTest12、ANTLR64）、消费者4/4、鸿蒙1/1，零失败/跳过。测试tree为5efc5e0ac4da2bd4bd79ace788ab591c88db1632，父HEAD为caf27fea727eab79895128111aaaad2ce4665efd；独立观察SHA256为bd00bcc29fc5eee4af31524ef97c79ae85b62989640f6e2e9db72751ad7d1481，源码匹配SHA256为6b915055c56707d2a786d28f5e30e723873f6cccba56bc15c7d358751c94fa5f，完整原日志SHA256为2a85cbca3192ee7a6e3cc1562abd85588129c65c070545bbec6dc39bfaab5143。完整WAL/receipt链、release/postrelease和自有进程0已独立核验。仅为当前真机正式验证，不冒称平台CI。

worker真实日志显示maps为内核HMDFS backing路径，当前命名空间realpath返回ENOENT。本轮以canonical实际dl_iterate_phdr对象、文件型PT_LOAD地址/偏移和非零inode完整见证核对映射；实际dev字段仅解析，不单独作为来源证明。重复/外来对象、未知错误或不匹配区间仍拒绝。不按basename或路径前缀放行，不移除codec、签名和dladdr断言。当前修复已在r008同run验证；新完整HEAD仍需平台Review/CI。

以下r007及更早均为保全的历史，不拼跨run结果。

## 历史 r007

本轮唯一事务 `libwebp-1.6.0.2-finish-step5-20261011-r007`：官方 step35、干净 Conan create 真实 RC0；原测试76/76（FuzzTest12、ANTLR64）、消费者4/4、鸿蒙1/1，零失败/跳过。测试tree为7da2a158453f89f09f3ea299defe4e8ae779282c，父HEAD为8e964cf639e8eae0663254077e9856b49e8c1c23；独立观察SHA256为69ec44c1f5fe4c12213d2650537c235bd37bc6cde21c9897a7fb7349d84f0ce1，源码匹配SHA256为83c7bfa98574d51c94f5c6b9db872ccf29b625d8b6d24a457e7ebe5f7beeb5e1，完整原日志SHA256为48f73b073fbd63b701c29f6a3d0bd577f81b47c5be265b8677a705ab1819aa07。完整WAL/receipt链、release/postrelease和自有进程0已独立核验。

平台worker build97366的严格映射归属判定仍真实失败，根因尚未确定。本轮只在原拒绝分支输出实际map路径、realpath、expected包根、errno和拒绝理由，保留dlopen/dlsym、codec、dladdr/maps及所有原拒绝逻辑。真机成功不能证明该worker故障已经修复；新提交仍须实际平台Review/CI。下面r006及更早内容均为保全的历史结果，不跨run拼接。

## 历史：2026-10-11 r006

官方 step35、干净 Conan create 真实 RC0；同一唯一事务原76/76、消费者4/4、鸿蒙1/1，零失败/跳过。测试 tree a7565e8d6933b00a88643ac072ac06d118a73f2c；独立观察SHA256 3e480e02ac65adbc42fb933508be13ccfc33e5dc2651d66b6702454c744434d1；逐源码匹配SHA256 7eb67685a4a2c95a6fe0e8862f423c15dc1ae5a2b45ac45d030359745c97bcec。完整回执链/release/postrelease/自有进程0均独立核验。原生装载器实际失败 stdout/stderr/返回码传播修复已在该输入中，原异常、120秒超时和测试语义不变。下列均为历史记录；不迁移旧平台 CI 或跨 run 拼接。

## 当前整改候选的独立验证（2026-10-09）

非OHOS编译器选择修复后的 recipe SHA256：5c01bbe198dc2735f6af6bfc426e311692a503004a80e0d384bb6e04e658e199。实测 staged tree：1f561d3e25f7cc1bcb759ecdb074f1fe13e7bbe0。

正式 Conan r006 和官方 step35 r002 分别在各自唯一事务中完成原上游76/76、消费者4/4、鸿蒙专项1/1，零失败、零跳过；真实原源码 IDs 与 ANTLR32+32原参数均独立核验。原方法自动生成的当前`.ci-result.json` SHA256为16a71d99dfffabdb37b6b66dcdba61172c684f03726f56b2f9da1fa7d39c4733，完整原日志SHA256为1cff1cf7b5315e96fd1ca0d02434f99b1c0802220d0fe82c0c570da3d7871b8d。仅精确字节导出，没有手工生成或修改结果字段。

官方step35独立观察SHA256：b7cf658765973d34eb27d4f8048f2b5f5f24ab3cca1179895a68ff8acd304bb1；同run源码核验SHA256：25a16a8f75bbe09397893264394d31c9fc55c103235a7d12c24d1031a1f5be65。release/postrelease、自有进程0与完整WAL/receipt chain均已核对。

本次公开PR仍为#14954，Issue3565/task14927，当前远端HEAD仍须提交前权威回读；本地候选尚未推送。后续只有报告、真实证据及合同绑定变化，运行输入不变。以下均为保留的历史记录，不代表当前配方；当前记录也不宣称平台CI、发布或提审通过。

---

本节旧 r005/r001 是历史真实结果。2026-10-09 配方 OS 编译器 guard 修复后新输入必须 fresh 验证，尚无新目标结果，不能把下面76/76宣称为当前整改配方通过。公开完整报告为 PR14954 评论192792991；当前公开 HEAD c3c08c461fa921b76f0d466178e812c22f8b6b57，新的 mutable 配方尚未 push。

字节集说明：两份观察引用 SHA 9c44182d…/10f3be25… 对应任务原始 CRLF 字节；Git LF blob 精确 SHA 分别 d248ac7cb328d2a55fe40a8676f6d0934335c6bd73ef7d3fb3283de6e45326ac / b46560f37ff58aabde82889ca9eba41ae7b03694ab0c80daae153d8adb14dfd3。公开前已逐字节确认原始副本相同、LF 规范化哈希匹配、解析值相同，不修改原证据。

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
