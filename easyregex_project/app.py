from flask import Flask, jsonify, render_template_string, request

from easyregex.compiler import compile_source
from easyregex.errors import CompilerError
from easyregex.testrunner import match_string

app = Flask(__name__)

DEFAULT_SOURCE = """# Try editing this pattern
pattern email:
  one or more letter_or_digit
  then "@"
  one or more letter
  then "."
  then ("com" or "org" or "in")

test email:
  match "alice@example.com"
  reject "no-at-sign.com"
"""

PAGE = """<!doctype html>
<html>
<head>
<meta charset="utf-8">
<title>EasyRegEx</title>
<style>
  body { font-family: system-ui, sans-serif; margin: 0; padding: 24px;
         background: #fafafa; color: #111; }
  h1 { font-size: 22px; margin: 0 0 4px; }
  p.sub { margin: 0 0 20px; color: #555; font-size: 14px; }
  .cols { display: flex; gap: 20px; align-items: flex-start; flex-wrap: wrap; }
  .col { flex: 1; min-width: 340px; }
  textarea { width: 100%; height: 300px; font-family: ui-monospace, monospace;
             font-size: 13px; padding: 10px; border: 1px solid #ccc;
             border-radius: 6px; box-sizing: border-box; }
  input[type=text] { width: 100%; font-family: ui-monospace, monospace;
             font-size: 13px; padding: 8px; border: 1px solid #ccc;
             border-radius: 6px; box-sizing: border-box; }
  button { margin-top: 10px; padding: 8px 18px; font-size: 14px;
           border: 1px solid #333; background: #333; color: #fff;
           border-radius: 6px; cursor: pointer; }
  button:hover { background: #000; }
  pre { background: #fff; border: 1px solid #ddd; border-radius: 6px;
        padding: 12px; font-size: 12.5px; overflow-x: auto; }
  h2 { font-size: 14px; text-transform: uppercase; letter-spacing: .04em;
       color: #444; margin: 18px 0 6px; }
  .err { color: #a00; font-weight: 600; white-space: pre-wrap; }
  .pass { color: #060; }
  .fail { color: #a00; }
</style>
</head>
<body>
<h1>EasyRegEx</h1>
<p class="sub">A domain-specific language that compiles readable pattern
descriptions into regular expressions.</p>

<div class="cols">
  <div class="col">
    <h2>Source (.rx)</h2>
    <textarea id="src">{{ initial }}</textarea>
    <button onclick="compile()">Compile</button>

    <h2>Try a string</h2>
    <input type="text" id="probe" placeholder="type a string to test"
           oninput="probe()">
    <pre id="probeout">(type above)</pre>
  </div>

  <div class="col">
    <h2>Output</h2>
    <pre id="out">(press Compile)</pre>
  </div>
</div>

<script>
let lastRegexes = {};

async function compile() {
  const source = document.getElementById('src').value;
  const res = await fetch('/compile', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({source})
  });
  const data = await res.json();
  const out = document.getElementById('out');

  if (!data.ok) {
    lastRegexes = {};
    out.innerHTML = '<span class="err">' + escapeHtml(data.error) + '</span>';
    probe();
    return;
  }

  lastRegexes = data.regexes;
  let html = '';
  html += 'REGULAR EXPRESSIONS\\n';
  for (const [name, regex] of Object.entries(data.regexes)) {
    html += '  ' + name + '  ->  ' + escapeHtml(regex) + '\\n';
  }
  if (data.optimizer) html += '\\n' + escapeHtml(data.optimizer) + '\\n';

  if (data.tests.length) {
    html += '\\nTEST CASES\\n';
    for (const t of data.tests) {
      const cls = t.passed ? 'pass' : 'fail';
      html += '  <span class="' + cls + '">' + escapeHtml(t.line) + '</span>\\n';
    }
    html += '\\n' + escapeHtml(data.summary) + '\\n';
  }

  html += '\\nTOKENS: ' + data.token_count + '\\n';
  html += '\\nABSTRACT SYNTAX TREE\\n' + escapeHtml(data.ast);
  out.innerHTML = html;
  probe();
}

function probe() {
  const text = document.getElementById('probe').value;
  const box = document.getElementById('probeout');
  const names = Object.keys(lastRegexes);
  if (!names.length) { box.textContent = '(compile first)'; return; }
  if (!text) { box.textContent = '(type above)'; return; }

  fetch('/match', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({regexes: lastRegexes, text})
  }).then(r => r.json()).then(data => {
    let html = '';
    for (const [name, matched] of Object.entries(data.results)) {
      const cls = matched ? 'pass' : 'fail';
      const verdict = matched ? 'MATCH' : 'NO MATCH';
      html += name + ': <span class="' + cls + '">' + verdict + '</span>\\n';
    }
    box.innerHTML = html;
  });
}

function escapeHtml(s) {
  return String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;')
                  .replace(/>/g, '&gt;');
}

compile();
</script>
</body>
</html>
"""


@app.route("/")
def index():
    return render_template_string(PAGE, initial=DEFAULT_SOURCE)


@app.route("/compile", methods=["POST"])
def compile_route():
    source = request.get_json(force=True).get("source", "")
    try:
        result = compile_source(source)
    except CompilerError as e:
        return jsonify({"ok": False, "error": e.format()})
    except Exception as e:  # unexpected failure, still report cleanly
        return jsonify({"ok": False, "error": f"Unexpected error: {e}"})

    return jsonify({
        "ok": True,
        "regexes": result.regexes,
        "token_count": len(result.tokens),
        "ast": result.ast_dump(),
        "optimizer": result.optimizer.report() if result.optimizer else "",
        "tests": [
            {"line": r.describe(), "passed": r.passed}
            for r in result.report.results
        ],
        "summary": result.report.summary(),
    })


@app.route("/match", methods=["POST"])
def match_route():
    data = request.get_json(force=True)
    text = data.get("text", "")
    regexes = data.get("regexes", {})
    results = {}
    for name, regex in regexes.items():
        try:
            results[name] = match_string(regex, text)
        except Exception:
            results[name] = False
    return jsonify({"results": results})


if __name__ == "__main__":
    app.run(debug=True)
