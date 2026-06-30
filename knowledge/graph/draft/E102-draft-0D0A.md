# E102: pthread_setcancelstate 未定义错误

## 问题表现

编译时出现pthread函数未定义错误：
```
undefined symbol: pthread_setcancelstate
ld: error: pthread
PTHREAD_CANCEL_DISABLE: undeclared
```

## 根因分析

HarmonyOS musl libc不支持pthread_setcancelstate和pthread_cancel函数，这些是POSIX线程取消功能的可选实现。

## 解决方案

修改C代码添加平台条件检查：

```bash
sed -i 's/#if !defined(__ANDROID__)/#if !defined(__ANDROID__) \&\& !defined(__OHOS__) \&\& !defined(__harmonyos__)/' spawn_stubs.c
```

## 影响范围

使用pthread_cancel功能的C代码，spawn库，OCaml spawn模块，进程管理工具。

## 验证方法

```bash
grep -q "__OHOS__" spawn_stubs.c
echo "HarmonyOS pthread patch applied"
```

## 分类

- 类别: libc, pthread, musl, harmonyos, cancel
- 严重性: 2（可通过条件编译解决）
- 贡献者: 0D0A