import * as esbuild from "esbuild";

await esbuild.build({
  entryPoints: [
    "content/linkedin-publisher.js",
    "content/instagram-publisher.js",
    "content/meta-suite-publisher.js",
    "content/analytics-scraper.js",
  ],
  bundle: true,
  outdir: "dist/content",
  format: "iife",
  platform: "browser",
  target: "chrome92",
  logLevel: "info",
});
