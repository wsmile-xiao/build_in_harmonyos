// test.js - Simple JavaScript file for esbuild bundling test
const greeting = "Hello from esbuild on HarmonyOS!";
const numbers = [1, 2, 3, 4, 5];
const sum = numbers.reduce((a, b) => a + b, 0);
console.log(greeting);
console.log("Sum:", sum);
export { greeting, sum };
