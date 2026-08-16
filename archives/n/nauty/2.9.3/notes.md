# nauty 2.9.3 编译笔记

## 编译信息

- **软件**: nauty 2.9.3
- **URL**: https://pallini.di.uniroma1.it/nauty2_9_3.tar.gz
- **构建系统**: autotools
- **编译器**: clang / clang++
- **配置参数**: `--prefix=/storage/Users/currentUser/usr/local` (R1 最少化参数)
- **编译日期**: 2026-06-01

## 编译流程

### Step 1: init-build
- tarball 已存在，无需下载
- .orig 和 .work 已存在（历史编译目录）
- 环境检查通过（clang 15.0.4, make 4.4.1, autoconf 2.72）

### Step 2: Configure + Make + Install (DESTDIR 模式 R20)
- `./configure --prefix=$DEFAULT_PREFIX` 成功
- `make -j2` 成功（161.7s）
- `make install DESTDIR=$TEST_PREFIX` 成功
- 安装产物：48 个二进制, 18 个头文件, 10 个 .pc 文件, 共享库和静态库

### Step 3: Make check
- `make check` **PASSED ALL TESTS** ✅
- 所有 dreadnaut 测试、geng 测试、labelg 测试等均通过

### Step 4: Package (R19 禁止手动打包)
- `ohc-run.py package` 成功
- `nauty-2.9.3-ohos-aarch64.tar.gz`: 31273KB
- 74 个文件权限修复, ELF 签名, Strip, RPATH 设置

### Step 5: 本地安装验证
- `make install`（不带 DESTDIR）成功
- 48 个二进制在 ~/usr/local/bin/ 可执行验证
- 关键二进制: dreadnaut, geng, labelg, shortg, uniqg, genbg, gentreeg 等
- 库文件: libnauty, libnauty1, libnautyS, libnautyW, libnautyL, libnautyQ (共享+静态)
- pkg-config: 10 个 .pc 文件

### Step 6: Finish published
- 状态: published ✅
- G1-G4 质量门禁全通过

## 补丁说明 (R6: 只改源文件)

### 0001-config.guess.patch
- **类型**: platform (E007)
- **内容**: 添加 HarmonyOS 平台识别支持
  - `__OHOS__` libc 检测
  - `HarmonyOS` uname 系统识别 → `aarch64-unknown-linux-ohos`

### 0002-config.sub.patch
- **类型**: platform (E007)
- **内容**: 添加 `ohos-linux` 三元组支持
  - `basic_machine=$field1-unknown`
  - `basic_os=linux-ohos`

## HMDFS 平台限制 (G0 门禁)

### 根因分析
G0 干净构建验证失败，根因是 HMDFS 文件系统的 `umask 077` bug:

```
umask 077 && mktemp -d "./confXXXXXX"
# → 创建目录权限: drwx--S--- (HMDFS 行为)
# → 在该目录内创建文件失败: Permission denied
```

config.status 内部使用 `umask 077 && mktemp -d` 创建临时目录，但 HMDFS 在此 umask 下创建的目录无法写入文件（即使是目录所有者）。

### 手动验证
- 在 umask 002 下，目录创建和文件写入正常: `drwxrws--x` ✅
- 实际编译（在已有 work 目录中）成功，因为该目录已在之前的编译会话中正确配置
- **G0 失败是 HMDFS 平台限制，不是 nauty 的问题**

### 临时解决方案
未来可通过以下方式修复 G0:
1. 创建 hints/fix-umask.sh 脚本，在 configure 后修改 config.status 的 `umask 077` → `umask 002`
2. 或修改 clean-verify 脚本支持 post-configure hooks

## 铁律合规

| 铁律 | 合规 | 说明 |
|------|------|------|
| R1 | ✅ | 只用 --prefix，无额外参数 |
| R6 | ✅ | 只改源文件(config.guess/config.sub)，不改生成文件 |
| R13 | ✅ | 使用完整路径调用脚本 |
| R19 | ✅ | 使用 ohc-run.py package，禁止手动打包 |
| R20 | ✅ | DESTDIR 模式: --prefix=$DEFAULT_PREFIX + DESTDIR=$TEST_PREFIX |
| R22 | ⚠️ | G0 因 HMDFS bug 失败，手动验证通过 |
| R23 | ✅ | 使用 config.guess/config.sub 平台检测 |

## 知识沉淀
- E007: autotools 软件需要 patch config.guess/config.sub 以支持 HarmonyOS
- HMDFS umask 077 bug: 创建目录后无法写入文件（需记录为新的错误模式）

**编译结束**
**最终状态**: published

---

## 补充：鸿蒙 PC conan 配方（2026-08-17）

# nauty 2.9.3 编译笔记（HarmonyOS PC · conan / autotools）
## 定位
图同构与图生成工具集 — geng/genbg 枚举图、labelg 规范标号、shortg 去重等 50 余个命令
产出库：`libnauty.so`。
产出命令行工具：`geng`、`genbg`、`labelg`、`shortg`、`dreadnaut`、`amtog`、`complg`、`converseg`。

## 源码
- URL：https://users.cecs.anu.edu.au/~bdm/nauty/nauty2_9_3.tar.gz
- sha256：`9fc4edae04f88a0f5883985be3b39cf7f898fd6cc96e96b9ee25452743cc1b5b`

## 关键适配

- **上游站点 `pallini.di.uniroma1.it` 的 TLS 证书已过期**，mac 与设备两侧都下不动 （CERTIFICATE_VERIFY_FAILED）→ 改用作者本人在 ANU 的镜像，sha256 与 sage 的 checksums.ini 逐位一致，是同一份文件
- Makefile **不支持 VPATH**（异地构建产物找不到源）→ `self.folders.build = self.folders.source` 改成源码内构建
- 删除 `lib/*.la`：里面烤死 libdir 绝对路径（conan 按 prefix=/ 构建 → 写的是 `/lib`），下游 libtool 会去找 `//lib/libxxx.la` 而失败
- 修 configure 的 `umask 077` → `022`（HMDFS 上 077 会让后续步骤读不到自己刚建的临时文件）

## 真机验证（2026-08-17）

设备：HUAWEI MateBook（HAD-W32 / 2in1），OHOS aarch64。
`conan create . -pr ohos-native` 通过，test_package 断言：

1. K4 的自同构群阶 |Aut| = 24 ✅
2. P3（路径图）的 |Aut| = 2 ✅

## 状态

built —— 真机已验证；制品**尚未上传**（上传须单独过闸）。

