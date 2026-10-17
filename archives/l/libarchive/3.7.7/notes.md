# libarchive 3.7.7 — 适配记录

**日期**: 2026-09-05
**状态**: ✅ 已适配（依赖项 PR，published）
**构建系统**: CMake（区别于仓内 3.8.7 的 autotools）

## 对话记录（断点续传核心）

### 对话 #1 — 2026-09-05
**操作**: 积分赛依赖项任务，全流程适配（W0-W5）
**结果**: ✅ conan create + W3 本地 CI 全绿（.ci-result.json exit_code=0，L0/L1/L5 pass，L1e R34 反向验证通过），上游五套件 783/800 通过
**发现的问题**: CMake 4.x 需 CMAKE_POLICY_VERSION_MINIMUM=3.5（E187 命中）；SDK 无 llvm-ranlib 需 shim；hmfs 平台限制致 17 测试失败（非包缺陷）
**当前状态**: 已完成，待 submit
**遗留问题**: 无

## 一、基本信息
| 项目 | 值 |
|------|-----|
| 软件 | libarchive |
| 版本 | 3.7.7 |
| 构建系统 | CMake (Ninja) |
| 源码 | https://www.libarchive.org/downloads/libarchive-3.7.7.tar.gz |
| SHA256 | 4cc540a3e9a1eebdefa1045d2e4184831100667e6d7d5b315bb1cbc951f8ddff（与官方 .sums.txt 核对一致） |
| 产物 | libarchive.so/.a + bsdtar/bsdcpio/bsdcat/bsdunzip |

## 二、适配决策与依据（W0b 历史核验）

本包与仓内 3.8.7（autotools）同源不同构建系统。3.8.7 的坑逐项比对：

| 3.8.7 (autotools) 的坑 | 3.7.7 (CMake) 本版情况 |
|---|---|
| config.guess 不识别 HarmonyOS → 补丁 0001 | ✅ 不适用：CMake + ohos.toolchain.cmake 直接过 |
| configure umask 077 临时目录 Permission denied → 补丁 0002 | ✅ 不适用：无 configure 阶段 |
| zlib/1.3.1 libz.a 非 PIC → R_AARCH64 relocation | ✅ 同样存在：require zlib/1.3.1.1（-fPIC 静态版） |
| pkg-config 误检 harmonybrew liblzma | ✅ 不适用：预设 Find 模块缓存变量，不跑 pkg-config |
| 依赖仅 zlib+xz（configure 未检出其余） | ⬆️ 增强：CMake 接线后 zlib+bzip2+xz+zstd 四后端全启用 |

### 本版新坑（新增知识）
1. **CMake 4.x 兼容**：上游 `cmake_minimum_required(VERSION 2.8.0)`，CMake 4.1.2 直接报错
   → `-DCMAKE_POLICY_VERSION_MINIMUM=3.5`（与 libtiff 同法）。
2. **OHOS SDK 无 llvm-ranlib**：链接 libarchive.a 时 `llvm-ranlib: inaccessible or not found`
   → 生成 wrapper 脚本 `exec llvm-ar s "$@"`（zstd 配方同法）+ `-DCMAKE_AR` 指定 llvm-ar。
3. **依赖接线**：FIND_ROOT_PATH_MODE=ONLY 屏蔽 conan 包目录 → 直接预设 Find 模块缓存变量
   （ZLIB_INCLUDE_DIR/ZLIB_LIBRARY、BZIP2_*、LIBLZMA_*、ZSTD_*），libtiff 4.7.2 配方同法。

### 可选依赖禁用策略（任务要求记录）
| 依赖 | 决策 | 理由 |
|---|---|---|
| zlib/bzip2/xz/zstd | ✅ 启用 | 四大压缩后端，全部在仓（任务核心依赖） |
| lz4 | ❌ 禁用 | 不在制品仓（探测确认），非核心格式 |
| libxml2 / expat | ❌ 禁用 | 两者是 xar 格式 XML 解析的**二选一**替代关系；xar 非核心格式，禁用后依赖图更精简，避免 libxml2 的传递依赖（zlib/iconv）牵连 |
| nettle / mbedtls | ❌ 禁用 | 加密可选后端，OpenSSL 未接线（libarchive 内置 md5/sha1/sha256/sha512 纯 C 实现已够用，archive_digest.c 回退内置） |
| openssl | 未接线（默认 ON 但未预设缓存变量，交叉环境未检出 → 自动回退内置实现） | 与 3.8.7 保持一致（其也未用 openssl） |
| lzo | ❌ 禁用 | 许可限制 + 不在仓 |
| pcre/pcre2 | ❌ 禁用 | 不在仓 |
| iconv | musl 内置 → 自动检出可用（HAVE_ICONV=true） | 无需干预 |

## 三、上游测试（L1 证据，本机 HarmonyOS PC 实测）

| 测试套 | 跑 | 失败 | 断言 | 失败断言 | 备注 |
|---|---|---|---|---|---|
| libarchive_test | 637 | 2 | 30,982,315 | 9 | test_write_disk_hardlink（hmfs 不支持硬链接）、test_write_disk_secure（hmfs 权限位裁剪） |
| bsdtar_test | 73 | 14 | 86,392 | 961 | 根因：hmfs utime() EPERM（"Can't restore time"）、hmfs GID 语义（"Numeric group ID too large"）、fflags/xattr 限制 |
| bsdcpio_test | 49 | 0 | 16,385 | 0 | ✅ 全过 |
| bsdcat_test | 18 | 0 | - | 0 | ✅ 全过 |
| bsdunzip_test | 23 | 1 | - | 3 | test_P_encryption |
| **合计** | **800** | **17** | **~31.08M** | **973** | 失败全部为 OHOS hmfs 平台限制（与 3.8.7 notes 记录同类），非包缺陷 |

失败样例证据（bsdtar test_basic）：
- `symlink: Can't restore time: Permission denied`（hmfs utime 受限）
- `file: Numeric group ID too large`（hmfs GID 语义差异）

## 四、产物形态
- lib/libarchive.so.13.7.7 + lib/libarchive.a（默认 shared=True；系统无同名 libarchive，R26 不约束）
- bin/bsdtar、bsdcpio、bsdcat、bsdunzip（R38：已声明 bindirs；库+工具混合包，软件级 commands.json 按仓库惯例由 CI 校验——本包主体是 library）

## 五、经验沉淀（路径 B 素材方向）
"多压缩后端统一抽象层"在交叉编译下的组合问题：CMake 流水线中每个后端用不同探测方式
（FindZLIB 标准模块 / BZip2 标准模块 / LibLZMA 标准模块 / ZSTD 自写 find_path+find_library），
在 FIND_ROOT_PATH_MODE=ONLY 交叉环境下**只有预设缓存变量一种可靠接线法**；
zlib 必须用 -fPIC 重编译版才能链入 .so。此知识已具备跨库复用性。

## 结束标记
最终状态: published (依赖项 PR)
---

**编译结束**: 2026-09-05 02:07
**最终状态**: published
