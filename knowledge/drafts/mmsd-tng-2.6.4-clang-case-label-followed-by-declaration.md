# clang 拒绝「case 标签后紧跟声明」（GCC GNU 扩展容忍）

> 草稿 ID：`mmsd-tng-2.6.4-clang-case-label-followed-by-declaration`
> 来源任务：mmsd-tng 2.6.4 适配（HarmonyOS PC aarch64 / clang 15.0.4 / Meson）

## 错误特征

```
../src/service.c:3966:7: error: expected expression
      gsize length;
      ^
../src/service.c:3977:60: error: use of undeclared identifier 'length'
      g_file_get_contents (request->data_path, &contents, &length,
                                                           ^
../src/service.c:4016:6: error: cannot jump from switch statement to this case label
     default:
     ^
../src/service.c:3967:25: note: jump bypasses initialization of variable with __attribute__((cleanup))
      g_autofree gchar *contents = NULL;
```

对应源码形态（`src/service.c` 的 `process_request()`）：

```c
    case MMS_REQUEST_TYPE_POST:
    case MMS_REQUEST_TYPE_POST_TMP:
      /* Collect contents of file to POST */
      gsize length;                    /* ← 标签后紧跟声明：ISO C 约束违例 */
      g_autofree gchar *contents = NULL;   /* ← cleanup 属性 → 次生"跳转绕过初始化" */
      ...
      return msg;
     default:
```

## 触发条件

- 源码中存在 `case X:` / `default:` 之后**直接写声明**的写法（声明不是语句）；
- 使用 clang 编译（HarmonyOS/OHOS、macOS、Android 等 clang 主环境）；
- GCC 环境下完全无症状（GNU 扩展长期容忍），因此**上游仓库看不出来**，只在移植时暴露。

## 根因

ISO C 规定标签只能作为**语句**的前缀，而声明不是语句。GCC 以 GNU 扩展容忍；clang 严格按标准处理：

1. 解析到该声明即 `error: expected expression`；
2. 该声明解析失败后，后续引用它的语句级联报 `use of undeclared identifier`
   （**级联会误导定位——真正的首错在标签行**）；
3. 若声明带 `__attribute__((cleanup))`（glib 的 `g_autofree` / `g_autoptr`），
   跳到后面的 `default:` 会"绕过"该变量的初始化，clang 再报
   `cannot jump from switch statement to this case label`。

## 解决方案（推荐）

给该 case 分支加一层**块作用域**，一次解决两个报错：

```diff
     case MMS_REQUEST_TYPE_POST:
     case MMS_REQUEST_TYPE_POST_TMP:
       /* Collect contents of file to POST */
+      {
       gsize length;
       g_autofree gchar *contents = NULL;
       ...
       return msg;
+      }
      default:
```

- 标签后紧跟的是**复合语句** → 满足 ISO C；
- 变量作用域收在该分支内 → 跳转到其它 case/default 不再"绕过初始化"；
- **运行时语义零变化**，无需平台宏（R8），比"把声明上提到 switch 之前"更安全
  （后者会拉长 `g_autofree` 的生命周期、把释放点从分支结束改到函数结束）。

本例落地为 `patches/0002-src-service.c.patch`（+2 行）。

## 验证

```bash
# 最小复现（clang 直接报错，gcc 通过）
$ printf 'int f(int c){switch(c){case 1: int x=0; return x;} return 0;}\n' > t.c
$ clang -c t.c
t.c:1:32: error: expected expression
t.c:1:48: error: use of undeclared identifier 'x'
2 errors generated.
$ exit=1

# 修复后：上游 4 项单元测试全绿
$ meson test -C <builddir> --print-errorlogs
Ok: 4   Fail: 0   Skip: 0
```

## 证据

- 触发日志：`archives/m/mmsd-tng/2.6.4/reports/01-meson-compile-ohos.log`
- 补丁：`archives/m/mmsd-tng/2.6.4/patches/0002-src-service.c.patch`
- 适配笔记：`archives/m/mmsd-tng/2.6.4/notes.md` §2/E3
