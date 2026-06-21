// Reference urirun connector in TypeScript: prints a urirun.bindings.v2 document.
import { connector } from "../urirun";

const c = connector("hash", { scheme: "hash" });
c.command(
  "sha256/command/file",
  { required: ["path"], properties: { path: { type: "string" } } },
  ["sha256sum", "{path}"],
);
console.log(c.toJSON());
