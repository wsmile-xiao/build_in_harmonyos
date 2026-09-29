# jgrowl 1.4.10 HarmonyOS PC package notes

## Package scope

- Upstream: https://github.com/stanlemon/jGrowl, exact upstream tag `1.4.10`.
- The release is a jQuery browser plugin. It ships ready-to-use JavaScript,
  CSS, and a JavaScript source map; it has no native code or target build step.
- Conan installs the five runtime/development assets under `share/jgrowl` and
  the MIT license under `licenses`.
- The package has no Conan dependencies. Consumers that execute the plugin
  provide jQuery separately, as specified by upstream metadata.

## Tests

- The upstream Gruntfile defines one `grunt test` case: its JSHint target over
  `Gruntfile.js` and `jquery.jgrowl.js`, with `jQuery`, `console`, `module`, and
  `document` declared as globals. The test package runs the vendored JSHint
  2.13.6 bundle using Node.js, executing the upstream JavaScript test with its
  exact inputs and options.
- Both lint inputs are copied unmodified from tag `1.4.10` and SHA-256 pinned in
  `test_package/verify_upstream_jshint.py`. The hash check normalizes line
  endings so Windows and Unix checkouts agree. Node.js execution passed the
  upstream test case **1/1** with zero JSHint diagnostics.
- The Conan consumer smoke test checks the five shipped assets and the license
  are present and non-empty (**6/6**). It runs after the upstream case as part
  of `conan create`.

## Build and packaging

- The upstream tag archive already contains minified and unminified JS/CSS,
  so the recipe does not run Grunt or require its development dependencies.
- The resource directory is exposed as `cpp_info.resdirs = ["share/jgrowl"]`;
  there are no headers, libraries, or executables.
- Source integrity is pinned to the SHA-256 of the official GitHub tag archive.
