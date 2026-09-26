# sideretro

sideRETRO — 检测体细胞（somatic）de novo retrocopy 插入的 C 流程工具。

## 简介

sideRETRO 是一个用于检测体细胞与多态性 processed pseudogene / retrocopy 插入的
生物信息学流程，编译产物为 `sider` 命令行工具，提供三个子命令：

- `process-sample`（ps）：提取与 retrocopy 事件相关的比对
- `merge-call`（mc）：发现并注释 retrocopy
- `make-vcf`（vcf）：生成包含注释 retrocopy 的 VCF 文件

## 构建系统

- Meson（meson.build + meson_options.txt），C99

## 依赖

| 依赖 | 版本 | 用途 |
|------|------|------|
| zlib | 1.3.1 | 压缩 |
| sqlite3 | 3.49.1 | 数据库 |
| htslib | 1.24-r0 | BAM/SAM/CRAM 处理 |
| check | 0.15.2 | 上游单元测试框架（测试期） |

依赖均通过 Conan 制品仓发布（ohpcd remote）。

## OHOS 适配要点

1. **ninja 运行环境**：OHOS 上的 ninja 是 C++ 动态链接 ELF，运行时需
   `libc++_shared.so`。conanfile 的 `_build_environment()` 注入 SDK
   `.../llvm/lib/aarch64-linux-ohos/c++` 到 `LD_LIBRARY_PATH`，否则 meson 报
   "Could not detect Ninja v1.8.2 or newer"。
2. **libc 兼容**：上游使用 glibc 专有 `secure_getenv()`，OHOS libc 未声明该
   函数导致隐式声明编译错误。补丁改用 `getenv()`（sideRETRO 非 setuid，语义
   等价），未引入 `__OHOS__` 平台宏。
3. **/tmp 只读**：OHOS `/tmp` 只读（errno=30），上游 check 单元测试硬编码
   `/tmp/ponga*` 临时文件路径导致 49 项失败。补丁将路径相对化为 `./ponga*`
   （meson test 工作目录可写）。
4. **打包方式**：`package()` 直接复制 build 产物 `src/sider`，不使用
   `Meson.install()`——OHOS 上 install 重写 RUNPATH 会破坏 `.codesign` 签名，
   导致运行时 EPERM（Operation not permitted）。

## 上游测试

- 框架：libcheck（check 单元测试）
- 数量：185 项（30 个测试模块汇总为单一 `check_sider` 可执行文件）
- 结果：OHOS 实测 185/185 全绿（随 `conan create` 的 `meson.test()` 执行）

## 许可

GPL-3.0-or-later（上游 The Linux Foundation / galantelab）
