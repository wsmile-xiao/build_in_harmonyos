# libmpeg2 0.5.1 HarmonyOS PC verification — 2026-10-10

Status: fresh OHOS Conan create, upstream 73/73 and complete consumer 1/1 PASS.
This report does not claim latest-HEAD competition CI or reviewer approval.

| Check | Result | Evidence |
|---|---|---|
| Official source | PASS | VideoLAN tarball SHA-256 dee22e893cb5fc2b2b6ebd60b88478ab8556cb3b93f9a0d7ce8f3b61851871d4 |
| Official CVS fixtures | PASS | ZIP SHA-256 4d42e8eb62bbeb8063ebd0c66a7fb6802b7a9882212c1f7253483f789eb85aa8; 224 restored files for 73 IDs |
| Upstream regression | 73/73 PASS | 68 MD5+dump checks and 5 original IGNORE-MD5 dump checks; missing=0, skipped=0 |
| Conan package | PASS | Two static libraries, public headers and three CLI tools |
| HarmonyOS complete consumer | 1/1 PASS | Input MPEG2 file → 12 decoded RGB24 frames → reference pixel checks → PPM file output/readback → cleanup |
| Transaction closure | PASS | 12 independently replayed receipt phases, release and postrelease complete |

Run: libmpeg2-w3-20261010T023245Z, endpoint 10.62.201.39:2222,
boot ID bf793f5a-e65c-4ce7-959b-bbbc57c6e54d, UID 20020084.
Conan log SHA-256:
379cc3ce8749d03385489b00162453e630dbdf6b314e86dcbb45affa8554c9bf.
Runtime input candidate tree: 64b69b8a37f4fdcbf36cedc76796f7e287852699.
Subsequent report/knowledge changes do not alter the verified runtime inputs.

The installed-package test embeds the complete 605-byte stream
mpeg2dec-streams/twilight_zone/walken/progressive_12x12/stream from the
same official CVS snapshot. Stream SHA-256:
ab2a5b809a69d9a9e0fbae6b6cb5f9ce461d1fe94065e8fda5ffa81c11bcd22c.
It writes the stream in a task-private writable working directory, reads
7-byte chunks through the packaged API and decodes 12 frames. RGB24 pixels
use the aligned 16-pixel stride but crop to the actual 12×12 picture.
The portable C IDCT reference was established with a separate x86 upstream
build and matches the OHOS outputs. This consumer pins mpeg2_accel(0);
the complete upstream suite retains the default decoding path.

Every PPM header and all 432 pixel bytes are read back and compared; input,
output and directory cleanup must also succeed. Each frame has a fixed FNV1a
pixel check. The log includes exactly 12 FRAME lines and
LIBMPEG2_HARMONY_E2E_PASS frames=12 picture=12x12 RGB24=verified PPM=roundtrip.
The 12 frames and internal checks comprise one consumer workflow, not
12 separate declared tests. Adapted total: 73 upstream + 1 consumer = 74.

Historical PR CI includes success #74751 on CI-020 and later worker-prep
SSH bridge refusal #77311 on CI-012. No /rebuild is issued in this repair;
neither historical CI nor local device PASS certifies the new HEAD's CI.
