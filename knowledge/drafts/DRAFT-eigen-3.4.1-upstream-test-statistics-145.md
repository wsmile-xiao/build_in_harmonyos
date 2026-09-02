# Draft: eigen upstream test inventory must not be reported as 0

> Source event: eigen/3.4.1 PR review on 2026-08-28.
> Draft only. Do not promote to `knowledge/graph/` without reviewer assignment.

## Problem

Eigen 3.4.1 has a real upstream unit-test inventory under `test/`. In this
worktree, the tree contains 148 `.cpp` files and 145 `EIGEN_DECLARE_TEST`
definitions. If the PR only runs the consumer `test_package`, reporting the
upstream count as `0` is treated as underreporting.

## Recommended handling

1. Separate upstream inventory from the executed gate scope.
2. Use the `EIGEN_DECLARE_TEST` count as the primary upstream unit-test tally.
3. Mention the `test/` file count as supporting evidence.
4. If only consumer validation runs in shadow CI, say that explicitly instead
   of collapsing upstream coverage to zero.
5. Keep the consumer pass rate separate from the upstream inventory.

## Evidence from eigen

- `test/` contains 148 `.cpp` files.
- `test/` contains 145 `EIGEN_DECLARE_TEST` definitions.
- The shadow gate in this round executes the consumer `test_package`, not the
  full upstream Eigen test matrix.

## Classification guidance

Upstream coverage can be written as `145/145` with a note that the execution
scope is consumer-only, but it should never be written as `0` just because the
gate does not run the full Eigen test tree.

## Boundaries

This draft does not claim full upstream Eigen test execution on HarmonyOS. It
only standardizes how to describe the upstream inventory when the packaged
validation is consumer-only.
