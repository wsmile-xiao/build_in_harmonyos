# perl-probe-perl 0.03 适配笔记

## 编译环境
- 构建系统: ExtUtils::MakeMaker (perl-eumm)
- 编译日期: 2026-06-26
- 编译器: clang/clang++ (纯Perl模块，无C编译)
- Perl: 5.42.0
- 状态: published

## 编译步骤

```bash
# 1. 初始化
python3 $SKILL_ROOT/scripts/ohc-run.py init-build perl-probe-perl 0.03

# 2. 读取上下文
source .build-context-perl-probe-perl-0.03

# 3. 设置环境变量
export PERL5LIB=$DEFAULT_PREFIX/lib/site_perl/5.42.0:$DEFAULT_PREFIX/lib/perl5/site_perl:$DEFAULT_PREFIX/lib/perl5:$PERL5LIB

# 4. 编译安装
cd $BUILD_SRC_DIR
perl Makefile.PL PREFIX=$DEFAULT_PREFIX INSTALLDIRS=site && make -j1 && make install DESTDIR=$TEST_PREFIX

# 5. 测试
make test  # 19 tests, all pass (1 author test skipped)

# 6. 生成Conan配方
python3 $SKILL_ROOT/scripts/ohc-run.py conan-init perl-probe-perl 0.03

# 7. 验证配方
python3 $SKILL_ROOT/scripts/ohc-run.py conan-verify perl-probe-perl 0.03
# G0-G4 + L2/L4/L5 全部 PASS

# 8. 收尾
python3 $SKILL_ROOT/scripts/ohc-run.py finish perl-probe-perl 0.03 published
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | notes.md 未填充 | finish 脚本自动生成模板但未填充 | 手动填充实际编译步骤和经验 |
| 2 | manifest.yaml 缺少字段 | 模板缺少 compile_date、build_system | 补充缺失字段，填充 knowledge_gained |
| 3 | conanfile.py settings 过度声明 | 纯Perl模块不需要 compiler/build_type | 简化为 settings = "os", "arch" |
| 4 | conanfile.py self.run 缺少 env | 未使用 conanrun 环境变量 | 添加 env="conanrun" |
| 5 | conanfile.py 使用 glob 而非 copy | 路径发现不够健壮 | 使用 copy() 从已知 site_perl 路径复制 |
| 6 | exports 依赖 lib/ workaround | package() 未正确复制产物 | 移除 exports lib/**，在 package() 中用 copy() |
| 7 | G0 无法识别构建系统 | perl-eumm 不在已知构建系统列表 | 已知平台限制，手动验证通过 |
| 8 | 缺少软件级 README.md 和 manifest.yaml | finish 脚本未生成软件级文件 | 手动创建软件级 README.md 和 manifest.yaml |

## 源码修改

无补丁，无源码修改。纯Perl模块直接编译安装。

## 依赖版本

| 依赖 | 版本 | 来源 |
|------|------|------|
| Config | 5.42.0 | Perl核心模块 |
| File::Spec | 3.75 | Perl核心模块 |
| Test::More | 1.302210 | Perl核心模块 |

## 验证结果

```bash
# make test
t/author-critic.t .. skipped: these tests are for testing by the author
t/basic.t .......... ok
All tests successful.
Files=2, Tests=19,  0 wallclock secs
Result: PASS

# 功能测试
perl -MProbe::Perl -e 'my $p=Probe::Perl->new; print $p->config("version"), "\n"'
# 5.42.0

# conan-verify
G0: PASS | G1: PASS | G2: PASS | G3: PASS | G4: PASS
L2: PASS | L4: PASS | L5: PASS
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| lib/Probe/Perl.pm | 7147 | 主模块文件 |

## 注意事项

- 纯Perl模块，无需C编译器，无.so文件，不受HMDFS/SELinux限制
- 仅依赖 Perl 核心模块 (Config, File::Spec)，无外部依赖
- PERL5LIB 必须包含 site_perl/5.42.0 路径以正确加载模块
- conanfile.py 的 package() 方法使用 copy() 将 .pm 从嵌套 site_perl 路径复制到 lib/ 供 Conan 产物检测

**编译结束**: 2026-06-26 13:38
**文档修复**: 2026-06-26
**最终状态**: published
