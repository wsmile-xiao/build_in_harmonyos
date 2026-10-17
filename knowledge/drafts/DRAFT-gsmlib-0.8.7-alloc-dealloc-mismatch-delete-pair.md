# draft-gsmlib-0.8.7-alloc-dealloc-mismatch-delete-pair

## 症状

gsmlib 0.8.7 上游 SMS 解码测试（testsms/testsms2/testssms）在 OHOS aarch64 直跑时
SIGSEGV（退出码 139）且无输出；ASAN 复现报：

```
ERROR: AddressSanitizer: alloc-dealloc-mismatch (operator new [] vs operator delete) on 0x006271191140
  #0 operator delete(void*)
  #1 gsmlib::SMSDecoder::~SMSDecoder() gsm_sms_codec.cc:474:3   delete _p;
  allocated by operator new[]
  #1 gsmlib::SMSDecoder::SMSDecoder(...) gsm_sms_codec.cc:246:8   _p = new unsigned char[pdu.length() / 2];
```

## 根因

SMSDecoder 用 `new unsigned char[n]` 分配缓冲区 `_p`，析构却写 `delete _p`
（标量 delete）。在 libc++/ASAN 下这是 alloc-dealloc-mismatch（未定义行为）；
非 ASAN 构建（-DNDEBUG）下内存布局差异导致解码路径运行时 SIGSEGV。
属于 2003 年前后代码常见的 new[]/delete 配对错误，与编译器平台无关，
在 clang/libc++ 工具链上以崩溃形式暴露。

## 方案

源码配对修复：`delete _p;` → `delete[] _p;`（见 archives/g/gsmlib/0.8.7/
patches/0004-gsmlib-gsm_sms_codec.cc.patch）。修复后 conan-verify 全门禁通过，
SMSDecoder 相关消费者用例（test_package）与鸿蒙专项测试转绿。

## 验证

- ASAN 复现定位：`clang++ -fsanitize=address,undefined ... mini_sms.cc` 报
  alloc-dealloc-mismatch，栈指向 SMSDecoder 构造/析构
- 修复后：`conan-verify gsmlib 0.8.7` G1-G4+L2/L4/L5 全 PASS；
  test_package 消费者 `Test #1: test_gsmlib Passed`；鸿蒙专项测试 PASSED

## 适用边界 / 反例

- 适用：任何 C++ 库中 new[] 配标量 delete 的堆缓冲区配对错误，均可在
  clang/libc++ + ASAN 下以 alloc-dealloc-mismatch 定位并 delete[] 修复。
- 反例：使用 std::vector/std::string 等容器管理的缓冲不适用（无裸 new[]）。

## 查重差异（七轴）

- exact_duplicate: 无；causal_duplicate: 无；trigger_overlap: 低（与 E293
  同属 legacy C++ 暴露，但 E293 是编译期诊断，此为运行期堆损坏）；
  solution_overlap: 无；combination_novelty: 是；boundary_novelty: 是
  （NDEBUG 下从 abort 变 SIGSEGV）；test_migration_novelty: 是
- similar_to: E293（legacy C++，不同面）；caused_by: new[]/delete 配对错误；
  prerequisite_of: 无；conflicts_with: 无
