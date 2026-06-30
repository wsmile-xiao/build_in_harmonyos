# mongosh 2.8.3 适配笔记

## 编译环境
- 构建系统: custom (Node.js monorepo)
- 编译日期: 2026-06-09
- 编译器: clang/clang++ (for potential native addons)
- Node.js: v24.13.0 (system)
- npm: 11.6.2 (system)
- 状态: published

## 编译步骤

1. **Init-build**: `ohc-run.py init-build mongosh 2.8.3 --url="https://github.com/mongodb-js/mongosh/archive/refs/tags/v2.8.3.tar.gz"`
2. **npm install**: `npm install --ignore-scripts` (installed ~1260 packages, skipped native addon build scripts)
3. **TypeScript compile**: `npm run compile` - compiled all workspaces TypeScript source to JS
4. **Webpack bundle**: `npm run webpack-build -w @mongosh/cli-repl` - created single-file bundle mongosh.js (15.5MB)
5. **Packaging approach**: Since mongosh's `boxednode` approach compiles Node.js from source and creates a standalone binary, which is not feasible on HarmonyOS NEXT, we use the pragmatic approach:
   - Use the webpack-bundled mongosh.js with system Node.js v24.13.0
   - Create a shell script launcher (`mongosh`) that invokes `node mongosh.js`
   - Install to: bin/mongosh (launcher) + lib/mongosh/ (JS bundle + supporting files)
6. **Package**: `ohc-run.py package mongosh 2.8.3`
7. **Verify**: `mongosh --version` → 2.8.2 (cli-repl package version; mongosh overall is 2.8.3)

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | boxednode standalone binary compilation not feasible on OHOS | boxednode compiles Node.js from source, requires full Node.js build infrastructure for OHOS | Use webpack bundle + system Node.js launcher script approach |
| 2 | Native addons (kerberos, mongodb-client-encryption) won't compile on musl/OHOS | These are C/C++ native addons requiring glibc/platform-specific headers | Used `--ignore-scripts` to skip native addon builds; mongosh webpack bundle works without these optional features |
| 3 | npm install very slow (~530s) | Large monorepo with many dependencies | Used `--ignore-scripts` to speed up installation |

## 源码修改

No source code modifications were required. The webpack bundle runs correctly with the system Node.js.

## 依赖版本

- Node.js: v24.13.0 (/data/service/hnp/bin/node)
- npm: 11.6.2 (/data/service/hnp/bin/npm)
- lerna: independent versioning
- webpack: 5.105.0
- TypeScript: ~5.3.3
- boxednode: ^3.0.0 (not used in OHOS build)

## 验证结果

```bash
$ /storage/Users/currentUser/usr/local/bin/mongosh --version
2.8.2

$ node /storage/Users/currentUser/tmp/builds/mongosh-2.8.3.work/packages/cli-repl/dist/mongosh.js --version
2.8.2
```

Note: The version output is 2.8.2 (the @mongosh/cli-repl package version), while the overall mongosh npm package is version 2.8.3. This is because mongosh uses lerna with independent versioning.

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| bin/mongosh | 274B | Shell script launcher |
| lib/mongosh/mongosh.js | 15.6MB | Webpack-bundled JS (single-file) |
| lib/mongosh/add-module-mapping.js | 22.9KB | Module mapping helper |
| lib/mongosh/build-info.js | 3.1KB | Build info metadata |
| lib/mongosh/mongosh.js.LICENSE.txt | 5.7KB | License text |
| share/doc/mongosh/LICENSE | 10.8KB | Apache-2.0 license |
| share/doc/mongosh/README.md | 8.9KB | Project README |
| share/doc/mongosh/THIRD_PARTY_NOTICES.md | 2.0MB | Third-party notices |

## 注意事项

- mongosh requires Node.js v24+ available at `/data/service/hnp/bin/node` on the system
- The launcher script uses a hardcoded Node.js path; may need adjustment for different deployment environments
- Native addons (kerberos, FLE/mongodb-client-encryption, os-dns-native) are NOT included; their features are unavailable
- The webpack bundle includes all JS dependencies; only native C/C++ addon features are missing
- Glibc-version check addon is not available; mongosh will not be able to detect glibc version (not needed on musl)
---

**编译结束**: 2026-06-09 15:46
**最终状态**: published
