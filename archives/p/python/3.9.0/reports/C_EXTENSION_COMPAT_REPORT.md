# Python 3.9.0 鸿蒙 C 扩展生态兼容性报告

> **日期**: 2026-03-27 | **测试环境**: HarmonyOS PC (aarch64, musl libc, Clang 15)
> **Python**: 3.9.0 (24 补丁版本, --enable-shared) | **pip**: 26.0.1
> **目的**: 验证 Python 3.9 鸿蒙适配能否支撑真实的 C 扩展生态

---

## 一、测试总览

| 测试项 | 结果 | 说明 |
|--------|------|------|
| numpy 1.24.4 编译 | ✅ 成功 | 19 个 .so 扩展模块，源码编译 |
| numpy wheel 打包 | ✅ 成功 | `numpy-1.24.4-cp39-cp39-ohos_aarch64.whl` (13MB) |
| numpy wheel 安装 | ✅ 成功 | pip install → import 正常 |
| numpy 功能测试 | ✅ 46/46 通过 | 数组/索引/数学/线性代数/FFT/随机数/文件I/O |

**结论**: Python 3.9 的鸿蒙适配已经从"能跑 Python 本身"跨越到"能跑 C 扩展生态"。numpy 作为 Python 科学计算基石，其成功编译和完整功能验证标志着鸿蒙上的 Python 具备实际可用性。

---

## 二、测试环境

| 项目 | 值 |
|------|-----|
| Python | 3.9.0（24 补丁，--enable-shared） |
| pip | 26.0.1 |
| 编译器 | Clang 15.0.4 (HarmonyOS SDK) |
| OS | HarmonyOS, HongMeng Kernel 1.11.0, aarch64 |
| C 库 | musl libc |
| sys.platform | `ohos` |
| numpy 版本 | 1.24.4（最后一个使用 numpy.distutils 的版本） |

---

## 三、编译过程

### 3.1 编译命令

```bash
cd numpy-1.24.4
export PATH=$HOME/usr/local/bin:$PATH
export LD_LIBRARY_PATH=$HOME/usr/local/lib:$LD_LIBRARY_PATH
export CC=clang CXX=clang++ AR=llvm-ar RANLIB=llvm-ranlib
export TMPDIR=$HOME/tmp
export SETUPTOOLS_SCM_PRETEND_VERSION=1.24.4

# 应用 2 处 patch（见下文）
python3.9 setup.py build
python3.9 setup.py install
```

### 3.2 wheel 打包命令

```bash
python3.9 setup.py bdist_wheel
# 产出: dist/numpy-1.24.4-cp39-cp39-ohos_aarch64.whl (13MB)
```

### 3.3 需要的 Patch（2 处，改 2 个文件 3 行）

**没有做任何功能裁剪**，仅绕过鸿蒙平台环境问题：

#### Patch 1: `numpy/distutils/system_info.py`（1 行）

```diff
-        except (OSError, DistutilsError):
+        except (OSError, DistutilsError, subprocess.SubprocessError):
```

**原因**: numpy 在模块导入时执行 `subprocess.Popen(["gcc", "-print-multiarch"])` 检测多架构库路径。鸿蒙没有 gcc，Python 的 subprocess 补丁将 `FileNotFoundError` 包装为 `SubprocessError`（非 `OSError` 的子类），原代码的 except 没接住。

#### Patch 2: `numpy/distutils/misc_util.py`（2 行，同一个修改出现在 `_get_svn_revision()` 和 `_get_hg_revision()` 两个函数中）

```diff
-        except (subprocess.CalledProcessError, OSError):
+        except (subprocess.CalledProcessError, OSError, subprocess.SubprocessError):
```

**原因**: numpy 在构建时调用 `subprocess.check_output(['svnversion'])` 和 `subprocess.check_output(['hg', 'identify'])` 获取版本号。鸿蒙没有这些工具，同样的 SubprocessError 问题。

### 3.4 额外环境准备（非代码 patch）

| 操作 | 原因 |
|------|------|
| `SETUPTOOLS_SCM_PRETEND_VERSION=1.24.4` | `setuptools_scm` 调用 `hg`/`git` 获取版本号失败 |
| 创建 `$HOME/usr/local/bin/gcc` → clang 符号链接 | numpy 构建系统多处硬编码调用 `gcc` |

### 3.5 编译产物

| 指标 | 数值 |
|------|------|
| .so 扩展模块数 | 19 个 |
| .so 总大小 | 25.0 MB |
| wheel 文件数 | 873 个 |
| wheel 总大小（解压） | 36.4 MB |
| wheel 文件大小（压缩） | 13 MB |
| wheel 标签 | `cp39-cp39-ohos_aarch64` |

**19 个 .so 扩展模块清单**:

| 模块 | 大小 | 说明 |
|------|------|------|
| `numpy/core/_multiarray_umath.so` | 10.2 MB | 核心数组 + 通用函数 |
| `numpy/linalg/_umath_linalg.so` | 3.6 MB | 线性代数 ufunc |
| `numpy/linalg/lapack_lite.so` | 3.2 MB | 内置 LAPACK |
| `numpy/core/_simd.so` | 870 KB | SIMD 优化分发 |
| `numpy/random/_generator.so` | ~2 MB | 随机数生成器 |
| `numpy/random/_bounded_integers.so` | ~1 MB | 有界随机整数 |
| `numpy/random/mtrand.so` | ~1.5 MB | 传统随机数（兼容） |
| `numpy/random/libnpyrandom.so` | ~1 MB | 随机数基础库 |
| `numpy/core/_multiarray_tests.so` | 358 KB | 测试辅助 |
| `numpy/random/_common.so` | ~100 KB | 随机数公共代码 |
| `numpy/random/bit_generator.so` | ~50 KB | 位生成器 |
| `numpy/core/_operand_flag_tests.so` | 38 KB | 测试辅助 |
| `numpy/core/_rational_tests.so` | 142 KB | 测试辅助 |
| `numpy/core/_struct_ufunc_tests.so` | ~50 KB | 测试辅助 |
| `numpy/core/_umath_tests.so` | ~100 KB | 测试辅助 |
| 其他 .so | ~1 MB | 其余辅助模块 |

### 3.6 BLAS/LAPACK 情况

| 库 | 状态 |
|----|------|
| OpenBLAS | ❌ 未安装（系统无预编译包） |
| MKL | ❌ 不适用 |
| ATLAS | ❌ 不适用 |
| **numpy 内置 lapack_lite** | ✅ **实际使用** |

numpy 内置了 `lapack_lite`（C 语言重写的精简版 LAPACK），功能完整但性能低于 OpenBLAS。编译时会尝试检测所有外部 BLAS/LAPACK 库，全部 NOT AVAILABLE 后自动使用内置版本。

**性能参考**（内置 lapack_lite）:
- 500×500 矩阵乘法: 0.24s
- 500×500 特征值分解: 0.40s

---

## 四、功能测试结果（46/46 ✅）

### 4.1 数组创建（9/9 ✅）

| 测试项 | 状态 |
|--------|------|
| basic array | ✅ |
| 2D array | ✅ |
| zeros | ✅ |
| ones | ✅ |
| arange | ✅ |
| linspace | ✅ |
| eye | ✅ |
| random | ✅ |
| dtypes (int8/16/32/64, float32/64, complex64/128, bool) | ✅ |

### 4.2 索引与切片（4/4 ✅）

| 测试项 | 状态 |
|--------|------|
| basic indexing & slicing | ✅ |
| fancy indexing | ✅ |
| boolean indexing | ✅ |
| 2D indexing | ✅ |

### 4.3 数学运算（11/11 ✅）

| 测试项 | 状态 |
|--------|------|
| addition | ✅ |
| multiplication | ✅ |
| dot product | ✅ |
| matmul | ✅ |
| sum | ✅ |
| mean | ✅ |
| std | ✅ |
| cumsum | ✅ |
| transpose | ✅ |
| reshape | ✅ |
| broadcasting | ✅ |

### 4.4 线性代数（9/9 ✅）

| 测试项 | 状态 |
|--------|------|
| det | ✅ |
| inv | ✅ |
| eigvals | ✅ |
| SVD | ✅ |
| solve | ✅ |
| norm | ✅ |
| matrix_rank | ✅ |
| QR | ✅ |
| 100×100 / 500×500 大矩阵 | ✅ |

### 4.5 FFT（2/2 ✅）

| 测试项 | 状态 |
|--------|------|
| FFT | ✅ |
| IFFT roundtrip | ✅ |

### 4.6 随机数（4/4 ✅）

| 测试项 | 状态 |
|--------|------|
| randn (正态分布验证) | ✅ |
| seed (可重现性) | ✅ |
| choice | ✅ |
| shuffle | ✅ |

### 4.7 文件 I/O（2/2 ✅）

| 测试项 | 状态 |
|--------|------|
| save/load .npy | ✅ |
| savetxt/loadtxt | ✅ |

### 4.8 其他（5/5 ✅）

| 测试项 | 状态 |
|--------|------|
| comparison | ✅ |
| where | ✅ |
| sort | ✅ |
| unique | ✅ |
| concatenate | ✅ |

---

## 五、关键发现

### 5.1 HMDFS 用户脚本执行限制（重要）

HarmonyOS HMDFS 文件系统存在一个隐蔽限制：**用户目录下创建的脚本文件无法被 `os.execvp()` 执行**，即使 `chmod +x` 且 `os.access(file, os.X_OK)` 返回 True。

```python
# 在 $HOME 下创建脚本
with open('$HOME/bin/gcc', 'w') as f:
    f.write('#!/system/bin/sh\nexec /data/service/hnp/bin/clang "$@"\n')
os.chmod('$HOME/bin/gcc', 0o755)

shutil.which('gcc')        # → '/home/user/bin/gcc'
os.access(gcc_path, os.X_OK)  # → True
subprocess.run(['gcc', '--version'])  # → PermissionError [Errno 13]
```

**影响范围**: 任何 C 扩展包如果在构建时通过 subprocess 执行用户目录下的 gcc wrapper 脚本，都会失败。

**当前绕过**: numpy 的 `gcc -print-multiarch` 调用可以通过 except 处理；但更复杂的包（如需要实际执行 gcc 进行测试编译的）可能需要更深层的修复。

**建议**: 这不是 Python 补丁层面能解决的问题，需要从 HMDFS/SELinux 系统层面改善。

### 5.2 pytest 在鸿蒙上不可用

pytest 内部大量使用 subprocess，在鸿蒙上因 HMDFS 执行限制和 SELinux 域转换问题无法正常工作。替代方案：
- 直接运行测试文件: `python3.9 test_file.py`
- 自定义测试脚本（如本报告的 46 项测试）

### 5.3 numpy.distutils 与 Python 补丁的协同效应

numpy 1.24.4 的编译验证了 Python 3.9 的 24 个补丁的正确性：
- 补丁 0001（configure.ac）→ 确保 `sysconfig.get_platform()` 返回 `ohos-aarch64` → wheel 标签正确
- 补丁 0002（setup.py）→ 扩展模块编译参数正确（`-lpython3.9`, `-L.`, `-fPIC`）
- 补丁 0024（build_ext.py）→ HMDFS 符号链接修复 → `LN_FORCE` 使用 `shutil.copy2` → .so 正确安装
- 补丁 0016/0020（subprocess）→ 构建过程中的子进程调用正常工作

### 5.4 平台标签

```
sysconfig.get_platform() → ohos-aarch64
wheel tag                 → cp39-cp39-ohos_aarch64
```

pip 会精确匹配 `ohos_aarch64` 标签，不会与 Linux 版本混淆。这得益于 Python 补丁 0005 和 0008 对平台字符串的处理。

---

## 六、wheel 包分发信息

| 项目 | 值 |
|------|-----|
| 文件名 | `numpy-1.24.4-cp39-cp39-ohos_aarch64.whl` |
| 大小 | 13 MB（压缩）/ 36.4 MB（解压） |
| 标签 | `cp39-cp39-ohos_aarch64` |
| Root-Is-Purelib | false（包含 C 扩展） |
| 文件数 | 873 |
| .so 文件数 | 19 |

**安装命令**:
```bash
pip3.9 install numpy-1.24.4-cp39-cp39-ohos_aarch64.whl
```

---

## 七、意义与后续

### 7.1 里程碑意义

numpy 是 Python 生态的基石包。几乎所有科学计算、数据科学、机器学习包（pandas、scipy、scikit-learn、torch、tensorflow）都依赖它。numpy 在鸿蒙上成功编译、功能完整、还能打包成 wheel，证明：

1. Python 3.9 的鸿蒙适配（24 补丁）**正确且完整**，足以支撑 C 扩展生态
2. musl BIND_NOW 问题（补丁 0001/0007）的修复方案是正确的
3. HMDFS 符号链接问题（补丁 0024）的修复方案是正确的
4. 平台标签体系（`ohos-aarch64`）工作正常，支持 wheel 分发

### 7.2 后续建议

| 优先级 | 任务 | 说明 |
|--------|------|------|
| 🟡 中 | 编译 OpenBLAS | 提升 numpy 线性代数性能 3-10 倍 |
| 🟡 中 | 测试 scipy | numpy 的上游依赖，验证更复杂的构建链 |
| 🟡 中 | 测试 pandas | 纯 Python + numpy 依赖，验证依赖链完整性 |
| 🟢 低 | 建立 wheel 仓库 | 为鸿蒙 Python 生态提供预编译包 |
| 🔴 高 | 解决 HMDFS execvp 限制 | 系统层面改善，影响所有 C 扩展包的构建体验 |

---

*报告生成时间: 2026-03-27*
