# E479 — Conan 依赖包以 SONAME 符号链接链安装时，OHOS 加载器拒载该 `.so`

## 错误特征

```
Error loading shared library libxml2.so.16: (needed by .../test_libosmscout)
Error relocating .../test_libosmscout: xmlCreatePushParserCtxt: symbol not found
Error relocating .../test_libosmscout: xmlCtxtUseOptions: symbol not found
```

注意第一行的**错因字段为空**（不是 `Permission denied`，也不是 `No such file`），随后是消费者二进制里所有来自该库的符号被判 `symbol not found`。

典型语境：`conan create` 的构建阶段全绿，`test_package` 运行阶段失败。

## 触发条件

- 阶段: runtime（执行消费者二进制）
- 依赖形态: 共享库 Conan 包，且包内安装为 SONAME 符号链接链
- 平台: OHOS / OpenHarmony（存储卷上的动态加载器行为）

## 根因分析

Conan 打包共享库时保留上游 `make install` 的结果，于是包内是符号链接链：

```
libxml2.so -> libxml2.so.16 -> libxml2.so.16.1.3     # 真实 ELF 只在最末一级
```

消费者按 `DT_NEEDED: libxml2.so.16` 请求加载，加载器打开该符号链接时失败，且**错因字段为空**。

**对照实验（确定性判据）**：

| 实验 | 结果 |
|------|------|
| 把同一实体文件 `cp -L` 成普通文件，放进 `LD_LIBRARY_PATH` | ✅ 正常运行 |
| 在自建目录里放一个指向该文件的**符号链接** | ❌ 复现同样失败 |

结论：故障点是**符号链接本身**，与文件内容、ELF 签名（该 .so 已由包自身签名）、权限、属主均无关（该 `.so` 的 SONAME 链与目录权限完全正常）。

## 解决方案

### 推荐方案

在 `test_package` 的 `generate()` 中把依赖共享库**实体化**：

```python
real_dir = os.path.join(self.build_folder, "realdep_libs")
os.makedirs(real_dir, exist_ok=True)
for requirement in self.dependencies.host.values():
    for libdir in requirement.cpp_info.libdirs:
        folder = os.path.join(requirement.package_folder, libdir)
        for entry in sorted(os.listdir(folder)):
            if ".so" not in entry:
                continue
            # copy2 跟随符号链接，落成实体文件
            shutil.copy2(os.path.join(folder, entry),
                         os.path.join(real_dir, entry))

env = Environment()
env.prepend_path("LD_LIBRARY_PATH", real_dir)
env.vars(self, scope="run").save_script("conanrealdep_run")
```

`test()` 用 `env="conanrun"` 执行。`LD_LIBRARY_PATH` 的搜索优先级高于 `DT_RUNPATH`，因此实体目录必然命中，无需改写二进制 RPATH。

### 备选

若该依赖包发布了静态变体（`shared=False`），改用静态链接可从根上避开运行时加载；仅在确有预编译静态二进制时可用（否则会退化为源码构建该依赖）。

### 禁止做法

- ❌ 在修复路径上再造符号链接（`ln -s`、`os.symlink(..., ".so")`、`cp -d`）：等于把故障点搬个位置。
- ❌ 用静态二进制裸 `mmap(PROT_EXEC)` 探大文件来"验证"加载性：受 execmem 限制会误报，必须用动态加载器 `dlopen` + `dlerror` 取证。

## 验证

```bash
readlink -f <pkg>/lib/libxml2.so.16        # 确认是符号链接链
LD_LIBRARY_PATH=<realdep_libs> ./test_binary # 实体化后通过
```

## 关联条目

- 相似: E274 / E019 / E207（SONAME 符号链接的**创建**侧问题——本条目是其反面：链接存在但加载器拒载）、E073（HMDFS 符号链接限制）
- 原则: P016（HMDFS 文件系统限制必须用替代方案）、P017（ELF 签名必须与运行环境匹配，用于排除签名假设）
- 实证: libosmscout 2024.06.02.1（`test_package` 加载 `libxml2/2.15.3.1`）
