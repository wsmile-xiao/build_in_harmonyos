# E-DRAFT: 上游测试数据外部仓库漂移的恢复（git 稀疏克隆 + 格式适配 + 再生成）

- **触发实例**：astronomy 2.1.9 适配（2026-09-19，分支 feat/astronomy-2.1.9）
- **错误签名**：`Cannot open input file: constellation/test_input.txt`；`hygdata_v3.csv` 全镜像 404
- **类别**：test-data-drift（上游测试数据外部仓库漂移）
- **严重度**：2（测试数据缺失导致单个测试入口无法运行，恢复模式固定）

## 症状

上游 `generate/run` 硬编码下载：

```text
https://raw.githubusercontent.com/astronexus/HYG-Database/master/hygdata_v3.csv
```

执行 `./ctest all` 时：

```text
C ConstellationTest: Cannot open input file: constellation/test_input.txt
ctest: Unit test failed: constellation
```

`hygdata_v3.csv` 经 gh-proxy / ghfast / kkgithub / 直连等全部通道均 404。

## 根因

`generate/run` 与 `make_constellation_data.py` 依赖外部数据仓库
astronexus/HYG-Database 的 **master 分支固定路径**。该仓库已重构：
root 的 `hygdata_v3.csv` 迁移至 `hyg/v3/hyg_v3X.csv.gz`（v3 代数据仍在，
只是路径与压缩格式变化），硬编码 URL 全部失效。

## 修复（数据恢复，不改上游脚本、不补丁源码）

1. 经可用的镜像（gh-proxy）**git 稀疏克隆**数据仓库：

```bash
git clone --depth 1 --filter=blob:none --sparse \
    https://gh-proxy.com/https://github.com/astronexus/HYG-Database hygclone
cd hygclone && git sparse-checkout set hyg/v3
```

2. 取同代数据并做**格式适配**：仓库 CSV 为带引号格式，而上游生成器
   期望无引号列头（`columns['id']` 直接匹配），用 Python csv 模块转换：

```bash
gunzip -k hyg/v3/hyg_v33.csv.gz
python3 - <<'EOF'
import csv
with open('hygdata_v3.csv','r',newline='') as fin, open('hygdata_v3_plain.csv','w',newline='') as fout:
    r, w = csv.reader(fin), csv.writer(fout)
    for row in r: w.writerow(row)
EOF
```

3. 按上游脚本原样生成测试输入：

```bash
python3 make_constellation_data.py   # → Wrote 117958 test cases
./ctest all                          # → ConstellationTest PASS
```

## 验证

- `python3 make_constellation_data.py`：`Wrote 117958 test cases`（exit 0）
- `./ctest all`：ConstellationTest 通过，42/42 全部 PASS

## 适用边界

- **适用**：上游测试脚本硬编码外部 GitHub 数据仓库 raw 路径、仓库重构后
  404、但同代数据仍可通过 git 协议获取的包。
- **反例**：仓库整体删除或要求与被删版本字节一致的数据时无法恢复，
  需如实标记未运行并给出恢复条件（上游归档/重新发布）。

## 查重

- 完整重复：无；因果重复：无
- 部分重叠：E017（GitHub 网络不可达/镜像，仅下载通道）、E299（conan
  source() 阶段 404 分层诊断，非上游测试数据脚本）、E379（CMake
  ExternalData 二进制基线输入闭环，非 git 稀疏克隆路径）
- 新增差异：稀疏克隆取同代数据 + 引号 CSV→plain CSV 格式适配 +
  按上游生成器再生成的可复现测试数据恢复流程
- 关系：similar_to E017/E299/E379

## 决定

**new_draft（路径 B）**——已验证、可跨库复用、查重未命中。
