# DRAFT-legacy-cxx-modern-clang-cpp17-removals：老 C++ 代码在 `-std=c++17` 下的三类硬错误

> Contributor: Lee-BX | Status: Draft | Updated: 2026-10-04
> Source: smpeg 0.4.5-cvs20030824 HarmonyOS PC 适配（archives/s/smpeg/0.4.5-cvs20030824）
> 对应：knowledge/drafts/DRAFT-legacy-cxx-modern-clang-cpp17-removals.kv
> 相关：plink 1.07 草稿（legacy C++ 迭代器遮蔽，同族但不同类）

## 现象

smpeg（2003 年 CVS 快照）在 OHOS（`compiler.cppstd=17`）上编译时先后出现三类报错，位置分散、措辞互不相似：

```text
# 1) 13 个文件、87 处
error: ISO C++17 does not allow 'register' storage class specifier [-Wregister]

# 2) audio/huffmantable.cpp（3 行 6 处）
error: constant expression evaluates to -1 which cannot be narrowed to type 'unsigned int' [-Wc++11-narrowing]
  { 0, 0-1, 0-1, 0,  0, htd33},
       ^~~  ^~~

# 3) audio/MPEGaudio.cpp（类内 friend 声明过、类外被调用）
error: use of undeclared identifier 'Play_MPEGaudioSDL'
error: use of undeclared identifier 'Decode_MPEGaudio'
```

三类其实是**同一个根因的三个面**：代码写于 C++11 之前，依赖"旧编译器接受、现代标准禁止"的宽松行为。

| 写法 | 旧编译器（1998-2005） | clang + `-std=c++17` |
|------|----------------------|----------------------|
| `register int i;` | 提示/忽略 | **硬错误**（C++17 移除） |
| `{0, 0-1}` 初始化无符号字段 | 允许 | **硬错误**（C++11 起禁窄化） |
| 类内 `friend void f();` | 视作在外层命名空间声明 f | 不再引入 → 类外调用报 undeclared |

## 判定方法（先盘点，再改）

```sh
# 三类写法一次性盘点（在源码树执行）
grep -rnE '(^|[^A-Za-z0-9_])register[[:space:]]' --include=*.cpp --include=*.h . | wc -l
grep -rn '0-1' --include=*.cpp --include=*.h . | head
grep -rn 'friend ' --include=*.h . | head
```

编译日志里出现 `-Wregister`、`-Wc++11-narrowing`、或"某个只在 friend 里出现过的名字报 undeclared"，
即可按本条处理，不必逐个当新问题排查。

## 处置（最小语义改动，不动标准）

```cpp
// 1) register：直接删除关键字（语义完全不变）
-  register unsigned short a;
+  unsigned short a;

// 2) 窄化：给 -1 哨兵显式转型到字段类型
-  { 0, 0-1, 0-1, 0,  0, htd33},
+  { 0, (unsigned int)(0-1), (unsigned int)(0-1), 0,  0, htd33},

// 3) friend 声明：在类定义前补命名空间级原型（类内 friend 保留）
 class MPEGstream;
+void Play_MPEGaudioSDL(void *udata, Uint8 *stream, int len);
+#ifdef THREADED_AUDIO
+int Decode_MPEGaudio(void *udata);
+#endif
```

**不要**用降标绕过（`-std=gnu++98/-std=gnu++14`）：profile 的 `cppstd=17` 是平台统一口径，
降标会把真实兼容性问题掩盖到运行期。也不要为窄化改字段类型（动 ABI）。

## 验证

```text
smpeg 0.4.5-cvs20030824：conan create rc=0；消费者用例 6/6 通过；
libsmpeg.a 与 plaympeg 均产出（plaympeg 的 C 链接需要把上游硬编码的 -lstdc++ 改为 -lc++）
```

## 通用化建议

1. 适配任何 2005 年前后的 C++ 库前，先跑上面的三条 grep，一次把三类写法盘出来，
   避免"修一处、跑一轮 CI、再冒一处"。
2. 同一库往往还伴着另外两类老 C++ 坑（与语言标准无关、属构建层）：
   迭代器遮蔽外层循环变量（见 plink 1.07 草稿）、libtool 硬编码 `-lstdc++`
   （OHOS 只有 libc++）。见到其中之一时顺手检查其余。
