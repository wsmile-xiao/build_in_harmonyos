# DOSBox Staging 0.82.2-r1 test report

Status: `PASS_TARGET_W3_R178`

| Test class | Registered | Executed | Passed | Failed | Skipped |
|---|---:|---:|---:|---:|---:|
| Upstream Meson entries | 24 | 24 | 24 | 0 | 0 |
| Installed-package consumer flow (r178) | 1 | 1 | 1 | 0 | 0 |

The current target transaction is r178 on
`10.62.150.125:2222`, bound to candidate HEAD
`3901f085f182354cc7033f34cec8acb8507d192e`, staged tree
`a95623dfa420e596f4c9fe521088b7a02a4fc3e1`, and merge base
`5dff0c6a5c137331eb45d77ba4c2326dc01a0f4e`. It used one launch and
finished `POSTRELEASE_PASS` with upstream `24/24`: 23 entries reported `OK`
and the intentional `gtest example` entry reported `EXPECTEDFAIL`. The
installed production capability flow passed `4/4` inside one logical flow:
version identity, NativeWindow/OpenGLES2 frame presentation, non-dummy OHAudio
mixer callback observation, and dynrec guest execution. The target binary SHA-256
is `0270effeadcf6c4e3469e7b5b01fd4a5e03fd96f06ed773b997a6c1927de8e30`, and
the frozen evidence manifest SHA-256 is
`8ad58251ae8419a3e912889520d3e2dab0c2e2c64066cbc070ff472cb50e4371`.
Owner-only release completed with `ROOT_BASE=ABSENT`, `ROOT_EXEC=ABSENT`,
`ROOT_TMP=ABSENT`, and `PID_18532=ABSENT` on an independent readback.

The historical target transaction is r71 on
`10.62.148.108:2222`, bound to candidate HEAD
`4966be612920a2a4cb8d39b4970aa3d7b4639eb1`, staged tree
`fc51ceb58f9676c456864422637445310c49451e`, and merge base
`c705fe4d96e137723f3159ea24b6f22ac1d3b5e4`. It used one launch and
finished `POSTRELEASE_PASS` with upstream `24/24`: 23 entries reported `OK`
and the intentional `gtest example` entry reported `EXPECTEDFAIL`. The
historical installed `dosbox --version` flow passed `1/1`.

The r71 package identity is retained only as historical diagnostic evidence:

- RREV: `01b0062fe9f7abff039ff9330af7369c`
- package ID: `b2dfee4cb2c2d1983f430889a3e9b20656ef587f`
- PREV: `d3bc0865a95ec0c4eb99866fa2aea84b`
- binary SHA-256: `0d272515fadf5e453f6767fba9db7f3c5d8497d9ff7673297a12745166084613`
- binary MD5: `bb3bd27dd0e6089ec56ad1efb2178adb`

The historical frozen evidence manifest SHA-256 is
`40e3de5e3e88a63e85786a0768ac7fe303eb90f4f6722fb97540e5c49326d15d`.
The downloaded 52,199,424-byte evidence archive has SHA-256
`8ce587ab96b1bc41bf8badde5abf430a6f9cd320da8cfba17265e38c9c02088f`.
Release completed with root-bound process count zero and two final clean scans.

Fresh dependency W0 also passed for the historical r71 candidate: the OHOS/armv8 graph has 17 nodes,
`info_invalid=0`, `Missing=0`, and install materialized all 15 non-skipped
packages with `--build=never` and exact RREV/package-ID/PREV agreement.

Historical r16 and r62-r71 outcomes remain diagnostic only. They are not
spliced into the current capability candidate. The current r172 transaction is
bound to endpoint `10.62.150.125:8022`, run ID
`dosbox-staging-0.82.2-r1-issue1093-staged1ff876d8-r172-150125-w3`, HEAD
`56d5bf8ffd8a44aab9b23411c80c273c7a7c4dc6`, tree
`b9c676d934ea516bb4685239051fe9878a1f69e0`, and base
`c705fe4d96e137723f3159ea24b6f22ac1d3b5e4`. It completed one launch and
terminal PASS with upstream `24/24` (23 `OK`, one `EXPECTEDFAIL`) and the
installed capability flow `4/4 PASS`: version identity, NativeWindow/OpenGLES2
frame presentation, non-dummy OHAudio mixer callback observation, and dynrec
guest execution. Owner-only release and two post-release clean scans passed.
This r172 result remains immutable history; the current candidate verdict is
bound only to r178 above.
