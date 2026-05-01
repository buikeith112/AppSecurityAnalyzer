import { copyFileSync, mkdirSync, writeFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const root = dirname(fileURLToPath(import.meta.url));
const dist = join(root, "dist");
const apiBaseUrl = process.env.API_BASE_URL || "";

mkdirSync(dist, { recursive: true });
copyFileSync(join(root, "index.html"), join(dist, "index.html"));
writeFileSync(
  join(dist, "config.js"),
  `window.APP_CONFIG = ${JSON.stringify({ apiBaseUrl }, null, 2)};\n`,
  "utf-8",
);
