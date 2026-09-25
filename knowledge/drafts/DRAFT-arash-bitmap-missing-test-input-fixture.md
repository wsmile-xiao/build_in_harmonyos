# DRAFT-arash-bitmap-missing-test-input-fixture — 上游测试缺输入文件时用库自身 writer API 生成合法夹具

> 草稿（DRAFT）。与同目录 `DRAFT-arash-bitmap-missing-test-input-fixture.kv` 成对。
> 来源：任务 `feat/arash-bitmap-20260924`（arash-bitmap 20260924, Arash Partow C++ Bitmap
> Library, header-only 24-bit BMP 图像库）。知识候选台账见
> `archives/a/arash-bitmap/20260924/reports/knowledge-candidate-ledger.md` 的 C3。

## 问题

上游测试程序 `bitmap_test.cpp` 的 20 个 test 函数中 13 个需要样例输入 `image.bmp`，
但官方源码 tarball（master commit a03765d38698a138dbf162b0cc127fc17d6fc0c2）只含
`bitmap_image.hpp` / `bitmap_test.cpp` / `Makefile` / `readme.md` / `.travis.yml`，
未附带任何输入文件。直接运行 `./bitmap_test` 时 test01-08、10-13、16 全部报：

```
test01() - Error - Failed to open 'image.bmp'
```

13/20 项失败。若此时简单把测试标记为"不可运行"跳过，会掩盖实际可通过的上游用例；
若手工伪造二进制输入又违反测试真实性，且无法保证 24-bit BMP 格式合法。

## 根因

- 上游测试程序需要运行时输入文件（样本图片），源码包不附带；
- 库本身提供公开 writer API（`bitmap_image::set_pixel` / `save_image`），
  可生成与测试预期格式完全一致的合法输入。

## 方案

用库自身的公开 API 生成合法 24-bit BMP 夹具，再运行上游测试：

```cpp
// maker.cpp — 仅测试期夹具生成，不入包
bitmap_image image(512, 372);
image.clear(0);
for (y...) for (x...) {
    rgb_t c = {gradient...};
    image.set_pixel(x, y, c.red, c.green, c.blue);
}
image.save_image("image.bmp");
```

```bash
clang++ -ansi -pedantic-errors -Wall -Werror -Wextra -o maker maker.cpp && ./maker
clang++ -ansi -pedantic-errors -Wall -Werror -Wextra -o bitmap_test bitmap_test.cpp -L/usr/lib -lstdc++ -lm && ./bitmap_test
```

结果：`./bitmap_test` exit 0，20/20 全过，74 个输出 BMP 产物非空（`test -s` 抽验）。

## 验证

- 上游测试 20/20 通过（source_declared_total=20, configured_executable_total=20,
  executed_passed_total=20, 失败 0, 未运行 0）——双口径台账；
- 夹具生成命令、cwd、退出码、产物存在性均记录在
  `archives/a/arash-bitmap/20260924/reports/test-report.md`；
- 夹具生成器 maker.cpp 只存在于本地 work 目录，未进入 Conan 包或 PR。

## 适用边界 / 反例

- 适用：上游测试需要样本输入、库（或生态）提供合法 `save`/`write` API 的图像/
  音频/数据类库；输入格式无私有约束或可由 API 直接产出。
- 反例：输入有严格字节级格式约束且库无 writer API 时（如 LVM2 镜像），
  需按格式规范手工构造（参见 DRAFT-E593 libvslvm LVM2 夹具的字节级做法）；
  禁止用伪造输出或改写退出码把失败写成通过。

## 查重差异

- 与 E276/E392（codeload URL filename/BadZipFile）：机制不同（下载编码 vs 测试输入），
  无冲突。
- 与 E257/E321/E322（header-only 配方）：无冲突，配方与测试互不依赖。
- 与 DRAFT-E593（LVM2 镜像夹具）：主题相邻（合成夹具），但其为格式字节合成、
  libvslvm 专属约定；本条为"库自带 writer API 生成通用合法输入"，机制与适用范围
  不同，非重复。
- 与 E345/E370/E394（dlopen 夹具/Meson fixture 清点/LD_PRELOAD）：无冲突。

## 关系

- similar_to=DRAFT-E593-libvslvm-lvm2-image-fixture-and-api-contract
- caused_by=上游源码包未附带测试输入文件
- prerequisite_of=无；conflicts_with=无