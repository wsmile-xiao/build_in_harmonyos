# E257 — [简短错误描述]

## 错误特征
[描述触发此错误模式的典型日志输出或症状]

## 触发条件
- 构建系统: [autotools/cmake/meson/...]
- 阶段: [configure/make/install/...]

## 根因分析
[详细解释错误的根本原因]

## 解决方案

### 推荐方案
[描述修复步骤]

### 禁止做法
- ❌ [描述不应采取的操作]

## 验证
```bash
[验证修复的命令]
```

## 关联条目
- 相关: [E???]

## Evidence (dbus-glib/0.114, device 2026-08-28)
- Crash: upstream test /specialized-types/ao/GSList SIGSEGV only in the
  shared build; identical C reproducer passes when linked against
  libdbus-glib-1.a and crashes when linked against libdbus-glib-1.so.
- Offline backtrace (no ptrace): main -> g_value_unset (exe glib copy)
  -> slist_free (dbus-gvalue-utils.c:1303, inside the .so) ->
  g_object_unref (embedded second glib copy) -> PC=0 (NULL class vfunc).
- Registry proof: `conan install --requires=glib/2.88.0
  -o glib/*:shared=True` -> "Missing prebuilt package" (only the static
  binary is published).
- Fix: recipe builds --disable-shared --enable-static by default and
  raises ConanException if shared=True while glib lacks libglib-2.0.so /
  libgobject-2.0.so (guard copied from archives/a/avahi-glib/0.9_rc5).
- Related log: /storage/Users/currentUser/tmp/dbusglib-asan-spec.log,
  repro sources $HOME/tmp/dbusglib-repro-ao.c + dbusglib-trace.c.
