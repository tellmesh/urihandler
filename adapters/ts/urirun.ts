// urirun — TypeScript SDK for building urirun.bindings.v2 documents.

export const BINDINGS_VERSION = "urirun.bindings.v2";

export interface Schema {
  required?: string[];
  properties?: Record<string, unknown>;
}

export class Connector {
  private bindings: Record<string, unknown> = {};
  constructor(private id: string, private scheme: string, private target = "host") {}

  command(route: string, schema: Schema, argv: string[]): this {
    const uri = `${this.scheme}://${this.target}/${route}`;
    const input: Record<string, unknown> = {
      type: "object",
      additionalProperties: false,
      properties: schema.properties ?? {},
    };
    if (schema.required && schema.required.length) input.required = schema.required;
    this.bindings[uri] = {
      uri, kind: "command", adapter: "argv-template",
      inputSchema: input, argv,
      meta: { connector: this.id }, policy: { allowExecute: true },
    };
    return this;
  }

  document(): Record<string, unknown> {
    return { version: BINDINGS_VERSION, bindings: this.bindings };
  }

  toJSON(): string {
    return JSON.stringify(this.document(), null, 2);
  }
}

export function connector(id: string, opts: { scheme: string; target?: string }): Connector {
  return new Connector(id, opts.scheme, opts.target);
}
