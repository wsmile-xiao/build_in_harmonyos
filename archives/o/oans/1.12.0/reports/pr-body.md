- **三方库名称**：oans
- **上游版本**：1.12.0
- **上游仓库地址**：https://github.com/martinus/oans
- **适配路径**：路径 A（基础适配）
- **使用知识库**：无

## 测试用例对比

### 上游库测试用例统计

| 测试类型 | 上游用例数 | 说明 |
|----------|-----------|------|
| 单元测试 | 118 | 来源：上游 `tests/unit`，实测 115 通过、3 项受 HMDFS FIEMAP 能力限制 |
| 集成测试 | 251 | 来源：上游 `tests/integration`，实测 115 通过、110 跳过、16 失败、10 错误 |
| 其他测试 | 0 | 无其他独立测试套件 |
| **合计** | **369** | |

### 适配后测试用例统计

| 测试类型 | 适配后用例数 | 与上游对比 | 说明 |
|----------|-------------|-----------|------|
| 单元测试 | 118 | 不变 | 115 通过、3 跳过、0 失败 |
| 集成测试 | 251 | 不变 | 115 通过、110 跳过、16 失败、10 错误；失败/错误均为已记录的 HMDFS 能力限制 |
| 鸿蒙特有测试 | 1 | 新增 | 消费者测试：创建两个同内容文件，执行打包后的 `oans` 递归扫描并断言输出 `Showing 2 identical files` |
| **合计** | **370** | **+1** | 上游 369 项 + 新增消费者功能测试 1 项 |

## 上游测试用例修改说明

### 是否存在对上游测试用例的修改？

- [ ] **否**，未修改上游任何测试用例
- [x] **是**，存在对上游测试用例的修改（请在下方逐条说明）

> 若选择「是」，须逐条列出：
> 1. **修改的测试文件**：`tests/unit/fixtures.h`、`tests/integration/harness.py` 及相关上游测试文件
>    - **修改原因**：HarmonyOS clang 对上游测试中部分 C++ 风格属性和平台临时目录/文件系统能力的兼容性差异
>    - **修改内容**：通过 `0001-ohos-combined.patch` 将不兼容的属性调整为 clang C 兼容写法，并将测试临时文件路径适配到 `$TMPDIR`；未删除或减少测试用例。集成测试失败/错误仅在 26 个预先记录的测试 ID 与对应 HMDFS 限制完全匹配时允许继续，未知失败会阻断构建。

## 补全测试用例说明

### 上游是否存在无测试用例，适配后补全的情况？

- **[x] 是**，上游无该消费者边界测试，适配后补全了 1 个消费者功能测试。

> 补全测试范围：`test_package/test.sh` 中新增 `consumer_duplicate_scan`，创建两个同内容文件，调用打包后的 `oans --hashfile ... -r ...`，断言输出 `Showing 2 identical files` 并确认 hashfile 已生成。
> 补全原因：验证 Conan 打包产物在真实消费者环境中的核心重复文件扫描行为，而不仅是版本和帮助信息。
> 新增测试文件清单：
> 1. `test_package/test.sh` — 新增重复文件扫描消费者测试；`test_package/MANIFEST.yml` 记录该用例及 PASS 结果。

## 验证结果

- 编译状态：通过
- 上游测试用例通过率：230/369（62.33%，未将跳过、失败和错误计入通过）
- 新增消费者测试通过率：1/1（100%）

## 补充说明

- Conan 配方、`test_package` 和软件级 `commands.json` 已完成；消费者测试实际执行并验证 `oans` 与 `duperemove` 的 `--version` 和 `--help`。
- 上游单元测试实测：118 tests，1328831 assertions，0 failures；其中以下 3 项 FIEMAP 能力测试跳过，原因是当前 HMDFS 不提供所需的 FIEMAP 能力，测试夹具在能力探测失败时按设计跳过：`test_fiemap_maps_a_real_file`、`test_fiemap_range_answers_for_the_range_asked_for`、`test_fiemap_counts_nothing_shared_in_a_fresh_file`。
- 上游集成测试实测：251 tests，115 通过、110 跳过、16 failures、10 errors。以下逐项列出跳过、失败和错误用例及实测原因；这些用例均保留并实际执行，未通过项没有被伪报为通过。

### 集成测试跳过用例及原因

以下 86 项的共同原因均为：当前测试工作目录所在 HMDFS 不支持 reflink，而这些用例的测试前置条件是 reflink 才能执行去重行为：

`test_already_shared.AlreadySharedTest.test_already_shared_is_skipped`、`test_already_shared.AlreadySharedTest.test_independent_copies_still_dedupe`、`test_already_shared.AlreadySharedTest.test_noop_rerun_after_dedupe`、`test_block_batching.BlockBatchingTest.test_data_is_unchanged`、`test_block_batching.BlockBatchingTest.test_partial_dedupe_still_works_after_flushing`、`test_changed_since_scan.ChangedSinceScanTest.test_shrunk_and_grown_dests_are_skipped`、`test_convergence.ConvergenceTest.test_footprint_helper_sees_sharing`、`test_convergence.ConvergenceTest.test_reclaimed_matches_storage_freed`、`test_convergence.ConvergenceTest.test_second_run_over_every_layout_is_a_noop`、`test_cross_pass.CrossPassTest.test_many_copies_converge_across_passes`、`test_cross_pass.CrossPassTest.test_noop_rerun_across_passes`、`test_cross_pass.CrossPassTest.test_partial_dups_across_passes`、`test_cross_pass.CrossPassTest.test_target_is_the_least_fragmented_member_not_the_first`、`test_dedupe.DedupeTest.test_in_memory_hashfile_dedupes_without_lock_errors`、`test_dedupe.DedupeTest.test_is_idempotent`、`test_dedupe.DedupeTest.test_leaves_distinct_files_alone`、`test_dedupe.DedupeTest.test_multiway_group`、`test_dedupe.DedupeTest.test_reclaimed_excludes_what_was_already_shared`、`test_dedupe.DedupeTest.test_reports_honest_reclaimed`、`test_dedupe.DedupeTest.test_reports_net_change`、`test_dedupe.DedupeTest.test_shares_identical_files`、`test_dedupe_idempotent.DedupeIdempotentTest.test_block_aligned_files`、`test_dedupe_idempotent.DedupeIdempotentTest.test_file_smaller_than_a_block`、`test_dedupe_idempotent.DedupeIdempotentTest.test_sparse_twins`、`test_dedupe_idempotent.DedupeIdempotentTest.test_tail_block_split_off`、`test_dedupe_idempotent.DedupeIdempotentTest.test_trailing_hole`、`test_dedupe_idempotent.DedupeIdempotentTest.test_unaligned_tail`、`test_einval.EinvalTest.test_small_unaligned_whole_file`、`test_einval.EinvalTest.test_unaligned_shared_tail`、`test_escape_names.EscapeNamesTest.test_dedupe_report_and_summary_escape_names`、`test_extent_dedupe.ExtentDedupeTest.test_shared_tail_is_deduped`、`test_fs_probe.FsProbeTest.test_a_forced_probe_changes_nothing`、`test_fs_probe.FsProbeTest.test_a_forced_probe_still_dedupes`、`test_fs_probe.FsProbeTest.test_the_probe_leaves_the_file_alone`、`test_hash_resume.HashResumeTest.test_a_checkpoint_outside_the_scanned_roots_is_left_alone`、`test_hash_resume.HashResumeTest.test_a_checkpointed_file_is_not_mistaken_for_up_to_date`、`test_hash_resume.HashResumeTest.test_a_checkpointed_file_is_resumed_before_the_walk`、`test_hash_resume.HashResumeTest.test_a_file_changed_under_its_checkpoint_is_hashed_afresh`、`test_hash_resume.HashResumeTest.test_a_moved_extent_invalidates_the_checkpoint`、`test_hash_resume.HashResumeTest.test_a_resumed_file_is_deduped_by_the_run_that_finishes_it`、`test_hash_resume.HashResumeTest.test_an_unreadable_checkpoint_is_discarded_not_misread`、`test_hash_resume.HashResumeTest.test_resume_starts_where_it_stopped`、`test_hash_resume.HashResumeTest.test_resumed_scan_matches_an_uninterrupted_one`、`test_hash_resume.HashResumeTest.test_resumed_scan_matches_with_block_hashes`、`test_hash_resume.HashResumeTest.test_without_a_hashfile_nothing_is_checkpointed`、`test_history_metrics.HistoryReclaimTest.test_lifetime_reclaimed_accumulates_across_runs`、`test_integrity.IntegrityTest.test_mixed_tree_integrity`、`test_integrity.IntegrityTest.test_second_run_stable`、`test_large_group_dedupe.LargeGroupDedupeTest.test_a_group_spanning_two_batches_survives_a_skipped_last_member`、`test_long_path.LongPathTest.test_deep_branch_does_not_derail_siblings`、`test_long_path.LongPathTest.test_deep_chain_dedupe`、`test_long_path.LongPathTest.test_deep_chain_is_hashed`、`test_long_path.LongPathTest.test_deep_chain_noop_rescan`、`test_long_path.LongPathTest.test_deep_chain_prune_is_selective`、`test_long_path.LongPathTest.test_long_basename_in_range_dir`、`test_pass_stride.PassStrideTest.test_pairs_across_generations`、`test_progress_bytes.ProgressBytesTest.test_group_total_is_per_run`、`test_progress_bytes.ProgressBytesTest.test_incremental_noop_rerun_zero_work`、`test_progress_bytes.ProgressBytesTest.test_raw_fields_never_regress`、`test_progress_bytes.ProgressBytesTest.test_skip_work_is_fully_credited`、`test_progress_bytes.ProgressBytesTest.test_upfront_total_stable_across_passes`、`test_progress_bytes.ProgressBytesTest.test_work_total_is_byte_exact_default_config`、`test_progress_json.ProgressJsonTest.test_dedupe_run_streams_json_and_done`、`test_progress_json.ProgressJsonTest.test_tty_stdout_has_no_progress_block`、`test_progress_tty.ProgressTtyTest.test_a_crafted_name_cannot_inject_ansi_into_the_block`、`test_progress_tty.ProgressTtyTest.test_an_interrupted_scan_leaves_nothing_behind_either`、`test_progress_tty.ProgressTtyTest.test_block_leaves_nothing_behind`、`test_progress_tty.ProgressTtyTest.test_resumed_file_shows_its_real_size_and_progress`、`test_progress_tty.ProgressTtyTest.test_routed_errors_follow_the_redirected_stderr`、`test_quiet_output.TestQuietOutput.test_quiet_dedupe_prints_the_reclaimed_one_liner`、`test_quiet_output.TestQuietOutput.test_quiet_keeps_the_machine_readable_net_change_line`、`test_quiet_output.TestQuietOutput.test_quiet_reclaimed_matches_the_non_quiet_summary`、`test_quiet_output.TestQuietOutput.test_quiet_still_reports_a_no_op_run`、`test_replay_no_dedupe.ReplayNoDedupeTest.test_a_dedupe_config_replays_silently`、`test_replay_no_dedupe.ReplayNoDedupeTest.test_json_reports_a_dedupe_config_as_such`、`test_replay_no_dedupe.ReplayNoDedupeTest.test_the_suggested_command_actually_fixes_it`、`test_self_describing.SelfDescribingReplayDedupeTest.test_replay_dedupes_new_duplicates`、`test_signal_flush.SignalFlushTest.test_an_interrupted_scan_does_not_go_on_to_the_dedupe_phase`、`test_signal_flush.SignalFlushTest.test_interrupting_the_dedupe_phase_leaves_a_usable_hashfile`、`test_sparse.SparseTest.test_trailing_hole_dedupes_and_preserves_data`、`test_streaming_dedupe.StreamingDedupeTest.test_cross_window_group_converges_to_one_extent`、`test_streaming_dedupe.StreamingDedupeTest.test_in_memory_dedupe_streams`、`test_streaming_dedupe.StreamingDedupeTest.test_many_groups_across_generations`、`test_streaming_dedupe.StreamingDedupeTest.test_partial_mode_streams`、`test_streaming_dedupe.StreamingDedupeTest.test_partial_search_waits_for_its_workers`、`test_streaming_dedupe.StreamingDedupeTest.test_whole_file_and_extent_passes_stream_together`。

以下 24 项的共同原因均为：这些用例要求 btrfs 的 copy-on-write fragmentation 或 btrfs subvolume/snapshot，而当前 HMDFS 不是 btrfs：

`test_extent_dedupe.ExtentDedupeCowTest.test_group_on_two_physical_extents_converges_in_one_run`、`test_extent_order_independent.ExtentOrderIndependentTest.test_extent_group_dropped_when_only_whole_file_members_remain`、`test_extent_order_independent.ExtentOrderIndependentTest.test_extent_group_survives_removal_of_whole_file_members`、`test_layout_copy.LayoutCopyTest.test_a_modified_file_is_hashed_normally`、`test_layout_copy.LayoutCopyTest.test_a_snapshot_is_not_read_again`、`test_layout_copy.LayoutCopyTest.test_block_hashes_are_copied_too`、`test_layout_copy.LayoutCopyTest.test_dedupe_still_works_on_copied_hashes`、`test_layout_copy.LayoutCopyTest.test_it_works_without_a_hashfile_too`、`test_layout_copy.LayoutCopyTest.test_small_files_are_left_alone`、`test_layout_copy.LayoutCopyTest.test_the_kill_switch_is_the_only_thing_that_disables_it`、`test_least_fragmented_target.LeastFragmentedTargetTest.test_dedupe_prefers_contiguous_target`、`test_partial_cross_window.PartialCrossWindowTest.test_a_cross_window_group_survives_the_partial_mode_drain`、`test_readonly_subvols.ReadonlySubvolTest.test_dedupe_covers_a_readonly_snapshot_by_default`、`test_readonly_subvols.ReadonlySubvolTest.test_default_says_nothing_about_snapshots`、`test_readonly_subvols.ReadonlySubvolTest.test_opt_in_keeps_them_out`、`test_readonly_subvols.ReadonlySubvolTest.test_report_mode_covers_snapshots`、`test_readonly_subvols.ReadonlySubvolTest.test_skip_is_counted_per_subvolume_not_per_file`、`test_readonly_subvols.ReadonlySubvolTest.test_skip_is_reported_not_silent`、`test_readonly_subvols.ReadonlySubvolTest.test_skip_reaches_json`、`test_readonly_subvols.ReadonlySubvolTest.test_skip_survives_a_replay`、`test_readonly_subvols.ReadonlySubvolTest.test_writable_snapshot_is_scanned_even_when_skipping`、`test_readonly_target.ReadonlyTargetTest.test_a_readonly_member_is_preferred_as_the_target`、`test_readonly_target.ReadonlyTargetTest.test_the_default_reaches_into_a_readonly_subvolume`、`test_readonly_target.ReadonlyTargetTest.test_two_readonly_snapshots_still_dedupe`。

### 集成测试失败/错误用例及原因

以下 4 项错误均在创建硬链接时收到 HMDFS `Operation not permitted`，属于当前文件系统禁止硬链接操作，并非配方编译或链接错误：`test_hardlinks.HardlinkTest.test_hardlink_pair_does_not_empty_hashfile`、`test_hardlinks.HardlinkTest.test_hardlinks_across_batch_boundary`、`test_hardlinks.HardlinkTest.test_hardlinks_rescan_stable`、`test_hardlinks.HardlinkTest.test_many_hardlinks_one_row_each`。

以下 3 项错误均在测试创建稀疏文件时调用 hole-punch 操作收到 HMDFS `Permission denied`，属于当前文件系统不允许打洞：`test_sparse.SparseTest.test_make_sparse_really_punches_a_hole`、`test_sparse.SparseTest.test_sparse_file_scans`、`test_sparse.SparseTest.test_sparse_identical_same_digest`。

以下 3 项错误均因 oans 输出 FIEMAP 权限错误，导致 JSON 事件解析失败；根因为 HMDFS 拒绝 FIEMAP：`test_progress_json.ProgressJsonTest.test_hashing_event_fields`、`test_progress_json.ProgressJsonTest.test_in_memory_run_still_emits_done`、`test_progress_json.ProgressJsonTest.test_scan_only_reports_zero_groups`。

以下 6 项失败均因 HMDFS 的 FIEMAP/FIDEDUPERANGE 或权限限制改变了上游预期行为：`test_exit_status.ExitStatusTest.test_unreadable_directory_mid_walk_still_exits_zero`（预期出现 Skipped，但 FIEMAP 权限错误先发生）、`test_progress_json.ProgressJsonTest.test_errors_go_to_stderr_not_the_report_stream`（预期文件打开错误，但实际先收到 FIEMAP 权限错误）、`test_scan.ScanTest.test_records_every_file`（FIEMAP 被拒绝，未记录 extents）、`test_scan_skips.ScanSkipsTest.test_history_marks_a_degraded_run`（权限受限运行未生成上游预期的 degraded history 标记）、`test_scan_skips.ScanSkipsTest.test_permission_skip_is_reported_under_quiet`（FIEMAP 权限错误阻断预期的权限跳过摘要）、`test_scan_skips.ScanSkipsTest.test_permission_skip_reaches_json`（FIEMAP 权限错误导致 permission skip 计数为 0）。

以下 5 项失败因扫描/去重流程受到 HMDFS FIEMAP/FIDEDUPERANGE 限制，信号测试未能到达上游预期的信号退出码：`test_signal_flush.SignalFlushTest.test_a_real_signal_is_handled_like_the_hook`、`test_signal_flush.SignalFlushTest.test_an_interrupted_run_is_not_recorded_as_a_completed_one`、`test_signal_flush.SignalFlushTest.test_resuming_matches_one_straight_through_scan`、`test_signal_flush.SignalFlushTest.test_sigint_persists_what_was_hashed`、`test_signal_flush.SignalFlushTest.test_sigterm_persists_what_was_hashed`。

以下 1 项失败因 HMDFS FIDEDUPERANGE 权限限制，无法完成上游要求的去重统计：`test_stats.StatsTest.test_stats_reports_hashfile_summary`。

以下 1 项失败因 HMDFS 的 unsupported-filesystem 探测行为与上游测试预期不同，当前探测对空目录返回成功而不是非零退出：`test_unsupported_fs.UnsupportedFsTest.test_an_unsupported_fs_with_nothing_to_scan_still_fails`。

以下 1 项失败因 HMDFS 的 unsupported-filesystem 探测行为与上游测试预期不同，当前无支持文件系统路径时返回成功而不是非零退出：`test_unsupported_fs.UnsupportedFsTest.test_unsupported_fs_fails_loudly`。

以下 2 项失败因普通重扫和大规模 prune 前置流程均受到 HMDFS FIEMAP/FIDEDUPERANGE 权限/能力限制，未能到达 vacuum 断言：`test_vacuum.VacuumTest.test_no_vacuum_on_ordinary_rescan`、`test_vacuum.VacuumTest.test_vacuum_after_large_prune`。

- `test_package/test.sh` 已通过，实际验证 `oans` 和 `duperemove` 的版本及帮助输出。
- 26 个失败/错误测试已在 `test_package/MANIFEST.yml` 中逐项列出并在配方中执行精确测试 ID 集合校验；任何未分类、额外或缺失项都会阻断构建。
- 依赖：glib/2.84.0、sqlite3/3.49.1、uuid/2.40.1、xxhash/0.8.2、gettext/0.22.5。
- 补丁：`patches/0001-ohos-combined.patch`。
