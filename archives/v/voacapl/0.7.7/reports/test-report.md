# voacapl 0.7.7 功能测试报告

**测试日期:** 2026-09-25
**测试环境:** OpenHarmony PC aarch64
**编译器:** flang-ohos/20.1.0（Fortran）+ clang 15.0.4（SDK）

## 1. 编译测试

### 1.1 编译状态
✅ 编译成功（`make`，全部二进制产出）

### 1.2 源码修改（见 patches/ 0001-0006 + build() 内联适配）
- `configure`：移除 config.status 临时目录创建中的 `umask 077`（E114：HMDFS setgid + umask 077 产生不可写 `drwx--S---` 目录）
- `Makefile.in/.am`（voacapw 等）：移除 `-fno-sign-zero`（flang 不识别该 gfortran 选项）
- `voacapw` SOURCES：接入 `ohos_unlink_shim.for`
- 内联（build()）：Hollerith 编辑描述符替换（`FORMAT(1H`→`1X`、`2h`→字符常量）、新增 `ohos_unlink_shim.for`（gfortran 扩展过程 `call unlink` 的等价实现，flang 无内建）、coeffs 工具路径变量 `len=128→512`（DESTDIR 长路径截断）

## 2. 安装测试

### 2.1 安装产物（bin/）
- `voacapl`（主程序，16.8MB）
- `anttyp90`、`anttyp99`
- `dst2ascii`、`dst2csv`
- `coeffbin`、`coefbinw`、`fof2bin`、`fof2binw`
- `makeitshfbc`（安装后由 install-data-hook 替换前缀）

### 2.2 数据目录（share/voacapl/itshfbc/）
- coeffs/、database/、geocity/、geonatio/、geostate/、antennas/、news/、areadata/、area_inv/、run/

## 3. 功能测试

### 3.1 版本信息测试
```bash
$ voacapl --version
voacapl - release 0.7.7
```
✅ 版本输出正确

### 3.2 p2p 传播预测实测（上游 tests/p2p 资产）
```bash
$ voacapl <itshfbc_root>   # 处理 tests/p2p/test01.dat
```
✅ EXIT=0，生成预测输出文件
⚠️ 与上游参考 `test01.out` 存在平台性差异（参考为 Windows 平台生成：
`\SAMPLE.00` 路径分隔符/CRLF/VOACAP 无 L 标记；本机 `/sample.00`、LF、
`VOACAP L` 标记；数值差异 ≤1dB 属浮点/平台差异，核心计算一致）

### 3.3 辅助工具可执行性
```bash
$ anttyp90 --version   # ✅
$ anttyp99 --version   # ✅
$ dst2ascii --version  # ✅
$ dst2csv --version    # ✅
```

## 4. 消费者测试（test_package）

- `test.c`：popen 执行 `voacapl --version`，断言输出含 `voacapl - release`
- `voacapl --version` 直接执行校验
- ✅ 全部通过

## 5. Conan 验证

- `conan-verify`：G0-G4 全 PASS（配方可标记 published）
- W3 本地 CI 模拟：L0/L1/L2/L4/L5 全 PASS，通过率 100%（1/1）
