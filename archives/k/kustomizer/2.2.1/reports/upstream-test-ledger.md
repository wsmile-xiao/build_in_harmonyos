# kustomizer v2.2.1 上游测试台账 (upstream test ledger)

## 测试对象与运行环境

- 上游：https://github.com/stefanprodan/kustomizer (tag v2.2.1)
- 测试代码：`cmd/kustomizer/*_test.go`，共 **14 个测试文件**
- 运行工具链：自举官方静态 **go1.24.13 linux-arm64**（见 notes.md；上游
  go.mod 声明 `go 1.19`，但官方 1.19 linux-arm64 工具链动态链接 glibc，无法
  在 musl-only 的鸿蒙运行，故用纯静态且向后兼容的 1.24.13）
- 控制平面：[envtest](https://book.kubebuilder.io/reference/envtest.html)
  assets，为保证供应链可核验，按 setup-envtest 等价方式手动组装：
  - `kube-apiserver`、`kubectl`：官方静态二进制，来自 https://dl.k8s.io
    （v1.25.x）
  - `etcd`：官方发行版（v3.5.6 linux-arm64）
  - 三者均为旧 Go 链接产物，先 GNU strip 规整段头再用 binary-sign-tool
    自签名，否则无法在鸿蒙执行
- 关键环境变量：`KUBEBUILDER_ASSETS=<assets dir>`、
  `TMPDIR=/data/storage/el2/base/cache`（HMDFS 不支持 etcd WAL 的
  fallocate，需指向应用缓存目录）

### 测试设施说明（不修改上游源码/测试）

测试在完全干净的上游源码树上运行，**没有修改任何上游测试用例或源码**，
`conandata.yml` 的 `patches: []`。仅有两处沙箱专属的测试设施：

1. `KUBEBUILDER_ASSETS` 中的 `kube-apiserver` 用一个 wrapper 脚本包装，
   追加 `--advertise-address=127.0.0.1`。原因：沙箱内没有默认路由，
   kube-apiserver 自动探测 advertise address 会失败并导致启动超时；实测
   显式指定回环地址后 apiserver 正常启动。wrapper 属于 envtest 运行设施，
   不是上游代码或测试的一部分。
2. `TMPDIR` 指向支持 fallocate 的缓存目录（etcd WAL 需要）。

运行命令（静态编译测试二进制 → 签名 → 以 envtest 运行）：

```
CGO_ENABLED=0 go test -c -o kustomizer.test ./cmd/kustomizer
# strip + self-sign kustomizer.test
KUBEBUILDER_ASSETS=$PWD/testbin TMPDIR=/data/storage/el2/base/cache \
  ./kustomizer.test -test.v -test.count=1
```

## 结果汇总

| 口径 | 通过 | 失败 | 跳过 | 通过率 |
|---|---|---|---|---|
| 顶层测试函数 | 15 | 0 | 0 | 100% |
| 子测试 | 37 | 0 | 0 | 100% |

最终结果：`PASS`（rc=0）。无任何上游测试失败，因此不存在因失败需要说明
的用例；下列逐条结果来自实际测试日志（fulltest.log / rerun.log，两次独立
运行结果一致）。

## 逐条明细

### TestApply — PASS（6 个子测试）

| 子测试 | 结果 |
|---|---|
| TestApply/creates_objects | PASS |
| TestApply/labels_objects | PASS |
| TestApply/prunes_objects | PASS |
| TestApply/waits_for_objects | PASS |
| TestApply/recreates_immutable_objects | PASS |

### TestApplyArtifact — PASS（3 个子测试）

| 子测试 | 结果 |
|---|---|
| TestApplyArtifact/pushes_artifact | PASS |
| TestApplyArtifact/applies_artifact | PASS |
| TestApplyArtifact/sets_artifact_in_inventory | PASS |

### TestApplyEncryptedArtifact — PASS（2 个子测试）

| 子测试 | 结果 |
|---|---|
| TestApplyEncryptedArtifact/pushes_encrypted_artifact | PASS |
| TestApplyEncryptedArtifact/decrypts_and_applies_artifact | PASS |

### TestBuild — PASS（2 个子测试）

| 子测试 | 结果 |
|---|---|
| TestBuild/builds_objects | PASS |
| TestBuild/patch_objects | PASS |

### TestConfigView — PASS（无子测试）

### TestDelete — PASS（2 个子测试）

| 子测试 | 结果 |
|---|---|
| TestDelete/creates_objects | PASS |
| TestDelete/deletes_objects | PASS |

### TestDiffArtifact — PASS（2 个子测试）

| 子测试 | 结果 |
|---|---|
| TestDiffArtifact/push_artifacts | PASS |
| TestDiffArtifact/pull_artifact | PASS |

### TestDiffInventory — PASS（4 个子测试）

| 子测试 | 结果 |
|---|---|
| TestDiffInventory/creates_objects | PASS |
| TestDiffInventory/generates_empty_diff | PASS |
| TestDiffInventory/generates_created_diff | PASS |
| TestDiffInventory/generates_YAML_diff | PASS |

### TestGetInventories — PASS（3 个子测试）

| 子测试 | 结果 |
|---|---|
| TestGetInventories/creates_objects | PASS |
| TestGetInventories/gets_inventory | PASS |
| TestGetInventories/gets_inventories | PASS |

### TestInspect — PASS（3 个子测试）

| 子测试 | 结果 |
|---|---|
| TestInspect/build_and_push_artifact | PASS |
| TestInspect/inspect_artifact | PASS |
| TestInspect/inspect_artifact_images | PASS |

### TestGetInventory — PASS（2 个子测试）

| 子测试 | 结果 |
|---|---|
| TestGetInventory/creates_objects | PASS |
| TestGetInventory/prints_inventory_details | PASS |

### TestListArtifact — PASS（3 个子测试）

| 子测试 | 结果 |
|---|---|
| TestListArtifact/push_artifacts | PASS |
| TestListArtifact/lists_all_versions | PASS |
| TestListArtifact/lists_prereleases | PASS |

### TestPull — PASS（2 个子测试）

| 子测试 | 结果 |
|---|---|
| TestPull/push_artifact | PASS |
| TestPull/pull_artifact | PASS |

### TestPush — PASS（1 个子测试）

| 子测试 | 结果 |
|---|---|
| TestPush/build_and_push_artifact | PASS |

### TestTag — PASS（3 个子测试）

| 子测试 | 结果 |
|---|---|
| TestTag/push_artifact | PASS |
| TestTag/tag_artifact | PASS |
| TestTag/pull_artifact | PASS |

## 备注

- 子测试计数校验：5+3+2+2+0+2+2+4+3+3+2+3+2+1+3 = **37**。
- `TestMain` 负责启动/停止 envtest 控制平面，是测试夹具而非用例，不计入
  用例数。
- OCI artifact 相关用例（push/pull/list/tag/inspect/diff/apply artifact）
  使用测试内置的本地 registry（envtest 测试套件自带），无需外部 registry
  或真实 Kubernetes 集群，因此全部在本地真实跑通。
