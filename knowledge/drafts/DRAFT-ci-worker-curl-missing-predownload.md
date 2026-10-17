# E7xx（草稿）：CI Worker 缺 curl 的三连 fail 识别与配方侧判定法——Pre-download WARN 降级是良性平台噪音

**状态**: pending-editor-review（随 PR !10999 提交，最终编号由主编确认）

## 一、错误特征（可机器匹配）

CI 失败评论完整日志的** Pre-download 步骤段**出现三连同款 fail，且紧随 WARN 降级后流水线继续：

```console
[step] Pre-download: extracting source URLs from conandata.yml...
  [fail] [Errno 2] No such file or directory: 'curl'
  [fail] [Errno 2] No such file or directory: 'curl'
  [fail] [Errno 2] No such file or directory: 'curl'
[WARN] Failed to pre-download kxmlgui-6.26.0.tar.xz, will rely on conan's download
（此后流水线继续——conan 自身下载器接手并成功：）
kxmlgui/6.26.0: Sources correctly downloaded from https://download.kde.org/stable/frameworks/6.26/kxmlgui-6.26.0.tar.xz
```

**三要素齐 = 良性平台噪音**：① 三连 fail 都在 `[step] Pre-download:` 步骤内（不是配方的调用）；② 紧随 `[WARN] ... will rely on conan's download`；③ WARN 后流水线继续推进（下载/编译/测试步骤照常执行）。

## 二、根因链

```
CI Worker 池（buildbot conan-pr-check）部分机器无 curl 二进制
（实证：CI-011、CI-032；健康机：CI-007/012/020/026/033/036 无此噪音）
        │
        └─ ci/conan/build_and_test.sh Pre-download 步骤（L1164-1297）
           用外部 curl -sL --retry 3 从 conandata.yml 提取 URL 预下载，
           改写 conandata 为 file:// 本地路径（加速层）
                │
                ├─ curl 不存在 → Python FileNotFoundError ×3 → [fail] ×3
                │
                └─ 设计语义：尽力而为——失败输出 WARN（非 ERROR）降级，
                   conan 自身 source() 的 Python requests 下载器接手走官方 URL
```

**为什么配方侧无需动**：Pre-download 是 CI 侧的加速优化层，不是必需路径。降级后 conan 的下载器直接走 conandata.yml 的官方 URL——只要官方 URL 可达（download.kde.org 等原生可达），下载照常成功。**三连 curl fail + WARN + 流水线继续 = 病机 worker 的无害噪音**，与 PR 内容完全正交。

## 三、判别法（配方侧判定决策树）

1. **定位**：三连 `[Errno 2] No such file or directory: 'curl'` 是否都在 `[step] Pre-download:` 步骤内？——是 → CI 基础设施的外部 curl，不是配方调用。
2. **降级语义**：紧随 `[WARN] Failed to pre-download ... will rely on conan's download`？——是 → 不阻断，conan 下载器接手。
3. **分离判定**（关键一步，决定动不动配方）：
   - **3a WARN 后流水线继续**（conan source 下载成功 / conan create 走到编译测试段）→ curl 噪音，真红因（若有）在别处，**配方零修改**，`/rebuild` 撞健康 worker 即可；
   - **3b conan create 的 source() 也死**（Max retries exceeded / ConnectTimeout / github archive 302 链死）→ 切换到 E569 场景（改 codeload 直链）或 E372 场景（加权威 HTTP fallback）——这才是配方侧要动手的分支。
4. **不混淆分界线**（Pre-download 病机 ≠ 配方调 curl）：

   ```bash
   grep -rn "curl" test_package/ conanfile.py
   # 无命中 → Pre-download 病机（本条，不用改配方）
   # 有命中 → 配方侧 subprocess/os.system 调 curl 下载——CI L0o 门禁
   #          （build_and_test.sh L904-913）直接拦截，需改 python3
   #          urllib/requests（那是另一个条目的主题）
   ```

5. **处置**：3a 形态直接裸 `/rebuild`（健康 worker 池实证：CI-007/CI-012/CI-020/CI-026/CI-033/CI-036）。

## 四、实证链（五案连环，2026-09-19 同日）

| PR | curl 噪音轮（红） | 真红因（与 curl 分离） | 最终绿（配方未改） |
|----|------------------|----------------------|-------------------|
| !10999 kxmlgui（锚） | #51136（CI-011）#51180（CI-032） | kconfigwidgets/6.18.0 binary missing → 源码重建失败（`Error in build() method, line 143 cmake.configure()`）；curl fail 后 `Sources correctly downloaded` 成功 | #51251（CI-036） |
| !10894 kimageformats5 | #51109（CI-011） | 真因另判（同款噪音形态） | #51202（CI-012） |
| !11112 keditbookmarks | #51089/#51148/#51160/#51255/#51298（CI-011/CI-012 混跑五轮） | 真因另判 | #51466（CI-012） |
| !11147 daw-utf-range | #51289（CI-032） | 真因另判；AI review 通过 | #51377（CI-020） |
| !9693 mmkv（先例，E569 草稿） | #45043 系列实录 | conan 直连也死（github archive 302 链）→ 走配方侧修法（codeload 直链） | #45438/#45604（改 URL 后） |

**最有力的对照实证**：#11112 的 #51089（13:32，CI-012，含 curl 噪音红）与 #51466（18:52，CI-012，绿）是**同一台 worker**——CI-012 在 #11112 早期跑过含噪音的轮次、后期绿轮无噪音；且 #10999 的 CI-032（15:08 病机轮）与 #11147 的 CI-032（16:40 病机轮）同款——**噪音是"哪个 worker 接单"的函数，与 PR 内容（配方质量）正交**。

## 五、与 E372/E569 的边界（查重覆盖判断）

| 条目 | 回答的问题 | 配方侧动作 |
|------|-----------|-----------|
| **本条（判定法）** | 三连 curl fail 是不是红因？**要不要改配方？** | **零修改**（3a 形态）/ 转出（3b 形态） |
| E372（已入库） | worker 无 curl 且无 SSL，配方侧怎么加权威 HTTP fallback | 加 authority HTTP mirror |
| E569（草稿） | worker 缺 curl + github 302 链死，怎么改直链 | codeload 直链 + filename |

三条合起来覆盖"缺 curl worker"完整决策空间：**先判定（本条）→ 需要改时选修法（E569 直链 / E372 fallback）**。知识库 grep "No such file or directory: 'curl'" 命中 E372（pkgconf #5532，配方侧 fallback 策略）与 DRAFT-E569（mmkv #9693，配方侧直链策略）——**零条目覆盖"判定法/无需修改"这个增量**。

## 六、红线（禁止的反应）

- ❌ 看到三连 curl fail 就动 conandata.yml（改 http://、加 gh-proxy 前缀——会被 Pre-download 剥除且违反 R39）
- ❌ 把病机噪音当红因上报（真实红因被掩盖，白烧 CI 轮次）
- ❌ 混淆 Pre-download 病机与配方 test_package 调 curl（后者才需要改 urllib）——grep test_package 是分界线
- ✅ 正确姿势：定位三要素 → WARN 降级确认 → 真因分离 → 3a 直接 /rebuild

## 七、验证命令

```bash
# 判定流程（对任意 CI 失败评论的完整日志）：
# 1. 三连 fail 都在 Pre-download 步骤内？
grep -n "Pre-download: extracting\|\[fail\] \[Errno 2\] No such file or directory: 'curl'" ci_log.txt
# 2. WARN 降级存在？
grep -n "will rely on conan's download" ci_log.txt
# 3. conan 下载器接手成功？
grep -n "Sources correctly downloaded" ci_log.txt
# 4. 配方侧无 curl 调用（分界线）？
grep -rn "curl" test_package/ conanfile.py
# 全部确认 → 3a 良性噪音 → /rebuild（裸命令）
```
