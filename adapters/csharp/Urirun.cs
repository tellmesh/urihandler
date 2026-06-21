// urirun — C# SDK for building urirun.bindings.v2 documents (no dependencies).
using System.Collections.Generic;

namespace Urirun
{
    public sealed class Connector
    {
        public const string BindingsVersion = "urirun.bindings.v2";
        private readonly string _id;
        private readonly string _scheme;
        private readonly string _target;
        private readonly List<string> _members = new List<string>();

        public Connector(string id, string scheme, string target = "host")
        {
            _id = id;
            _scheme = scheme;
            _target = target;
        }

        // schemaJson and argvJson must be valid JSON fragments.
        public Connector Command(string route, string schemaJson, string argvJson)
        {
            var uri = $"{_scheme}://{_target}/{route}";
            _members.Add($"\"{uri}\":{{\"uri\":\"{uri}\",\"kind\":\"command\",\"adapter\":\"argv-template\",\"inputSchema\":{schemaJson},\"argv\":{argvJson},\"meta\":{{\"connector\":\"{_id}\"}},\"policy\":{{\"allowExecute\":true}}}}");
            return this;
        }

        public string BindingsJson() =>
            $"{{\"version\":\"{BindingsVersion}\",\"bindings\":{{{string.Join(",", _members)}}}}}";
    }
}
