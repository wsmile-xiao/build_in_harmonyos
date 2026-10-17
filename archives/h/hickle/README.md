# hickle

HDF5 based version of pickle. Instead of serializing to a pickle file, hickle
dumps to an HDF5 file, designed for large datasets and cross-platform support.

- **Homepage**: https://github.com/telegraphic/hickle
- **License**: MIT
- **Build system**: Python (setuptools, pure-Python py3-none-any)

## OHOS 适配

纯 Python 包，无需交叉编译。直接拷贝 `hickle/` 包目录到
`lib/python3.12/site-packages/`，usr_local deployer 铺到 `~/usr/local` 后
系统 python3 可直接 `import hickle`。

### 运行期依赖（非 Conan requires，由目标 Python 环境提供）
- **h5py** >=2.10.0（需 HDF5，已发布 archives/h/hdf5）
- **numpy** >=1.8,!=1.20（OHOS 已随 openblas 验证可用）

## 版本
| 版本 | 状态 | 日期 |
|------|------|------|
| 5.0.3 | built | 2026-07-31 |
