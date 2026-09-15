# pari-seadata

PARI/GP 的 **seadata** 数据包：`ellsea`/`ellap` 计算有限域上椭圆曲线 Frobenius
迹所需的模多项式数据表（prime level p < 500）。数据源自 ECHIDNA 数据库
（David R. Kohel, University of Sydney），以 GP 文本向量格式（`sea<p>` 文件）分发。

- 上游主页: https://pari.math.u-bordeaux.fr/packages.html#seadata
- 官方源:   https://pari.math.u-bordeaux.fr/pub/pari/packages/seadata.tgz
- 许可证:   GPL-2.0-or-later
- 性质:     **纯数据包**（Debian `Architecture: all`）——无编译、无 configure、
            无自动化测试；无任何强制第三方库依赖，仅被 PARI/GP（`Suggests: pari-gp`）在运行期消费。

## 版本

| 版本 | 说明 |
|------|------|
| 20090618 | 对应上游 2009-06-18 发布的 seadata（Debian 源包编码 `0.20090618`） |

## 消费方式

包安装后，数据位于 `<package_folder>/res/pari/seadata/`。下游 PARI/GP 通过
`gp` 的 `share_path`/seadata 目录定位读取（`ellsea` 自动加载）。
配方在 `package_info()` 通过 `cpp_info.resdirs=["res"]` 暴露数据根，并设置自定义
属性 `pari:seadata_rel`；下游取数：
`os.path.join(self.dependencies["pari-seadata"].package_folder, "res", "pari", "seadata")`。

## 目录

- `20090618/conanfile.py` — Conan 配方（数据安装）
- `20090618/conandata.yml` — 官方源 URL + sha256
- `20090618/test_package/` — 内容级校验（R34）+ 上游无测试声明
- `20090618/notes.md` — 适配笔记
- `commands.json` — 数据包声明（binary:false）
