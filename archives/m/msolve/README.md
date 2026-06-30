# msolve

## 简介
msolve 是一个用于多项式方程组求解的 C 库，基于计算机代数（符号计算）方法。提供了高效的多变量多项式系统求解算法，广泛应用于密码学、机器人学和科学计算领域。

## OHOS 适配

### 关键问题与解决方案

**E011 - HMDFS umask 077 问题**
- **问题描述**: HMDFS 文件系统默认 umask 077 导致 configure 创建临时文件失败
- **解决方案**: 修改 configure 中的 `umask 077` 为 `umask 022`
- **影响范围**: 所有 autotools 项目

**E007 - config.guess 不支持 OpenHarmony**
- **问题描述**: config.guess 无法识别 `aarch64-unknown-ohos` 平台
- **解决方案**: 使用已更新的 config.guess/config.sub（GMP/FLINT 已提供）

**P002 - GMP 静态库 PIC 问题**
- **问题描述**: GMP 静态库编译时未使用 -fPIC，导致链接共享库时失败
- **解决方案**: 使用 `--disable-shared --enable-static` 禁用共享库构建
- **依赖**: FLINT 也需要相同处理

## 排除与替代
无

## 依赖
- GMP >= 6.2.0
- MPFR >= 4.1.0
- FLINT >= 3.0.0

## 功能验证
```bash
msolve --version  # 输出 0.9.5
```

## 参考
- 官网: https://msolve.lip6.fr
- 源码: https://github.com/algebraic-solving/msolve
- 文档: https://msolve.lip6.fr/doc/
