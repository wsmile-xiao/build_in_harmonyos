# Upstream JSHint test runtime

The test package runs the upstream Grunt `jshint` target using the actual
JSHint 2.13.6 JavaScript bundle and Node.js. The inputs are the hash-pinned
`Gruntfile.js` and `jquery.jgrowl.js` from jGrowl tag 1.4.10, and the globals
match the upstream Gruntfile.

JSHint is distributed under the MIT license in `jshint/LICENSE`.
