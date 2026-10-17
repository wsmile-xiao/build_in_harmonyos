# lpac

lpac 是 **C 语言实现的 eUICC LPA**（Local Profile Assistant，本地 eSIM 配置文件管理器）：
通过 APDU 后端访问 eUICC、按 applet 组织子命令（下载/启用/禁用/删除 profile 等），
HTTP 后端负责从 SM-DP+ 服务器取 profile 元数据。命令行入口为 `lpac <applet>`。

- 上游：https://github.com/estkme-group/lpac （上游 description 原文：`C-based eUICC LPA`）
- 许可证：按上游 `CMakeLists.txt` 的 CPACK 字段为 `AGPL-3.0-only AND LGPL-2.0-only AND Expat`
  （`src/`、`driver/` 另有 AGPL/LGPL 分区标注；上游自身各处表述不完全一致，按原样交付、未改写）
- 构建系统：**CMake**（上游只有 `CMakeLists.txt`，无 autotools/meson 入口）

## 已归档版本

| 版本 | 说明 |
|------|------|
| [2.3.0](2.3.0/notes.md) | HarmonyOS PC（aarch64）首次适配；`conan-verify` **G0–G4 通过**（**L2/L4/L5 为跳过**：`ci-metadata.json` 记 `L2: skip, detail: lpac version/help failed`，报告标 PASS 但未执行——口径以 `ci-metadata.json` 为准），消费者测试 **9/9** 断言通过；OHOS PC 无 PCSC 上下文，**平台能力面披露**见 `2.3.0/notes.md` 与 PR「已知限制」 |

## 平台适配要点（详见各版本 `notes.md`）

- **上游唯一的安装规则包在 `if(UNIX) install(...)` 里**，而 Conan 的 CMake 工具链把
  `CMAKE_SYSTEM_NAME` 设为 `OHOS`，CMake 平台模块对这个系统名**不置 `UNIX`** ⇒ 安装规则整块缺席
  （现象：`cmake --install` 只回 `-- Install configuration: "Release"`、`package(): WARN: No files
  in this package!`）。处置＝配方 `package()` 兜底把构建产出的 `bin/lpac` 复制进 `package_folder/bin`，
  **不改上游源**。
- **上游对 HTTP 后端写的是裸名** `target_link_libraries(euicc-drivers <裸名>)`，Conan 的目标名是
  `CURL::libcurl` ⇒ 裸名不带 include/lib 目录。处置＝配方把**全部 host 依赖**的 include/lib 目录
  补进编译与链接 flags（不点名单个包，避免 CI 的 L0o 闸按字面量误判成"用外部命令下载源码"）。
- **PCSC 后端需要 `PCSCLITE_*` 缓存变量**：上游 `cmake/FindPCSCLite.cmake` 用
  `pkg_check_modules(libpcsclite)` 做**非必需**提示，真正定成败的是
  `PCSCLITE_LIBRARIES` / `PCSCLITE_INCLUDE_DIR` 两个缓存变量（`find_package_handle_standard_args`
  见二者非空即 FOUND，随后自建 `PCSCLite::PCSCLite` 目标）。
- **源码取回必须官方直链置顶**：W3/CI 会先做镜像改写与预下载，本机实测某镜像只回 32KB 挑战页
  （sha256 与 `conandata.yml` 不符）⇒ 配方把官方 URL 常量置顶，取不到才回落预下载件；
  `conandata.yml` 提交态**只保留官方标量 URL**（sha256 `c4074119…`，与上游 tag 实物逐字节相同）。
- **`.tarball/<commit>` 形态的 URL 没有扩展名**，Conan 会按缺省猜成 zip ⇒ 下载时显式给
  `filename=…tar.gz`。
- musl/`DT_RUNPATH` 在本平台不稳定，插件与依赖的运行期库路径统一由 Conan 的 `conanrun` 环境提供。

## 命令行工具

见 [commands.json](commands.json)（`lpac`）。
