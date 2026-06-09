const fs = require("fs");
const path = require("path");

const apiBase = process.env.VERCEL_API_BASE
  || process.env.NEXT_PUBLIC_API_BASE
  || process.env.API_BASE
  || process.env.API_URL
  || "";
const output = `(function () {
  window.API_BASE = ${JSON.stringify(apiBase.replace(/\/$/, ""))};
})();
`;

fs.writeFileSync(path.join(__dirname, "static", "env.js"), output);
