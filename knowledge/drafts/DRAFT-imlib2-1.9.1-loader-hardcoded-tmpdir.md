# imlib2 1.9.1：loader 硬编码 /tmp 的源码级 $TMPDIR 修复

## 场景

imlib2 1.9.1 适配 HarmonyOS PC。上游测试 LOAD2.load_1（加载 icon-64.ff.gz）
与 jpg.mp3（ID3 封面）失败：

```text
Unable to create a temporary file
*** Failed to load image: '.../icon-64.jpg.mp3'
```

## 根因

两个 loader 硬编码 mkstemp 模板，**不读取 TMPDIR 环境变量**：

```c
/* decompress_load.c */   char tmp[] = "/tmp/imlib2_loader_dec-XXXXXX";
/* loader_id3.c load2() */ char tmp[] = "/tmp/imlib2_loader_id3-XXXXXX";
```

OHOS /tmp 为只读 erofs（E002 平台限制）→ mkstemp 失败 → 解压/提取失败。
由于模板路径写死，仅设置 `TMPDIR/TMP/TEMP` 环境变量**无效**——这是与 E002
（configure/make 类用 TMPDIR 可解）的关键差异。

## 修复（源码级补丁）

```c
const char *tmpdir = getenv("TMPDIR");
char        tmp[512];
if (tmpdir && *tmpdir)
  snprintf(tmp, sizeof(tmp), "%s/imlib2_loader_dec-XXXXXX", tmpdir);
else
  snprintf(tmp, sizeof(tmp), "/tmp/imlib2_loader_dec-XXXXXX");
/* mkstemp(tmp) ... */
```

落地：`patches/0002-decompress-tmpdir.patch`、`patches/0003-loader-id3-tmpdir.patch`
（portability 类型，无平台宏）。测试运行环境同时设置
`TMPDIR/TMP/TEMP=<可写目录>`。

## 验证

- 修复前：LOAD2.load_1 失败（"Unable to create a temporary file"）。
- 修复后：`conan create -o imlib2/*:test=True`，LOAD2.load_1 通过，
  上游测试 31/31（test_load_2 含 ff.gz/jpg.mp3 全部通过）。

## 边界

- 适用：库内部 loader/工具用 `mkstemp("/tmp/固定名-XXXXXX")` 的场景
  （/tmp 只读平台均适用，非 OHOS 专属）。
- 反例：若代码用 glibc 标准临时文件机制（尊重 TMPDIR）或模板含
  `$TMPDIR` 环境展开，则无需源码补丁。
- 前置检查：grep -n 'mkstemp' src/**/*.c 确认硬编码模板后再决定补丁范围。

## 查重

| 既有条目 | 关系 |
|---|---|
| E002（/tmp 只读，set-env-var） | similar_to：trigger 相同（/tmp 只读）；**新增差异=硬编码模板不受 TMPDIR 影响，需源码级补丁** |
| E052 / E136（config.status 临时目录） | 相邻：configure 侧方案，非 loader 侧 |
| E225 / E253 / E265 | 弱相关（conan 布局 / 测试临时文件绕过） |

同 stem 草稿：DRAFT-imlib2-1.9.1-loader-hardcoded-tmpdir.kv