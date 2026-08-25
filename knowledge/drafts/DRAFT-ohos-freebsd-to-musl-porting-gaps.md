# DRAFT-ohos-freebsd-to-musl-porting-gaps：FreeBSD/OpenBSD 源码移植 OHOS musl 的常见缺项清单——逐项 stub/替换/移除

> Contributor: bsdmainutils-12.1.8 适配 | Status: Draft | Updated: 2026-08-24
> Source: archives/b/bsdmainutils/12.1.8（本地 conan create 实测）

## 现象

FreeBSD/OpenBSD 源码（bsdmainutils 的 calendar.c/ncal.c）在 OHOS（musl
libc）编译时报一连串"未声明标识符/隐式函数声明"错误，-Werror 下直接失败：

```
calendar.c:128:7: warning: call to undeclared function 'pledge'
calendar.c:195:9: error: use of undeclared identifier 'LOGIN_SETALL'
calendar.c:195:24: error: use of undeclared identifier 'LOGIN_SETLOGIN'
ncal.c:30:10: error: expected ')'          // __FBSDID(...)
ncal.c:547:27: error: use of undeclared identifier 'D_MD_ORDER'
ncal.c:1120:12: error: incompatible integer to pointer conversion ... 'tgetstr'
```

## 缺项清单与处理（逐项实测）

| # | BSD 私有物 | 来源 | musl 状态 | 处理 |
|---|-----------|------|----------|------|
| 1 | `__FBSDID("...")` | FreeBSD RCS ID 宏（sys/cdefs.h） | musl 无 | 移除该行 |
| 2 | `pledge("...", NULL)` | OpenBSD 沙箱承诺调用 | musl 无 | stub 为 0（`if (0 == -1)` 恒假，不进入 err 分支） |
| 3 | `setusercontext` + `LOGIN_SETALL ^ LOGIN_SETLOGIN` | login_cap 库函数/宏 | musl 无 | 替换为等价 `setuid(pw->pw_uid)`（doall 模式 fork 子进程按 uid 切换，Linux 语义一致） |
| 4 | `<login_cap.h>` | libbsd 提供 | musl 无 | 仅 include 未调用 login_* 函数 → 整体移除 |
| 5 | `D_MD_ORDER` | musl langinfo.h 无此 FreeBSD 扩展宏 | musl 无 | 固定 m/d 日期顺序（`d_first = 0`——C locale 默认） |
| 6 | `<term.h>` + `tgetent`/`tgetstr` | termcap 高亮 | OHOS 无 tty（isatty 恒假） | 移除 include + termcap 高亮初始化块（term_so/term_se 保持 NULL） |
| 7 | `u_long` 等 BSD 旧类型名 | BSD 头文件 | musl 无 | 见 E113（已覆盖）——本主题不重复 |

## 主从根因

- **主根因**：FreeBSD/OpenBSD 源码依赖 BSD 私有 API/宏/头（musl 无对应
  物）——平台 libc 差异（归轴 1 平台能力边界）。
- **附加 note（非主根因）**：BSD 私有符号常为**可选/防御性代码**——
  沙箱承诺（pledge）、终端高亮（termcap）、登录上下文（setusercontext）
  在 OHOS 上要么无对应物、要么无 tty/无沙箱语义——可安全 stub、替换为
  POSIX 等价物或整体移除，**无需完整实现 BSD 语义**。判断依据：grep
  确认该符号是否在关键路径（如 pledge 只在 main 开头、termcap 只在
  isatty 分支内）。

## 与现有知识的关系

- 现有 E113（u_long/u_int/u_char/caddr_t BSD 类型缺失）覆盖**类型缺失**
  维度——本主题覆盖 **API/宏/头文件缺项**维度，互不重复。
- 现有 E063（-Werror + implicit-function-declaration）是通用编译告警
  升级问题——本主题是具体缺项清单，可配合使用。
- 跨库可复用：任何 FreeBSD/OpenBSD 源码移植 OHOS（calendar/ncal/
  look/script/banner 等 BSD 工具，及含沙箱承诺/终端高亮/login_cap 的
  项目）都会命中其中多项。

## 方案

配方 build() 内逐项 patch（环境适配，不改上游测试断言）：

```python
import re
# __FBSDID：移除整行
s = re.sub(r'__FBSDID\("[^"]*"\);\n', '', s)
# pledge：stub 为 0
s = re.sub(r'pledge\("[^"]*", NULL\)', '0', s)
# setusercontext → setuid（LOGIN_SETALL/LOGIN_SETLOGIN 宏随之消失）
s = re.sub(
    r'setusercontext\(NULL, pw, pw->pw_uid,\s*LOGIN_SETALL \^ LOGIN_SETLOGIN\)',
    'setuid(pw->pw_uid)', s)
# login_cap.h：移除 include
s = s.replace("#include <login_cap.h>\n", "")
# D_MD_ORDER：固定 m/d 顺序
s = s.replace("d_first = (*nl_langinfo(D_MD_ORDER) == 'd');",
              "d_first = 0; /* musl 无 D_MD_ORDER */")
# termcap 高亮块：整体移除（term_so/term_se 保持 NULL）
s = s.replace("""if (isatty(STDOUT_FILENO) && tgetent(tbuf, NULL) == 1) {
    b = cbuf;
    term_so = tgetstr("so", &b);
    term_se = tgetstr("se", &b);
}""", "/* OHOS 无 tty——termcap 高亮不生效 */")
```

## 验证

- 本地 conan create（bsdmainutils/12.1.8）通过：calendar + ncal 构建
  成功，Package created + test_package PASSED。
- patch 前后对照：patch 前 6 类缺项逐一报错；patch 后全部编译链接通过
  （calendar -h usage、ncal 无参数真实运行当月日历均正常）。
