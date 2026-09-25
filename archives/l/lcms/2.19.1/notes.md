# lcms (Little CMS) 2.19.1 adaptation notes

## Build

- Build system: Autotools
- Conan package type: library
- Options: `shared=True/False`, `fPIC`
- Dependencies: none (JPEG/TIFF/zlib optional support disabled to keep the core ICC engine dependency-free)
- Patches: `0001-config.guess.patch`, `0002-config.sub.patch`, `0003-configure-hmdfs-umask.patch`
- Status: version follow-up of the merged `lcms2/2.19` recipe (#7578); same patch set applies cleanly to the official 2.19.1 release archive (verified via `patch -p1 --dry-run` before integration)

## Upstream changes 2.19 -> 2.19.1

Upstream maintenance release; `include/lcms2.h` keeps `LCMS_VERSION 2190`. Build layout,
`configure`, `config.guess` (2018-02-24) and `config.sub` (2024-01-01) are identical to 2.19,
so the three portability patches carry over verbatim.

## Notes

- 归档目录按平台任务名 `lcms` 新建（taskBranch `feat/lcms-2.19.1`），仓内另有
  `lcms2` 历史线（2.16/2.19）；两者并存遵循 open-scene-graph #5578 先例——L0n 分支
  门禁从归档目录名推导期望分支名，归档路径必须与任务 taskBranch 对齐。
- Conan 包名 `lcms`，但 CMake 目标名/pc 文件保持上游原值 `lcms2::lcms2` / `lcms2`，
  消费者接口与上游完全一致。

## Validation

- OHOS aarch64 本机（local_verify）：`conan create` + 上游 `make check`（testbed 270 项检查）+ test_package 消费者测试
- 详见 PR 正文测试统计表
