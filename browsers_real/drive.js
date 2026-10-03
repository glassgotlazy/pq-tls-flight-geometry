// drive.js — Task 1: launch a real browser via Playwright, fresh profile per connection,
// point it at https://www.example.com:8443/ mapped to 127.0.0.1, and let OpenSSL 3.5.4
// s_server -msg log the raw ClientHello. One s_server per launch; raw output saved per run.
// usage: node drive.js <label> <channel|executablePath> <runs>
const { chromium } = require('playwright');
const { spawn } = require('child_process');
const fs = require('fs');
const [label, target, runsArg] = process.argv.slice(2);
const RUNS = parseInt(runsArg || '5', 10);
const O = '/opt/ossl35/bin/openssl';
const G = 'X25519MLKEM768:X25519:secp256r1:secp384r1:SecP256r1MLKEM768:MLKEM768';
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

(async () => {
  for (let i = 1; i <= RUNS; i++) {
    const out = fs.openSync(`raw/${label}_${i}.txt`, 'w');
    const srv = spawn(O, ['s_server', '-www', '-accept', '8443', '-cert', 'c.pem', '-key', 'k.pem', '-msg', '-groups', G],
      { env: { ...process.env, LD_LIBRARY_PATH: '/opt/ossl35/lib' }, stdio: ['pipe', out, out] });
    await sleep(1000);
    const opts = {
      headless: true,
      args: ['--host-resolver-rules=MAP www.example.com 127.0.0.1', '--no-proxy-server'],
    };
    if (target.startsWith('/')) opts.executablePath = target; else opts.channel = target;
    // launch() (not launchPersistentContext) => Playwright creates a new temporary profile each time
    const browser = await chromium.launch(opts);
    const version = browser.version();
    const page = await browser.newPage();
    let err = '';
    try { await page.goto('https://www.example.com:8443/', { timeout: 8000 }); } catch (e) { err = String(e.message).split('\n')[0]; }
    await sleep(1500);
    await browser.close();
    srv.kill('SIGTERM');
    await sleep(500);
    fs.closeSync(out);
    fs.appendFileSync('runs.jsonl', JSON.stringify({ label, run: i, target, version, goto_error: err, ts: new Date().toISOString() }) + '\n');
    console.log(label, i, version, err || 'loaded');
  }
})();
