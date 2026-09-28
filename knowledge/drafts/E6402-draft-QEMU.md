# DRAFT-E6402: OHOS conan 包执行不可用——meson 不写 $ORIGIN RUNPATH（rc=127）+ 未签名多二进制 ELF 拒绝加载（rc=126 EPERM）

- **触发实例**: qemu 11.1.1 OHOS armv8 适配（build_in_harmonyos archives/q/qemu/11.1.1，2026-09-22，分支 feat/qemu-11.1.1）
- **错误签名**: `Error loading shared library libpixman-1.so.0` / `cannot open shared object file` / `Operation not permitted`（rc=126/127）
- **类别**: linking, packaging, ohos, hmdfs
- **严重度**: 1（blocking——编译全部通过但产物不可执行，test_package 实跑必挂）

## 症状（可复现）

1. 编译、安装全部成功后，执行打包产物报
   `Error loading shared library libpixman-1.so.0: cannot open shared object file`（rc=127）——
   meson 只记录构建期 -L 路径，不写 $ORIGIN，包迁移到 conan package folder 后依赖库定位失败。
2. RUNPATH 修好后执行仍报 `Operation not permitted`（rc=126）——OHOS 内核拒绝加载
   无有效 `.codesign` 签名段的 ELF。
3. QEMU 是大型应用包：bin/libexec/lib 下 50+ 个 ELF（含 qemu-system-riscv64/qemu-img/qemu-nbd/
   qemu-io 与 .so），逐个手签不现实，需在 package() 中批量处理。

## 根因

两个独立根因叠加：① meson 的 RPATH 语义（构建期 -L 绝对路径，无 $ORIGIN）与 conan
"构建目录 ≠ 包目录"的模型冲突；② OHOS 内核的强制 ELF 签名策略（E077 四步流程的适用场景）。
两者都不在源码层，只能在 conan 配方的 generate()/package() 层解决。

## 方案（已验证，qemu 11.1.1 实测通过）

1. **generate() 注入 RUNPATH**：对每个动态依赖（pixman/glib/zlib）
   `Environment.append("LDFLAGS", "-Wl,-rpath,<dep.package_folder>/lib")`，
   写入独立 env 脚本 `qemu_env`（不用 conan 聚合脚本 conanbuild）。
   链接期生效，产物 RUNPATH 直指各依赖 lib 目录。
2. **package() 批量签名** `_sign_all_elfs()`：递归扫描 `bin/`、`libexec/`、`lib/`（含 `lib/**/*.so*`），
   按 `\x7fELF` magic 判定（跳过 .a/数据文件/符号链接，去重），对每个 ELF 执行 E077 流程：
   `llvm-objcopy --remove-section .codesign <t>` →
   `binary-sign-tool sign -inFile <t> -outFile <t> -selfSign 1`。
   签名工具缺失时直接抛 ConanException（fail-fast，不静默跳过）。

## 验证

```bash
readelf -d bin/qemu-img | grep -E 'RUNPATH|NEEDED'   # RUNPATH 指向 conan 依赖 lib 目录
bin/qemu-img --version          # 输出 11.1.1（rc=0）
bin/qemu-system-riscv64 --version
llvm-readelf -S bin/qemu-img | grep codesign          # 签名段存在
```

qemu 11.1.1 实测：test_package 5/5 通过（4 个 --version + qcow2 create/info 往返），
conan-verify G2 通过（日志见 archives/q/qemu/11.1.1/reports/w3-local-ci.log）。

## 禁止策略

- 依赖注入指向共享 `/usr/local`（R49/E524：CI worker 与本地共享文件系统，互相污染）。
- 用 `os.access(path, os.X_OK)` 探测 work 目录可执行性（HMDFS 忽略 chmod、权限固定 660，X_OK 恒 False）。
- 跳过签名只补可执行位（内核按签名段判定，chmod 无效）。

## 关联条目

- E077：ELF 签名四步通用流程（本条目的签名部分直接引用其顺序约束）。
- E6401（同任务草稿）：meson×OHOS 构建期修复——本条目是其后置（构建通过后才暴露执行问题）。
