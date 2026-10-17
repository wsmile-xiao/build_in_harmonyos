- **三方库名称**：cdargs
- **上游版本**：1.35
- **上游仓库地址**：http://www.skamphausen.de/cgi-bin/ska/CDargs
- **适配路径**：路径 A（基础适配）
- **使用知识库**：无

## 测试用例对比

### 上游库测试用例统计

| 测试类型 | 上游用例数 | 说明 |
|----------|-----------|------|
| 单元测试 | 0 | 上游 1.35 官方 tarball 无测试套件（无 test/ 目录、无 make check 目标） |
| 集成测试 | 0 | 无 |
| 其他测试 | 0 | 无 |
| **合计** | **0** | |

### 适配后测试用例统计

| 测试类型 | 适配后用例数 | 与上游对比 | 说明 |
|----------|-------------|-----------|------|
| 单元测试 | 0 | 不变 | |
| 集成测试 | 1 | +1 | 消费者测试：真实运行打包二进制 |
| 鸿蒙特有测试 | 0 | 新增 | |
| **合计** | **1** | **+1** | |

## 上游测试用例修改说明

### 是否存在对上游测试用例的修改？

- [x] **否**，未修改上游任何测试用例

## 补全测试用例说明

### 上游是否存在无测试用例，适配后补全的情况？

- [x] **是**，上游无测试用例，适配后补全了测试（请在下方说明）

> - **补全的测试范围**：为二进制可执行性补全 1 个消费者测试
> - **补全原因**：上游仅提供源码无正式测试框架
> - **新增测试文件清单**：
>   1. `test_package/test_cdargs.py` — 真实执行 `cdargs -f <list> -a <absdir>` 非交互书签添加，校验书签文件写入绝对路径

## 验证结果

- 编译状态：通过
- 上游测试用例通过率：0/0（无上游测试）
- 新增测试用例通过率：1/1（100%）

## 补充说明

- cdargs 1.35 为单一 C++ 翻译单元工具（`src/cdargs.cc` + `src/cdargs.h`），链接 ncurses。OHOS 的 ncurses 包仅提供宽字符静态库（libncursesw.a），头文件经 `--enable-overwrite` 装在顶层 include。
- **构建方式**：直接 `clang++ -DHAVE_NCURSES_H -I<ncurses>/include src/cdargs.cc -o cdargs -L<ncurses>/lib -lncursesw` 编译，不跑 autotools make。cdargs 无 config.h、无 configure 生成宏（源码仅用 `_GNU_SOURCE` 自声明 + 可选 `TERMINFO` 分支），单一文件直接编译等价且确定。
- **弃用 autotools 的原因（CI 实证）**：cdargs 1.35 的 automake 1.4-p5 递归构建在 OHOS worker 上生成子 Makefile 时，`@top_srcdir@` 被环境污染成二进制乱码（`config.status` 替换出的 `top_srcdir = '/\xef\xbf\xbd-v\x11...flag'`），make 进入 `contrib/`（SUBDIRS 首项）重建 `Makefile.in` 时对不存在的乱码路径报 `No rule to make target '/<乱码>flag/configure.in'` 失败——二进制在 `src/` 根本未构建。已在本地用假编译器复现 configure：正常环境 `top_srcdir = ..` 干净，乱码为 worker 环境特有。直接编译不依赖 configure/config.status 生成的 Makefile，确定性构建。
- 源码复制到非 HMDFS `/data/storage/el2/base/cache` 后编译（E011：HMDFS 执行位被剥）。
- OHOS 应用二进制已用 binary-sign-tool self-sign，可在真机/CI 执行。
