# activity-aware-firefox 0.4.2+git20250816.c6082f37 adaptation notes

## Environment

- Target: OpenHarmony/HarmonyOS PC, arm64
- Build system: script packaging (Conan 2)
- Date: 2026-08-12
- Status: built

## Root cause

Upstream selects a Firefox profile from KDE Activities and exits when
`plasma-activities-cli`, X11 `xdpyinfo`, or `kdialog` is unavailable.
OpenHarmony does not expose an equivalent KDE Activities interface.

## Adaptation

`0001-activityfirefox.patch` keeps automatic KDE provider
discovery; adds explicit ID/name inputs suitable for an OpenHarmony launcher or
system parameter bridge; makes display geometry and notifications optional; and
adds `--probe-context` for deterministic verification.

## Verification

The test package checks fourteen assertions. It invokes the packaged
`bin/activityfirefox`, verifies explicit provider resolution and rejects partial
or unsafe IDs, then runs the complete profile flow with an isolated HOME and a
recording Firefox executable. The flow covers template/profile creation,
existing-profile reuse, profile-path selection, and Firefox argument forwarding.

## Boundary

The package does not emulate KDE Activities and does not ship Firefox. A caller
must provide a stable OpenHarmony workspace/context identity using the documented
safe ID alphabet. The isolated functional test verifies the wrapper's profile
creation/selection contract; a real Firefox GUI session still requires Firefox,
Bash, and a graphical target device.

## 最终状态

COMPLETED — OHOS/arm64 Conan package creation passed. The packaged-script
functional test passed 14/14 assertions. A real Firefox GUI session remains a
documented integration boundary and is not counted as tested.
