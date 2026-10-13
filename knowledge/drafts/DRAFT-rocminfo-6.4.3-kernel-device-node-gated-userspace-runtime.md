# 内核设备节点门控的用户态运行时库不可适配判定：构建期 REQUIRED 依赖零命中 + 运行期硬编码 `/dev/kfd` 且平台无该内核驱动与硬件

> 草稿来源：`rocminfo` 6.4.3 适配任务（平台任务 `10212`，`taskBranch = feat/rocminfo-6.4.3`）
> 状态：DRAFT（预审 `create`，待人工/复审转正式 E 条目）
> 日期：2026-10-04
> 实测环境：WSL2 Ubuntu 22.04（宿主，**无 AMD GPU**）；OHOS 6.0 SDK `/root/ohpc/sdk/ohos-6.0`；
> `native/llvm` **clang 15.0.4**，target `aarch64-unknown-linux-ohos`，sysroot `native/sysroot`
> 申报记录：【无法适配】issue [#3625](https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos/issues/3625)
> 相邻条目：`DRAFT-jool-modules-lts-6.18.39-kernel-module-not-deliverable`（内核模块类，互为边界）；
> `DRAFT-x86-simd-only-c-library-aarch64-scalar-fallback`（有回退 ⇒ **可**适配，反例）

---

## 1. 适用场景（什么时候该想起这条）

任务里的三方库，其**全部功能**是"**通过某个内核驱动暴露的设备节点，枚举/操作平台硬件**"。
判别提问只有一句：

> **「把设备节点与硬件去掉后，本库是否还有可交付语义？」**

- 答**否** ⇒ 命中本条，应直接判 `env_unsupported`（本案例 `rocminfo`：移除 KFD/AMD GPU 后**没有任何剩余语义**）；
- 答**是** ⇒ **不**适用本条，应正常适配（如只打包头文件/构建宏，或库另有纯软件回退路径）。

判别特征（任一组合命中即入本判）：

- `CMakeLists.txt` 出现 `find_package(<runtime> REQUIRED)`，且该运行时**不在** SDK sysroot / 制品仓；
- 源码直接 `#include` 某运行时的头（本案例 `hsa/hsa.h`、`hsa/hsa_ext_amd.h`）；
- 其下层 thunk 源码里出现**硬编码设备节点字面量**（本案例 `"/dev/kfd"`）或 sysfs 拓扑路径
  （本案例 `/sys/class/kfd/kfd/topology/nodes/`）；
- 上游 README 明说 target platform 依赖某厂商驱动集/硬件。

**反例（不入本判）**：库虽引用设备节点，但有**纯软件回退**或**可交付子集**；或它只是
把厂商**头文件/构建宏**打包（如 `rocm-hipamd` 这类 header-only 包本身是可适配的，
本条的阻塞是**它的消费者**要真的运行时）。

---

## 2. 判定清单（全部为可复现命令）

| 步骤 | 命令 | 判据 |
|---|---|---|
| ① 构建期硬依赖 | `grep -n 'find_package(.*REQUIRED' CMakeLists.txt` | 出现 ⇒ 记下运行时名，进入② |
| ② 制品仓检索 | `conan search -r ohpcd 'hsa*'`、`'hsakmt*'`、`'rocr*'` | **全 0 命中** ⇒ 依赖链整条断裂 |
| ②b **下包看内容** | `conan download <疑似包> -r ohpcd` 后 `find` 其 `p/` 目录 | 名字像不等于能用：`rocm-hipamd/5.7.1` 实为 header-only（无 `.so`、无 `hsa.h`） |
| ③ 平台能力核查 | `find $SYSROOT -iname '*hsa*' \| wc -l` | **0** ⇒ SDK 未提供该运行时 |
| ③b **反例核对（必做）** | `find $SYSROOT -iname '*kfd*' -o -iname '*amdgpu*'` | KFD/AMDGPU **UAPI 头存在** ⇒ "缺内核头"论据**不成立**，不得写进报告 |
| ④ 目标工具链实测 | `cmake -DCMAKE_SYSTEM_NAME=OHOS -DCMAKE_SYSROOT=$SYSROOT -DCMAKE_CXX_COMPILER=$OHOS_CXX .` | `CMAKE_EXIT=1`（贴原始报错） |
| ⑤ 运行期硬编码 | `grep -rn '"/dev/kfd"' <runtime-src>/` | 命中 ⇒ 阻塞在**内核态**，用户态无法绕 |
| ⑥ 设备节点确认 | `ls -l /dev/kfd; ls /sys/class/kfd` | 不存在 ⇒ 平台无该内核驱动 |
| ⑦ **决定性运行期实测（强推）** | 见 §3.5 | 抓 `openat("/dev/kfd",…) = -1 ENOENT` ⇒ 结论从"构建不过"升级为"构建过了也确定不可用" |

---

## 3. 实测证据（rocminfo 6.4.3）

### 3.1 上游与版本

GitHub tag 归档 `rocm-6.4.3.tar.gz`：**27,947 bytes**，
sha256 `0aa040963daaa2b5ebbec818a2d53c83612912686336160c223fb664dc0ca92b`（NCSA 许可）。
全树仅 **27** 个文件，真正源码只有 **1 个 C++ 文件** `rocminfo.cc`（1336 行）+ 1 个 Python 脚本
`rocm_agent_enumerator`（278 行）。

### 3.2 构建期第一道门（实测失败）

```cmake
# CMakeLists.txt:63
find_package(hsa-runtime64 1.0 REQUIRED )
```

用 **真实 OHOS 工具链**配置的实测结果：

```console
$ cmake -DCMAKE_SYSTEM_NAME=OHOS \
        -DCMAKE_CXX_COMPILER=$SDK/native/llvm/bin/aarch64-unknown-linux-ohos-clang++ \
        -DCMAKE_SYSROOT=$SDK/native/sysroot <rocminfo-6.4.3>
CMake Error at CMakeLists.txt:63 (find_package):
  By not providing "Findhsa-runtime64.cmake" in CMAKE_MODULE_PATH this
  project has asked CMake to find a package configuration file provided by
  "hsa-runtime64", but CMake did not find one.
    hsa-runtime64Config.cmake
    hsa-runtime64-config.cmake
CMake_EXIT=1
```

源码侧同样是 HSA API 的**直接**调用——共 **29** 个唯一 `hsa_*` 符号，其中
`hsa_agent_get_info` 41 次、`hsa_system_get_info` 12 次、`hsa_isa_get_info_alt` 12 次。

### 3.3 制品仓零命中（本次复验）

```console
$ conan search -r ohpcd 'hsa*'     → Found 0 pkg/version recipes
$ conan search -r ohpcd 'hsakmt*'  → Found 0
$ conan search -r ohpcd 'kfd*'     → Found 0
$ conan search -r ohpcd 'rocm*'    → Found 2: rocm-cmake/0.12.0, rocm-hipamd/5.7.1
```

**②b 步骤的价值**——把唯一"看起来像运行时"的包下下来看内容：

```console
$ conan download 'rocm-hipamd/5.7.1:*' -r ohpcd
$ find ~/.conan2/p/rocm-c933e05609fbe/p -maxdepth 2
  include/hip         cmake/FindHIP.cmake        bin/hipdemangleatp
  cmake/hip-lang-config.cmake.in                 bin/hipcc_cmake_linker_helper
$ find ... -name '*.so*'   → (无输出)
$ find ... -name 'hsa.h'   → (无输出)
```

即仓内的"rocm"只是**头文件 + 构建宏 + 辅助脚本**，**没有任何 HSA 运行时**，
无法满足 `find_package(hsa-runtime64 1.0 REQUIRED)`。

### 3.4 平台能力核查 + **反例自我否定**

```console
$ SDK=/root/ohpc/sdk/ohos-6.0/native/sysroot
$ find $SDK -iname '*hsa*' | wc -l                      → 0
$ find $SDK \( -name 'libhsa*' -o -name 'libhsakmt*' \) → (无输出)

# ⚠️ 反例：这两条不成立，不得作为阻塞理由
$ find $SDK -iname '*kfd*'
  $SDK/usr/include/linux/kfd_ioctl.h          ← 存在！
$ find $SDK -iname '*amdgpu*'
  $SDK/usr/include/drm/amdgpu_drm.h           ← 存在！
```

**所以"鸿蒙缺 KFD 头文件"这条论据是不成立的**（★2026-10-05 真机复核补充）——OHOS 的 bionic UAPI 集合覆盖了
上游 Linux UAPI（含 AMD 的 ioctl 编号）。真正的缺口在**内核侧驱动 + 设备节点 + 硬件**三处。

> ★**2026-10-05 真机复核补充（区分构建期与运行期）**★
>
> 上述反例针对**构建期**的 SDK sysroot。真机复核发现**运行期**情况不同，两处必须分开写：
>
> | 位置 | `linux/kfd_ioctl.h` | `drm/amdgpu_drm.h` | 说明 |
> |---|---|---|---|
> | 构建期 `$SYSROOT/usr/include` | **存在**（11,218 B） | **存在**（19,939 B） | ⇒ "缺头"论据不成立 |
> | 运行期 真机 `/usr/include` | **不存在**（实测 `F_absent`） | **不存在**（实测 `F_absent`） | 头未随镜像部署 |
>
> 实测命令与输出（真机 DAYU200-RK3568 / OpenHarmony 6.0.0.47）：
>
> ```console
> $ ls /usr/include/linux/kfd_ioctl.h
> ls: /usr/include/linux/kfd_ioctl.h: No such file or directory
> $ ls /usr/include/drm/amdgpu_drm.h
> ls: /usr/include/drm/amdgpu_drm.h: No such file or directory
> ```
>
> **结论不变且更强**：缺的从来不是"头文件有没有"，而是**内核侧驱动 + `/dev/kfd` 设备节点
> + AMD GPU 硬件**三处。本判据**完全不依赖**"缺头"这一论据，故构建期/运行期的差异
> 不影响判定成立。
>
> **补充反例②**：真机 `/dev/dri` 实有 `card0` 与 `renderD128` ⇒ **平台有 GPU，只是非 AMD**。
> 因此"OHOS PC 没有 GPU"同样是**错误**论据，不得写进报告。
（同理，仓内存在 `libomptarget-rtl-amdgpu/18.1.8` 这类 GPU 插件**不能**反推平台支持 AMD GPU：
那类插件"能编过但注册 0 设备"。）

### 3.5 运行期硬依赖 + **决定性实测**（本条最强证据）

补上运行时也过不了第二道门。`ROCR-Runtime` 源码
（`rocm-6.4.3.tar.gz`，**2,292,387 bytes**，
sha256 `3b23bed04cbed72304d31d69901eb76afa2099c7ac37f055348dfcda2d25e41a`）中：

```c
// libhsakmt/src/openclose.c:47,178
static const char kfd_device_name[] = "/dev/kfd";
...  fd = open(kfd_device_name, O_RDWR | O_CLOEXEC);
```

```cpp
// runtime/hsa-runtime/core/driver/kfd/amd_kfd_driver.cpp:131
auto tmp_driver = std::unique_ptr<core::Driver>(new KfdDriver("/dev/kfd"));
```

**关键实验（建议所有同类判定都做）**：在**无 AMD GPU** 的宿主上，用 Ubuntu 归档的
**真实** `libhsa-runtime64` + `libhsakmt`（ROCt thunk），配 `ROCR-Runtime` 6.4.3 的
匹配头文件，把 `rocminfo` **真正编出来**并运行：

```console
$ ldd rocminfo | grep -Ei 'hsa|hsakmt'
  libhsa-runtime64.so.1 => .../libhsa-runtime64.so.1
  libhsakmt.so.1        => .../libhsakmt.so.1          ← 真链接成功
$ ls -l rocminfo
  -rwxr-xr-x 1 root root 220640 ... rocminfo

# 宿主前置条件：确认无 AMD GPU / 无 KFD
$ ls -l /dev/kfd ; ls /sys/class/kfd ; ls -l /dev/dri
  No such file or directory  ×3
$ lspci | grep -iE 'amd|radeon|vga'     → (none)

# === 运行实测 ===
$ ./rocminfo
WSL environment detected.
hsa api call failure at: rocminfo.cc:1306
Call returned HSA_STATUS_ERROR_OUT_OF_RESOURCES: The runtime failed to allocate
the necessary resources. ...
EXITCODE=8

# === strace 抓到那一次失败的系统调用 ===
$ strace -f -e trace=openat ./rocminfo | grep -iE 'dxg|kfd'
openat(AT_FDCWD, "/dev/dxg", O_RDONLY)          = 3
openat(AT_FDCWD, "/dev/kfd", O_RDWR|O_CLOEXEC)  = -1 ENOENT (No such file or directory)
```

**回退路径同样死掉**——自带的 `rocm_agent_enumerator` 会退到读 KFD 拓扑：

```python
# rocm_agent_enumerator:192
topology_dir = '/sys/class/kfd/kfd/topology/nodes/'
```

```console
$ python3 rocm_agent_enumerator ; echo "EXITCODE=$?  stdout_bytes=$(wc -c < out)"
EXITCODE=0  stdout_bytes=0
$ ls /sys/class/kfd/kfd/topology/nodes/
ls: cannot access '...': No such file or directory
```

即：**没有任何一条路径能绕开 KFD**。

### 3.6 不得裁剪

`rocminfo` 是**单一功能**工具：`hsa_init()` → 枚举 agents → 打印属性。
没有 GPU 时不存在"降级可用"的子集；把 `hsa_init()` 换成空实现得到的只是恒失败的壳
（属空壳红线）。平台明确"软件要求绝对不能裁剪"，故只交付名称而无实际功能的产物不可接受。

---

## 4. 为什么不判「暂时搁置」

对齐"依赖未适配 ⇒ 暂时搁置"的区分口径：本条的缺口**不是一个可自行适配的库**，
而是**内核态驱动 + 硬件**。

| 假设动作 | 能否解决 | 原因 |
|---|---|---|
| 自行写 `hsa-runtime64` 的 conan 配方 | ⚠️ 只解决构建 | 能编出 `libhsa-runtime64.so`，但运行期仍要 `/dev/kfd` |
| 自行适配 `ROCR-Runtime` + `libhsakmt` | ❌ 不能 | `libhsakmt` 的语义就是"与 ROCk 内核驱动通话"，无驱动即无对象 |
| 在 OHOS 上构建/加载 `amdkfd` | ❌ 不能 | 内核态交付，超出用户态 conan 框架；且需 AMD GPU 与整套 AMDGPU 驱动集 |
| 换设备 / 换网络 | ❌ 不能 | OHOS PC 为麒麟 SoC + 自研 GPU，不含 AMD 显卡 |

故判 `技术不可行` / `env_unsupported`。

---

## 5. 处置与禁止项

**建议处置**：
1. 判 `env_unsupported`，按仓库手册【无法适配】issue 通道申报（**不建配方包目录**，
   否则 CI 报 `No packages to build` + exit 1 会被误判 rule4 编译失败）；先例
   #3163 / #3339 / #3340 / #3347 / #3624 / #3625；
2. 另开【知识库扩展】草稿 PR 沉淀本条通用判据（先例：mexce 1.0.1 的
   "ISA 依赖型 JIT 后端库不可适配判定"）。

**禁止项**：

| 禁止做法 | 理由 | 后果 |
|---|---|---|
| 删掉/降级 `find_package` 的 `REQUIRED` 让它"编过" | 源码仍需真实运行时符号；运行期必然因无 `/dev/kfd` 失败 | 伪适配，目标机零功能，判任务失败 |
| 伪造 `hsa.h` / 桩化 `hsa_init()` | 无法补齐内核驱动与硬件这一真实缺口 | 恒失败空壳，违反"不得裁剪"与空壳红线 |
| 交付预编译二进制 | 不经构建链、不可审计 | 违反仓库规范 |
| 把"自己写个软件 GPU 模拟器"当适配交付 | 属重写而非适配 | 超出三方库适配任务范畴 |

---

## 6. 证据复现命令

```bash
# 上游可下载性与校验
curl -sSL -o rocminfo-rocm-6.4.3.tar.gz \
  https://github.com/ROCm/rocminfo/archive/refs/tags/rocm-6.4.3.tar.gz
sha256sum rocminfo-rocm-6.4.3.tar.gz
# 0aa040963daaa2b5ebbec818a2d53c83612912686336160c223fb664dc0ca92b  (27947 bytes)

# 构建期第一道门（期望失败）
tar xzf rocminfo-rocm-6.4.3.tar.gz && mkdir b && cd b
cmake -DCMAKE_SYSTEM_NAME=OHOS -DCMAKE_CXX_COMPILER=$OHOS_CXX \
      -DCMAKE_SYSROOT=$SYSROOT ../rocminfo-rocm-6.4.3      # CMAKE_EXIT=1

# 制品仓检索
conan search -r ohpcd 'hsa*' ; conan search -r ohpcd 'hsakmt*' ; conan search -r ohpcd 'rocm*'

# 平台能力 + 反例
find $SYSROOT -iname '*hsa*' | wc -l            # 0
find $SYSROOT -iname '*kfd*'                    # 存在（反例，不得用作阻塞理由）

# 运行期硬依赖
curl -sSL -o rocr.tar.gz \
  https://github.com/ROCm/ROCR-Runtime/archive/refs/tags/rocm-6.4.3.tar.gz
sha256sum rocr.tar.gz
# 3b23bed04cbed72304d31d69901eb76afa2099c7ac37f055348dfcda2d25e41a  (2292387 bytes)
tar xzf rocr.tar.gz && grep -rn '"/dev/kfd"' ROCR-Runtime-rocm-6.4.3/

# 决定性实测：用真实运行时编出并运行（宿主需无 AMD GPU）
apt-get download libhsa-runtime64-1 libhsa-runtime-dev libhsakmt1
# 解包后以 ROCR-Runtime 6.4.3 的 inc/ 为头文件前缀配置、链接，然后：
strace -f -e trace=openat ./rocminfo | grep -i kfd
# openat(AT_FDCWD, "/dev/kfd", O_RDWR|O_CLOEXEC) = -1 ENOENT
./rocminfo ; echo $?    # HSA_STATUS_ERROR_OUT_OF_RESOURCES → 8
```

---

## 7. 推广价值（为什么这是"一条通用判据"而非单库补丁）

本条的**判定流程**可跨库复用：

1. **"构建期 REQUIRED + 制品仓零命中"** ⇒ 任何 `find_package(X REQUIRED)` 且 X 不在仓的库都适用；
2. **"②b 下包看内容"** ⇒ 防止被"名字像"的包误导（本案例 `rocm-hipamd` 名字像运行时，实为 header-only）；
3. **"反例自我否定"** ⇒ 强制核对"看似缺失但实际存在"的项（本案例 KFD/AMDGPU UAPI 头），
   这正是仓库手册要求"必须写反例"的落地做法，避免整份报告被一句"论据不成立"驳回；
4. **"决定性运行期实测"** ⇒ 在**无该硬件**的宿主上把工具**真编真跑**，用 `strace` 指认那一次
   失败的系统调用。这是把结论从"我配不过"抬到"配过了也确定不可用"的**唯一**办法，
   可推广到一切"构建期依赖缺失 + 运行期设备门控"的库（GPU/NPU/专用加速器运行时、
   其它 `/dev/*` 节点门控的运行时）。

与 `kernel-module-not-deliverable` 类的边界一句话：
**那条的交付物本身是内核模块；本条的交付物是用户态二进制，只是被内核驱动门控。**
