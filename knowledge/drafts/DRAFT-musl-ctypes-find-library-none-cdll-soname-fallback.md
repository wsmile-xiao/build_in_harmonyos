# DRAFT: musl 平台 ctypes.util.find_library() 恒返回 None —— ctypes 纯 Python 库的 CDLL(SONAME) 兜底与显式依赖路径注入

- **草稿 ID**: DRAFT-musl-ctypes-find-library-none-cdll-soname-fallback
- **来源库**: legacycrypt 0.3（纯 Python 单文件，stdlib crypt 独立版；运行时依赖 libxcrypt 4.5.2，OHOS PC aarch64 / musl / clang 15）
- **状态**: 草稿（待主编 promote 为正式 E 条目；slug 为问题类命名，Exxx 编号由知识库主编确认）
- **案例落点**: `archives/l/legacycrypt/0.3/`（conandata.yml patches / conanfile.py / manifest.yaml knowledge_gained[1]）

## 一、机理叙事：find_library 三条探测路径在 musl 上全部失效

`ctypes.util.find_library(name)` 在 CPython 内部按顺序尝试三条路径：

1. **`_findSoname_ldconfig(name)`** —— 执行 `ldconfig -p` 读共享库缓存。
   musl 发行版（含 OHOS）**没有 `/sbin/ldconfig`**，这条路径不存在。
2. **`_findLib_gcc(name)`** —— 让 `gcc`（或 `cc`）输出链接搜索结果
   （`gcc -Wl,-t -lname` 之类）。OHOS 设备工具链是裸 clang，无 gcc/objdump
   可供 ctypes 调用，路径不可用。
3. **`_findLib_ld(name)`** —— 调 `ld` 或读 `LIBRARY_PATH`。同样依赖
   binutils 生态，设备上不存在。

三条全失效时函数返回 **None**——注意这与"库不存在"是两个概念：
**对任何库、包括设备上真实存在的共享库（连 musl 自带的 libm），返回值都是
None**。ctypes 文档中"find_library 找不到返回 None"的语义在这里被放大成
"永远返回 None"。

上游库（本案例 legacycrypt）按 glibc 生态假设写死加载链：

```python
_libname = _find_library('xcrypt')      # → None
if _libname is not None: ...
else:
    _libname = _find_library('crypt')   # → None
if _libname is not None:
    _libcrypt = _ctypes.CDLL(_libname)
else:
    raise OSError
except OSError:
    raise ImportError("libcrypt / libxcrypt missing") from None
```

结果：**库在 import 期不可用**，纯 Python 代码一行都没执行到。

### 与 E068 的衔接：E068 的修复恰好产出本条的 None 态

E068（find_library 崩溃）记录的是同一根因的**另一种失败签名**：旧版
Python 的 `_findSoname_ldconfig` 在 `ldconfig` 缺失时抛
**SubprocessError**（崩溃态）；其修复方式是给 Python stdlib 打补丁、让
find_library **直接 return None**（静默态）。

也就是说：**E068 的修复把"崩溃"转换成了"恒 None"**，而 None 态下游
（消费库侧）如何适配，E068 没有覆盖——它只给了 affected_scope 提示
（cffi/trio 等），没有给任何消费侧解法。本条补上的正是这一环：
在 musl 上，None ≠ 库不存在，消费库必须有能力在 find_library 返回
None 之后自行完成"按确切 SONAME 直载"的降级。

## 二、案例复现（自包含四步探针，真机实测）

legacycrypt 0.3 在 OHOS 设备上（2026-09-26，legacycrypt-0.3 run）：

```
$ PY=$(command -v python3 || echo /storage/Users/currentUser/usr/local/bin/python3)
$ XP=$(find /storage/Users/currentUser/.conan2/p -maxdepth 5 -name libcrypt.so.2 2>/dev/null | head -1 | xargs dirname)
$ $PY -c "import ctypes.util as u; print(u.find_library('crypt'), u.find_library('m'))"
None None                    # 连 musl 自带的 libm 都返回 None
$ $PY -c "import ctypes; ctypes.CDLL('libcrypt.so.2')"; echo rc=$?
OSError: Error loading shared library libcrypt.so.2: No such file or directory
rc=1                         # 依赖未就位时（discovery 阶段设备未装任何 libcrypt）
$ LD_LIBRARY_PATH=$XP $PY -c "import ctypes; print(ctypes.CDLL('libcrypt.so.2'))"
<CDLL 'libcrypt.so.2', handle 0x...>     # 注入依赖 lib 目录后 CDLL OK
$ readelf -d $XP/libcrypt.so.2.0.0 | grep SONAME
0x000000000000000e (SONAME)  Library soname: [libcrypt.so.2]   # NEEDED 仅 libc.so
```

佐证链：

- discovery 阶段实测（`tmp/oh-device-porting-v2/legacycrypt-0.3-discovery.md`）：
  `find_library('xcrypt')=None, ('crypt')=None, ('crypto')=None, ('z')=None,
  ('m')=None`；`import legacycrypt` 直接
  `ImportError: libcrypt / libxcrypt missing`。
- 修复后权威 CI（`tmp/oh-device-porting-v2/legacycrypt-0.3-ci-run1.log`）：
  build() 内 `python tests.py` 真实执行 8 用例（7 passed / 1 failed，
  失败为 libxcrypt failure-tokens 行为差异，与本条机理无关）；
  test_package 经显式 LD_LIBRARY_PATH 注入后 import + crypt() 往返 OK。
- 修复后模块态验证：`legacycrypt._libcrypt` 为
  `<CDLL 'libcrypt.so.2'>`，`_crypt_data` 为 `_crypt_data_libxcrypt`
  （补丁在 fallback 分支同步选择了 libxcrypt 的 crypt_data 布局）。

## 三、方案空间三件套（缺一不可）

### 1. 消费库侧补丁：find_library 全失败 → try CDLL(实测 SONAME)

```python
except OSError:
    # OHOS (musl) fallback: find_library() returns None even for installed
    # libraries (no ldconfig/gcc). Load the SONAME directly through the
    # normal dynamic-loader search path.
    _crypt_data = _crypt_data_libxcrypt     # libxcrypt 的 crypt_data 布局
    try:
        _libcrypt = _ctypes.CDLL('libcrypt.so.2')
    except OSError:
        raise ImportError("libcrypt / libxcrypt missing") from None
```

要点：

- **SONAME 必须实测**：`readelf -d <依赖包 shared 产物> | grep SONAME`。
  本案例 libxcrypt 的安装产物 SONAME 是 `libcrypt.so.2`（不是直觉上的
  `libxcrypt.so.2`）——libxcrypt 是 glibc libcrypt 的 drop-in 替换实现。
- **保持探测语义**：fallback 只放在 find_library 全失败的
  `except OSError` 分支，上游正常平台（glibc 有 ldconfig）路径零改动；
  补丁不引入平台名宏，未来 musl 提供 ldconfig 缓存时上游路径自动恢复。
- **结构体布局同步选择**：fallback 分支明确按 libxcrypt 的
  `crypt_data` 布局选实现（`_crypt_data_libxcrypt`），与 CDLL 加载到的
  库一致；不要沿用 glibc 布局（大缓冲虽不越界，但语义漂移不可审计）。

### 2. 配方侧：依赖必须 shared=True

`default_options = {"libxcrypt/*:shared": True}`。**静态归档（.a）无法被
dlopen/CDLL**——配方若使用制品仓默认的 static 二进制，构建期"看似接好"，
运行期 CDLL 必失败。注意制品仓 libxcrypt/4.5.2 目前只有 static 预编译
二进制，shared 变体靠 `--build=missing` 从源码构建（配方已含完整 OHOS
补丁与 make check）。

### 3. 显式注入依赖 lib 目录

**conan 依赖图不会为 ctypes/dlopen 式消费注入 LD_LIBRARY_PATH**——conan
只为链接器和生成器铺路径（cpp_info 是给"链接消费"用的），而
`ctypes.CDLL(soname)` 走的是动态加载器搜索路径。因此 build() 与
test_package 都要显式前置注入：

```python
env["LD_LIBRARY_PATH"] = os.pathsep.join(
    self._xcrypt_libdirs() + [env.get("LD_LIBRARY_PATH", "")])   # build()

cmd = 'LD_LIBRARY_PATH="' + ":".join(libdirs) + ':$LD_LIBRARY_PATH" ' + cmd  # test_package
```

三件套的因果链：补丁让"库在哪"从 find_library 退化为 SONAME 搜索 →
SONAME 搜索依赖 loader 路径 → loader 路径依赖 shared 产物 + 显式注入。
任何一环缺失都退回 ImportError。

## 四、forbid 反模式

1. **平台名硬编码路径**（`if OHOS: CDLL('/data/.../libcrypt.so.2')`）：
   把"探测语义"换成"平台假设"，掩盖真实失败点；平台行为变化（如未来
   musl 提供 ldconfig 缓存、或产物改路径）时静默走错分支。正确形态是
   `CDLL('<SONAME>')`——依赖加载器搜索路径，路径问题交给环境。
2. **CDLL 开发符号链接 / 依赖 static 归档**（`CDLL('libcrypt.so')`、
   `shared: False` 依赖）：`libcrypt.so` 是随 -dev 包交付的开发符号链接，
   运行环境不存在；静态归档无法 dlopen。CDLL 的目标必须是 SONAME 级
   真实 shared 产物。

## 五、同族差异（与 E068 / E465 / E502）

| 条目 | 问题态 | 修复层 | 与本条关系 |
|---|---|---|---|
| **E068** | find_library 崩溃（SubprocessError，ldconfig 缺失） | 改 Python stdlib：让 find_library 直接 return None | **E068 修复恰好产出本条的 None 态**；E068 未覆盖消费库侧适配，本条补齐 |
| **E465 / E502** | worker/loader 安全策略拒绝 dlopen 用户目录 .so（Permission denied，带签名也拒） | embedded-python-launcher（C 垫片绕行） | loader **策略**问题 vs 本条的 loader **探测语义**失效；E465 模式可作本条 fallback |
| **E488** | HMDFS owner 导致 dlopen Permission denied | 权限问题 | 不同机理 |
| **E447/E481/E538/E286** | CMake/Meson 侧 find_library/find_path | 构建期探测 | 非 Python ctypes 运行期 |

## 六、传播面（下一步该查谁）

- **cffi 系**：cffi 内部同样使用 find_library/dlopen 定位 ABI 库；任何
  `cffi.dlopen`/`ffi.cdef` + 动态定位模式的库在 musl 上命中同一 None 态。
- **stdlib crypt 独立移植族**：legacycrypt 之外，未来 Python 3.13 把
  crypt 模块移出 stdlib 后，PyPI `crypt` 系包是同型补丁的直接受众。
- **SSO/Kerberos/数据库驱动等纯 Python 绑定**：python-kerberos、
  python-ldap、psycopg（ctypes 模式）、smbpasswd 等经 find_library 定位
  libsso/krb5/pq 的库，适配时可跳过"先试 find_library"的试错，直接
  规划"SONAME fallback 补丁 + shared 依赖 + 显式注入"三件套。
- **Scout/Builder 盘点信号**：源码中出现 `ctypes.util.find_library` 即为
  OHOS 高风险信号，盘点阶段就应按本条规划补丁与配方，不再试错。

## 七、验证与度量

- verification_cmd 见 .kv（自包含四步探针：find_library=None →
  无注入 CDLL OSError → 注入后 CDLL OK → readelf SONAME）。
- 本 run 实证：CI run1（2026-09-26）一次通过，L1e 拆除负向测试确认
  test_package 对 legacycrypt 依赖真实性；上游 tests.py 8 用例全量执行。
