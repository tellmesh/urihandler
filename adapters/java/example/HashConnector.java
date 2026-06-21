// Reference urirun connector in Java: prints a urirun.bindings.v2 document.
public final class HashConnector {
    public static void main(String[] args) {
        Urirun.Connector c = new Urirun.Connector("hash", "hash");
        c.command(
            "sha256/command/file",
            "{\"type\":\"object\",\"additionalProperties\":false,\"required\":[\"path\"],\"properties\":{\"path\":{\"type\":\"string\"}}}",
            "[\"sha256sum\",\"{path}\"]");
        System.out.println(c.bindingsJson());
    }
}
