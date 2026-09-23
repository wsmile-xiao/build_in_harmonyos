# DRAFT-cconv-0.6.3-rindex-strrchr：OHOS libc 无 BSD 遗留函数 rindex

> Contributor: pc1-6 | Status: Draft | Updated: 2026-09-05
> Source: cconv 0.6.3 HarmonyOS PC adaptation（main.c usage()）
> 对应：knowledge/drafts/DRAFT-cconv-0.6.3-rindex-strrchr.kv

## 现象

cconv 0.6.3 在 OHOS PC（aarch64-linux-ohos）构建时链接失败：

```text
ld.lld: error: undefined symbol: rindex
>>> referenced by main.c:40 (.../main.c:40)
>>>               cconv-main.o:(usage)
>>> did you mean: index
>>> defined in: .../sysroot/usr/lib/aarch64-linux-ohos/libc.so
```

编译期仅有 `include the header <strings.h> or explicitly provide a declaration
for 'rindex'` 的隐式声明警告，链接期才暴露符号缺失。

## 根因

- 上游 main.c 使用 BSD 遗留函数 `rindex(s_program, '/')` 查找最后一个 `/`。
- `rindex` 是 POSIX 已废弃函数，语义与标准 `strrchr` 完全等价（自右向左
  查找字符，未找到返回 NULL）。
- OHOS libc（musl 系裁剪）未导出 `rindex` 符号，而 `index` 仍存在
  （链接器提示 "did you mean: index"），说明是 OHOS libc 对 BSD 遗留
  符号的裁剪，不是全局无兼容层。

## 方案

将 `rindex(s, c)` 替换为 `strrchr(s, c)`：

```c
- char *p = (char *)rindex(s_program, '/');
+ char *p = (char *)strrchr(s_program, '/');
```

`strrchr` 在 `<string.h>` 中声明（main.c 已包含），无需新增头文件。
两者参数、返回（含 NULL 语义）完全一致，为 1:1 等价替换。

## 验证

```bash
# 修复前：链接失败
make -j1  # ld.lld: error: undefined symbol: rindex

# 修复后：链接通过，构建成功
make -j1  # 生成 cconv 二进制 + libcconv.so/a

# 功能验证（上游语料）
./cconv -f UTF8-CN -t UTF8-TW < test_s2t   # rc=0，输出正确繁体
./cconv -f UTF8-TW -t UTF8-CN < test_t2s   # rc=0，输出正确简体
```

## 适用边界

- 适用于所有在 OHOS PC 上链接期报 `undefined symbol: rindex` 的 C/C++ 库。
- 替换目标必须是 `strrchr`（标准等价），不可换成 `strchr`（语义不同：
  自左向右查找）。
- 若源码同时依赖 `strings.h` 中的 `bcmp/bcopy/bzero` 等同类裁剪符号，
  需逐一按标准替代（memcmp/memmove/memset），本条目仅覆盖 rindex。

## 反例与限制

- 反例：不适用 `index`（OHOS libc 存在该符号，无需替换）。
- 限制：若上游代码用 `rindex` 作为函数指针或宏重定义，需单独评估；
  本条目针对普通函数调用场景。

## 与现有知识的关系（查重证据）

检查范围：knowledge/graph（E001~E540）+ knowledge/drafts + 只读快照
（cconv-0.6.3-r01-20260905T083629Z，HEAD 29f36237，540 条 E*.kv + 170 条草稿）。
检索词：rindex / strrchr / strings.h / BSD legacy / undefined symbol。
命中：E011/E175（umask 077 config.status）、E007（config.guess）、E116
（Automake::Config.pm）、E248（make 重生成 automake）、E460（无 configure）
等均为等价命中（路径 A）；rindex 符号缺失**无任何等价条目或草稿**，
且跨库可复用（任何 BSD 移植代码均可能命中），判定为路径 B 新草稿。
