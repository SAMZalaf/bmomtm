import express, { type Request, Response, NextFunction } from "express";
import { registerRoutes } from "./routes";
import { serveStatic } from "./static";
import { createServer } from "http";
import { spawn, ChildProcess } from "child_process";
import path from "path";
import fs from "fs";

const app = express();
const httpServer = createServer(app);

let botProcess: ChildProcess | null = null;

function getBotDir(): string {
  if (process.env.BOT_DIR) {
    return process.env.BOT_DIR;
  }
  
  const webUiDir = process.cwd();
  const parentDir = path.dirname(webUiDir);
  
  if (fs.existsSync(path.join(parentDir, "bot.py"))) {
    return parentDir;
  }
  
  if (fs.existsSync(path.join(webUiDir, "bot.py"))) {
    return webUiDir;
  }
  
  const replitBotDir = path.join(process.cwd(), "telegram_bot");
  if (fs.existsSync(path.join(replitBotDir, "bot.py"))) {
    return replitBotDir;
  }
  
  return parentDir;
}

function startTelegramBot(): void {
  const botDir = getBotDir();
  const lockFile = path.join(botDir, "bot.lock");
  const botPyPath = path.join(botDir, "bot.py");
  
  if (!fs.existsSync(botPyPath)) {
    console.log(`⚠️ Bot not found at ${botPyPath}, skipping bot startup`);
    return;
  }
  
  if (fs.existsSync(lockFile)) {
    fs.unlinkSync(lockFile);
    console.log("🔓 Removed old bot lock file");
  }
  
  console.log(`🤖 Starting Telegram Bot from ${botDir}...`);
  
  const venvPython = path.join(botDir, "venv", "bin", "python3");
  const pythonCmd = fs.existsSync(venvPython) ? venvPython : "python3";
  
  botProcess = spawn(pythonCmd, ["bot.py"], {
    cwd: botDir,
    stdio: ["ignore", "pipe", "pipe"],
    detached: false
  });
  
  botProcess.stdout?.on("data", (data) => {
    const lines = data.toString().split("\n").filter((line: string) => line.trim());
    lines.forEach((line: string) => {
      console.log(`[Bot] ${line}`);
    });
  });
  
  botProcess.stderr?.on("data", (data) => {
    const lines = data.toString().split("\n").filter((line: string) => line.trim());
    lines.forEach((line: string) => {
      console.error(`[Bot Error] ${line}`);
    });
  });
  
  botProcess.on("close", (code) => {
    console.log(`🤖 Telegram Bot exited with code ${code}`);
    botProcess = null;
  });
  
  botProcess.on("error", (err) => {
    console.error(`🤖 Failed to start Telegram Bot: ${err.message}`);
  });
  
  console.log(`✅ Telegram Bot started (PID: ${botProcess.pid})`);
}

function stopTelegramBot(): void {
  if (botProcess) {
    console.log("🛑 Stopping Telegram Bot...");
    botProcess.kill("SIGTERM");
    botProcess = null;
  }
}

process.on("SIGINT", () => {
  stopTelegramBot();
  process.exit(0);
});

process.on("SIGTERM", () => {
  stopTelegramBot();
  process.exit(0);
});

declare module "http" {
  interface IncomingMessage {
    rawBody: unknown;
  }
}

app.use(
  express.json({
    verify: (req, _res, buf) => {
      req.rawBody = buf;
    },
  }),
);

app.use(express.urlencoded({ extended: false }));

export function log(message: string, source = "express") {
  const formattedTime = new Date().toLocaleTimeString("en-US", {
    hour: "numeric",
    minute: "2-digit",
    second: "2-digit",
    hour12: true,
  });

  console.log(`${formattedTime} [${source}] ${message}`);
}

app.use((req, res, next) => {
  const start = Date.now();
  const path = req.path;
  let capturedJsonResponse: Record<string, any> | undefined = undefined;

  const originalResJson = res.json;
  res.json = function (bodyJson, ...args) {
    capturedJsonResponse = bodyJson;
    return originalResJson.apply(res, [bodyJson, ...args]);
  };

  res.on("finish", () => {
    const duration = Date.now() - start;
    if (path.startsWith("/api")) {
      let logLine = `${req.method} ${path} ${res.statusCode} in ${duration}ms`;
      if (capturedJsonResponse) {
        logLine += ` :: ${JSON.stringify(capturedJsonResponse)}`;
      }

      log(logLine);
    }
  });

  next();
});

(async () => {
  await registerRoutes(httpServer, app);

  app.use((err: any, _req: Request, res: Response, _next: NextFunction) => {
    const status = err.status || err.statusCode || 500;
    const message = err.message || "Internal Server Error";

    res.status(status).json({ message });
    throw err;
  });

  if (process.env.NODE_ENV === "production") {
    serveStatic(app);
  } else {
    const { setupVite } = await import("./vite");
    await setupVite(httpServer, app);
  }

  const port = parseInt(process.env.PORT || "5000", 10);
  httpServer.listen(
    {
      port,
      host: "0.0.0.0",
      reusePort: true,
    },
    () => {
      log(`serving on port ${port}`);
      
      setTimeout(() => {
        startTelegramBot();
      }, 2000);
    },
  );
})();
