# DRAFT-E634-libstorj-library-temp-path-tmp-readonly-storj-temp：上游库内部临时目录走自选环境变量或硬编码 /tmp（TMPDIR 分支是死代码），OHOS 上 /tmp 只读 ⇒ "File encryption error" 假象

> Contributor: libstorj-1.0.3 任务 | Status: Draft | Updated: 2026-09-21
> Source: libstorj 1.0.3 适配（feat/libstorj-1.0.3）采信轮诊断
> 对应：`knowledge/drafts/DRAFT-E634-libstorj-library-temp-path-tmp-readonly-storj-temp.kv`

## 现象

`make check` 的上传集成测试 `storj_bridge_store_file` 以
`STORJ_FILE_ENCRYPTION_ERROR`（"File encryption error"）失败，重试 6 次后退出；
同套件其余 38 项全过、且加密本身（test_meta_encryption 等）全过——形态完全像
"加密/密码学在 OHOS 上坏了"。错误文本与文件系统毫无关联词，极易误判。

## 根因

上游库自己选临时目录（`storj_init_env()`，src/storj.c:625–626，`env->tmp_path = NULL;` 紧跟 `if (env->tmp_path && ...)`）：

```c
env->tmp_path = NULL;
if (env->tmp_path && stat(env->tmp_path, &sb) == 0 && ...) {   // ← 死代码：刚置 NULL 又判自己
```

- 第一分支（本意应为 `getenv("TMPDIR")`）恒假 —— **TMPDIR 从不被读取**；
- 环境覆盖只认 `getenv("STORJ_TEMP")`；
- 兜底 `stat("/tmp")` —— OHOS 设备上 `/tmp` **存在但只读**（device-facts §一.1），
  `stat` 成功 ⇒ 选中 `/tmp` ⇒ `fopen("/tmp/xxx.crypt", "w+")` 失败
  （HMDFS 只读）⇒ 上传状态机重试 6 次后报 "File encryption error"。

日志原文（库内 log level=4 重建后才可见；测试默认 level=0 全静默）：

```
Encrypting file...
Can't create file for encrypted data [/tmp/b7f8...crypt]
Failed to encrypt data.    ← ×6
```

## 方案

不改源码，用上游自带的覆盖变量驱动测试：库临时目录认 `STORJ_TEMP`，
测试程序自身的上传源文件路径认 `TMPDIR`（tests.c main 直接 getenv），两个都指向
同一个可写目录：

```python
# conanfile.py build()
self.run('export TMPDIR="%s" STORJ_TEMP="%s" && make check -j1'
         % (check_tmp, check_tmp), cwd=self.build_folder, env="conanbuild")
```

## 判读序（写配方前先跑）

1. 见 "File encryption error"/"parity error" 一类**语义错误码**时，先别查密码学：
   把测试二进制以日志全开重链（tests.c 的 `log_options.level = 0` → 改 4，
   重链本地 libstorj.a 即可，不动提交面），库内部日志会直接给出真实失败点；
2. 库内部日志出现 `Can't create file ... [/tmp/...]` ⇒ 临时目录问题；
3. 确认 `/tmp` 只读后，找上游文档/源码里的 env 覆盖口（storj 家族是
   `STORJ_TEMP`），conan 配方在 make check 时显式注入，不改上游源码。

## 家族复现记录

| 任务 | 版本 | 现象 | 处置 |
|---|---|---|---|
| libstorj | 1.0.3 | store_file 报 File encryption error，37/38 | make check 注入 STORJ_TEMP，39/39 |
