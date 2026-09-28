# DRAFT-E-autoptr-unique-ptr: std::auto_ptr → std::unique_ptr 迁移

## 场景

2014 年前的 C++ 库在 OHOS SDK（clang 15 + libc++，-std=c++17）下编译报：
```
error: no template named 'auto_ptr' in namespace 'std'; did you mean 'xml::dom::auto_ptr'?
```

C++17 正式移除了 std::auto_ptr。老库依赖其"拷贝即转移所有权"的语义，
简单文本替换会引入新错误（unique_ptr 拷贝被 delete）。

## 根因

- std::auto_ptr（C++98）在 C++11 deprecated、C++17 移除
- libc++ 17 的 <memory> 不再提供 auto_ptr
- 相关：CodeSynthesis libxsd 的 xsd::cxx::xml::dom::auto_ptr 兼容类在
  XSD_CXX11 宏定义时由 unique_ptr 别名替代（auto-ptr.hxx 条件编译）

## 修复方案（两步）

### 1. 声明/构造点机械替换
```diff
- std::auto_ptr<KolabXSD::Note> note;
+ std::unique_ptr<KolabXSD::Note> note;

- xsd::cxx::xml::dom::auto_ptr<xercesc::DOMDocument> doc = ...;
+ xsd::cxx::xml::dom::unique_ptr<xercesc::DOMDocument> doc = ...;
```
确保头文件有 `#include <memory>`。

### 2. 所有权转移点显式 std::move

auto_ptr 的拷贝构造即转移；unique_ptr 拷贝被 delete，必须 std::move：

```diff
- note = KolabXSD::note(doc);                    # 按值传参
+ note = KolabXSD::note(std::move(doc));

- prop.recurrence_id(recurrenceId);              # setter 接受 unique_ptr
+ prop.recurrence_id(std::move(recurrenceId));

- components.valarm().push_back(ValarmType(p));  # 容器内构造转移
+ components.valarm().push_back(ValarmType(std::move(p)));
```

按值返回局部 unique_ptr 的函数无需修改（NRVO/移动语义自动处理）。

### 3. 定位漏改
```bash
for f in $(find . -name "*.obj"); do
  nm -u "$f" 2>/dev/null | grep -q auto_ptr && echo "REF: $f"
done
```

## 验证

- libkolabxml 1.2.1：20+ 处替换（kolabconversions.h / xcalconversions.h /
  xcardconversions.h / compiled/XMLParserWrapper.{h,cpp}）
- OHOS arm64 conan create 全绿
- 上游测试 84/84 全过（含 conversiontest::threadLocalTest 线程安全验证）

## 兜底

上游必须停留 C++03 时：`-D_LIBCPP_ENABLE_CXX17_REMOVED_AUTO_PTR`
（libc++ 逃生口，不可移植，仅过渡）。
