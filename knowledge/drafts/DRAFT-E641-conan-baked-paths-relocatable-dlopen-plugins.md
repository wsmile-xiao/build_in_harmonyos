# DRAFT-E641 — 编译期烘焙路径 × Conan 包目录搬移：可重定位三件套

- **触发**：上游把插件目录（-DPLUGINSDIR）、数据文件目录（-DSHAREDIR）烘焙成
  编译期绝对路径；pev 的工具在目录打不开时直接 `exit(EXIT_FAILURE)`（text
  默认输出也依赖插件）。
- **Conan 事实**：conan create 的 package_folder 构建期在
  `~/.conan2/p/b/<hash>/p`，成功后搬移到 `p/<hash>/p`——构建期烘焙的任何绝对
  路径（含 rpath）终态必然悬空；patchelf 事后改写在 HMDFS 上被运行期拒绝。
- **三件套**：
  1. 路径回退补丁：`baked_or_relocatable(baked, exe_relative)`——存在即用，
     否则 `/proc/self/exe` 推导 `<exedir>/../<suffix>`，非 Linux 行为不变
     （DESTDIR/staging 同样受益，可上游化）；
  2. dlopen 符号：宿主动态可执行 + `-Wl,--export-dynamic`（musl 从全局作用
     域解析插件未定义符号）；
  3. R26 同名库冲突（设备 /lib64/libpe.so 已存在）：libpe 改静态归档链接进
     各工具（`AR ?= ar` + `$(AR) rcs libpe.a $^`），包内零 .so。
- **反面清单**：不要绝对 rpath 指包目录；不要 patchelf 改写；不要把含
  dlopen 插件的工具做成纯静态可执行（无动态符号表，插件全失联）。
- **验收**：readelf -d 无缓存路径残留；包目录搬移后工具仍可运行并出 json。
- **实例**：`archives/p/pev/0.82`（patches 0002/0003 + conanfile package()）。
