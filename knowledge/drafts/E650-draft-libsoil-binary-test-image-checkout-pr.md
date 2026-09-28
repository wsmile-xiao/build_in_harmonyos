# E650: PR 新增二进制测试图片致 CI checkout-pr "missing binary patch data"

## 基本信息
- **严重度**: 3（blocking，重试必然复现）
- **类别**: ci, patch, testing, conan
- **作者**: Awstme <awstme@qq.com>
- **来源 PR**: 12488（libsoil 1.07.20080707.dfsg，CI #60156）
- **同根因先例**: dbview PR #9495（CI #44073）；正式条目 E256（构建产物 tar.gz 场景）

## 错误特征
```
missing binary patch data for 'archives/l/libsoil/.../test_package/img_test.bmp'
error: binary patch does not apply to 'archives/.../img_test.bmp'
Falling back to direct application...   (逐文件重复)
patch: Unknown option 'fuzz=3' (see "patch --help")
[ERROR] PR 12488 diff 无法应用——PR 与 main 分支存在冲突
```

构建步骤表特征：`git-clone ✅ → checkout-pr ❌`，耗时仅数秒；**L0/L1/test_package 全部未执行**。

## 根因分析
CI 的 `checkout-pr` 不 checkout PR 分支，而是：
clone 默认分支 → `git reset --hard HEAD && git clean -fdx` → `curl <PR>.diff` → `git apply` / `git apply --3way` / `patch -p1`。

GitCode 的 PR diff 端点对**新增的二进制文件**只输出 `Binary files /dev/null/... and ... differ` 标记，**不携带 `GIT binary patch` 的 base85 数据段**。`git apply` 对这样的文件报 `missing binary patch data`，`--3way` 与 fallback 的 `patch -p1` 也相继失败（且该 patch 版本不认识 `--fuzz=3`），脚本最终给出误导性的「PR 与 main 分支存在冲突」提示——**与 main 是否真实冲突无关**，merge-base 干净的 PR 同样必死。

典型触发物（正当需求场景）：
- test_package 测试图片（bmp/png/tga/dds/ttf…）——测试需要真实图片输入；
- 字体/图标等测试资源；
- 归档（tar.gz/zip）、prebuilt 产物、`.staging-verified` 标记（E256 场景）。

## 最小判据（一行）
```
curl -sL https://gitcode.com/{owner}/{repo}/pull/{n}.diff | grep -c 'GIT binary patch'
# diff 里存在 'Binary files ... differ' 标记但上面计数为 0 → 必命中本条，重试无效
```

## 推荐方案：test-time-deterministic-generator（dbview 先例）
当二进制文件是**测试输入**（不能简单删除）时：

1. `git rm` 全部二进制测试文件；
2. 入库一个**纯文本确定性生成器**（如 `test_package/make_images.py`），
   以显式字节布局生成与测试断言一致的输入（dbview 的 `fixtures/make_fixtures.py` 先例）；
3. 由 `CMakeLists.txt` 的 `add_custom_command(OUTPUT ... DEPENDS 生成器)` +
   `add_custom_target(ALL)` 在测试期调用（`python3` 在 conan/CI 环境自带），
   或由 `test.sh` 在运行前生成到 mktemp 私有目录（dbview 方式）；
4. 生成器/依赖缺失时必须**显式报错退出**，禁止静默当作「全部通过」。

### 实测细节（libsoil img_test 生成器，2026-09-25 验证 21/21 通过）
- 四格式均为 256×256、左上角像素 RGB(0,0,255)：BMP=24 位 BGR 底行优先（3 通道）、
  PNG=32 位 RGBA（stdlib `zlib` 即可，无需 PIL）、TGA=32 位 BGRA 顶左原点（4 通道）、
  DDS=未压缩 RGBA（`DDPF_RGB|DDPF_ALPHAPIXELS`，数据按 BGR[A] 字节序写，读取方自行交换）；
- **stb 系 DDS 加载器坑**：`stbi_DDS_aug_c.h` 在 `req_comp==SOIL_LOAD_AUTO` 时，
  若整图 alpha 全为 255 会自动降为 3 通道——需放一个 `alpha=128` 的确定性像素
  （远离被断言的角落）保住 4 通道路径；
- DDS 头 128 字节：`ddspf` 在偏移 76 共 8 个 uint32（dwSize/dwFlags/dwFourCC/
  dwRGBBitCount/R/G/B/A 掩码）——**dwRGBBitCount=32 不能漏**；
- 不要写 `dwMipMapCount=1`（stb 会按 mip 数量 skip 数据，导致后续校验失败）；
- 生成后用 md5 双跑校验字节级确定性。

### 验证/命令
```
git rm archives/.../test_package/img_test.* 
# 新增 test_package/make_images.py + CMakeLists.txt add_custom_command
conan create . -pr:h ohos-aarch64 -pr:b ohos-aarch64 --build=missing
git push origin <原分支>   # 新 diff 无二进制条目，checkout-pr 即通过
```

## 回退方案：remove-binary-from-commit（E256）
二进制文件是纯构建产物/标记文件（测试不需要）时直接删除并 force push。
测试确需二进制输入又无法生成时，改运行期下载（conandata 第二源 / `get()`）——
引入网络依赖，仅作最后回退。

## 禁止事项
- ❌ 反复 `/rebuild`：确定性失败，重试必然复现；
- ❌ 在 `patch --fuzz` 参数上排查：fallback patch 报 `Unknown option 'fuzz=3'`
  只是 git apply 全失败后的连锁现象，不是根因；
- ❌ 把二进制拆成多个小文件/换格式（png→tga 等）：任何新增二进制都命中同一死点。

## 关系
- similar_to: E256（同根因，构建产物场景）、E379（二进制 patch 传输场景）
- 适用原则: W2（PR 原子性）、W3（本地编译验证）

---
*由 libsoil PR #12488（CI #60156）修复过程沉淀，2026-09-25*
