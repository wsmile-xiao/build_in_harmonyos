# E548（草稿）OHOS 工具链默认不设 SONAME → 消费者 DT_NEEDED 记相对路径 → dlopen 失败

- **现象**：共享构建下格式插件 dlopen 失败（`cannot open shared object`），`readelf -d 插件.so | grep NEEDED` 显示对主库的依赖是相对路径而非库名。
- **根因**：OHOS clang/lld 默认不添加 `-Wl,-soname`（Linux 工具链会从输出名自动派生 soname）。消费者链接无 SONAME 的共享库时，链接器把被依赖库的相对路径原样写入 `DT_NEEDED`；运行期 dlopen 按进程 CWD 相对解析，包布局变动后即失败。
- **解法**：配方 `generate()` 注入
  `CMAKE_SHARED_LIBRARY_SONAME_CXX_FLAG=-Wl,-soname,` / `C_SHARED_LIBRARY_SONAME_C_FLAG` 同名 C 旗标，恢复标准 soname 机制（全部共享库获得 `lib<name>.so` 形式 SONAME，DT_NEEDED 回归库名）。
- **验证**：`readelf -d libopenbabel.so.8 | grep SONAME` 有条目；插件 DT_NEEDED 为库名；92+ 插件 dlopen 成功（上游 ctest 348/348）。
- **来源**：openbabel 3.2.1 OHOS aarch64 适配，PR #14369。
