# Draft: polyseed AArch64 plain-char 符号性导致 UTF-8 惰性归一化静默失效

(配套 DRAFT-9645-polyseed-aarch64-char-signed-utf8-lazy.kv)

## 错误特征

同一设备上默认参数编译全部成功, 但运行上游测试在
`test_roundtrip1` (多语言 encode/decode 往返) 断言失败 SIGABRT;
仅英语子测试通过, 首个非 ASCII 语言即失败。

## 根因

AArch64 ELF ABI 默认 plain `char` 无符号 (`CHAR_MIN=0`), 而 polyseed 的
`utf8_nfkd_lazy()` (src/dependency.h) 与 `src/lang.c` noaccent 比较器使用
`*p < 0` 判定非 ASCII 字节。条件恒假 → 惰性路径对任何输入直接逐字节拷贝,
注入的 `u8_nfkd` 依赖永远不会被调用 → 含 U+3000 分隔符的日语短语无法分词,
decode 返回错误。x86-64 (char 有符号) 上无此问题, 属典型平台默认差异类
移植陷阱, 编译期与链接期均无任何告警。

## 修复

conanfile `generate()`: `tc.extra_cflags.append("-fsigned-char")`, 零源码补丁。
诊断口诀: 运行期才失败 + 只挂非 ASCII 路径 → 先测 `CHAR_MIN`, 单变量
`-fsigned-char` 重编对比。

## 消费者测试注意

test_package 注入的 `u8_nfkd` 必须与上游测试 `u8_nfkd_spaces` 同契约
(全部空白字符归一为 ASCII 空格); 恒等实现会让日语往返以
POLYSEED_ERR_NUM_WORDS 失败, 这是依赖注入不完整, 不是库缺陷。
