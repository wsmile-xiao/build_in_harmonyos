#!/usr/bin/env python3
"""Conan recipe for ts 10.9.2 — TypeScript execution environment and REPL (upstream: ts-node).

Package name "ts" follows the task/registry name; the upstream project is
ts-node (https://github.com/TypeStrong/ts-node), Debian source package
ts-node 10.9.2.

Build system: npm + tsc (TypeScript compiler)
Package type: application (CLI tools with shell wrappers)

ts-node is a pure JavaScript/TypeScript project: no native modules, no C/C++
compiler needed.  Runtime dependencies are all pure-JS npm packages, so this
recipe follows the same approach as codecov-cli: install with npm, compile
with tsc, prune dev dependencies, and install shell wrappers that exec the
system Node.js.
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches


class TsConan(ConanFile):
    name = "ts"
    version = "10.9.2"
    description = ("TypeScript execution environment and REPL for node.js, "
                   "with source map support (upstream project: ts-node)")
    license = "MIT"
    homepage = "https://typestrong.org/ts-node"
    url = "https://github.com/TypeStrong/ts-node"

    package_type = "application"

    # R32/L0p: OHOS profile requires all four settings even for pure-JS
    # packages (no C/C++ compiler is actually invoked; compiler/build_type
    # participate in the package id only)
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        # In-source build: build folder = source folder
        self.folders.source = "."
        self.folders.build = "."

    def source(self):
        # Official tag archive (includes full tests/); SHA256 pinned.
        # Multi-source URL list lives in conandata.yml (conan tries each in
        # order): CI workers reach github.com only through intermittent
        # public proxies, so we list gh-proxy / ghfast / official and let
        # conan fall back natively. All entries are byte-identical.
        get(self, **self.conan_data["sources"], strip_root=True)

    def _npm(self, args):
        """Run npm via a wrapper-safe invocation.

        The OHOS hnp npm wrapper (/data/service/hnp/bin/npm) crashes with
        V8 Signal 5 "Check failed: 12 == (*__errno_location())" (see
        DRAFT-npm-ohos-nodejs-toolchain).  Workaround, verified on device:
        invoke npm-cli.js directly with NODE_OPTIONS=--jitless.  On other
        hosts the plain npm command is used.
        """
        hnp_npm = ("/data/service/hnp/node.org/node_v24.13.0/lib/"
                   "node_modules/npm/bin/npm-cli.js")
        if os.path.isfile(hnp_npm):
            self.run('NODE_OPTIONS=--jitless node "%s" %s' % (hnp_npm, args),
                     cwd=self.source_folder)
        else:
            self.run("npm %s" % args, cwd=self.source_folder)

    def build(self):
        # Apply patches from conandata.yml (none for this version; kept for
        # CI G1 patch-application convention)
        apply_conandata_patches(self)
        # Install all dependencies from the upstream lockfile (dev deps
        # included: typescript/tsc is needed to build dist/).
        # --ignore-scripts skips native postinstall hooks (dprint, husky)
        # that have no OpenHarmony binaries.
        # --legacy-peer-deps is required: devDep typedoc@0.22.10 declares
        # peer typescript<=4.5 while the project pins typescript@4.7.4;
        # plain install/ci fails with ERESOLVE on npm >=7.
        # --no-bin-links: HMDFS/SELinux deny symlink creation, npm's
        # node_modules/.bin links fail with EACCES (E018/E080 family);
        # bin entries are invoked through node directly instead
        self._npm("ci --ignore-scripts --legacy-peer-deps --no-bin-links")
        # Compile TypeScript -> JavaScript (dist/); tsc invoked through
        # node directly since node_modules/.bin does not exist (--no-bin-links).
        # --jitless: OHOS node crashes with V8 Signal 5 on heavy JS workloads
        # (DRAFT-npm-ohos-nodejs-toolchain), so all node invocations use it.
        self.run(
            "NODE_OPTIONS=--jitless node node_modules/typescript/bin/tsc "
            "-b tsconfig.build-dist.json",
            cwd=self.source_folder)
        # Generate tsconfig.schema.json locally (typescript-json-schema is
        # pure JS; invoked through node directly to avoid the broken hnp
        # npx wrapper).  The upstream `npm run build-configSchema`
        # additionally runs scripts/create-merged-schema which downloads
        # https://json.schemastore.org/tsconfig via axios; that host is
        # unreachable (403) and would make builds depend on external
        # network, so the merge step is skipped as a documented downgrade.
        # tsconfig.schemastore-schema.json is therefore not shipped; core
        # ts-node functionality does not require it.
        self.run(
            "NODE_OPTIONS=--jitless node "
            "node_modules/typescript-json-schema/bin/"
            "typescript-json-schema --topRef --refs "
            "--validationKeywords allOf --out tsconfig.schema.json "
            "tsconfig.build-schema.json TsConfigSchema",
            cwd=self.source_folder)
        # Move typescript and @types/node from devDependencies to
        # dependencies so that `npm prune --omit=dev` keeps them.
        # ts-node declares both only as devDep+peerDep; prune would remove
        # them and the packaged tree would break ("Cannot find module
        # 'typescript'"; TS2591 "Cannot find name 'process'" without
        # @types/node).  A follow-up `npm install` is NOT used because on a
        # clean tree it reinstalls all devDependencies and runs their
        # native postinstall hooks (dprint, @swc/core), which have no
        # OpenHarmony binaries and fail.  This in-tree edit is build-time
        # only and is not shipped as a source patch.
        import json
        pkg_json_path = os.path.join(self.source_folder, "package.json")
        with open(pkg_json_path, encoding="utf-8") as f:
            pkg_json = json.load(f)
        for peer in ("typescript", "@types/node"):
            pkg_json.setdefault("dependencies", {})[peer] = \
                pkg_json["devDependencies"].pop(peer)
        with open(pkg_json_path, "w", encoding="utf-8") as f:
            json.dump(pkg_json, f, indent=2)
            f.write("\n")
        # Remove dev dependencies; keep runtime node_modules incl. the
        # peer typescript (375 pure-JS packages after prune).
        self._npm("prune --omit=dev --legacy-peer-deps --no-bin-links")

    def package(self):
        src = self.source_folder
        share = os.path.join(self.package_folder, "share", "ts")
        # Runtime payload (mirrors upstream package.json "files")
        for path in ("dist", "dist-raw", "register", "esm",
                     "node10", "node12", "node14", "node16", "transpilers"):
            copy(self, "*", src=os.path.join(src, path), dst=os.path.join(share, path))
        for fname in ("esm.mjs", "child-loader.mjs", "package.json",
                      "tsconfig.schema.json", "LICENSE"):
            copy(self, fname, src=src, dst=share)
        # Runtime node_modules (all pure JS, includes peer typescript)
        copy(self, "*", src=os.path.join(src, "node_modules"),
             dst=os.path.join(share, "node_modules"))
        # Remove nested bin/ and .bin directories inside node_modules:
        # CI's L2 smoke test discovers them (find -name bin) and fails to
        # execute tsc/tsserver there; module resolution does not need them
        # (package.json main/exports only).  See DRAFT-npm-ohos-nodejs-toolchain.
        import shutil
        for root, dirs, _files in os.walk(os.path.join(share, "node_modules")):
            for d in list(dirs):
                if d in ("bin", ".bin"):
                    shutil.rmtree(os.path.join(root, d), ignore_errors=True)
                    dirs.remove(d)
        # Shell wrappers for every upstream bin entry
        bin_dir = os.path.join(self.package_folder, "bin")
        os.makedirs(bin_dir, exist_ok=True)
        bins = {
            "ts-node": "dist/bin.js",
            "ts-node-cwd": "dist/bin-cwd.js",
            "ts-node-esm": "dist/bin-esm.js",
            "ts-node-script": "dist/bin-script.js",
            "ts-node-transpile-only": "dist/bin-transpile.js",
        }
        for bin_name, entry in bins.items():
            wrapper_path = os.path.join(bin_dir, bin_name)
            # NOTE: built by plain concatenation, never str.format():
            # the shell expansion ${TS_HOME:-...} would be misparsed as a
            # Python format placeholder (KeyError).
            wrapper_content = (
                "#!/bin/sh\n"
                "# " + bin_name + " (ts-node) wrapper for HarmonyOS\n"
                "# PATH: ensure hnp node is reachable in cleaned envs\n"
                "# NODE_OPTIONS=--jitless: OHOS node crashes with V8 Signal 5\n"
                "# on heavy JS workloads without it\n"
                "# NOTE: no $(...) command substitution here — some CI workers\n"
                "# cannot fork (can't fork - try again); ${0%/*} parameter\n"
                "# expansion is a shell builtin and needs no child process.\n"
                'PATH="/data/service/hnp/bin:$PATH"\n'
                'TS_HOME="${TS_HOME:-${0%/*}/../share/ts}"\n'
                'NODE_OPTIONS="${NODE_OPTIONS:---jitless}" '
                'exec node "$TS_HOME/' + entry + '" "$@"\n'
            )
            with open(wrapper_path, "w") as f:
                f.write(wrapper_content)
            os.chmod(wrapper_path, 0o755)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        # Consumers may also resolve modules from the packaged tree
        self.runenv_info.define_path("NODE_PATH",
                                     os.path.join(self.package_folder, "share", "ts", "node_modules"))
