# 上游测试二进制输出非 UTF-8 字节导致工具链文本解码崩溃（UnicodeDecodeError → 假 G2 FAIL）

> Draft: DRAFT-UPSTREAM-TEST-BINARY-NONUTF8-LOG-DECODE-CRASH
> Stem: `klibc-dash-upstream-test-nonutf8-log-decode-crash` — pairs with the same-stem `.kv`
> 来源：klibc-dash/2.0.14 适配（2026-09-25）

## 基本信息

- **ID**: DRAFT-UPSTREAM-TEST-BINARY-NONUTF8-LOG-DECODE-CRASH
- **严重度**: 2
- **类别**: testing|conan|packaging|compat
- **触发工具**: conan|test|python
- **阶段**: testing|verification

## 错误特征

`conan create` 本身能编过，但配方内批量执行上游测试后，验证器崩溃：

```
Traceback (most recent call last):
  File ".../ohc/conan_verify.py", line 117, in _run
    r = subprocess.run(cmd, capture_output=True, text=True, ...)
  File ".../subprocess.py", line 2182, in _communicate
    stderr = self._translate_newlines(stderr, ...)
UnicodeDecodeError: 'utf-8' codec can't decode byte 0xb1 in position 348245: invalid start byte
```

表象是 **`conan-verify` G2 FAIL**，而日志里看不到任何构建错误——极易误判为编译失败。

## 根因

klibc 的 `usr/klibc/tests` 里有程序会把**原始字节**写到 stdout：`inet_aton` / `inet_pton`
打印解析后的地址字节（含 `0xb1` 等非 UTF-8 字节）。若配方用 `self.run("timeout 20 <prog>")`
让这些输出回到 conan 的输出流，工具侧（`subprocess.run(..., text=True)`）在解码捕获输出时
就会抛 `UnicodeDecodeError`。定位命令：

```bash
python3 -c "import glob,os
for f in glob.glob('<build>/upstream-tests/*.log'):
    try: open(f,'rb').read().decode('utf-8')
    except UnicodeDecodeError as e: print(os.path.basename(f), hex(e.object[e.start]))"
# → inet_aton.log 0xb1 / inet_pton.log 0xb1
```

## 修复

批量执行上游用例时，**每个用例的输出重定向到独立日志文件**，退出码仍由 `self.run` 返回用于
统计；同时把 `(name, status, log_path)` 汇总成 `results.tsv`（顺带满足 R51 的逐项留档要求）：

```bash
timeout 20 "<tests>/<prog>" <args> > "<build>/upstream-tests/<prog>.log" 2>&1
```

反模式：① 用 `text=False` 或先解码再转发（治标且丢证据）；② 因解码崩溃就把测试整体跳过
（丢失上游测试统计）。

## 验证与判据

- 复验：`conan create` exit 0，且整份日志可通过 UTF-8 严格解码：
  `python3 -c "open('<log>','rb').read().decode('utf-8')"` 无异常
- `conan-verify` 恢复 G2 PASS
- 关联：E265（上游测试在 OHOS 的适配与统计口径）
