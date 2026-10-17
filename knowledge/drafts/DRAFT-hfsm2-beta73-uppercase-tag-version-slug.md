# DRAFT — 大写上游 tag 必须小写化为 Conan 版本 slug（beta73）

> 状态: 草稿（基于 hfsm2 Beta73 R01 真实证据，2026-09-05）。
> 查重: E416 部分覆盖（包名目录 slug / 大小写不敏感 FS 双 case 并存）；草稿层
> DRAFT-indicators 提及关键字未展开 → 本条目为版本目录视角的边界扩展。

## 真实问题（场景）

hfsm2 上游官方 tag 为 **`Beta73`**（大写）。init-build 以任务头 version=Beta73 创建
归档目录 `archives/h/hfsm2/Beta73/`，conan-init 生成 `conanfile.py version = "Beta73"`。

本地 `conan create` 直接失败：

```
ERROR: Conan packages names 'hfsm2/Beta73@ohpcd/stable' must be all lowercase
```

随后 `finish` 的 W3 本地 CI 门禁再拦：

```
[fail] L0m: 目录结构不合规 (R39/L0m-4/L0m-5): 版本目录 'Beta73' 不是 conan slug（L0m-5）：
必须全小写且仅含 [a-z0-9._+-]
```

## 根因

1. **Conan 2 强制全小写**：name/version 非 slug 直接拒绝创建。
2. **CI L0m-5 目录门禁**：`re.fullmatch(r"[a-z0-9][a-z0-9._+-]*", ...)` 校验包名和版本目录，
   大写目录即使配方改小写也会被拦（L0m-3 还要求 版本目录名 == conanfile version）。
3. **三处必须同步小写化**：归档目录名、conanfile.py version、test_package/MANIFEST.yml
   package 字段；任一残留大写都会导致门禁或台账不一致。
4. **R39 官方 URL 不能改写**：conandata.yml `sources.url` 必须保持官方
   `https://github.com/.../archive/refs/tags/Beta73.tar.gz`（原 tag 大小写），
   小写化 URL 会 404；sha256 以官方 tarball 实测为准。
5. **大小写不敏感 FS 陷阱**：`Beta73` 与 `beta73` 在同一设备上是**同一物理目录**。
   R01 实测：先 `mkdir -p beta73 && cp -r Beta73/. beta73/` 再 `rm -rf Beta73`，
   由于两者同名同目录，`rm` 把唯一副本整目录删掉 → 全部归档文件丢失，只能重建。
   重命名必须一步到位（`mv Beta73 beta73` 在大小写不敏感 FS 上同样报 Invalid argument，
   更稳妥做法是直接以正确小写名重建为新文件树，或 git mv 提交时规范化）。

## 验证

| 检查 | 结果 |
|------|------|
| `conan create archives/h/hfsm2/beta73 -pr=h=...ohos-aarch64 --build=missing`（version=beta73） | G2 PASS |
| `conan-verify hfsm2 beta73`（G0-G4 + L2/L4/L5） | PASS |
| `finish hfsm2 beta73 published` W3 本地 CI（L0m/L0n/L0o/L0p/L0q + JC + KC） | PASS（100% 1/1） |
| `conandata.yml` URL 保持 `...Beta73.tar.gz` | 是（官方 gitcode 镜像 ls-remote tag Beta73 同在） |

## 适用范围

- 上游版本 tag 含大写字母或非常规字符（Beta/RC/Alpha/`A273` 风格）的库，在
  OHOS Conan 2 + CI L0m-5 体系下的首次适配。
- 维护期遇到同一 tag 体系（如后续 Beta74/Beta75）时的快速处理。

## 适用边界 / 反例

- **不适用**：版本为纯数字/小写 slug（1.2.3、5.0.0-beta8）的库——直接按官方 tag 原名。
- **反例**：把 conandata URL 改成小写 tag（404）；包名目录大写但版本小写的
  双 case 并存（E416 场景，属另一主题）；在大小写不敏感 FS 上"先建后删"式重命名
  （R01 实测数据丢失事故，forbid_2）。
- 与 E416 的边界：E416 = 包名目录双 case 并存（SDL2_image 元数据目录 + sdl2_image
  配方目录）；本条目 = 版本目录单一大写 tag 的小写化操作链，两者方案不同。

## 关系

- similar_to: E416（conan slug / L0m-5 门禁）、DRAFT-indicators（must be all lowercase）
- caused_by: Conan 2 全小写约束 + CI L0m-5 目录门禁
- prerequisite_of: 无
- conflicts_with: 无

## 决定

`new_draft` — 与 DRAFT-hfsm2-beta73-aarch64-char-narrowing 同 PR 入库。