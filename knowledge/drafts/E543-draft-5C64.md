# E543 — make 默认目标=all：conanfile 二次 make 未显式 install 目标 → 空包 → test_package 127

## 错误特征
- `conan create` 输出 `package(): WARN: No files in this package!`
- test_package 报 `.../bin/<exe>: inaccessible or not found` → `ConanException: Error 127`
- `DESTDIR=<stage>` 目录存在但为空

## 触发条件
- 构建系统: GNU make / autotools（Makefile 默认目标为 `all` 而非 `install`）
- 阶段: installation / packaging / testing
- 配方: build() 先 `make`，再**不带目标**执行 `make ... DESTDIR=<stage>`，误以为会安装

## 根因分析
GNU make 不带目标时执行的是 default goal（通常是第一个规则/`all`），
`DESTDIR` 只是变量，不会自动触发 `install` 规则。第二次 make 因此只是
重新构建 `all`，stage 目录始终为空。package() 从空 stage 复制 → 空包 →
test_package 找不到 bin → Error 127。此错误易与 E077(未签名)/E011(执行位)
混淆，应先检查包内是否有文件再归因。

## 解决方案

### 推荐方案
`build()` 中安装步骤必须显式传 `install` 目标：

```bash
make -j1 NCURSESW_CONFIG=... CC=clang ... install DESTDIR=$STAGE
```

个别 prerequisite 缺失（如 `myman.txt` 依赖 groff/col）若目标带 `(ignored)`
可忽略，不影响安装主体。

### 禁止做法
- ❌ 不带 `install` 目标地执行 `make ... DESTDIR=...` 当安装
- ❌ 忽略空包直接标 published（伪造状态）
- ❌ 误判为签名问题反复 chmod / 加签名而不同时修 install 目标

## 实例
myman 0.7.1（feat/myman-0.7.1，2026-09-06）：W3 曾空包失败 127；修正
`make ... install DESTDIR=<stage>` + package() 内 E077 ELF 签名后，
test_package `myman --version` 真实执行成功，conan create passed。
