# E-DRAFT: libyal 2025+ 实验库三处适配事实（发布资产 -experimental 命名 / 公开 error 类型已换名 / UDIF koly 尾块可合成最小读回夹具）

- **触发实例**：libmodi 0-20251121 适配（2026-09-20，任务 libmodi-0-20251121，分支 feat/libmodi-0-20251121）
- **错误签名**：`use of undeclared identifier 'libcerror_error_t'`、
  `undefined symbol: libmodi_handle_get_image_size`、
  `The requested URL returned error: 404`（配 libmodi release 资产名场景）
- **类别**：source-provenance + consumer-test-contract + libyal（autotools / OHOS）
- **严重度**：2（三处都是"可快速判死/卡住"的形态，处置模式固定，不涉及库本身缺陷）
- **与既有条目的关系**：lang-preflight 的绑定 manifest 误判同族形态见上游池既有条目
  DRAFT-libuninameslist-langpreflight-setuptools-binding-misdetect；本条讲**另三处
  独立事实**（资产命名、公开类型契约、合成夹具），同属 libyal 家族新任务高概率复用，
  与既有条目互不重叠。

## 症状与根因

### 事实 1：实验状态 libyal 库的 release 资产名带 `-experimental` 后缀，tag 存在 ≠ plain 资产名可用

libmodi tag `20251121` 真实存在（`git ls-remote --tags` 可证），但 release 资产
`libmodi-20251121.tar.gz`、`libmodi-alpha-20251121.tar.gz`、`.tar.xz` 变体**全部 404**，
实际资产是 **`libmodi-experimental-20251121.tar.gz`**（README 自述 `Status: experimental`）。
上游 README 同时说明该库是 **Mac OS 磁盘镜像格式**库（sparse bundle / sparse disk image /
UDIF），与任务卡软件名 "modi" 容易让人联想的 Microsoft Office Document Imaging (.mdi)
**无关**——包身份必须以 README 为准，不得按名字望文生义。

```text
libmodi-20251121.tar.gz             -> 404
libmodi-alpha-20251121.tar.gz       -> 404
libmodi-experimental-20251121.tar.gz -> 200（sha256 b3c6783c908480711957d9e0e14227c90821be9e90c10f6abe7af1f86ed4bccb）
```

探测顺序：plain → `-alpha` → `-experimental`；GitHub API 在本设备解析受限
（api.github.com 落非公网地址），资产探测用 `curl -I -L` 或 `git ls-remote` 完成。

### 事实 2：2025+ libyal 公开 API 的 error 类型是 `lib<lib>_error_t`（消费者测试沿用 `libcerror_error_t` 模板直接编译失败）

libmodi 20251121 安装后的公开头文件把 error 类型定义为**本库自有别名**
（`include/libmodi/error.h`: `typedef intptr_t libmodi_error_t;`），所有公开函数
（`libmodi_check_file_signature`、`libmodi_handle_*`）的 error 参数都是
`libmodi_error_t **error`。内嵌 libcerror 的类型**不出现在已安装头文件**，
旧 libyal 配方模板的消费者测试若写 `libcerror_error_t *error` 会：

```text
error: use of undeclared identifier 'libcerror_error_t'
```

错误打印用公开的 `libmodi_error_fprint(error, stdout)`；没有公开的 error_free，
消费者测试对失败路径只打印即可（实测一次探针即确认）。

同族陷阱（同一根因：按别家 libyal 的 getter 名望文生义）：
`libmodi_handle_get_image_size` **不存在**，链接期
`ld.lld: error: undefined symbol: libmodi_handle_get_image_size`；该库的真实
getter 集是 `libmodi_handle_get_media_size / get_image_type / get_offset`（读
`include/libmodi.h` 函数清单确认，不要按 libfsntfs 式命名推）。

### 事实 3：UDIF 的 koly 尾块可合成，最小消费者读回链路（发布包无 tests/input/ 夹具时的替代真实验证）

libmodi 的签名判定对**文件**是「头 4 字节签名或**文件末尾 512 字节处**的 `koly`
魔数」二选一；`handle_open` 对 UDIF 是惰性解析（只读尾块，XML plist 延后）。
因此在消费者测试里合成一个 **512 字节全零 + `koly` 魔数**的文件即可拿到完整
真实库调用链：

```text
check_file_signature(koly 文件) == 1
handle_initialize == 1
handle_open(koly 文件, LIBMODI_OPEN_READ) == 1
handle_get_media_size == 1 且 size == 0（尾块字段全零的自洽结果）
handle_close == 0 ; handle_free == 1
```

发布包 `tests/input/` 缺失 → `test_modiinfo.sh` 按上游规则 `exit 77` SKIP
（`SKIP test_modiinfo.sh (exit status: 77)`，日志原文
`Test input directory not found.`）；test_package 合成夹具链路补上
"打开/读取"这段真实行为验证。程序级证据不在 automake 主日志里，而在
**`tests/test_*.sh.log`**（test-driver 落盘）：`Testing: <program> (PASS)` 行，
21 个 `check_PROGRAMS` 逐条可数（18 + 3）。

## 处置建议

1. 源 URL 按 plain/-alpha/-experimental 顺序探测；包身份以 README 格式清单为准。
2. 消费者测试只用安装后的公开头文件：error 类型用 `libmodi_error_t`，getter 名
   先读头文件清单再写断言，失败路径只 `libmodi_error_fprint` 不 free。
3. 上游测试无夹具时，消费者测试用 koly 尾块合成夹具补"打开-读取"链路；
   程序级 PASS 证据到 `tests/test_*.sh.log` 里取数，不要只引 automake 汇总。

## 复现

```sh
TASK_DIR=$HOME/tmp/libmodi-0-20251121
sh "$TASK_DIR/repro-e594.sh"   # 资产名探测 + 两形态编译对照 + koly 链路实测
```

（脚本落任务私有 `$TASK_DIR`，不写 /tmp；产物亦全部在 `$TASK_DIR` 下。）

## 禁止

- 不得为绕过 404 把源码 URL 换成非官方镜像、codeload 自动归档冒充 release 资产，
  或在 conandata.yml 写未实际校验过的 sha256。
- 不得为"修好"消费者测试在配方里塞 libcerror 内部头路径（bundled 目录未安装、
  也未导出 include），那会让包外的消费者拿到不可用的 include 面。
- 不得把 `test_modiinfo.sh` 的 SKIP 记成 PASS（上游无夹具是环境事实，须按
  SKIP 申报并给替代验证）。

## 影响面

- 事实 1：实验状态 libyal 库（README `Status: experimental`）+ 2025+ tag 版本；
  判定信号：资产 URL 404 但 `git ls-remote --tags` 可见 tag。
- 事实 2：2025+ libyal 发布包（含 `lib<lib>_error_t` 别名头的家族版本）；判定信号：
  安装头文件里 `typedef intptr_t lib<lib>_error_t`。
- 事实 3：UDIF 读取族（libmodi；同构尾块判定的镜像库可类比），发布包缺
  tests/input/ 的形态。
