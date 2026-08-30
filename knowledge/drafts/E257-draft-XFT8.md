# E257 — OHOS 加载器：LD_LIBRARY_PATH 压过 DT_RPATH，且符号链接别名无法解析

## 错误特征

```
configure-ohos: error: cannot run C compiled programs.
If you meant to cross compile, use `--host'.
```

config.log 里的第一条真实错误由加载器给出：

```
Error loading shared library libfontconfig.so.1: (needed by ./conftest)
```

而文件确实存在、`SONAME` 正确、`.codesign` 段也在——只看文件系统层面会误判。

## 触发条件

- 构建系统: autotools（也适用于任何在设备上执行刚编译出的二进制的场景）
- 阶段: configure 运行探测 / test_package / 运行期 dlopen
- 前提: 依赖以共享库发布，其版本化别名是指向实体文件的符号链接

## 根因分析

本机（HongMeng Kernel 1.12.0）musl 加载器的三条实测语义：

1. `LD_LIBRARY_PATH` **被识别**，但一旦设置，其查找**压过**二进制内嵌的 `DT_RPATH`。
2. 依赖包里的版本化别名（`libfoo.so.1 -> libfoo.so.1.2.3`）是符号链接，
   加载器在 HMDFS 上无法经别名名解析。
3. 于是"把 `LD_LIBRARY_PATH` 指向依赖包 lib 目录"这个在 Linux 上正确的做法，
   在这里会让**本来可用的 rpath 查找整体失败**。

同一二进制的三组对照：

| 条件 | 结果 |
| --- | --- |
| 不设 `LD_LIBRARY_PATH`，仅 `-Wl,--disable-new-dtags,-rpath,<实体化视图>` | rc=0 |
| `LD_LIBRARY_PATH=<依赖包目录>`（含符号链接别名）+ 同样 rpath | **rc=127** |
| `LD_LIBRARY_PATH=<实体化视图>` + 同样 rpath | rc=0 |

本条据实收窄 E088/E186/E266 的旧读法：`LD_LIBRARY_PATH` 不是"被忽略"，
而是"优先级过高，且指向不可解析目录时导致查找整体失败"。

## 解决方案

### 推荐方案

在任务私有构建目录内为依赖共享库闭包建立**实体化视图**：

1. 遍历依赖 `cpp_info.libdirs`，`resolve` 符号链接后，以**调用方使用的文件名**
   复制为普通文件；同名不同字节必须失败退出，避免静默错链。
2. 复制时保留 owner 可执行位——缺 `S_IXUSR` 无法 `PROT_EXEC` 映射，
   会以 `Permission denied` 被拒。
3. 只把该视图嵌入**所构建二进制**的 `DT_RPATH`：
   `-Wl,--disable-new-dtags -Wl,-rpath,<view>`。用 `DT_RPATH` 而非 `DT_RUNPATH`，
   让闭包的传递 NEEDED 也走同一搜索路径。
4. **不要**为此导出全局 `LD_LIBRARY_PATH`。对照实验证明"仅设 rpath、不设该变量"
   即可让运行探测通过（上表 A 组 rc=0），而导出它只有副作用：

   - 指向包目录 → 因符号链接别名不可解析而失败（B 组 rc=127）；
   - 指向视图目录 → 该变量被子进程继承，视图里的依赖副本会抢占**工具链自身**
     的库解析。CI worker 上实测：OHOS SDK 的 `lld` 需要 `libxml2`，被 Conan 的
     `libxml2.so.16` 顶掉后崩溃：

     ```
     Error relocating /data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/bin/lld: xmlFreeDoc: symbol not found
     ```

     autoconf 只把它报成 `C compiler cannot create executables`，且**本机可能侥幸
     不复现**（依赖本机 SDK 那份 libxml2 是否已被优先命中）。

打包阶段用 `patchelf --remove-rpath` 去掉指向构建目录的 rpath，别把本机路径写进产物。

### 禁止做法

- ❌ 用 `--host=<triplet>` 使 `cross_compiling=yes` 从而**跳过**运行探测（R1 禁止，
  且会把 config.h 的能力检测写成与真实平台不符的值）
- ❌ 预设 `ac_cv_prog_cc_works=yes` 一类缓存变量伪造探测结果
- ❌ "加载不了就改静态链接"（只为掩盖运行环境问题，属禁止项）
- ❌ 用 `chmod 777`/放宽 umask 修复（MAC 优先于 DAC；反复 `chmod +x` 是签名失效信号）
- ❌ 为了修运行探测而 `export LD_LIBRARY_PATH=<视图或包目录>`：该变量被子进程继承，
  会抢占工具链自身（如 SDK `lld`）的库解析，见上文第 4 步

## 验证

```bash
clang -o probe probe.c -lfontconfig -L"$VIEW" \
      -Wl,--disable-new-dtags -Wl,-rpath,"$VIEW"
env -u LD_LIBRARY_PATH ./probe; echo $?     # 期望 0
LD_LIBRARY_PATH="$VIEW" ./probe; echo $?    # 期望 0
```

## 关联条目

- 相关: E321（签名无效也表现为加载失败，但错误码不同）、E050、E073
- 收窄: E088、E186、E266
- 来源: libxft 2.3.8 适配，2026-08-28，HarmonyOS PC 设备端实测
