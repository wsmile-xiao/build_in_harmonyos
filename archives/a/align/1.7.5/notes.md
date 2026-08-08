# align 1.7.5 适配笔记

## 编译环境
- 构建系统: makefile（纯 Perl 脚本项目，Makefile 仅修改 shebang）
- 编译日期: 2026-08-07
- 编译器: 无需编译（align/width 为 Perl 脚本）
- 状态: built

## 编译步骤

```bash
# 1. init-build（源码来自官方站 kinzler.com）
python3 scripts/ohc-run.py init-build align 1.7.5 \
  --url=https://kinzler.com/me/align/align-1.7.5.tgz

# 2. 构建与验证（align/width 是 Perl 脚本，无 configure/编译）
cd $BUILD_SRC_DIR
make PERL=/data/service/hnp/bin/perl   # 仅修改 shebang
printf 'a b\nccc dddd\n' | ./align      # 对齐输出验证
printf 'hello world\n' | ./width        # 行宽统计验证

# 3. 配方生成与验证
python3 scripts/ohc-run.py conan-init align 1.7.5
python3 scripts/ohc-run.py conan-verify align 1.7.5
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | shebang 指向 /usr/bin/perl 不可用 | OHOS 无 /usr/bin/perl | build() 重写 shebang 为设备标准路径 /data/service/hnp/bin/perl |
| 2 | test_package L1e 破坏性测试失败 | test 命中系统安装的 align 而非包内版本 | 移除探索阶段手动安装的 align/width，test_package 显式将包内 bin 加入 PATH |

## 源码修改

无补丁。align/width 是 Perl 脚本，build() 中直接重写 shebang（等效上游 Makefile 的 perl 目标）。

## 依赖版本

- perl/5.42.2（制品仓已发布，align/width 运行时依赖）

## 验证结果

```bash
# 功能验证：PASS
printf 'a b\nccc dddd\n' | align   # → 输出对齐后的列
printf 'hi\n' | width              # → 2:-:1:hi

# test_package（conan create L1 测试）
./test_align  # → PASS: align produced output: a   b

# conan-verify 门禁
G1-G4 全部 PASS，配方验证通过
```

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py + conandata.yml | Conan 配方（Perl 脚本安装） |
| test_package/ | L1 实质测试（system 调用 align 验证对齐输出） |
| packaging/align-1.7.5-ohos-aarch64.tar.gz | release 打包产物 |
| commands.json | 命令行工具声明 (R38) |

## 注意事项

- align/width 为 Perl 脚本（非编译产物），`package_type=application`，`cpp_info.bindirs=["bin"]`
- 运行时依赖 perl/5.42.2（Conan 依赖已声明）
- 上游无 make check 目标，通过功能命令验证

---

**编译结束**: 2026-08-07 17:38
**最终状态**: built
