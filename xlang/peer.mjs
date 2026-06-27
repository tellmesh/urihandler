#!/usr/bin/env node
// JS wire peer — cross-ROUTE handoff, porting the kernel wire layer (dig / wire_payload /
// consumer_input_check) + list-schema check. Reads the SAME neutral contracts as peer.py.
//   conform                 — dynamic wire check: each wire's golden example must consume cleanly
//   produce <route>         — print the golden ok envelope
//   consume <prod> <cons>   — build the consumer payload via the wire, validate, print result
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const DOC = JSON.parse(fs.readFileSync(path.join(HERE, process.env.XLANG_CONTRACTS || 'contracts.kvm.json'), 'utf8'));
const CONTRACTS = DOC.contracts;
const WIRES = DOC.wires;
const isObj = (x) => x !== null && typeof x === 'object' && !Array.isArray(x);

function parseConst(t) { if (t === 'true') return true; if (t === 'false') return false; if (/^-?\d+$/.test(t)) return parseInt(t, 10); return t; }
function leafOk(tok, v) {
  if (tok.startsWith('?')) return v === null || v === undefined || leafOk(tok.slice(1), v);
  if (tok.startsWith('const:')) return v === parseConst(tok.slice(6));
  if (tok.startsWith('enum:')) return tok.slice(5).split('|').includes(v);
  switch (tok) {
    case 'str': return typeof v === 'string';
    case 'int': return Number.isInteger(v);
    case 'num': return typeof v === 'number';
    case 'bool': return typeof v === 'boolean';
    case 'obj': return isObj(v);
    case 'list': return Array.isArray(v);
    case 'any': return true;
    default: return false;
  }
}
function check(schema, value, where) {
  if (isObj(schema)) {
    if ('oneOf' in schema) {
      const errs = [];
      for (let i = 0; i < schema.oneOf.length; i++) {
        try { check(schema.oneOf[i], value, `${where}|oneOf[${i}]`); return; } catch (e) { errs.push(e.message); }
      }
      throw new Error(`${where}: matched none of oneOf -> ${JSON.stringify(errs)}`);
    }
    if (!isObj(value)) throw new Error(`${where}: expected object`);
    for (const [k, spec] of Object.entries(schema)) {
      if (!(k in value)) { if (typeof spec === 'string' && spec.startsWith('?')) continue; throw new Error(`${where}: missing required key '${k}'`); }
      check(spec, value[k], `${where}.${k}`);
    }
    return;
  }
  if (Array.isArray(schema)) { // homogeneous list: schema[0] describes every element
    if (!Array.isArray(value)) throw new Error(`${where}: expected list`);
    if (schema.length) value.forEach((it, i) => check(schema[0], it, `${where}[${i}]`));
    return;
  }
  if (!leafOk(schema, value)) throw new Error(`${where}: ${JSON.stringify(value)} does not satisfy '${schema}'`);
}

function dig(value, dotted) {
  let cur = value;
  for (const seg of dotted.split('.')) {
    if (Array.isArray(cur) && /^\d+$/.test(seg)) cur = cur[Number(seg)];
    else if (isObj(cur) && seg in cur) cur = cur[seg];
    else throw new Error(`${dotted}: missing segment '${seg}'`);
  }
  return cur;
}
function wirePayload(wire, env) {
  const out = {};
  for (const [field, p] of Object.entries(wire.mapping)) { try { out[field] = dig(env, p); } catch { /* skip absent */ } }
  return out;
}
function consumerInputCheck(consumer, payload, wire) {
  const inp = consumer.inp;
  const required = new Set(Object.entries(inp).filter(([, v]) => !(typeof v === 'string' && v.startsWith('?'))).map(([k]) => k));
  const carried = new Set(Object.keys(wire.mapping));
  const problems = [];
  if ([...required].every((k) => carried.has(k))) {
    const missing = [...required].filter((k) => !(k in payload));
    if (missing.length) problems.push(`full handoff, producer variant missing: ${JSON.stringify(missing)}`);
    try { check(inp, payload, 'consumer.inp'); } catch (e) { problems.push(e.message); }
    return ['full', problems];
  }
  for (const fld of [...carried].filter((k) => k in payload).sort()) {
    const sub = inp[fld]; if (sub === undefined) continue;
    const opt = typeof sub === 'string' && sub.startsWith('?');
    try { check(opt ? sub.slice(1) : sub, payload[fld], `consumer.inp.${fld}`); } catch (e) { problems.push(e.message); }
  }
  return ['partial', problems];
}
function findWire(p, c) { const w = WIRES.find((w) => w.producer === p && w.consumer === c); if (!w) throw new Error(`no edge ${p} -> ${c}`); return w; }
function okExample(route) { for (const ex of CONTRACTS[route].examples) if ((ex.result || {}).ok) return ex.result; throw new Error(`${route}: no golden ok`); }

const [cmd, a, b] = process.argv.slice(2);
if (cmd === 'conform') {
  let bad = [];
  for (const w of WIRES) {
    const [, problems] = consumerInputCheck(CONTRACTS[w.consumer], wirePayload(w, okExample(w.producer)), w);
    bad = bad.concat(problems.map((p) => `${w.producer}->${w.consumer}: ${p}`));
  }
  if (bad.length) { process.stderr.write(`JS  wire conform FAIL: ${JSON.stringify(bad)}\n`); process.exit(1); }
  process.stderr.write(`JS  wire conform OK — ${WIRES.length} edges\n`);
} else if (cmd === 'produce') {
  process.stdout.write(JSON.stringify(okExample(a)));
} else if (cmd === 'consume') {
  const env = JSON.parse(fs.readFileSync(0, 'utf8'));
  const wire = findWire(a, b);
  const payload = wirePayload(wire, env);
  const [mode, problems] = consumerInputCheck(CONTRACTS[b], payload, wire);
  process.stdout.write(JSON.stringify({ ok: problems.length === 0, lang: 'js', mode, builtInput: payload, problems }));
  if (problems.length) process.exit(1);
} else {
  throw new Error(`unknown cmd ${cmd}`);
}
