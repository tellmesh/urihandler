// urirun — Java SDK for building urirun.bindings.v2 documents (no dependencies).
// The caller passes valid JSON fragments for the schema and argv; the SDK
// assembles the standardized document.
import java.util.ArrayList;
import java.util.List;

public final class Urirun {
    public static final String BINDINGS_VERSION = "urirun.bindings.v2";

    public static final class Connector {
        private final String id;
        private final String scheme;
        private final String target;
        private final List<String> members = new ArrayList<>();

        public Connector(String id, String scheme) { this(id, scheme, "host"); }

        public Connector(String id, String scheme, String target) {
            this.id = id;
            this.scheme = scheme;
            this.target = target;
        }

        public Connector command(String route, String schemaJson, String argvJson) {
            String uri = scheme + "://" + target + "/" + route;
            members.add("\"" + uri + "\":{\"uri\":\"" + uri
                + "\",\"kind\":\"command\",\"adapter\":\"argv-template\",\"inputSchema\":" + schemaJson
                + ",\"argv\":" + argvJson + ",\"meta\":{\"connector\":\"" + id
                + "\"},\"policy\":{\"allowExecute\":true}}");
            return this;
        }

        public String bindingsJson() {
            return "{\"version\":\"" + BINDINGS_VERSION + "\",\"bindings\":{"
                + String.join(",", members) + "}}";
        }
    }
}
