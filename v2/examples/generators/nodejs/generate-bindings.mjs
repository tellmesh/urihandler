import { writeFileSync } from 'node:fs';
import { bindingDocument, string, uriCommand } from '../js/uri-command.mjs';

const sha256 = uriCommand(
  'node://local/hash/sha256',
  {
    text: string({ required: true }),
  },
  ({ text }) => [
    'node',
    '-e',
    "const crypto=require('crypto'); console.log(crypto.createHash('sha256').update(process.argv[1]).digest('hex'))",
    text,
  ],
  { meta: { label: 'Node sha256' } },
);

const document = bindingDocument([sha256]);
const out = process.argv[2];

if (out) {
  writeFileSync(out, `${JSON.stringify(document, null, 2)}\n`);
} else {
  console.log(JSON.stringify(document, null, 2));
}
