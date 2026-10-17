#!/usr/bin/env node
"use strict";

const fs = require("fs");
const JSHINT = require(process.argv[2]).JSHINT;
const inputs = process.argv.slice(3);
const globals = {
  jQuery: true,
  console: true,
  module: true,
  document: true
};
let failed = false;

for (const filename of inputs) {
  const source = fs.readFileSync(filename, "utf8");
  const passed = JSHINT(source, { globals });
  const errors = (JSHINT.errors || []).filter(Boolean);
  if (!passed || errors.length) {
    failed = true;
    for (const error of errors) {
      console.error("[JSHint] " + filename + ":" + error.line + ":" +
        error.character + " " + error.reason);
    }
  }
}

if (failed) {
  process.exitCode = 1;
} else {
  console.log("Executed pinned JSHint 2.13.6 under Node.js");
}
