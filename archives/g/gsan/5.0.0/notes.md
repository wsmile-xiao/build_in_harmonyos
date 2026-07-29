# gsan 5.0.0 OpenHarmony adaptation

This Path B adaptation keeps the upstream CLI behavior while removing runtime dependencies unavailable in the repository's OpenHarmony package graph.

- Upstream: `https://pypi.org/project/gsan/5.0.0/`
- Source archive SHA256: `2418a6897b0eb1c6eb44c3521ccc5c69a811071f864b8001fd9699a4d2f4c9e3`
- Patch: `0001-use-python-stdlib.patch`
- Upstream tests: none found in the source archive.
- Added consumer tests: 10 assertions covering CLI, SAN decoding, normalization, endpoint parsing, and JSON failure reporting.

- `adaptation-analysis.md`: Path B 适配困难分析报告，记录依赖障碍、尝试方案和验证证据。
