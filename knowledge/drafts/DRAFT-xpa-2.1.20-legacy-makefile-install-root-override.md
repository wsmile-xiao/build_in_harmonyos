# DRAFT-xpa-2.1.20: Tcl 系老式 Makefile 无 DESTDIR 约定、只认 INSTALL_ROOT —— conan package() 暂存变量以被测包实际支持者为准

## 基本信息
- **严重度**: 2
- **类别**: makefile, packaging, installation, conan
- **阶段**: installation（package 阶段）
- **作者**: Q-10（判定与证据）／ DS-31（成稿）
- **来源 PR**: xpa 2.1.20 ／ **来源 commit**: (提交后回填)

## 错误特征
```
mkdir: cannot create directory '//include': Permission denied
```
关键指纹：**编译与链接均已成功**，失败发生在 install recipe；路径是**根级双斜杠**（`//include`
= 空前缀 + 绝对路径拼接）。同族干扰项：`make: *** No rule to make target 'Makefile.in'`
（那是 out-of-source 次生错，经 in-source 布局另修，不属于本机制）。

## 根因分析
xpa 的 Makefile 由 Tcl/Tk 风格 configure 模板生成，安装路径体系**不走 GNU DESTDIR 约定**：

```make
# Makefile.in:33-43（实测行号）
# The following definition can be set to non-null for special systems
# like AFS with replication.  It allows the pathnames used for installation
# to be different than those used for actually reference files at
# run-time.  INSTALL_ROOT is prepended to $prefix and $exec_prefix
# when installing files.
INSTALL_ROOT =

LIB_INSTALL_DIR =	$(INSTALL_ROOT)$(exec_prefix)/lib
BIN_INSTALL_DIR =	$(INSTALL_ROOT)$(exec_prefix)/bin
```

整份 Makefile 没有一处 `DESTDIR` 展开 ⇒ conan/Autotools 默认注入的
`make install DESTDIR=<package_folder>` 被静默忽略，install 按原生 prefix 直接落盘；
prefix 展开为空时拼出 `//include` 根级目录，HMDFS 根目录只读 ⇒ Permission denied。

## 推荐方案
**方法**: upstream-install-root-override（用上游预留的安装根变量完成暂存）

```python
def package(self):
    autotools = Autotools(self)
    root = self.package_folder.replace("\\", "/")
    autotools.install(args=["INSTALL_ROOT=%s" % root])
```

上游 install 目标、目录创建与安装清单语义全部保留，仅改落点前缀。

## 验证/命令
```
grep -n "DESTDIR" Makefile.in        # 无命中 ⇒ 无 DESTDIR 约定
grep -n "INSTALL_ROOT" Makefile.in   # 命中 $(INSTALL_ROOT)$(exec_prefix)/lib ⇒ 有把手
make install DESTDIR=<t>             # 复现：mkdir: cannot create directory //include: Permission denied
make install INSTALL_ROOT=<t>        # 通过；find <t> 复验落点（注意落 <t>/<exec_prefix>/…）
```

## 适用范围/反例
- **适用**：Tcl/Tk 家族 configure 生成物及一切"安装路径仅由自有根变量前缀"的 Makefile 包。
- **不适用**：标准 automake/libtool 项目（天然支持 DESTDIR）；安装**命令缺失**族
  （E098/E108/M13）；运行期路径烧死族（M7，阶段不同）。
- **注意落点差异**：INSTALL_ROOT 前缀的是 prefix/exec_prefix 的展开结果，产物落
  `<t>/<exec_prefix>/bin` 而非 `<t>/bin`，package_info 声明需按实际落点核对。
- **禁忌**：安装路径是内联字面量时变量覆盖无效，退回配方侧复制或补丁；不得用于掩盖交叉编译错误。

## 查重结论（2026-09-22 四范围）
E098/E108/M13 是"安装命令缺失"族（Error 127），本条命令存在、失败是落点体系不同 ⇒ 非 hit；
M7 是运行期 prefix 烧死，本条是暂存期落点，阶段不同 ⇒ 非 hit；E011/E114 是文件系统权限位语义，
本条是路径拼接错误 ⇒ 非 hit。新增价值：**"认 DESTDIR 用 DESTDIR、认 INSTALL_ROOT 用
INSTALL_ROOT，都没有才自己复制"** 的暂存变量判别口诀 + prescan 双 grep 判据。

## 来源事件（xpa 2.1.20 真机链）
GLM-63 起草配方 → conan create 在 DESTDIR 安装阶段报 `mkdir: cannot create directory
'//include': Permission denied`；Q-10 定位 Makefile.in:35-43 并改
`autotools.install(args=["INSTALL_ROOT=..."])` + in-source 布局（verify8 主体通过）；DS-31 接手
完成 xpans 后台化与 test_package 链（verify11/12），`make -j1 testall` 与
stest/xpaset/xpaget/ctest 往返实测跑通。日志：`~/tmp/uc2/xpa-2.1.20/verify*.log`、
`archives/x/xpa/2.1.20/reports/conan-create.log`。
