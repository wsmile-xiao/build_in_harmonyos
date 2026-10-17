# DRAFT-E716 — sprng 2.0a 移植三连坑 + rc 判据

> 路径 B 草稿 ｜ 取号 `knowledge_id.py --claim` = **E716**（三面并集最小空号，回查 ✅ 未占用）
> 实例配方：`archives/s/sprng/2.0a`（任务卡 10876，分支 `feat/sprng-2.0a`）
> 设备实测：质量测试 **13/13 PASS**、checksprng **17/18**（唯一 FAILED 已根因为上游固有缺陷）

## 一句话

老式 `make.$(PLAT)` C 工程上 OHOS，最容易在四处翻车：**默认平台硬写 MPI 路径**、
**1999 年捆绑的 gmp.h 与 gmp6 符号不兼容**、**`_mymalloc(size==0)→NULL` 让 pmlcg
pack/unpack 恒失败（上游 bug）**、以及**上游 `void main` 让 rc 根本不能当判据**。

## 复现命令（设备可直接执行；一律落 `$TASK_DIR`，不用 `/tmp`）

```sh
. "$HOME/tmp/sprng-2.0a/env.sh"                 # TARGET_REPO / TASK_DIR
W0="$TASK_DIR/w0"

# ① 平台判据：默认 PLAT 是谁、它有没有硬写 MPI
grep -n '^#*PLAT' "$W0/patch/orig2/make.CHOICES"
grep -n 'MPI\|mpich\|/usr/local/mpi' "$W0/patch/orig2/SRC/make.INTEL" "$W0/patch/orig2/SRC/make.GENERIC"

# ② gmp 头文件代差（编译过、链接炸）
grep -n '#include "gmp.h"' "$W0/patch/orig2/SRC/pmlcg/pmlcg.c"
#    未切 <gmp.h> 时的链接错误（实测）：
#    ld.lld: error: undefined symbol: __mpn_add_n / __mpn_sub_n / mpz_init / mpz_init_set_str / mpz_clear

# ③ _mymalloc size==0 → pmlcg unpack 恒 NULL（上游固有，平台无关）
grep -n -A2 'if(size == 0)' "$W0/patch/orig2/SRC/memory.c"      # return NULL
grep -n 'mpz_init_set_ui(&k, gennum)' "$W0/patch/orig2/SRC/pmlcg/pmlcg.c"
python3 - <<'PY'
import subprocess, textwrap, os
gmp_inc = "/storage/Users/currentUser/.conan2/p/gmp1e0cc591edf00/p/include"   # conan cache path gmp/6.3.0
gmp_lib = "/storage/Users/currentUser/.conan2/p/gmp1e0cc591edf00/p/lib"
src = textwrap.dedent(r'''
    #include <stdio.h>
    #include <gmp.h>
    int main(void){ mpz_t z; mpz_init(z);
      printf("fresh alloc=%d size=%d\n", z->_mp_alloc, z->_mp_size); return 0; }
    ''')
p = os.path.join(os.environ["TASK_DIR"], "w0", "gmpprobe.c")
open(p, "w").write(src)
subprocess.run(["clang", "-O2", "-I" + gmp_inc, p, "-o", p + ".bin", "-L" + gmp_lib, "-lgmp"], check=True)
print(subprocess.run([p + ".bin"], capture_output=True, text=True).stdout.strip())
# 实测输出: fresh alloc=0 size=0   ← 这就是 k=0 时 _mp_alloc=0 的直接证据
PY

# ④ rc 不可作判据（void main / K&R main 无 return）
grep -l 'void main' "$W0/probe/sprng2.0/TESTS"/*.c      # 8 个
python3 -c "print(open('$HOME/tmp/sprng-2.0a/test-logs/equidist.out').read())"   # rc=8 但结果行完整、KS%=26.76
```

## 判据与口径

| 项 | 口径 |
|---|---|
| 测试面 N | `grep '^TESTLIST' TESTS/Makefile` 的**注册数**（sprng=13；`fft` 不在表内且需 SGI 库 ⇒ 不运行） |
| 种子 | 全部来自命令行 `argv[4]`，`TESTS/*.c` 无 `time()`/`srand()` ⇒ 固定 seed 即可复算 |
| 统计判据 | KS 百分数 / 百分数落 **[0.5%, 99.5%]**；Ising 类（wolff/metropolis）以结果行完整为 PASS |
| rc | **只留档不判据**（`void main`/K&R 返回值未定义）；不改上游测试源码 |

## 修法要点（详见 `archives/s/sprng/2.0a/notes.md` 与补丁 0001）

1. `PLAT=GENERIC` 显式钉（命令行 + `make.CHOICES` 默认值双保险）；
2. flags 落点先实测（本例全部 Makefile include 同一个 `make.GENERIC` ⇒
   `CFLAGS`/`CLDFLAGS` 是注入面），钉成 `-O3 -pipe -DNDEBUG`，**保留**
   `$(PMLCGDEF) $(MPIDEF)`，新增 `$(CPPFLAGS)/$(LDFLAGS)` 注入口给 conan 依赖；
3. `#include "gmp.h"` → `<gmp.h>` + `requires("gmp/…")`；
4. 同名全局 `primes[]` → `static`（现代工具链 `-fno-common`，原版链接不过）；
5. 上游固有缺陷只记录不修，**不得写成 PASS**。
