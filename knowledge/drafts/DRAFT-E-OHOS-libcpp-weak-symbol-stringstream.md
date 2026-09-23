# DRAFT-E-OHOS-libcpp-weak-symbol-stringstream

## OHOS clang-15 libc++ 弱符号双副本 → 静态库内 std::stringstream 析构 invalid free

### 错误特征（可机器匹配）

```
AddressSanitizer: attempting free on address which was not malloc()-ed
    #1 ... std::__n1::ios_base::~ios_base() (/system/lib64/libc++_shared.so)
    #2 ... <UserClass>::~UserClass() (consumer binary)
Signal 11 (core dumped)   ← 全部业务逻辑完成后、进程退出阶段
exit code 139
```

关键判定线索：**所有测试断言已输出且通过，崩溃发生在 return main 之后**——
无缓冲 stdout（setvbuf _IONBF）+ 完整日志是定位前提，否则只见标题行。

### 根因

OHOS SDK clang-15 编译含 libc++ 模板实例的静态库（.a）时生成 weak 符号副本
（带 inline-namespace 版本标记，如 `_ZNSt4__n118basic_stringstream...D1Ev`
与 `_ZSt28__throw_bad_array_new_lengthB6v15004v`）；消费者二进制运行时链接
libc++_shared.so，同名符号存在两份实现。静态析构阶段一份实现的
ios_base::~ios_base 释放了另一份分配域的 __loc_/iword/pword → invalid free。

### 诊断路径（三步）

1. 最小复现探针：只构造含 stringstream 成员的类再退出（不带业务逻辑）
2. `-fsanitize=address` 编译运行——栈直指 ios_base::~ios_base
3. 对照实验：无该成员的兄弟类干净退出 = 成员级根因确认

### 修复方案（优先级序）

1. **编译开关消除成员**（首选）：若 stringstream 的功能消费者是 GUI/可选
   组件，用上游开关（如 cubicsdr 的 ENABLE_DIGITAL_LAB=0）把成员挡在库外。
   注意上游可能存在"开关关闭时源码编不过"的缺陷（cubicsdr FSK/GMSK 的
   outStream 无条件引用），需守卫补丁（patches/0001 形态）。
2. 移到共享库：含该成员的类在 .so 内与 libc++_shared 同域编译。
3. 测试二进制规避（不解决库消费者）：`std::_Exit(0)` 跳过静态析构。
   ⚠️ 交付库场景禁用——掩盖问题。

### 反模式（实测无效）

- `objcopy --localize-symbol` 处理 .a 的 D1/D0 weak 副本：thunk（_ZThn16_）
  副本仍逃逸，崩溃依旧
- `-fvisibility=hidden` / `-fvisibility-inlines-hidden`：weak 符号不受
  visibility 控制，无效
- 静态链接 libc++（libc++_static.a）：问题依旧（副本域换了但析构边界没变）

### 实证

cubicsdr 0.2.7 任务 #89（2026-09-20）：
- 复现：digital modem 构造/析构探针 8/8 Signal 11；analog modem 干净退出
- 修复：ENABLE_DIGITAL_LAB=0 + patches/0001 → test_package 11/11 ALL PASS
  退出码 0

### 预扫描建议

含 `std::stringstream|basic_stringstream` 成员的类进入静态库交付时，
在配方阶段评估成员的功能必要性（GUI 消费者 → 编译开关挡出库）。

---
关联：E249（Signal 11/139 家族，但 E249 是 borrowed-ownership 未初始化，
本条是工具链弱符号双副本——根因不同，修复法不同）
