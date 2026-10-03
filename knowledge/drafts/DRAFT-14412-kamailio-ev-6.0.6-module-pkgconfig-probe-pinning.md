# DRAFT-14412 — kamailio 模块外部依赖的 pkg-config 探测变量按模块而异，需显式钉死以免构建机同名库劫持

- 条目主题：kamailio（经典 Makefile 体系）各模块 Makefile 的**外部依赖探测变量名逐模块不同**，
  在交叉编译/制品仓依赖场景下必须显式钉死，否则链接可能落到构建机同名系统库上。
- 状态：草稿（待知识库主编审核，拟提升编号 Exxx）
- 关联：kamailio-ev 6.0.6 适配（archives/k/kamailio-ev/6.0.6/）；同类先例 kamailio-tls / kamailio-gcrypt / kamailio-xml / kamailio-extras

## 适用场景

kamailio 源码树内模块的 `src/modules/<mod>/Makefile` 普遍带这样一段（以 evapi 为例，原文）：

```make
ifeq ($(CROSS_COMPILE),)
	BUILDER = $(shell which pkg-config)
ifneq ($(BUILDER),)
	PKGLIBUV = $(shell $(BUILDER) --exists libev > /dev/null 2>&1 ; echo $$? )
ifneq ($(PKGLIBUV),0)
	BUILDER =
endif
endif
endif
ifneq ($(BUILDER),)
	DEFS += $(shell $(BUILDER) --cflags libev)
	LIBS += $(shell $(BUILDER) --libs libev)
else
	DEFS += -I$(LOCALBASE)/include -I$(SYSBASE)/include
	LIBS += -L$(LOCALBASE)/lib -L$(SYSBASE)/lib -lev
endif
```

三个容易踩的坑：

1. **变量名逐模块不同**：`tls` 用 `SSL_BUILDER`/`CRYPTO_BUILDER`，`gcrypt` 用
   `GCRYPT_BUILDER`，而 `evapi` 用的是**裸 `BUILDER`**。套用同族配方变量名（以为都叫
   `<NAME>_BUILDER`）会钉死失败，且**不报任何错**——命令照跑，只是走了另一条分支。
2. **探测失败会静默回退**：`pkg-config --exists <dep>` 失败时模块 Makefile 自己把变量
   清空，改走 `LOCALBASE` 回退。所以"依赖包是否提供 `.pc`"直接决定链路落点
   （`libev/4.33` 就不提供 `.pc`，包内只有 `include/ev.h` 与 `lib/libev.so`）。
3. **构建机同名库会劫持**：若构建机装有同名系统库且带 `.pc`，探测命中并取到构建机
   路径 → 交叉编译链接到宿主库（或链接失败）。

## 检测手段

```bash
# 1) 打印实际编译/链接行，检查依赖路径是否出现
make -C src -n -B modules modules=modules/<mod> -j1 LOCALBASE=<dep-pkg> extra_defs="<...>" \
  | grep -E "LD .*<mod>\.so"

# 2) 可证伪的劫持实验：PATH 前置一个假 pkg-config，对照传/不传钉死变量
mkdir -p /tmp/fakebin && cat > /tmp/fakebin/pkg-config <<'EOF'
#!/bin/sh
case "$1" in
  --exists) exit 0 ;;
  --cflags) echo "-I/FAKE_HIJACK/include" ;;
  --libs)   echo "-L/FAKE_HIJACK/lib -lev" ;;
esac
exit 0
EOF
chmod +x /tmp/fakebin/pkg-config
PATH=/tmp/fakebin:$PATH make -C src -n -B modules modules=modules/<mod> -j1 LOCALBASE=<dep-pkg>   # 会被劫持
PATH=/tmp/fakebin:$PATH make -C src -n -B modules modules=modules/<mod> -j1 BUILDER= LOCALBASE=<dep-pkg>  # 钉死
```

> 注意：假 pkg-config 所在路径**不能含空格**，否则 `$(shell ...)` 展开会被词分割打断，
> 实验会因无关原因失败（本次实测曾踩到，改用无空格路径后结论才成立）。

## 实测结论（kamailio-ev 6.0.6 / OHOS aarch64）

| 实验 | 链接行实得 | 判定 |
|------|-----------|------|
| A：不传 `BUILDER=` | `-L/FAKE_HIJACK/lib -lev` | ❌ 被构建机 pkg-config 劫持 |
| B：传 `BUILDER=` | `-L<libev 包>/lib -L/lib -lev` | ✅ 钉死到 conan 依赖包 |

反向核验：本机 `pkg-config --exists libev` 为"未找到"（无系统 libev.pc），即同一命令
在两种构建机上落点不同 —— 这正是必须显式钉死的原因。

## 处理策略（推荐姿势）

1. 读模块 Makefile 原文，确认探测变量名（逐模块核对，勿套用同族配方）。
2. make 命令行显式钉死：依赖包**无** `.pc` 时直接 `VAR=` 置空以跳过探测分支；
   依赖包**有** `.pc` 时（如 gcrypt 的 `libgcrypt.pc`）传 `VAR="pkg-config <dep>"`
   并令 `PKG_CONFIG_PATH` 指向依赖包。
3. `LOCALBASE` / `CPATH` / `LIBRARY_PATH` 三处均指向 conan 依赖包目录，使探测与编译
   链接两条路径都只可能命中依赖包。
4. 用 `make -n` 把实际编译/链接行留档（本仓先例：kamailio-{tls,gcrypt,extras} 的 notes
   均贴链接行），把"应该没问题"变成"有原始输出"。

## 关联条目

- E525 / E074：OHOS SELinux 禁止用户进程创建 FIFO → GNU make jobserver 失效，全流程 `-j1`
- 同族先例：`archives/k/kamailio-gcrypt/6.0.6/notes.md` §4.3（三重钉死）、
  `archives/k/kamailio-tls/6.0.6/notes.md`（`SSL_BUILDER=` 置空）、
  `archives/k/kamailio-ev/6.0.6/notes.md` §4.3（本条目出处 + A/B 劫持实验）
