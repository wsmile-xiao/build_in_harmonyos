# E-DRAFT: libyal 发布包自带 `config.sub` 的 ohos 分支随版本变化

- **触发实例**：libfsxfs 20240501 全新包适配（2026-09-19，任务 libfsxfs-20240501，分支 feat/libfsxfs-20240501）
- **错误签名**：`OS 'ohos' not recognized` / `Invalid configuration 'aarch64-unknown-linux-ohos'`
- **类别**：ohos-triplet（autotools 配置阶段）
- **严重度**：2（确定性失败，处置模式固定；不影响库本身）

## 症状

libyal 发布包（`*-<版本>.orig.tar.gz`，自带预生成 `configure`）用「标准」ohos 三元组配置：

```text
checking build system type... Invalid configuration 'aarch64-unknown-linux-ohos': OS 'ohos' not recognized
configure: error: /data/service/hnp/bin/bash ./config.sub aarch64-unknown-linux-ohos failed
```

同一个包、同一台设备，只把三元组换成 `aarch64-unknown-linux-gnu`（`--build` 与 `--host` **相同**）：

```text
checking build system type... aarch64-unknown-linux-gnu
checking host system type... aarch64-unknown-linux-gnu
checking whether we are cross compiling... no
...
config.status: creating common/config.h        # 新生成的这份含 108 个 #define HAVE_*
```

G2 干净通过（上游 `make check` + `test_package` 全绿）。

## 根因

libyal 的 release/orig tarball 是 `make dist` 产物，**自带预生成的 `configure` 与 `config.sub`/`config.guess`**，
且不含 maintainer 模式。于是「三元组能否被识别」由**打包时那一版 gnulib `config.sub`** 决定：

| 包 / 版本 | `grep -c ohos config.sub` | `./config.sub aarch64-unknown-linux-ohos` | 可用三元组 |
|---|---|---|---|
| libfsxfs 20240501 | **0** | rc=1 `OS 'ohos' not recognized` | `aarch64-unknown-linux-gnu` |
| libvhdi 20251119 | >0 | rc=0 | `aarch64-unknown-linux-ohos` |
| libfsntfs 20251028（已合入配方） | — | — | `aarch64-unknown-linux-gnu` |

**同族不同版本结论相反**：照抄同族任一先例都可能直接命中或直接失败，必须现场取证。

### 对 E007 那句警告的澄清

E007「根因分析」写：*「若用 --build/--host 绕过则误判为交叉编译，导致 AC_RUN_IFELSE 等全部跳过，
生成错误 config.h」*。实测该后果只在 **build ≠ host**（真交叉）时成立。把两者设成**同一个**
非 ohos 三元组（`--build=aarch64-unknown-linux-gnu --host=aarch64-unknown-linux-gnu`）时，
configure 明确打印 `checking whether we are cross compiling... no`，AC_RUN_IFELSE 正常执行
（libfsxfs 实测：configure 新生成的 `common/config.h` 含 **108** 个 `#define HAVE_*`，
取数 `grep -c 'define HAVE_' <build_folder>/common/config.h`；tar 包内**自带**的那份是上游
make dist 遗留的旧文件、含 119 个，会被 config.status 覆盖，不可当读数）。

## 判定流程（两行取证）

```sh
# 1) 这个包的 config.sub 认识 ohos 吗？
grep -c ohos config.sub
# 2) 直接问 config.sub（不要问设备、不要问同族先例）
./config.sub aarch64-unknown-linux-ohos; echo "rc=$?"
```

- rc=0 → 用 `--build/--host=aarch64-unknown-linux-ohos`（libvhdi 形态）。
- rc≠0 → 回落 `--build/--host=aarch64-unknown-linux-gnu`（**两者必须相同**）。

`config.guess` 侧同理：设备 `uname -s` = `HarmonyOS` 无法自识别，三元组必须**显式**传，
两条都写进 `generate()` 的 `configure_args`。

## 禁止形态

1. **写死 ohos 三元组**（`--host=aarch64-unknown-linux-ohos`）而不先取证 → configure 第一阶段硬失败，
   且措辞像"工具链坏了"，把排查方向带偏到编译器/sysroot（本任务实测正是如此绕了一圈）。
2. **只改 host 不改 build**（`--build=…-gnu --host=…-ohos`）——**分两种情形**（W4 审计 P3 用本
   草稿自带 repro 实测纠正）：
   - 该版本 `config.sub` **不认识 ohos**（本包即此形态）：混合三元组在 `config.sub` 阶段就硬失败
     （`Invalid configuration 'aarch64-unknown-linux-ohos': OS 'ohos' not recognized`），
     **不会**进入交叉编译分支，也不产生假绿；
   - 该版本 `config.sub` **认识 ohos**（如 libvhdi 20251119）而只把 host 设成 ohos：configure 才会
     打印 `cross compiling... yes`、跳过全部 `AC_RUN_IFELSE`，生成与设备能力不符的 `config.h`，
     症状后移到运行期（难定位的假绿）。

## 复现

```sh
TASK_DIR=$HOME/tmp/libfsxfs-20240501
sh "$TASK_DIR/repro-e587-config-sub-triplet.sh"
```

脚本展开 orig tarball 后现场打印：`grep -c ohos config.sub`、两个三元组的 `config.sub` rc，
以及两种 `--build/--host` 组合下 configure 的 `whether we are cross compiling` 读数。

## 与既有条目的关系

- **E007**（patch-autotools-script）覆盖同一错误签名，但推荐方案是 `patch-autotools-ohos.pl` 打补丁。
  本条目补的是：①**同族版本差异**与「先取证再选」的流程；②**同三元组回落不会进入交叉编译**的
  实测反证（E007 的警告只适用于 build ≠ host）；③发布包自带生成物、无法 `autoreconf` 的边界。
- **E540**（shadow-ci runner-path-prepend）是另一层现象（构建期 PATH 找不到工具），与本条不重叠。
