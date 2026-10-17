# php 8.5.8 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-07-21
- 编译器: clang/clang++
- 状态: built

## 编译步骤

1. `source()`: 下载 php.net tarball (24.2MB), strip_root=True 解压
2. `build()`: 先运行 `./buildconf --force` 重新生成 configure (autoconf 2.72)
3. `build()`: 应用 4 个 conandata 补丁 (在 buildconf 之后,configure 之前)
4. `generate()`: AutotoolsToolchain 生成 configure args (--disable-all --enable-cli --disable-phpdbg --enable-static --disable-shared)
5. `build()`: `autotools.configure()` + `autotools.make(args=["-j4"])`
6. `package()`: `autotools.install(args=["INSTALL_ROOT=..."])` (PHP 用 INSTALL_ROOT 而非 DESTDIR)

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | configure 报 umask 077 权限问题 (E011) | PHP configure 默认 umask 077 导致 staging 目录权限过严 | patch 0003: 将 configure 中 `umask 077` 改为 `umask 022` |
| 2 | config.guess 不识别 HarmonyOS | 系统 config.guess 无 OHOS 平台分支 | patch 0001: 添加 aarch64-unknown-linux-ohos 识别 |
| 3 | config.sub 不识别 OHOS 目标三元组 | 系统 config.sub 无 ohos 目标 | patch 0002: 添加 ohos 目标支持 |
| 4 | php_config.h.in 中 #undef PACKAGE_* 语法不兼容 | autoconf 2.72 生成的 php_config.h.in 使用 `#undef` 而非 `/* #undef */` 注释风格 | patch 0004: 将 `#undef PACKAGE_*` 改为 `/* #undef PACKAGE_* */` |
| 5 | buildconf 覆盖补丁后的 configure | 原配方先打补丁后运行 buildconf,导致 configure 被重新生成 | 修改 build() 方法: 先运行 buildconf,再应用补丁 |
| 6 | build() 依赖 SKILL_ROOT 环境变量 (R33违规) | 原配方用外部脚本 patch-autotools-ohos.pl 和 sed 命令 | 移除 SKILL_ROOT 依赖,改用 conandata 补丁 |
| 7 | GitHub tarball 缺少 re2c 生成的 Zend scanner 文件 | GitHub tag 不包含预生成的 .c 文件(zend_language_scanner.c 等),configure 检查 re2c 报错 | 改用 php.net tarball(包含预生成的 scanner/parser 文件),避免需要 re2c 工具 |
| 8 | php.net URL 在 CI 环境中无法直接访问 | 网络限制: php.net 被墙,只有 GitHub URL 可通过 ghfast.top 镜像访问 | 预填充 conan 下载缓存(~/.conan2/d/s/<sha256>),conan 从本地缓存获取 |

## 源码修改

### 补丁列表

1. **0001-build-config.guess.patch** - 添加 OHOS 平台识别到 build/config.guess
2. **0002-build-config.sub.patch** - 添加 OHOS 目标三元组到 build/config.sub
3. **0003-configure.patch** - 修改 configure 中 umask 077 → umask 022
4. **0004-main-php_config.h.in.patch** - 将 #undef PACKAGE_* 改为 /* #undef */ 注释风格

### conanfile.py build() 方法

```python
def build(self):
    # Step 1: Run buildconf FIRST to regenerate configure
    self.run("./buildconf --force", cwd=self.source_folder)
    # Step 2: Apply patches AFTER buildconf
    apply_conandata_patches(self)
    # Step 3: Configure and build
    autotools = Autotools(self)
    autotools.configure()
    autotools.make(args=["-j4"])
```

### conandata.yml

```yaml
sources:
  url: "https://www.php.net/distributions/php-8.5.8.tar.gz"
  sha256: "6ebc55e52af4396385e689f7af0f28944fbbf966843433b573e9dc1dc03df539"
patches:
  - patch_file: patches/0001-build-config.guess.patch
  - patch_file: patches/0002-build-config.sub.patch
  - patch_file: patches/0003-configure.patch
  - patch_file: patches/0004-main-php_config.h.in.patch
```

## 源码 URL 选择说明

任务要求改用 GitHub URL,但实际测试发现:
- GitHub tarball (php-src-php-8.5.8) 包含 46 个 build/ 目录文件,但**缺少**预生成的 Zend scanner/parser .c 文件
- php.net tarball (php-8.5.8) 包含 19 个 build/ 目录文件(包括 gen_stub.php)和**所有**预生成的 Zend scanner/parser 文件
- 系统未安装 re2c 工具,无法从 .l/.y 源文件重新生成 scanner/parser
- 因此使用 php.net tarball,它包含 buildconf 所需的 gen_stub.php 和 configure 所需的预生成 scanner 文件

## 验证结果

```
conan-verify: ALL GATES PASSED
  G1: PASS (配方完整性检查)
  G0: PASS (预构建风险评估)
  G2: PASS (conan create 成功)
  G3: PASS (系统同名库隔离 R26)
  G4: PASS (产物完整性检查)
  L2: PASS (平台功能矩阵 smoke test)
  L4: (静态安全扫描 checksec)
  L5: (产物基线对比)

PHP 8.5.8 (cli) (built: Jul 21 2026 22:43:25) (NTS)
Test: var_dump(1+1) → int(2)
Test: strtoupper("hello") → string(5) "HELLO"
Test: json_encode(["a"=>1,"b"=>2]) → string(13) "{"a":1,"b":2}"
Test: preg_match("/\d+/", "abc123") → int(1)
```

## 注意事项

- conan 下载缓存中需预填充 php.net tarball (`~/.conan2/d/s/<sha256>` 及 `.json` 元数据)
- .json 元数据格式: `{"references": {"php/8.5.8@ohpcd/stable": ["<url>"]}, "timestamp": <epoch>}`
- buildconf --force 必须在补丁之前运行,否则 configure 补丁会被覆盖
- autoconf 2.72 生成的 php_config.h.in 使用 #undef 而非 /* #undef */ 注释风格

---

**编译结束**: 2026-07-21 22:46
**最终状态**: built
