# mujs — HarmonyOS aarch64 预编译包

## 快速安装

```bash
tar xzf mujs-1.3.9-ohos-aarch64.tar.gz -C ~/usr/local
cd mujs-1.3.9-ohos-aarch64 && sh install-mujs-1.3.9.sh
```

## 可用版本

| 版本 | 状态 | 补丁数 | 测试结果 |
|------|------|--------|----------|
| 1.3.9 | success | 0 | 10/10 ✅ |

## 当前版本 (1.3.9) 详情

### 包内容

**二进制文件**:
- `bin/mujs` - JavaScript 解释器
- `bin/mujs-pp` - JavaScript 美化打印工具

**库文件**:
- `lib/libmujs.a` - 静态库
- `lib/libmujs.so` - 动态库

**其他**:
- `include/mujs.h` - 头文件
- `lib/pkgconfig/mujs.pc` - pkg-config 文件

**包大小**: 1.5MB

### 编译信息

- **构建系统**: Makefile
- **目标**: ohos-aarch64
- **编译参数**: `HAVE_READLINE=no`
- **质量门禁**: PASS (G1-G4)
- **补丁数**: 0

### 测试结果

**测试日期**: 2026-05-07
**测试结果**: ✅ 10/10 通过

测试覆盖的功能：
- ✅ 基本数学运算（Math.pow/sqrt/abs）
- ✅ 字符串操作（toUpperCase/toLowerCase/substring/replace）
- ✅ 数组操作（push/pop/join/map/filter/reduce）
- ✅ 对象属性读写
- ✅ 函数定义和递归
- ✅ 闭包和立即执行函数
- ✅ 控制流（if-else/switch/循环）
- ✅ JSON序列化/反序列化
- ✅ 正则表达式（match/replace/test/分组捕获）
- ✅ 错误处理（try-catch/Error/ReferenceError/TypeError）
- ✅ Date对象操作
- ✅ 内置对象方法（Object.keys/Array.forEach/String.trim/Math方法）

测试脚本位置：`reports/test-scripts/`

### 功能验证

```bash
$ mujs
Welcome to MuJS 1.3.8.
> print('Hello, MuJS!')
Hello, MuJS!
> 1 + 2
3
```

## 环境要求

- HarmonyOS/OpenHarmony aarch64
- 建议将 `~/usr/local/bin` 加入 PATH

## 使用示例

```bash
# 执行 JavaScript 文件
mujs script.js

# 交互模式
mujs -i

# 美化打印 JavaScript 代码
mujs-pp messy_code.js
```

## 编译者

- 编译日期: 2026-05-07
- 编译系统: openharmony-compile-agent