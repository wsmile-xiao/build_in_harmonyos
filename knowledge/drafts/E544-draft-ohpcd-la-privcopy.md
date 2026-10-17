# E544: ohpcd 依赖包 .la 的 //lib 引用修复（完整根因链）

## 现象
autotools 配方 conan create 在最终链接（`CCLD libX.la`）时报：
```
grep: //lib/libgpg-error.la: No such file or directory
libtool: error: '//lib/libgpg-error.la' is not a valid libtool archive
```
本地全绿但 CI 干净环境必挂。

## 根因（分层）
1. **源头**：ohpcd 制品仓二进制包以 `prefix=/` 构建，`conan_package.tgz` 内的 `.la` 携带 `libdir='//lib'` 与跨包 `//lib/libfoo.la` 字面引用（解压 tgz 直接实证）。libtool 链接时递归解析依赖 .la，遇到 `//lib/` 路径中止。
2. **修复陷阱一（路由）**：`//lib/libgpg-error.la` 必须按 basename 路由到**提供它的包目录**，不是当前处理的 .la 所在目录——单遍替换会错路由（实测把 gpg-error 的 .la 路由进 libgcrypt 目录）。
3. **修复陷阱二（save 丢失——最隐蔽）**：修复函数重构时 save 调用丢失，替换结果**从未写回磁盘**。症状极具迷惑性：日志无 save 错误（静默）、本地缓存被更早的有 save 版本修过所以本地全绿、CI 干净缓存必挂。**教训：修复类代码必须"计算 new → save → 打印 fixed 三段齐活"，且验证时先还原原始数据再测。**
4. **环境差异盲区**：本地 conan 缓存的依赖 .la 一旦被任何一次成功修复改写过，后续本地测试永远全绿（幂等残留）——**本地验证 .la 修复前必须先从 conan_package.tgz 还原原始状态**。

## 修复（已验证组合）
configure 前 + make 前各一次（BFS 全图含传递依赖）：
1. Pass1：收集全依赖图（`self.dependencies.values()` BFS，ConanFileInterface 有 .dependencies 属性）所有 `.la` 的 basename→owner 目录映射
2. Pass2：`libdir='//lib'`→实际目录；`//lib/<name>.la` 按 basename 路由 owner；`-L//lib`→实际目录；剥离 `-lpthread`（musl pthread 在 libc）
3. **save 写回 + `fixed .la paths` 日志**（缺一不可）

配套：`--libdir` 等传绝对路径（根除 configure 生成的 `//lib`）；package() 用 DESTDIR 暂存（configure cross 模式对绝对路径的相对化行为不可预测）；test_package 用环境变量注入二进制绝对路径（`env="conanrun"` 会整体替换进程环境，PATH 注入无效）。

参考：PR #7713 openconnect 8.10（20+ 轮排查实录）；同族 E543（autoconf 2.72 ltmain.sh 引号）。
