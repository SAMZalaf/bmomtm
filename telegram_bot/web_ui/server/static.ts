import express, { type Express } from "express";
import fs from "fs";
import path from "path";
import { fileURLToPath } from "url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

export function serveStatic(app: Express) {
  let distPath = path.resolve(process.cwd(), "dist", "public");
  
  if (!fs.existsSync(distPath)) {
    distPath = path.resolve(__dirname, "..", "dist", "public");
  }
  
  if (!fs.existsSync(distPath)) {
    distPath = path.resolve(__dirname, "public");
  }
  
  if (!fs.existsSync(distPath)) {
    throw new Error(
      `Could not find the build directory, make sure to build the client first`,
    );
  }

  console.log(`Serving static files from: ${distPath}`);
  app.use(express.static(distPath));

  app.use("*", (_req, res) => {
    res.sendFile(path.resolve(distPath, "index.html"));
  });
}
