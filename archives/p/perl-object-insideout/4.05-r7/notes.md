# perl-object-insideout 4.05-r7 适配笔记

## 编译环境
- 构建系统: Perl ExtUtils::MakeMaker (perl Makefile.PL)
- 编译日期: 2026-07-01 (二次验证修复)
- 编译器: N/A (纯Perl模块，无C/C++编译)
- 状态: published

## 编译步骤

1. 下载源码: 从 CPAN (https://cpan.metacpan.org/authors/id/J/JD/JDHEDDEN/Object-InsideOut-4.05.tar.gz) 使用 curl -kL 下载
2. perl Makefile.PL INSTALL_BASE=$DEFAULT_PREFIX
3. make -j2
4. make test
5. make install DESTDIR=$TEST_PREFIX

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | SSL证书验证失败 | 鸿蒙环境缺少CA证书 | 使用 curl -kL 下载源码包，手动放置到构建目录 |
| 2 | /tmp只读 | 鸿蒙平台 /tmp 为只读文件系统 (E002) | 使用 $TMPDIR/$HOME/tmp 替代 |
| 3 | Conan配方env参数错误 | Conan 2.x 的 run() env参数需要list格式 | 移除env参数，改用os.environ设置环境变量 |
| 4 | Conan build目录找不到Makefile.PL | basic_layout导致source和build目录分离 | 使用 cwd=self.source_folder 参数指定工作目录 |
| 5 | test_package测试失败 | Object::InsideOut不能从main包直接use | 创建独立Perl测试脚本，在package上下文中使用模块 |
| 6 | conan-verify G1失败 | test_package/MANIFEST.yml 缺失 (CI L0e 门禁) | 运行 conan-init --force 生成模板，手动填写上游测试声明 |
| 7 | conan-init --force覆盖定制配方 | --force 用通用autotools模板覆盖了Perl专用conanfile.py | 手动恢复Perl专用配方（ExtUtils::MakeMaker），删除CMake模板文件 |
| 8 | test_package加载旧版本(3.88) | conanfile.py package() 的 copy() 因 DESTDIR+绝对路径导致路径嵌套，Perl回退到系统旧版 | 修复 conanfile.py：使用 build_folder 下临时 prefix + 直接 make install（不用 DESTDIR）|

## 问题7-8详细说明（参考perl-dbd-pg经验修复）

### 问题7: conan-init --force 覆盖定制配方

运行 `conan-init --force` 生成 MANIFEST.yml 时，该命令会用通用 autotools 模板覆盖已有的 Perl 专用 conanfile.py：
- 生成 `AutotoolsToolchain` + `-static` 链接（不适用于纯Perl模块）
- 生成 CMake 测试模板（不适用于 Perl 模块）
- 丢失 Perl 专用逻辑（INSTALL_BASE, *.pm copy, cwd=source_folder）

**修复**: 手动恢复 Perl 专用 conanfile.py，仅保留新生成的 MANIFEST.yml，删除 CMakeLists.txt 和 test.c。

### 问题8: DESTDIR 路径嵌套导致 test_package 加载旧版本

原 conanfile.py 的 package() 方法：
```python
prefix = os.path.join(self.package_folder, "usr")  # 绝对路径
self.run(f'make install DESTDIR="{staging}"')     # DESTDIR + 绝对路径
copy(self, "*.pm", staging, ...)                   # copy 保留完整路径
```

`make install DESTDIR=staging INSTALL_BASE=/abs/path` 会将文件安装到 `staging/abs/path/lib/perl5/`。
Conan 的 `copy()` 从 staging 搜索 *.pm，保留相对路径，导致产物路径为 `lib/abs/path/lib/perl5/...`。

test_package 的 `copy()` 从 `dep_pkg/lib/` 复制时，文件路径不正确，Perl 找不到模块，回退到系统已安装的旧版本 (3.88)。

**修复**: 改用 build_folder 下的临时 prefix + 直接 `make install`（不用 DESTDIR）：
```python
def build(self):
    self._prefix = os.path.join(self.build_folder, "perl_prefix")
    self.run(f'perl Makefile.PL INSTALL_BASE="{self._prefix}"')

def package(self):
    self.run("make install")  # 直接安装到 prefix
    perl_lib = os.path.join(self._prefix, "lib", "perl5")
    copy(self, "*.pm", perl_lib, os.path.join(self.package_folder, "lib"))
```

## 源码修改

无补丁。纯Perl模块，源码无需修改。

## 依赖版本

- Perl 5.42.0 (系统自带)
- ExtUtils::MakeMaker (Perl核心模块)
- 可选依赖: Want, Math::Random::MT::Auto (未安装，不影响核心功能)

## 验证结果

### conan-verify (8道门禁)
```
G0: PASS (预构建风险评估)
G1: PASS (配方完整性 - 含 MANIFEST.yml)
G2: PASS (conan create 干净构建)
G3: PASS (系统同名库隔离)
G4: PASS (产物完整性 - 16 .pm + 2 .pod)
L2: PASS (smoke test - 纯Perl包跳过)
L4: PASS (安全扫描 - 无ELF文件)
L5: PASS (产物基线对比 - 18个文件)
```

### test_package 测试
```
python3 test_oio.py
Object::InsideOut version: 4.05
Test OK
```

### 功能测试 (25项)
```
PASS: 23
FAIL: 0
SKIP: 2 (threads/Want 可选依赖)
```

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py | Conan配方 (Perl ExtUtils::MakeMaker构建系统) |
| conandata.yml | 源码SHA256声明 |
| test_package/conanfile.py | Conan测试配方 |
| test_package/MANIFEST.yml | 上游测试声明 |
| manifest.yaml | 编译元数据 (published) |
| packaging/perl-object-insideout-4.05-r7-ohos-aarch64.tar.gz | 打包产物 (337KB) |
| reports/conan-verify-report.md | Conan验证报告 |
| reports/test-report.md | 功能测试报告 |
| reports/reviewer-report.md | 上库评估报告 |

## 注意事项

- 纯Perl模块，无C/XS编译，不需要编译器设置
- Object::InsideOut必须在class package上下文中使用，不能从main包直接use
- 可选模块Want和Math::Random::MT::Auto未安装，不影响核心功能
- 部分测试因缺少threads支持而跳过（鸿蒙平台限制）
- conan-init --force 会覆盖定制配方，对非标准构建系统（Perl/Meson等）需手动恢复
- DESTDIR + INSTALL_BASE绝对路径会导致 Conan copy() 路径嵌套，应避免组合使用
---

**编译结束**: 2026-07-01 17:53
**最终状态**: published
