// Go gate — reads the SAME neutral contracts.json and ports the validator.
// Handles the two Go-specific frictions the design flagged:
//   * JSON numbers decode to float64 → the "int" token checks integrality (f == trunc(f)).
//   * missing vs zero → validate map[string]any (not a struct), so absent keys are detectable.
//   conform | produce <route> | consume <route>
package main

import (
	"encoding/json"
	"fmt"
	"io"
	"math"
	"os"
	"path/filepath"
	"strconv"
	"strings"
)

type doc struct {
	Contracts map[string]map[string]any `json:"contracts"`
}

var contracts map[string]map[string]any

func jsonish(v any) string { b, _ := json.Marshal(v); return string(b) }

func constEq(tok string, v any) bool {
	if tok == "true" {
		b, ok := v.(bool)
		return ok && b
	}
	if tok == "false" {
		b, ok := v.(bool)
		return ok && !b
	}
	if n, err := strconv.Atoi(tok); err == nil {
		f, ok := v.(float64)
		return ok && f == float64(n)
	}
	s, ok := v.(string)
	return ok && s == tok
}

func leafOk(tok string, v any) bool {
	if strings.HasPrefix(tok, "?") {
		return v == nil || leafOk(tok[1:], v)
	}
	if strings.HasPrefix(tok, "const:") {
		return constEq(tok[6:], v)
	}
	if strings.HasPrefix(tok, "enum:") {
		s, ok := v.(string)
		if !ok {
			return false
		}
		for _, e := range strings.Split(tok[5:], "|") {
			if s == e {
				return true
			}
		}
		return false
	}
	switch tok {
	case "str":
		_, ok := v.(string)
		return ok
	case "int":
		f, ok := v.(float64)
		return ok && f == math.Trunc(f) // JSON int arrives as float64
	case "num":
		_, ok := v.(float64)
		return ok
	case "bool":
		_, ok := v.(bool)
		return ok
	case "obj":
		_, ok := v.(map[string]any)
		return ok
	case "list":
		_, ok := v.([]any)
		return ok
	case "any":
		return true
	}
	return false
}

func check(schema any, value any, where string) error {
	switch sch := schema.(type) {
	case map[string]any:
		if oneOf, ok := sch["oneOf"]; ok {
			var errs []string
			for i, alt := range oneOf.([]any) {
				if err := check(alt, value, fmt.Sprintf("%s|oneOf[%d]", where, i)); err == nil {
					return nil
				} else {
					errs = append(errs, err.Error())
				}
			}
			return fmt.Errorf("%s: matched none of oneOf -> %v", where, errs)
		}
		m, ok := value.(map[string]any)
		if !ok {
			return fmt.Errorf("%s: expected object", where)
		}
		for k, spec := range sch {
			vv, present := m[k]
			if !present {
				if s, ok := spec.(string); ok && strings.HasPrefix(s, "?") {
					continue
				}
				return fmt.Errorf("%s: missing required key '%s'", where, k)
			}
			if err := check(spec, vv, where+"."+k); err != nil {
				return err
			}
		}
		return nil
	case string:
		if !leafOk(sch, value) {
			return fmt.Errorf("%s: %s does not satisfy '%s'", where, jsonish(value), sch)
		}
		return nil
	}
	return fmt.Errorf("%s: unknown schema", where)
}

func examples(c map[string]any) []any {
	if ex, ok := c["examples"].([]any); ok {
		return ex
	}
	return nil
}

func okExample(route string) map[string]any {
	for _, ex := range examples(contracts[route]) {
		e := ex.(map[string]any)
		if r, ok := e["result"].(map[string]any); ok && r["ok"] == true {
			return r
		}
	}
	panic(route + ": no golden ok example")
}

func conform() error {
	for route, c := range contracts {
		effect, _ := c["effect"].(string)
		if effect != "query" && effect != "command" {
			return fmt.Errorf("%s: bad effect", route)
		}
		if strings.Contains(route, "/query/") != (effect == "query") {
			return fmt.Errorf("%s: effect %s contradicts URI verb", route, effect)
		}
		rev, _ := c["reversible"].(bool)
		inv, _ := c["inverseRoute"].(string)
		if rev {
			if _, ok := contracts[inv]; !ok {
				return fmt.Errorf("%s: inverseRoute %s not declared", route, inv)
			}
		}
		for i, ex := range examples(c) {
			e := ex.(map[string]any)
			pl, _ := e["payload"].(map[string]any)
			if pl == nil {
				pl = map[string]any{}
			}
			if err := check(c["inp"], pl, fmt.Sprintf("%s ex[%d].payload", route, i)); err != nil {
				return err
			}
			res, _ := e["result"].(map[string]any)
			if res != nil && res["ok"] == true {
				if err := check(c["out"], res, fmt.Sprintf("%s ex[%d].result", route, i)); err != nil {
					return err
				}
			}
		}
		if rev {
			invInp := contracts[inv]["inp"]
			for i, ex := range examples(c) {
				e := ex.(map[string]any)
				res, _ := e["result"].(map[string]any)
				args := map[string]any{}
				if res != nil {
					if iv, ok := res["inverse"].(map[string]any); ok {
						if a, ok := iv["args"].(map[string]any); ok {
							args = a
						}
					}
				}
				if err := check(invInp, args, fmt.Sprintf("%s ex[%d].inverse.args -> %s input", route, i, inv)); err != nil {
					return err
				}
			}
		}
	}
	return nil
}

func main() {
	here, _ := filepath.Abs(filepath.Dir(os.Args[0]))
	// os.Args[0] is the temp build path under `go run`; read contracts.json next to the source via env.
	path := os.Getenv("XLANG_DIR")
	if path == "" {
		path = here
	}
	raw, err := os.ReadFile(filepath.Join(path, "contracts.json"))
	if err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(2)
	}
	var d doc
	if err := json.Unmarshal(raw, &d); err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(2)
	}
	contracts = d.Contracts

	cmd := os.Args[1]
	switch cmd {
	case "conform":
		if err := conform(); err != nil {
			fmt.Fprintln(os.Stderr, "GO  conform FAIL:", err)
			os.Exit(1)
		}
		fmt.Fprintf(os.Stderr, "GO  conform OK — %d contracts\n", len(contracts))
	case "produce":
		b, _ := json.Marshal(okExample(os.Args[2]))
		os.Stdout.Write(b)
	case "consume":
		route := os.Args[2]
		raw, _ := io.ReadAll(os.Stdin)
		var env any
		json.Unmarshal(raw, &env)
		if err := check(contracts[route]["out"], env, "out"); err != nil {
			fmt.Printf(`{"ok":false,"lang":"go","route":%q,"problem":%q}`, route, err.Error())
			os.Exit(1)
		}
		fmt.Printf(`{"ok":true,"lang":"go","route":%q}`, route)
	default:
		fmt.Fprintln(os.Stderr, "unknown cmd", cmd)
		os.Exit(2)
	}
}
