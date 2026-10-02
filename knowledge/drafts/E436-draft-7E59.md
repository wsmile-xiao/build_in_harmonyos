# E436 — musl 动态加载器文件名随工具链而异，不能写死单一拼写进跨环境 ELF 断言

> 草稿条目，来源：`rtl-wmbus/1.1.0` 适配 HarmonyOS PC（OHOS aarch64）。
> 状态：draft，待主编审核后 promote 为正式知识条目。

## 错误特征

```text
ELF 断言本地绿、远端 CI 红：PT_INTERP 的 loader 名因工具链而异
```

实际经历（本包 PR #14175 第二次 CI，唯一失败项）：

```text
本地 qemu clang 产物 PT_INTERP=/lib/ld-linux-aarch64.so.1（断言通过）；OHOS CI worker 的 NDK 工具链产物 PT_INTERP=/lib/ld-musl-aarch64.so.1 -> [FAIL] PT_INTERP is the aarch64 loader under /lib
```

## 触发条件

- 分类：`libc`
- 阶段：`testing`（平台/ABI 断言）
- 适用范围：所有在 test_package 里解析被测 ELF 并断言 PT_INTERP 的 OHOS 包；本地工具链与 CI worker 工具链不同的包（几乎全部 OHOS 包）

## 根因分析

musl 的动态加载器文件名不是唯一约定。本地 /opt 交叉工具链产出 /lib/ld-linux-aarch64.so.1，而 OHOS CI worker 的 NDK 驱动产出 /lib/ld-musl-aarch64.so.1。把某一个拼写写进断言，等于把本地工具链的偶然行为固化成跨环境契约。更隐蔽的是：glibc 的 aarch64 加载器也叫 /lib/ld-linux-aarch64.so.1，所以解释器路径本身根本不具 musl/glibc 判别力。

## 解决方案

### 推荐方案

断言 loader 时按语义而非精确文件名匹配：目录前缀 + 架构 + musl 标识三者组合；musl 与 glibc 的判别交给 DT_NEEDED 精确 soname 比对（OHOS 是 libc.so，glibc 是 libc.so.6/libgcc_s.so.1 等）。

**方案说明**：用「/lib/ 前缀 + aarch64 + ld-musl|ld-linux-aarch64」语义匹配替代硬编码文件名。

```c
interp_ok = strncmp(interp, "/lib/", 5) == 0
        && strstr(interp, "aarch64") != NULL
        && (strstr(interp, "ld-musl") != NULL
            || strstr(interp, "ld-linux-aarch64") != NULL);
```

### 禁止做法

- ❌ 不要把单一加载器文件名写进跨环境断言
  - 原因：musl 加载器名随工具链而异；且 glibc 的 aarch64 加载器恰好同名，路径本身无判别力
  - 后果：本地绿、远端红，产生只在 CI 暴露的假失败，浪费一整轮 CI 额度

### 回退方案

若不需要区分 musl/glibc，直接只断言"存在 PT_INTERP 且是 aarch64 加载器"，把 libc 归属完全交给 DT_NEEDED 精确 soname 比对。

## 验证

```bash
对候选路径做谓词单测：/lib/ld-musl-aarch64.so.1 接受、/lib/ld-linux-aarch64.so.1 接受、/lib64/ld-linux-aarch64.so.1（glibc）拒绝、/lib/ld-linux-armhf.so.3 拒绝、/system/bin/linker64（bionic）拒绝；修复后本地 13/13 与 OHOS CI 远端 13/13 同时为绿
```

## 关联条目

- 相关软件包：`rtl-wmbus/1.1.0`
- 同类环境语义问题：`archives/r/rtl-wmbus/1.1.0/notes.md` 第 3.3、7 节
