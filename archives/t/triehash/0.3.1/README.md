# triehash 0.3.1 — 鸿蒙 PC conan 制品

triehash = 从一组关键字生成 **order-preserving minimal perfect hash** 的 C 代码
（头文件 + 源文件），dpkg / apt 用它生成架构 trie 查找表。

上游为**单个 Perl 脚本**（`triehash.pl`），**无编译步骤**。

## 出包（鸿蒙 PC）

```bash
conan create archives/t/triehash/0.3.1 \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
```

## 源

```
https://github.com/julian-klode/triehash/archive/refs/tags/v0.3.tar.gz
sha256 289a0966c02c2008cd263d3913a8e3c84c97b8ded3e08373d63a382c71d2199c   (14059 字节)
```

> 版本说明：配方版本 `0.3.1` 对应上游 **v0.3**。main 上原已有 `0.3` 占位目录
> （仅 manifest/notes/patch/README，**无 conanfile**），本配方补齐使其**可用**。

## 依赖

| 依赖 | 版本 | 说明 |
|------|------|------|
| **perl** | **5.42.2** | ohpcd 已发布；脚本仅用核心模块（`strict`/`warnings`/`utf8`/`Getopt::Long`），无需额外 CPAN 包 |

## OHOS 适配要点

| # | 措施 | 原因 |
|---|------|------|
| 1 | **shebang 改为 `#!/usr/bin/env perl`** | 上游为 `#!/usr/bin/perl -w`，而 **OHOS 上没有 `/usr/bin/perl`**（perl 由 ohpcd 的 `perl/5.42.2` 提供，位于包内 `bin/`）→ 由 `PATH` 解析。<br>仓库内 24 处采用该写法，为主流惯例 |
| 2 | **一并去掉 `-w`** | ⚠️ `#!/usr/bin/env perl -w` 是**错误写法**：内核只把 shebang 首个空白之后的**全部内容作为「一个」参数**传给解释器 → `env` 会把 `"perl -w"` 当作**单个程序名**去查找而失败。脚本内已有 `use warnings`，去掉 `-w` 无功能损失 |
| 3 | 安装为 `bin/triehash`（去掉 `.pl` 后缀）+ `chmod +x` | 便于直接调用；上游 Makefile 亦如此 |
| 4 | `build()` 中自校 shebang | 补丁未生效时立即报错，避免"静默失效"后装出不可执行的脚本 |

## 测试

- **test_package**：`run_triehash_tests.sh` **真实执行** `bin/triehash`，共 6 项断言：
  ① 可执行且 `--help` 正常；② 正常路径生成非空 `.h`；③ 生成非空 `.c`；
  ④ 头文件含 `enum`/关键字（内容真实）；⑤ `-C -`（标准输出）可用；
  ⑥ 不存在的输入文件应**失败**（负向用例）。
- **上游测试**：`tests/` 有 7 个用例（`test-basic` 等），由 `tests/run-tests.sh` 驱动；
  但其框架 `tests/framework.sh` 用 `perl -MDevel::Cover=...` 运行被测脚本，
  而 **`Devel::Cover` 不在 ohpcd 的 perl 包内**（实测 `Can't locate Devel/Cover.pm`），
  故该驱动方式在本环境不可直接用 —— 详见 `manifest.yaml` 的 `test_note`。

## 产物

```
bin/triehash
```
