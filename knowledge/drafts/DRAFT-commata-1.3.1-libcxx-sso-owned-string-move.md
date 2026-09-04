# DRAFT-commata-1.3.1-libcxx-sso-owned-string-move

## 问题
OHOS（libc++）上，上游测试 `CharsBufferSizes/TestTablePull/{0,1,2,3}.Move`（4 个）失败：
`pull.skip_record()()` 后 `std::move(pull)`，再 `*pull2()` 返回 7 个 NUL 字符而非 `"def"`。
堆分配长串输入（>22 字符）的相同用例通过。

## 根因
libc++ 的 `std::basic_string` SSO 内联缓冲阈值约 22 字符。`owned_string_input` 持有 19 字符的短串时数据存于对象内部；
`std::move` 使短串数据复制到新对象的内联缓冲，`data()` 地址改变。`base_parser` 移动构造与 handler 数据队列仍持有
指向旧缓冲的直读指针（零拷贝直读设计），之后解引用读到已被搬走/清零的旧缓冲 → NUL。
上游 CI 使用 libstdc++（SSO 阈值 15），同一 19 字符串走堆分配，移动仅转移堆指针、地址不变，故上游未暴露。

## 触发条件
- 编译器：OHOS clang 15 + libcxx-ohos
- 输入：拥有字符串长度 ≤ 22（libc++ SSO 内联）
- 流程：构造 `make_table_pull(make_csv_source(std::string(...)))` → `skip_record()` → `std::move(pull)` → 继续读取

## 方案
修改 `include/commata/char_input.hpp` 中 `owned_string_input`：内部字符串改用 `std::unique_ptr<std::basic_string<Ch,Tr,Allocator>>`
堆间接层持有，移动时仅转移堆指针，`data()` 地址稳定，直读指针不悬空；移动构造/赋值保持 noexcept。

## 验证
- 修复前：`CharsBufferSizes/TestTablePull/*.Move` 4 个失败（`*pull2()` 返回 7 NUL）
- 修复后：上游测试全量 `668/668 PASSED`；堆串与 SSO 短串输入均正确返回 `"def"`

## 适用边界
- 仅影响 libc++（OHOS）；libstdc++/MSVC 因 SSO 阈值不同或堆分配行为不触发
- 属平台工具链差异暴露的库缺陷，修复后对两套工具链均正确

## 反例与限制
- 不得通过清除解析器缓冲指针绕过（破坏零拷贝直读语义）
- 不得仅加长测试串规避（掩盖缺陷，非修复）；补丁方案为唯一推荐路径
