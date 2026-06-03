const fs = require("fs");
const path = require("path");

const DEFAULT_API_BASE = "https://director-disabilities-worlds-sunglasses.trycloudflare.com/api/anochat-backend";
const apiBase = process.env.VERCEL_API_BASE
  || process.env.NEXT_PUBLIC_API_BASE
  || process.env.API_BASE
  || process.env.API_URL
  || DEFAULT_API_BASE;
const output = `(function () {
  window.API_BASE = ${JSON.stringify(apiBase.replace(/\/$/, ""))};
})();
`;

fs.writeFileSync(path.join(__dirname, "static", "env.js"), output);
