import assert from 'node:assert/strict';
import { bindingDocument, string, uriCommand } from './uri-command.mjs';

const greet = uriCommand(
  'js://local/greet/message',
  {
    name: string({ required: true }),
  },
  ({ name }) => ['node', '-e', 'console.log(process.argv[1])', name],
  { meta: { label: 'JS greet' } },
);

const document = bindingDocument([greet]);

assert.equal(document.bindings['js://local/greet/message'].inputSchema.required[0], 'name');
assert.equal(document.bindings['js://local/greet/message'].argv.at(-1), '{name}');
console.log(JSON.stringify(document, null, 2));
