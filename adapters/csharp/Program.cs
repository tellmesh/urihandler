// Reference urirun connector in C#: prints a urirun.bindings.v2 document.
var c = new Urirun.Connector("hash", "hash");
c.Command(
    "sha256/command/file",
    "{\"type\":\"object\",\"additionalProperties\":false,\"required\":[\"path\"],\"properties\":{\"path\":{\"type\":\"string\"}}}",
    "[\"sha256sum\",\"{path}\"]");
System.Console.WriteLine(c.BindingsJson());
