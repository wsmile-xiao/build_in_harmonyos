libimagequant 4.4.1 — 测试报告

## 1. 构建验证

- 命令：`cargo build --release -p imagequant-sys --target aarch64-unknown-linux-ohos`
- 工具链：rust-toolchain/1.97.1（conan tool_requires，制品仓 !8610）
- 链接器：clang（ohos-aarch64 profile，aarch64-unknown-linux-ohos triplet）
- 产物：`libimagequant_sys.a`（ar archive，23.6MB），打包规范化为
  `libimagequant.a`

## 2. 上游测试（真实执行）

命令：`cargo test --release --workspace --tests --no-fail-fast`

```
running 1 test   (c_test: C 集成，test.c run_liq_tests 串跑 5 个断言函数)
test result: ok. 1 passed; 0 failed; 0 ignored

running 16 tests (imagequant lib 单元: attr/pal/remap/rows/lib)
test result: ok. 16 passed; 0 failed

running 4 tests  (imagequant-sys ffi: c_callback_test_c/link_every_symbol/
                  links_and_runs/ownership_bitflags)
test result: ok. 4 passed; 0 failed
```

**合计 21/21 通过（100%），0 失败**（执行环境：rust-toolchain/1.97.1
aarch64-OHOS 本机真跑）。

## 3. 消费者测试（R34 实质调用被测库 API）

test_package/test_consumer.c —— pngquant 同款 roundtrip：

```
palette entries: 4
remap roundtrip OK (indices within palette)
consumer test PASS
```

断言覆盖：liq_attr_create / liq_set_max_colors / liq_image_create_rgba /
liq_quantize_image / liq_get_palette（规模 1..4）/ liq_set_dithering_level /
liq_write_remapped_image（逐像素索引范围）/ 资源销毁顺序。

## 4. 验证结论

| 项目 | 结果 |
|------|------|
| conan create（交叉构建） | PASS |
| 上游测试 21 项 | 21/21 PASS（100%） |
| 消费者 roundtrip | PASS |
| L0 结构门禁（test_package/MANIFEST 等） | 预检通过 |
