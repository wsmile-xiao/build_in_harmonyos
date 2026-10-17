# tomlc99 0git20260130 评审修复与真实验证

## 上游与构建身份

官方提交：29076dfd095bbbbd50a3c1b2760d29f4b83e74ac。
源码归档 SHA-256：fdd1bf848bd81f3e98dd98dd4381a626a4a6255537ac8571be0f0a7e34a4becf。
配方只发布库和头文件，不发布三个示例 CLI；零外部产品依赖。
上游 Makefile 实际包含静态库、共享库和 install 目标，但共享链接行
未提供 SONAME。历史“无 shared/install”及“上游测试为 0”说明错误，
已纠正。配方建立任务私有 libtoml.so.0/.so.0.0.0，不写系统 lib 目录。

## 源码修复与官方补丁

1. toml.c：RFC3629 的 1–4 字节 UTF-8 和 Unicode 标量边界、原始
   控制/NUL/bare-CR 拒绝；日期与时区合法范围、严格数值与下划线语法；
   quote/escape 闭合；内联表、静态数组、dotted-key 与 header 不可重定义。
2. toml.c/toml.h：增加兼容的显式长度字符串和键访问 API，保留旧 API，
   用长度加 memcmp 区分合法 escaped-NUL 键与空键，JSON 编码不截断。
3. toml_json.c：使用显式长度访问器，转义 JSON 控制字符，保持有符号/
   无符号字节域独立。此类语义修复是跨平台 bugfix，不加虚假 OHOS 守卫。
4. unittest/t1.c：保留 10 组/20 断言；5 组旧超 Unicode 范围成功
   预期改为严格失败断言，原输入保留，没有删除失败用例。

四个补丁只由官方 refresh-patch --auto 生成，patch --dry-run 通过；
独立 patch-ng 重放逐文件 SHA-256 与下面真机 PASS 源码完全相同。
重放证据：同任务根 tomlc99-patch-replay-r001.json。

## 全量测试入口与规范修正

完整 765 个用例 ID：unittest/t1 1 项、stdex 62 项、固定官方
toml-test TOML1.0 清单 556 项、固定 toml-spec-tests 146 项。
两套外部测试数据分别固定官方提交及归档 SHA，所有输入与原 golden
有逐文件哈希。没有 skip、缩小分母或用消费者替代上游测试。

- stdex 的 toml_cat 解析诊断后仍 RC0，value 解码失败才 RC1；判据同时
  核对原完整输出。NaN 符号只做明确数学等价归一化。
- stdex/string8.toml 的原 golden 记录解析器 bug：基本双引号字符串内
  单引号是合法的。保留原输入和原 golden 哈希，显式记录规范原因，
  比较修复后完整输出，不以旧错误预期迫使产品拒绝合法输入。
- test2/errors/array-7.toml 是旧 TOML 0.x 混合数组预期，TOML1.0
  允许混合数组；保留原 ID/输入/原分类，显式验证两个 typed 值。
- 旧 tagged-array/local-date/time 名称与无偏移 datetime 按原数据语义
  归一化，不宽松混淆布尔、整数、字符串、时区和具体值。

## 真实目标结果及不可变失败历史

端点 10.62.201.39:2222，HarmonyOS/aarch64，UID20020084。
每轮源/测试/工具/控制器 SHA、boot_id 和候选身份独立冻结。

- r002：662/765，103 个实际失败；消费者1/1、鸿蒙专项1/1。
- r003：745/765，20 个实际失败；消费者1/1、鸿蒙专项1/1。
- r004：764/765，剩余原 golden 的字符串预期问题。
- r005：765/765，上游完整；消费者1/1（8 断言），鸿蒙专项1/1。

r005 配置 SHA-256：7a1b96dcc9ffa9c0f5234ac7b7c73e6a473b2b0a18e337aba12e51dbe879f129。
完整 WAL/receipt 链、原清单/结果 ID 一致、唯一 launch=1、after 检查、
自有进程0、release/postrelease 和冻结 validator PASS。
证据：F:/HarmonyPC/pr-review-closure-20261004-r1/w3-tomlc99-r005/validation.json。
旧失败全部保存原始日志并精确清理自有 work，不改写、不重跑、不拼接。

## 鸿蒙特有测试与边界

独立 hmdfs_toml.c 编译守卫 __OHOS__/aarch64，真实 uname 检查，
任务私有 HMDFS 中文文件名独占创建；精确 UTF-8 字节写入并由实际
TOML 库解析，比较父目录 projected owner 而非错误硬绑进程 UID；
验证 unlink 与 ENOENT。普通消费者没有被重复算成平台专项。

当前正式配方仍需新的 Conan/合同与 push，当前 HEAD 平台 CI/Review
和提审不能由以上原生 PASS 或补丁重放推断。CLI/共享系统目录、其他
任务进程、服务、账号及制品仓没有修改。
