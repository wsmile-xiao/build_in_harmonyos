# DRAFT-audacious-buildsys-in-source-static-chain — audacious buildsys.mk 适配三事实（源内构建/无 check/LIBS 顺序）

> **Contributor**: Awstme | **Status**: DRAFT | **Updated**: 2026-09-02
> **Severity**: blocking (2) | **Category**: build-system / autotools / linking / conan / ohos
> **Audience**: audacious 家族（libaudclient/audacious）OHOS 适配者；一切"自研 buildsys + 静态依赖链"配方维护者

## 触发（trigger）

- libaudclient 3.5-rc2 发布 tarball：audacious 自研 `m4/buildsys.m4` +
  `buildsys.mk.in`（非 automake），自带预生成 configure 与检入的顶层 Makefile。
- Conan basic_layout（out-of-source build 目录）+ OHOS static-only 依赖制品。

## 症状（symptom）

1. make 阶段：`make: *** No targets specified and no makefile found.  Stop.`
   （build-release/ 目录为空，检入的顶层 Makefile 不在那里）。
2. 上游测试审计：任何 check 目标/TESTS/check_PROGRAMS/check-local 均不存在。
3. 静态链下 make：`undefined reference to 'g_type_*'/'g_object_*'` 等
   glib 系符号无法闭合（libdbus-glib-1.a 在 glib 归档之后）。

## 机制（root cause）

1. **仅源内构建**：检入的顶层 `Makefile` 直接 `include buildsys.mk`，
   `buildsys.mk.in` 无 VPATH 支持——configure 必须在源内跑，make 必须在
   生成 buildsys.mk 的同一目录跑。Conan basic_layout 的 out-of-source
   build 目录必然失败。
2. **无 check 目标**：buildsys.mk.in 不定义 check；四个 Makefile 与
   configure.ac 均无 TESTS/check_PROGRAMS/check-local/测试宏；无 tests/
   目录 → 上游无自动化测试（HMBS_UPSTREAM_TEST_RESULT status=no_tests 口径）。
   另：`all → depend → pre-depend` 每轮 make 都进 `src/audacious`，但其
   重建规则的 `DBUS_BINDINGS_SOURCES` 从未被 AC_SUBST（前置为空），
   tarball 自带 dbus-client-bindings.h 存在即永不重建——dbus-binding-tool
   只被 configure 的 AC_PATH_PROG 存在性门禁要求。
3. **静态链 LIBS 顺序**：链接规则
   `${LD} -o $@ $$objs ${LIB_LDFLAGS} ${LDFLAGS} ${LIBS}` 将 LIBS 全部置于
   目标对象之后；GNU ld 单遍左到右解析。上游
   `src/libaudclient/Makefile:23-24` `LIBS += ${GLIB_LIBS} ${DBUS_LIBS}`
   （glib 归档在前）→ 静态 glib 无法闭合 libdbus-glib-1.a 的 `g_*` 引用。
   共享链不受影响（本包 .so 内联静态链，DT_NEEDED 仅 libexpat.so）。

## 修复（rec）

```python
def layout(self):
    self.folders.source = "."
    self.folders.build = "."
    self.folders.generators = "conan"
```

补丁 0003 交换 Makefile LIBS 追加顺序（DBUS_LIBS 先、GLIB_LIBS 后——
消费者先于依赖）；上游测试按 no_tests 口径申报，消费者侧 test_package
以 dlopen(soname) + 全量 71 EXPORT 符号 dlsym + 9 API 取址 + dladdr
共 82 断言覆盖（OHOS 无 D-Bus session bus 下的最大可执行范围）。

## 查重（dedup）

- E156（fbida Autoconf.mk 自研构建）/E097（bearssl SingleUnix.mk）/
  E095（lzip custom configure）/E204（libvpx configure.sh）：同类"非标准
  构建系统"家族，但均未覆盖 audacious buildsys.mk 的三个具体事实，
  也无"自研 buildsys LIBS 追加顺序"的链接语义。
- E234（--with-pic/fPIC/AutotoolsToolchain）：不同问题面。
- 全库 grep `audacious`/`buildsys.mk`/`单遍`/`左到右`：零命中。

## 证据（evidence）

- 设备实跑：run5（basic_layout）→ "No targets specified and no makefile
  found" → run6（layout 源内 + CONFIG_SHELL 置空）make 推进；静态链顺序
  问题在本地静态勘察（buildsys.mk.in:205 + Makefile:23-24）与补丁前后
  设备链接结果（run2 前后 undefined `g_*` → 全链闭合）双重实锤。
- 上游审计 grep 在配方 build() 内执行，conan create 日志留痕（零命中）。
- 配方提交：07662cd5f0（in-source layout）、9fb29e3185；
  PR https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos/merge_requests/7671
  （CI #36622 全门禁通过）。

## 关系

- similar_to: E156、E097、E095、E204、E234
