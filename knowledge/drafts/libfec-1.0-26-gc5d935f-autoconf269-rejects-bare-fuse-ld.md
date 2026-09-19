# autoconf 2.69 configure 拒绝裸 `-fuse-ld`（celt 参数不可照抄）

- **软件**: libfec 1.0-26-gc5d935f（泛化到所有 autoconf 2.6x 项目）
- **阶段**: configure（conan create）
- **severity**: 2
- **状态**: DRAFT

## 现象

```
configure: error: unrecognized option: `-fuse-ld=/storage/Users/currentUser/usr/local/bin/ld.lld'
Try `... --help' for more information
ConanException: Error 1 while executing
```

## 根因

celt 1.0.0 的 OHOS 范式把裸 `-fuse-ld=<ld.lld>` append 到 `tc.configure_args`——
它生成的 configure 较老，对未知单横线参数静默放行，所以 celt 真机/CI 绿。
但 **autoconf 2.69** 生成的 configure 对一切无法识别的 `-*` 参数直接报
`unrecognized option` 并退出。把 celt 的 configure_args 抄到 2.69 项目必挂。

更深一层：这个参数在设备上通常**本来就多余**。OHOS 真机的 clang 与 ld.lld
同目录（`~/usr/local/bin`），clang 驱动能自行定位同目录链接器——实测
`clang x.c -o x` 零链接器参数即可链接并运行。

## 修复

1. 首选**删掉** `-fuse-ld` 注入；先用最小探针验证 clang 独立链接能力
   （注意 clang 临时文件同样要 `TMPDIR` 指向可写目录，`/tmp` 只读时报
   `unable to make temporary file: Read-only file system`）：
   ```sh
   echo "int main(){return 0;}" > t.c && clang t.c -o t && ./t
   ```
2. 确需指定链接器时，把 `-fuse-ld=...` 放进 **CFLAGS/LDFLAGS 环境变量**
   （随 configure 的编译探测透传），不要作为 configure 命令行参数。
3. make 阶段的裸 `ld` 探测仍用 build-local `bin/` 符号链接（`ld → ld.lld`）
   + PATH 前置解决——celt 范式的这一半依然有效。

## 证据

libfec 1.0-26-gc5d935f 真机（frp-tip.com:56267，`ohos-aarch64-fixed`，clang-15）：

- create-5：configure 报 `unrecognized option: -fuse-ld=...`（与 celt 同款 append）；
- 设备探针：`clang linkprobe.c -o linkprobe` LINK OK、`./linkprobe` rc=0；
- 删除参数（commit `cc68af6eef`）后 create-8 全绿：configure 通过、上游
  `make test` 全过（rstest 228×OK）、test_package 19/19。
