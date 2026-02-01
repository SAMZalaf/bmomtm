import { execSync } from "child_process";
import fs from "fs";
import path from "path";

const rootDir = process.cwd();
const distDir = path.join(rootDir, "dist");
const publicDir = path.join(distDir, "public");

if (fs.existsSync(distDir)) {
  fs.rmSync(distDir, { recursive: true });
}
fs.mkdirSync(distDir, { recursive: true });
fs.mkdirSync(publicDir, { recursive: true });

console.log("Building frontend...");
execSync(`npx vite build --outDir ${publicDir}`, { stdio: "inherit" });

console.log("Build complete!");
console.log(`Frontend: ${publicDir}`);
