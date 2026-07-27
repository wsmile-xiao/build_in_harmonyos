# fontconfig 2.18.1.1 编译笔记（HarmonyOS PC）

## 本版改了什么

**仅一处**：依赖从 `expat/2.8.2` 升到 `expat/2.8.2.1`。配方其余部分与 2.18.1 完全一致。

## 为什么需要这个修复

`expat/2.8.2` 的 `.so` **无 SONAME**（其配方用 conan `CMakeToolchain`，`os=OHOS` 下不生成 SONAME）。
链接器遇到无 SONAME 的被链库时，会把该库的**绝对路径**写进本包的 DT_NEEDED：

```
libfontconfig.so.1 → NEEDED /…/.conan2/p/expat9fb72708ad085/p/lib/libexpat.so
```

于是本包的已发布二进制**不可重定位**——换机器或清 cache 后 expat 落到别的包目录哈希，
消费方即在加载期报 `Error loading shared library` 与一串 `XML_* symbol not found`。

`expat/2.8.2.1` 改用裸 cmake + `ohos.toolchain` 后正常生成 SONAME，本版重新链接即可得到
可重定位的 DT_NEEDED（记 soname 而非路径）。

## 版本号

按 R37：`2.18.1` 已发布到制品仓，依赖变更即配方变更，须递增后缀 → `2.18.1.1`。
