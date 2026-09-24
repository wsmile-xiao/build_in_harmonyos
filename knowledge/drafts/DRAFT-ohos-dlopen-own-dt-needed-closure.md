# DRAFT-ohos-dlopen-own-dt-needed-closure：HarmonyOS/musl 下 dlopen 的对象仅从自身 DT_NEEDED 闭包解析符号：主程序符号、主程序 DT_NEEDED 库、RTLD_GLOBAL 预加载库均不可见，插件必须自带 DT_NEEDED

> Status: **Draft**（待审核 promote）| severity: `3` | category: `platform|linking|runtime` | Updated: ?
> 对应: `knowledge/drafts/DRAFT-ohos-dlopen-own-dt-needed-closure.kv`

---

## 触发面

- trigger_tool: `dlopen / ld-musl / libtool`
- phase: `runtime`

**匹配关键词**：dlopen, symbol not found, Error relocating, DT_NEEDED, RTLD_GLOBAL, RTLD_LOCAL, plugin, module, libtool -module, musl, namespace, nfsidmap_conf_path

## 错误签名（error_signature）

```text
Error relocating .*undefined symbol|Error relocating .*: \w+: symbol not found|symbol not found.*needed by
```

## 根因（root_cause）

三组最小对照实验（同一 aarch64 OHOS 设备，clang 15）： ① 符号定义在主程序自身 → dlopen 失败 `my_global_var: symbol not found`； ② 宿主先 dlopen(libvar.so, RTLD_GLOBAL) 再 dlopen 插件 → 仍失败（RTLD_GLOBAL 不进入后续 dlopen 对象的解析作用域）； ③ 插件自身 DT_NEEDED libvar.so → 成功（get_var()=42）。 即本平台 dlopen 对象的解析作用域 = 自身 DT_NEEDED 闭包 + libc，进程全局作用域不参与。

## 推荐方案（rec_approach: `plugin-links-its-host-library`）


## 验证方式（verification）

```text
libnfsidmap-ldap/2.6.4 实证：修复前 `Error relocating umich_ldap.so: nfsidmap_conf_path: symbol not found`（四个插件全部无法加载， 因它们引用 libnfsidmap 导出的 nfsidmap_conf_path / nfsidmap_config_get / nfs4_get_default_domain）；给四个插件加 DT_NEEDED libnfsidmap.so.1 后 `libnfsidmap: loaded plugin umich_ldap.so for method umich_ldap`、 `nfs4_init_name_mapping(...) = 0`，test_package 4/4 断言 PASS（2026-09-15/16）。
```

## 补充关键词

dlopen 符号解析, DT_NEEDED 闭包, 插件加载失败, RTLD_GLOBAL 无效, 主程序符号不可见, plugin module, libnfsidmap 插件

## 关联

- **关联**：E004（undefined symbol / BIND_NOW）、E019（dlopen/rpath 搜索路径）、 E088（ld-musl 命名空间）、E086（OHOS 平台守卫）；DRAFT-ohos-* 系列。

---

*本文件由 `knowledge/drafts/DRAFT-ohos-dlopen-own-dt-needed-closure.kv` 字段派生生成（补齐 kv↔md 配套）；内容与 kv 一致，待主编审核 promote 后转入 `knowledge/doc/`。*
