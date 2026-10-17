# JFlex 1.9.1 Path B candidate

## Claim

- Library: `jflex/1.9.1`
- Issue: `2241`
- Branch: `feat/jflex-1.9.1-2241`
- Requested classification: Path A basic adaptation plus Path B contribution
  innovation candidate
- Final Path B classification remains subject to official project review.

The Path B candidate is not based only on adding more assertions. The
contribution is a reusable Conan build-tool interface for downstream Java
source-generation recipes on HarmonyOS, together with an execution strategy
that respects the platform's packaged-script policy.

## Before and after

Before the enhancement, the test package consumed JFlex as a normal host
requirement, opened the dependency package folder directly, assembled a
`java -jar` command itself, and generated one small lexer. That proved the JAR
worked but did not prove a downstream build recipe could reuse JFlex as a
Conan tool requirement.

After the enhancement:

1. The package ships `libexec/jflex.sh` beside
   `libexec/jflex-full-1.9.1.jar`.
2. `package_info()` exports `JFLEX_COMMAND`, `JFLEX_JAR`, and `JFLEX_VERSION`
   through `buildenv_info`.
3. The consumer declares `self.tool_requires(self.tested_reference_str)` and
   runs under `env="conanbuild"`.
4. The consumer validates both exported paths, the packaged wrapper, version
   output, two source generations, two Java compilations, and twelve semantic
   assertions.
5. The second grammar covers Unicode identifiers, Unicode string content, and
   an explicit `STRING` lexical state instead of repeating the basic grammar.

## Reusable consumer contract

A downstream recipe can use the package without knowing its Conan cache path:

```python
def build_requirements(self):
    self.tool_requires("jflex/1.9.1")

def build(self):
    self.run(
        'sh "$JFLEX_COMMAND" --encoding UTF-8 -d generated Lexer.flex',
        env="conanbuild",
    )
```

`JFLEX_JAR` is also available when a build system needs to pass the full JAR
path to another JVM process. The wrapper is relocatable because it resolves
the JAR relative to its own packaged location and locates Java through
`JAVA_HOME` or `PATH`.

HarmonyOS consumers deliberately invoke the wrapper with `sh` rather than
requiring direct executable permission. This is the same platform boundary
that required the recipe to invoke the extracted Maven launcher through
`sh mvn`; the package turns that observed failure into a stable downstream
contract.

## Novelty boundary

This candidate does not claim that calling a shell interpreter is new. Its
library-specific contribution is the complete JFlex integration pattern:

- classify the JVM source generator as `build-scripts`, not a native CLI;
- keep the full JAR and wrapper under `libexec/`, avoiding an unrelated
  software-level `commands.json` change;
- expose stable build-environment variables for Conan `tool_requires`;
- verify the contract from the build dependency graph rather than by opening a
  normal host dependency; and
- execute generated Java on the HarmonyOS device across basic and
  Unicode/stateful scanner behavior.

No shared CI, template, script, knowledge index, or other library is changed.
No dependency adaptation is mixed into this package.

## True-device evidence

Final run:
`codex-jflex-jflex-1.9.1-2241-b-shadow-r4-20260817-132158-24356`

- Runner mode: heavy, global `--try-lock`, isolated HOME/CONAN_HOME/TMPDIR
- Duration: 10m23s
- Exit code: 0
- Build summary: 1 package, 1 success, 0 failures
- Upstream Maven/Surefire: 133 executed, 132 passed, 0 failed, 1 skipped
- Conan consumer: 19 discovered, 19 passed
- Basic result: `[IDENT(sum), PLUS, INTEGER(42), IDENT(value)]`
- Unicode/state result:
  `[KEYWORD(let), IDENT(café), EQUALS, QUOTE_OPEN, TEXT(你好), QUOTE_CLOSE]`
- Gates: L0 pass, L1 pass, L2 expected skip, L4 pass, L5 non-blocking warning
- Package revision:
  `jflex/1.9.1#06bb2a48df25ffa76fd3b5b41a344ceb:6b129b068851896169fae42d399fa922d239ce8a#33b0e4477cbb075097db1e63ef9ce406`

The cold b-r3 run independently completed the same 133 upstream cases and
built the JAR before exposing the missing wrapper-copy path. The final b-r4
used a fresh Conan home and reused only the jflex-specific Maven repository
populated by b-r3.

## Limits

- JDK 11 or newer remains a build/runtime prerequisite for the generator.
- This is a JVM build tool, so L2 has no native `bin/` to probe and L5 does not
  recognize the `libexec/` artifact layout; both results are non-blocking.
- The package does not claim native HarmonyOS code generation or Path C.
- Path B is requested as a candidate based on the reusable downstream tool
  contract and true-device evidence; reviewers make the final classification.
