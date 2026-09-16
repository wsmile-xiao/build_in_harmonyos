# objfw/1.5.7: ObjC 消费方必须携带 OFConstantString 常量字符串类标志

## 现象

objfw/1.5.7 打包后，消费方 ObjC 程序：

- 纯类定义 + 消息发送：正常
- `[OFString stringWithUTF8String:]`：正常
- `@"..."` 字面量单独赋值：正常
- **带字面量参数的消息**（`[str containsString: @"x"]`）：**Signal 11 (SIGSEGV)**
- 字面量对象跨方法调用（`[str dataWithEncoding:]` 返回值再调用）：**Signal 6 + `OFMethodNotFound` 栈**

## 根因

ObjFW 自带 runtime（libobjfwrt），常量字符串类是 `OFConstantString`。
上游 buildsys 编译库本身时使用：

```
-fconstant-string-class=OFConstantString -Xclang -fno-constant-cfstrings
```

消费方若只链接 `-lobjfw -lobjfwrt` 而不传该 flag，clang 把 `@"..."`
按 CFConstantString 布局发射。编译/链接全静默通过，运行期 ObjFW runtime
把 CFString 结构当 OFConstantString 解引用 → SIGSEGV；或查 selector 落在
外来对象上 → OFMethodNotFound abort。

## 修复（配方层）

```python
def package_info(self):
    self.cpp_info.libs = ["objfw", "objfwrt", "objfwtls"]
    self.cpp_info.objcflags = [
        "-fobjc-runtime=objfw",
        "-fconstant-string-class=OFConstantString",
    ]
```

test_package 必须是真实 .m 源码（OFString/OFNumber/OFArray/OFData 实调），
用 `clang -x objective-c -fobjc-runtime=objfw -fconstant-string-class=OFConstantString`
编译，`can_run()` 下实跑。C-only 消费方无法证明 ObjC ABI。

## 与 E449 的关系

E449（gnustep-base/libobjc2，`-fobjc-runtime=gcc` +
`-fconstant-string-class=NSConstantString`）确立了"ObjC 包必须发布消费方
runtime flags"的模式；本条是同一模式在 ObjFW 自带 runtime
（`-fobjc-runtime=objfw` + OFConstantString）上的实例，且补充了
"字面量参数消息发送"这一最小复现路径。

## 验证

- `conan create archives/o/objfw/1.5.7 -pr:h=ohos-aarch64 -pr:b=ohos-aarch64 --build=missing`
  → Package created + test_package（.m 实调 5 个断言）运行 rc=0
- 不带 `-fconstant-string-class` 的最小复现：`[str containsString: @"x"]` → SIGSEGV
