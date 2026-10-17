# DRAFT-easyhttpcpp-2.1.0-poco-1.15-autoptr-return-api：Poco 1.15 通道/格式器接口返回 AutoPtr

## 现象

在 OHOS 平台用 Poco 1.15.3 编译 easyhttpcpp 2.1.0 上游单元测试
`tests/unittests/common/DefaultLogWriterUnitTest.cpp` 时，编译器拒绝
把 `logger.getChannel()` / `FormattingChannel::getChannel()` /
`getFormatter()` 的返回值直接 `static_cast` 到具体类型指针：

```text
error: cannot cast from type 'Channel::Ptr' (aka 'AutoPtr<Poco::Channel>')
       to pointer type 'Poco::FormattingChannel *'
error: cannot cast from type 'Formatter::Ptr' (aka 'AutoPtr<Poco::Formatter>')
       to pointer type 'Poco::PatternFormatter *'
```

## 根因

Poco 1.15 把 `Logger::getChannel()`、`FormattingChannel::getChannel()`、
`FormattingChannel::getFormatter()` 的返回类型从裸指针改为 `AutoPtr<T>`
（`Channel::Ptr` / `Formatter::Ptr`）。老版本上游测试代码直接对返回值做
`static_cast<T*>`，在 Poco 1.15 下不再编译。这是 Poco API 演进导致的
消费者源码兼容问题，不是 OHOS 平台缺陷。

## 可复用修复模式

把对 AutoPtr 返回值的 `static_cast<T*>(...)` 改为先取裸指针再转换：

```cpp
Poco::FormattingChannel* pFCchannel =
    static_cast<Poco::FormattingChannel*>(logger.getChannel().get());
Poco::ColorConsoleChannel* pChannel =
    static_cast<Poco::ColorConsoleChannel*>(pFCchannel->getChannel().get());
Poco::Formatter* pFormatter =
    static_cast<Poco::PatternFormatter*>(pFCchannel->getFormatter().get());
```

适用范围：所有直接 `static_cast<具体Poco类型*>` AutoPtr 返回值的测试/工具代码；
升级 Poco 1.15 时统一改为 `.get()` 后再转换，不改变测试语义。

## 验证证据

easyhttpcpp 2.1.0 采用该修复后，`easyhttp-UnitTestRunner` 在 OHOS aarch64
（clang 15.0.4）下实际运行：1515 tests from 147 test suites，PASSED 1506 /
FAILED 9（9 项失败均为 HMDFS 无写权限断言与 URL 解码差异等平台限制，与
本修复无关）。补丁：`patches/0008-tests-unittests-common-DefaultLogWriterUnitTest.cpp.patch`。
