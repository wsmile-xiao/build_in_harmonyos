# dircproxy 1.1.0 编译笔记

## 编译状态：built

---

### 编译环境

- **软件**: dircproxy 1.1.0
- **来源**: https://github.com/w8tvi/dircproxy/archive/refs/tags/RELEASE-1_1_0.tar.gz
- **构建系统**: autotools (autoconf/automake)
- **编译时间**: 2026-05-29

---

### 修复方案（2026-05-29）

**问题1：HMDFS mktemp 权限限制（E081）**

config.status 脚本在 HMDFS 文件系统上使用 `mktemp -d` 创建临时目录失败。

**修复**：修改 config.status 第 585-595 行，使用固定临时目录替代 mktemp
```bash
# 原代码：
{
  tmp=`(umask 077 && mktemp -d "./confXXXXXX") 2>/dev/null` &&
  test -d "$tmp"
}  ||
{
  tmp=./conf$$-$RANDOM
  (umask 077 && mkdir "$tmp")
} || as_fn_error $? "cannot create a temporary directory in ." "$LINENO" 5
ac_tmp=$tmp

# 修复后：
# HMDFS workaround: use fixed directory instead of mktemp
# See E081: HMDFS mktemp permission restriction
tmp=./config-tmp-fixed
ac_tmp=$tmp
```

**操作步骤**：
1. 创建固定临时目录：`mkdir -p config-tmp-fixed && chmod 777 config-tmp-fixed`
2. 修改 config.status 脚本
3. 重新运行：`./config.status`

---

**问题2：OpenHarmony crypt 函数位置**

OpenHarmony 的 crypt.h 只定义 `struct crypt_data`，crypt 函数在 unistd.h 中声明。

**修复**：修改源码头文件引用
- 文件：`crypt/main.c`, `src/irc_client.c`
- 原代码：
```c
#ifdef HAVE_CRYPT_H
#include <crypt.h>
#else
#include <unistd.h>
#endif
```
- 修复后：
```c
/* OpenHarmony: crypt() is declared in unistd.h, not crypt.h */
#include <unistd.h>
```

---

**问题3：现代 C 编译器兼容性问题**

Clang 15 不支持部分老旧 C 语法：
1. 指针到 int 的转换（需要使用 intptr_t）
2. 三元运算符结果赋值（左值问题）
3. socklen_t 类型不匹配

**修复**：

**irc_client.c:1953** - 指针转换
```c
// 原：connect = (int)data;
// 修复：connect = (int)(intptr_t)data;
```

**irc_server.c:702,748** - 链表删除赋值
```c
// 原：s = (l ? l->next : p->squelch_modes) = n;
// 修复：
if (l) l->next = n;
else p->squelch_modes = n;
s = n;
```

**irc_server.c:341,1092; dcc_net.c:200,298; net.c:790** - socklen_t 类型
```c
// 原：int len;
// 修复：socklen_t len;
```

**dcc_net.c:368** - 链表删除赋值（同 irc_server.c）
```c
// 原：p = (l ? l->next : proxies) = n;
// 修复：
if (l) l->next = n;
else proxies = n;
p = n;
```

**net.c:462** - 取地址右值
```c
// 原：l = &(buff == SB_IN ? s->in_buff_last : s->out_buff_last);
// 修复：
if (buff == SB_IN)
  l = &s->in_buff_last;
else
  l = &s->out_buff_last;
```

---

### 编译成功

**编译产物**：
- `src/dircproxy` (134KB)
- `crypt/dircproxy-crypt` (26KB)

**安装位置**：`~/usr/local/bin/`

**验证**：二进制文件已生成，等待 ELF 签名

---

### 知识提取

**建议编号**：E081（HMDFS mktemp 权限限制）

**错误模式**：
- 类型：平台限制
- 触发条件：使用 `mktemp -d` 创建临时目录
- 系统影响：OpenHarmony/HMDFS 文件系统
- 表现：创建的目录无法写入文件（权限 denied）

**解决方案**：
- 修改 autoconf 生成的 config.status 脚本
- 使用预创建的固定目录替代 mktemp
- 适用于所有 autotools 构建的软件

---

**编译结束**

**最终状态**: built

**成功日期**: 2026-05-29

**备注**: 需要为其他 autotools 软件创建通用解决方案（E081 知识图谱条目）
---

**编译结束**: 2026-05-29 14:13
**最终状态**: published
