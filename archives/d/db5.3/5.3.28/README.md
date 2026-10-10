# db5.3 5.3.28

**Berkeley DB 5.3.28（Oracle / Sleepycat 经典版）** —— 嵌入式 key/value 数据库 C 库，
上游归档：<https://download.oracle.com/berkeley-db/db-5.3.28.tar.gz>，
许可证 Sleepycat（=`licenses/LICENSE`）。

```c
#include <db.h>
DB *dbp; DBT key, data;
db_create(&dbp, NULL, 0);
dbp->open(dbp, NULL, "test.db", NULL, DB_BTREE, DB_CREATE, 0);
/* dbp->put / dbp->get / dbp->cursor → DB_NEXT / txn_begin·commit·abort … */
```

交付内容：

| 交付 | 说明 |
|---|---|
| `lib/libdb-5.3.so` + `libdb.so`/`libdb-5.so` 链接 | C 库（btree/hash/queue/heap/recno、事务、日志、锁、共享内存环境、复制） |
| `include/db.h`、`include/db_cxx.h` | 公开头（C API；C++ 头随上游 install 一并交付，本包未开 `--enable-cxx`） |
| `bin/db_archive` … `bin/db_verify`（14 个） | 上游命令行工具，见版本目录内 `commands.json`（R38） |
| `licenses/LICENSE` | Sleepycat 许可 |

构建要点（都是实测出来的，细节见 `notes.md`）：
`mkdir build_unix && cd build_unix && ../dist/configure … && make`，并且
**CFLAGS 必须带 `-Wno-error=implicit-function-declaration`**（GCC15/clang 把
implicit-function-declaration 当硬错误；缺它会静默劣化 configure 的三个运行期探测，
最终导致 `HAVE_64BIT_TYPES` 未定义、Tcl API 库缺 `_SetListElemWideInt` 而无法 `load`）。

测试：`build()` 内真跑上游测试 —— `make check`（上游原本是 `target not available` 桩，
本包用 `patches/0003` 把它拆成真目标 `check: cutest` → `./cutest`，因此 `make check`
就是上游 CuTest 套件的真实入口，失败即构建失败）与上游 Tcl 测试套件
（`test/tcl/test.tcl` 的 `r <subsystem>`，本机 12 个子系统 70 个测试）；`test_package/`
里另有 C API 消费者（14 项）、CLI 端到端链路（15 项）与交付形态自检（20 项）。
