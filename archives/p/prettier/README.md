# Prettier

Prettier is an opinionated code formatter. It enforces a consistent style by parsing your code and re-printing it with its own rules that take the maximum line length into account, wrapping code when necessary.

- Homepage: https://prettier.io
- Source: https://github.com/prettier/prettier
- License: MIT

## OpenHarmony Build Notes

- Built as a Node.js/npm package using Yarn 4.12.0
- Requires Node.js >= 20 to run
- Core prettier package with 13 built-in plugins (acorn, angular, babel, estree, flow, glimmer, graphql, html, markdown, meriyah, postcss, typescript, yaml)
- Experimental plugins (oxc, hermes) are excluded due to native binding issues on OpenHarmony
