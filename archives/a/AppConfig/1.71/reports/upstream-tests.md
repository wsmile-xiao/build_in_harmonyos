# AppConfig 1.71 Upstream Tests

Source: `E:/HarmonyPC/source-audit/appconfig-1.71/AppConfig-1.71`

Functional test command pattern:

```bash
PERL5LIB=lib perl t/<test>.t
```

Result:

- Functional upstream tests: 14/14 passed.
- Author POD tests: 2 skipped by upstream default installation logic.
- Raw functional log: `E:/HarmonyPC/source-audit/appconfig-1.71/upstream-functional-tests-git-perl.log`
- Author skip log: `E:/HarmonyPC/source-audit/appconfig-1.71/upstream-author-tests-skip-git-perl.log`

The counted upstream denominator is the 14 functional test files. The two
author POD tests are documented separately because upstream does not require
them for ordinary installation.
