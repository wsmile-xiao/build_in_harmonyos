# Build Notes: npm-check-updates 22.2.3

## Software Info
- npm-check-updates is a pure JavaScript/Node.js npm package
- No compilation needed, just npm install
- Uses Node v24.13.0, npm 11.6.2 on OpenHarmony

## Build Approach
- Used DESTDIR staging mode (R20)
- npm install -g --prefix DESTDIR npm-check-updates@22.2.3
- China npm mirror (registry.npmmirror.com) for reliability
- Replaced symlinks with wrapper scripts (HMDFS compatibility)

## Discoveries
- Pure npm packages work straightforwardly with DESTDIR mode
- npm install -g --prefix works correctly for staging installs
- Relative path symlinks from npm need replacement with wrapper scripts for HMDFS
---

**编译结束**: 2026-06-15 15:43
**最终状态**: published
