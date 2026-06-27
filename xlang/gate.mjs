#!/usr/bin/env node
// JS gate — reads the SAME neutral contracts.json and ports the kernel validator 1:1.
// No shared object, no privileged language: the contract file is the only glue.
//   conform                 — validate every contract's golden examples
//   produce <route>         — print the golden ok envelope as JSON
//   consume <route>         — read an envelope on stdin, validate it against <route>.out
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const DOC = JSON.parse(fs.readFileSync(path.join(HERE, 'contracts.json'), 'utf8'));
const CONTRACTS = DOC.contracts;

function parseConst(t) {
  if (t === 'true') return true;
  if (t === 'false') return false;
  if (/^-?\d+$/.test(t)) return parseInt(t, 10);
  return t;
}
function leafOk(tok, v) {
  if (tok.startsWith('?')) return v === null || v === undefined || leafOk(tok.slice(1), v);
  if (tok.startsWith('const:')) return v === parseConst(tok.slice(6));
  if (tok.startsWith('enum:')) return tok.slice(5).split('|').includes(v);
  switch (tok) {
    case 'str': return typeof v === 'string';
    case 'int': return Number.isInteger(v);
    case 'num': return typeof v === 'number';
    case 'bool': return typeof v === 'boolean';
    case 'obj': return v !== null && typeof v === 'object' && !Array.isArray(v);
    case 'list': return Array.isArray(v);
    case 'any': return true;
    default: return false;
  }
}
function check(schema, value, where) {
  const isObj = (x) => x !== null && typeof x === 'object' && !Array.isArray(x);
  if (isObj(schema)) {
    if ('oneOf' in schema) {
      const errs = [];
      for (let i = 0; i < schema.oneOf.length; i++) {
        try { check(schema.oneOf[i], value, `${where}|oneOf[${i}]`); return; }
        catch (e) { errs.push(e.message); }
      }
      throw new Error(`${where}: matched none of oneOf -> ${JSON.stringify(errs)}`);
    }
    if (!isObj(value)) throw new Error(`${where}: expected object, got ${Array.isArray(value) ? 'list' : typeof value}`);
    for (const [k, spec] of Object.entries(schema)) {
      if (!(k in value)) {
        if (typeof spec === 'string' && spec.startsWith('?')) continue;
        throw new Error(`${where}: missing required key '${k}'`);
      }
      check(spec, value[k], `${where}.${k}`);
    }
    return;
  }
  if (!leafOk(schema, value)) throw new Error(`${where}: ${JSON.stringify(value)} does not satisfy '${schema}'`);
}

function conform() {
  for (const [route, c] of Object.entries(CONTRACTS)) {
    if (!['query', 'command'].includes(c.effect)) throw new Error(`${route}: bad effect`);
    if ((route.includes('/query/')) !== (c.effect === 'query'))
      throw new Error(`${route}: effect ${c.effect} contradicts URI verb`);
    if (c.reversible && !(c.inverseRoute in CONTRACTS))
      throw new Error(`${route}: inverseRoute ${c.inverseRoute} not declared`);
    (c.examples || []).forEach((ex, i) => {
      check(c.inp, ex.payload || {}, `${route} ex[${i}].payload`);
      if ((ex.result || {}).ok) check(c.out, ex.result, `${route} ex[${i}].result`);
    });
    if (c.reversible) {
      const inv = CONTRACTS[c.inverseRoute];
      (c.examples || []).forEach((ex, i) => {
        const args = ((ex.result || {}).inverse || {}).args || {};
        check(inv.inp, args, `${route} ex[${i}].inverse.args -> ${c.inverseRoute} input`);
      });
    }
  }
}

function okExample(route) {
  for (const ex of CONTRACTS[route].examples || []) if ((ex.result || {}).ok) return ex.result;
  throw new Error(`${route}: no golden ok example`);
}

function readStdin() {
  return JSON.parse(fs.readFileSync(0, 'utf8'));
}

const [cmd, route] = process.argv.slice(2);
if (cmd === 'conform') {
  conform();
  process.stderr.write(`JS  conform OK — ${Object.keys(CONTRACTS).length} contracts\n`);
} else if (cmd === 'produce') {
  process.stdout.write(JSON.stringify(okExample(route)));
} else if (cmd === 'consume') {
  const env = readStdin();
  try {
    check(CONTRACTS[route].out, env, 'out');
    process.stdout.write(JSON.stringify({ ok: true, lang: 'js', route }));
  } catch (e) {
    process.stdout.write(JSON.stringify({ ok: false, lang: 'js', route, problem: e.message }));
    process.exit(1);
  }
} else {
  throw new Error(`unknown cmd ${cmd}`);
}
