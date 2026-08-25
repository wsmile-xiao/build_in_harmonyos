# DRAFT-ohos-libbsd-dep-bypass-method：FreeBSD 工具源码链接 -lbsd 而 libbsd 制品仓无包——移除 -lbsd/bsd 头 include + 内置 strtonum 兼容实现绕过

> Contributor: bsdmainutils-12.1.8 适配 | Status: Draft | Updated: 2026-08-24
> Source: archives/b/bsdmainutils/12.1.8（本地 conan create 实测）

## 现象

FreeBSD/OpenBSD 移植工具（bsdmainutils 的 calendar/ncal）Makefile 硬编码
链接 libbsd：

```
# usr.bin/calendar/Makefile
LIBS = -lbsd
FLAGS = -include sys/uio.h -include bsd/stdlib.h
# usr.bin/ncal/Makefile
FLAGS  = -D_GNU_SOURCE -include bsd/string.h
LIBS  += -ltinfo -lbsd
```

OHOS 构建时报：
- 链接：`ld.lld: error: unable to find library -lbsd`
- 编译：`bsd/stdlib.h` / `bsd/string.h` No such file or directory

原因：libbsd 在主仓库只有 manifest.yaml（status: built）而无 conanfile.py，
制品仓也无 libbsd 包——无法作为 conan 依赖满足。

## 主从根因

- **主根因**：依赖缺口——libbsd 未发布制品仓（主仓库无 conanfile.py），
  conan 依赖无法满足（归轴 1 平台能力边界/依赖生态）。
- **附加 note（非主根因）**：FreeBSD/OpenBSD 源码工具默认按 BSD 环境编写
  （`-lbsd` + `-include bsd/*.h`），实际用到的 libbsd 函数面往往很窄
  （strtonum/arc4random_uniform/strlcpy 等）——逐项核实用例后可用 musl
  自带或配方内置兼容实现替代，不必整体适配 libbsd。

## 与现有知识的关系

- 现有 afsctool 配方（archives/a/afsctool/1.7.3）已有同款先例：补丁
  0002/0003 移除 `<bsd/stdlib.h>` include 与 `-lbsd` 链接（musl string.h
  自带 strlcpy）——但知识库 graph/drafts 均无条目沉淀（查重 strtonum/
  libbsd/bsd 头关键词无覆盖）——本主题填补该空白。
- 现有 E113（u_long/u_int 等 BSD 类型缺失）是**类型缺失**维度，本主题是
  **依赖绕过**维度——机制不同，无覆盖。
- 跨库可复用：任何 FreeBSD/OpenBSD 源码工具链接 -lbsd 而制品仓无 libbsd
  包时（calendar/ncal/look/script 等 BSD 工具移植）都会命中。

## 方案

绕过 libbsd（环境适配，不改上游测试断言）：

1. **移除 -lbsd 链接与 -include bsd/*.h**（配方 build() 内 patch Makefile）：
   ```python
   s = s.replace("LIBS = -lbsd\n", "LIBS =\n")
   s = s.replace("FLAGS = -include sys/uio.h -include bsd/stdlib.h\n",
                 "FLAGS = -include sys/uio.h\n")
   ```
2. **核对源码实际用到的 libbsd 函数面**（grep strtonum/arc4random*/strlcpy
   等）——bsdmainutils 实测仅 `strtonum`（3 处）+ `arc4random_uniform`
   （1 处）：
   - `arc4random_uniform`：musl 自带（OHOS stdlib.h 声明 + 实现，实测
     可链接）——无需处理
   - `strtonum`：musl 无——配方内置 OpenBSD 语义兼容实现
     （`strtoll` + errstrp 错误描述 "invalid"/"too small"/"too large"，
     追加到 calendar SRC 编译单元）
3. **处理 bsd 头 include 牵连**：`<login_cap.h>`（libbsd 提供，仅 include
   未调用）→ 移除；`-include bsd/string.h` → 移除。

## 验证

- 本地 conan create（bsdmainutils/12.1.8）通过：calendar + ncal 构建成功，
  Package created + test_package（calendar -h usage + ncal 无参数真实运行
  当月日历）PASSED。
- patch 前后对照：patch 前链接报 `-lbsd` 找不到、编译报 bsd/ 头缺失；
  patch 后 calendar/ncal 全部编译链接通过。
