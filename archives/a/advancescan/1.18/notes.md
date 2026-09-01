# advancescan 1.18 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-06-16
- 编译器: clang 15.0.4 / clang++
- 目标平台: aarch64-unknown-linux-ohos
- 状态: built

## 编译步骤

### 对话 #1 [2026-06-16]

- 问题: `ohc-run.py build advancescan 1.18` 全自动模式因源码目录已有旧配置残留导致 configure 失败 ("source directory already configured")
- 操作: 重置 work 目录从 orig，手动编译
- 结果: 手动编译流程全部成功

### 对话 #2 [2026-06-16]

- 问题: config.guess (2013版) 不识别 HarmonyOS 平台
- 操作: 替换为 automake-1.17 附带的 GNU Config 2023 版 + patch-autotools-ohos.pl 补丁
- 结果: 检测到 aarch64-unknown-linux-ohos

### 对话 #3 [2026-06-16]

- 问题: configure 运行时创建临时文件 Permission denied
- 操作: sed 替换 umask 077 → umask 022
- 结果: configure 正常通过

### 对话 #4 [2026-06-16]

- 问题: 归档缺少真实测试报告和 README.md
- 操作: 补充 test-report.md、quality-report.md、软件级 README.md、manifest sha256
- 结果: 归档一致性修复完成

1. `python3 $SKILL_ROOT/scripts/ohc-run.py init-build advancescan 1.18 --url=https://github.com/amadvance/advancescan/releases/download/v1.18/advancescan-1.18.tar.gz`
   - 源码下载/解压完成，环境检查通过
   - 历史档案已有 built 状态记录

2. 从 orig 目录重置 work 目录（清除上一次编译残留）
   ```bash
   rm -rf ~/tmp/builds/advancescan-1.18.work
   cp -a ~/tmp/builds/advancescan-1.18.orig ~/tmp/builds/advancescan-1.18.work
   ```

3. 替换 config.guess/config.sub 为 GNU Config 2023 版（automake-1.17 附带版本）
   ```bash
   cp /storage/Users/currentUser/usr/local/share/automake-1.17/config.guess config.guess
   cp /storage/Users/currentUser/usr/local/share/automake-1.17/config.sub config.sub
   chmod +x config.guess config.sub
   perl $SKILL_ROOT/scripts/patch-autotools-ohos.pl config.guess config.sub
   # 结果: __OHOS__ LIBC 检测已内置, ohos 三元组支持已内置, Score: 5/5
   ```

4. `autoreconf -fi` 重新生成 configure 等构建系统文件
   - 有 AC_HEADER_STDC/AC_HEADER_TIME 弃用警告，不影响功能

5. 修改 configure 中 `umask 077` → `umask 022`（HMDFS 文件系统限制：umask 077 创建的目录无法写入文件）
   ```bash
   sed -i 's/umask 077/umask 022/g' configure
   ```

6. `./configure --prefix=$DEFAULT_PREFIX`
   - 检测结果: `aarch64-unknown-linux-ohos`（平台识别正确）
   - zlib 库检测成功
   - 生成 Makefile 和 config.h

7. `make -j1`
   - 编译成功，产出 advscan 和 advdiff 两个可执行文件
   - 有 std::binary_function 弃用警告（C++11），不影响功能
   - 有 expat/xmlparse.c enum 转换警告，不影响功能

8. `make install DESTDIR=$TEST_PREFIX`
   - 安装到 staging 目录:
     - bin/advscan (657920 bytes)
     - bin/advdiff (363008 bytes)
     - share/man/man1/advscan.1
     - share/man/man1/advdiff.1

9. **Staging 验证**: `$TEST_PREFIX/$DEFAULT_PREFIX/bin/advscan --version` → "advancescan v1.18"
   - `$TEST_PREFIX/$DEFAULT_PREFIX/bin/advdiff --version` → "advancescan v1.18"
   - 无安全弹窗，二进制可直接执行

10. **make check**: ✅ 成功！
    ```
    ./advscan -e < ./test/test.xml > check.lst
    cmp check.lst ./test/test.lst  → 无差异
    ./advdiff ./test/test.xml ./test/testd.xml > checkd.lst
    cmp checkd.lst ./test/testd.lst  → 无差异
    echo Success!  → Success!
    ```

11. **ohc-run.py package**: advancescan-1.18-ohos-aarch64.tar.gz (1098KB)
    - ELF 签名、RPATH、strip、权限均自动处理
    - 包含 bin/advscan, bin/advdiff, share/man/man1/

12. `make install`（本地部署，不带 DESTDIR）
    - 安装到 $DEFAULT_PREFIX (~/usr/local)

13. **用户验证**:
    ```bash
    $ advscan --version
    advancescan v1.18 by Andrea Mazzoleni, http://www.advancemame.it
    $ advdiff --version
    advancescan v1.18 by Andrea Mazzoleni
    ```

14. `python3 $SKILL_ROOT/scripts/ohc-run.py finish advancescan 1.18 built`
    - 补丁生成: 10 个补丁
    - G0 干净构建验证: toybox patch 不兼容（已手动验证）
    - G1-G4 质量门禁: PASS
    - 归档关闭: built

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 | 知识编号 |
|---|------|------|----------|---------|
| 1 | config.guess 无法识别 HarmonyOS | 2013 版不含 HarmonyOS 检测 | 替换为 GNU Config 2023 版 + patch-autotools-ohos.pl | E007/E072 |
| 2 | config.sub 不识别 ohos 三元组 | 2013 版缺少 ohos 支持 | 同上 | E007/E072 |
| 3 | configure 创建临时文件 "Permission denied" | HMDFS 下 umask 077 目录无法写入 | sed 替换 umask 077 → umask 022 | E002 |
| 4 | G0 干净构建验证中 patch 失败 | toybox patch 不支持 --input 选项 | 已手动验证补丁可正确应用 | 平台限制 |

## 源码修改

- config.guess: 替换为 GNU Config 2023 版（含 __OHOS__ LIBC 检测）
- config.sub: 替换为 GNU Config 2023 版（含 ohos 三元组支持）
- configure: umask 077 → umask 022（HMDFS 兼容性）
- 其他构建系统文件: 通过 autoreconf -fi 重新生成（Makefile.in, aclocal.m4, compile, config.h.in, install-sh, missing）

## 依赖版本

- zlib: 系统预编译包
- clang 15.0.4
- automake 1.17, autoconf 2.72

## 验证结果

### make check
```
Success! — 所有测试通过
```

### 二进制版本
```bash
/storage/Users/currentUser/usr/local/bin/advscan --version
advancescan v1.18 by Andrea Mazzoleni, http://www.advancemame.it

/storage/Users/currentUser/usr/local/bin/advdiff --version
advancescan v1.18 by Andrea Mazzoleni
```

### 质量门禁
- G0 干净构建: ⚠️ 已手动验证通过（toybox patch 不兼容）
- G1 二进制完整性: ✅ PASS
- G2 功能可用性: ✅ PASS
- G3 可移植性: ✅ PASS
- G4 档案完整性: ✅ PASS

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| advancescan-1.18-ohos-aarch64.tar.gz | 1098KB (1125057 bytes) | 预编译包 |
| advscan | 657920 bytes | 扫描工具二进制 |
| advdiff | 363008 bytes | 差异比对工具二进制 |

## 注意事项

- HMDFS 文件系统下 umask 077 创建的临时目录无法写入文件，需修改 configure 去除 umask 077
- 源码使用已弃用的 std::binary_function（C++11），编译时有弃用警告但不影响功能
- G0 干净构建验证中 toybox patch 不兼容，需使用 GNU patch 手动验证

---

**编译结束**: 2026-06-16
**最终状态**: built

## 对话记录

### 2026-06-16 编译全过程

**步骤 1-14 完整执行**:
- init-build → 替换 config.guess/config.sub → patch-autotools-ohos.pl → autoreconf -fi → sed umask 077→022 → configure → make → make install DESTDIR → make check(Success!) → package → make install → verify → finish

**关键修复**:
- [E007/E072] config.guess/config.sub HarmonyOS 检测补丁 → ✅ 已修复
- [E002] configure umask 077 → 022 → ✅ 已修复
- G0 toybox patch 不兼容 → ⚠️ 已手动验证通过
