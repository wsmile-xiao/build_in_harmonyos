# cpdf 0.0.7 编译进度

**日期**: 2026-05-25
**状态**: ✅ 编译完成 (部分功能受限)

## 步骤记录

| 步骤 | 状态 | 备注 |
|------|------|------|
| Step 1 init | ✅ | 从PyPI下载cpdf-0.0.7.tar.gz |
| Step 2 patches | ✅ | 3个补丁(2个auto+1个manual) |
| Step 3 configure | ✅ | pip install --no-deps |
| Step 4 build | ✅ | 手动staging+创建wrapper |
| Step 5 install | ✅ | 模块导入验证通过 |
| Step 6 check | ✅ | basic cat/metadata CLI可用 |
| Step 7 staging | ✅ | Python模块+wrapper脚本 |
| Step 8 package | ✅ | 2个预编译包 |
| Step 9 deploy | ✅ | 本地安装验证 |
| Step 10 finish | ✅ | 状态: built |

## 编译过程详情

### Step 1: init-build
- 源码下载: PyPI cpdf-0.0.7.tar.gz (7.7KB)
- 纯Python包，无C扩展

### Step 2: 补丁
1. `0001-cpdf.egg-info-PKG-INFO.patch` - 更新元数据版本和依赖声明
2. `0002-cpdf.egg-info-entry_points.txt.patch` - 修复entry_points末尾空行
3. `0003-add-harmonyos-wrapper-script.patch` - 新增bin/cpdf wrapper脚本

### Step 3: 安装
```bash
pip install pypdf2       # 依赖
pip install --no-deps cpdf-0.0.7  # 避免pip挂起
pip install pydantic     # 依赖
```

### Step 4: 创建wrapper脚本
```bash
mkdir -p staging/bin staging/lib/python3.12/site-packages
cp cpdf模块文件 staging/lib/python3.12/site-packages/cpdf/
cat > staging/bin/cpdf << wrapper脚本内容
```

### Step 5: 验证
```bash
python3 -c "import cpdf; print(cpdf.__version__)"
# Output: 0.0.7
```

### Step 6: 打包
```bash
python3 scripts/ohc-run.py package cpdf 0.0.7
```
- 主包: 22KB
- debug包: 2KB (纯Python无调试符号，仅含README)

## 发现与知识

### 问题1: pip install cpdf挂起/超时
- **现象**: pip download dependencies时网络慢/SSL问题
- **解决**: 使用 `pip install --no-deps` + 手动安装依赖

### 问题2: PIL/Pillow C扩展.so权限被拒
- **现象**: HarmonyOS沙箱不允许加载第三方.so
- **解决**: PIL依赖功能(extract_images)受限，基本cat/metadata功能正常

### 问题3: 无console_scripts入口
- **现象**: 纯Python包pip安装后bin/cpdf是Python脚本，在OHOS无法执行
- **解决**: 创建wrapper shell脚本，通过 `python3 -m cpdf` 调用

### 注意
- Python cpdf 0.0.7 ≠ CoherentPDF cpdf v2.9（OCaml专业PDF工具）
- CoherentPDF cpdf v2.9源码已下载，但OCaml编译器不可用无法编译

---

**编译开始**: 2026-05-25 22:57
**编译结束**: 2026-05-25 23:26
**最终状态**: built
**总耗时**: ~29分钟