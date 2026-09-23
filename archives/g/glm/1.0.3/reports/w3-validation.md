# GLM 1.0.3 W3 validation

- Candidate HEAD: `e7cb27e766463055eaf74eeedf78ff0e110026db`
- Candidate tree: `5c3f7a841a2e3a3d0fef6c1c3bf10ad7742fd38b`
- Run: `glm-1.0.3-w3-r005`
- Endpoint: `10.62.150.125:8022`
- Input ELF: 18,168 bytes, SHA-256
  `e0026ed332e56c34372c4dc736a4a9d29753a5c01bde8b5914944324b752d78f`
- Native signer archive SHA-256:
  `efb7d04e8dd326aef40d8c3788e5932a1f5b9ef4b4c1405ec049d872414306ce`
- Launch count: 1
- Result: target RC0; state assertions 4/4; consumer 1/1
- Output: `glm consumer PASS version 1.0.3`; stderr 0 bytes
- Receipt chain: 10/10, final head SHA-256
  `9d4436e4e39373838eabd537903c1225e78ecd3edafbd62c8aaa936d45859dee`
- Release: PASS; frozen post-release status: `REMOTE_ROOT=ABSENT`
- Final validator SHA-256:
  `4d4185d5c21dca28d798822b22f6c6a4f723e5e5236c7304e018fb9131b21788`

r002 and r003 ended before transfer with launch count 0. r004 consumed one
launch and reached a target RC0, but its frozen host readback entry failed, so
it was not counted as W3 PASS and was released. No result was combined across
runs.
