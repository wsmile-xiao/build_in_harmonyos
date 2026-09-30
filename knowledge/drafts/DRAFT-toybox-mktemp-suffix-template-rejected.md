# DRAFT：toybox mktemp 拒绝带后缀模板（"mktemp: need XXXXXX"）——test_package 临时文件写法

> Draft（未 promote）— 来源于 xfpt 1.00 真机 shadow CI（job xfpt-1.00-20260929，r2，2026-09-29）
> 对应 `.kv` 文件同 stem：`DRAFT-toybox-mktemp-suffix-template-rejected.kv`

## 症状

真机 CI 里 `conan create` 编译打包全部成功，test_package 前几项断言 PASS，
在需要临时文件的断言处无任何 FAIL 输出直接退出：

```
PASS: missing input reports error and non-zero exit
[test] DocBook conversion using packaged share data (-S)
mktemp: need XXXXXX
ERROR: xfpt/1.00 (test package): Error in test() method ... ConanException: Error 1 while executing
```

罪魁写法（GNU 下完全正常）：

```sh
tmpin="$(mktemp /tmp/xfpt-test-XXXXXX.txt)"
```

## 根因（两个坑叠加）

1. **toybox mktemp 模板语法限制**：OHOS 的 mktemp 是 toybox 实现，要求
   连续 X 出现在模板**结尾**；`XXXXXX.txt` 这种"中间 X + 扩展名"形态直接
   报 `mktemp: need XXXXXX` 退出 1。这与 HMDFS 权限类 mktemp 问题
   （E011/E060/E118/E125/E129/E136/E175，报 `Permission denied`）完全不同
   ——那些条目的模板恰好都是 X 结尾（`confXXXXXX`），所以没人暴露过本坑。
2. **`/tmp` 只读**（E002）：即使模板改对，`/tmp/...` 前缀在 OHOS 上也可能
   写不进去，必须用 `$TMPDIR`。

`set -euo pipefail` 下 mktemp 失败即静默退出（没有 FAIL 行），极易误判为
被测工具本身故障。

## 方案（推荐完全不用 mktemp）

```sh
tmpdir="${TMPDIR:-.}"
tmpin="$tmpdir/<lib>-test-$$.txt"
tmpout="$tmpdir/<lib>-test-$$.xml"
trap 'rm -f "$tmpin" "$tmpout"' EXIT
```

- `$$`（PID）保证并发唯一，无 toybox 兼容性问题；
- 若必须用 mktemp：`mktemp "$TMPDIR/foo.XXXXXX"`（X 结尾、无扩展名）。

## 诊断套路

1. test_package 在某断言"无声死亡"且 CI 日志无 FAIL 行 → 看该断言前面
   最后一条输出，定位是哪条命令在 `set -e` 下退出；
2. 在设备上手动跑测试脚本加 `bash -x`（`/data/service/hnp/bin/bash -x test_<lib>.sh`），
   精确到失败命令与退出码；
3. 修脚本 → scp 重传到 job 的 repo 目录 → 重跑 `run-conan-heavy.sh`。

## 复用面

所有 test_package 含 shell 冒烟脚本、且脚本里用 mktemp 生成带扩展名
临时文件的库（典型：转换/对比类工具的输入输出临时文件）。
