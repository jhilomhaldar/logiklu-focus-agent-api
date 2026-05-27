import html
import json
from typing import Any, Dict, List
from urllib.parse import urlencode


def esc(value: Any) -> str:
    if value is None:
        return ""

    return html.escape(str(value))


def json_pretty(value: Any) -> str:
    return html.escape(json.dumps(value, indent=2, default=str))


def method_class(method: str) -> str:
    method_value = str(method or "").upper()

    if method_value == "GET":
        return "method-get"

    if method_value == "POST":
        return "method-post"

    if method_value == "PATCH":
        return "method-patch"

    if method_value == "DELETE":
        return "method-delete"

    return "method-default"


def build_url(base_url: str, path: str, query: Dict[str, Any]) -> str:
    clean_base = str(base_url or "").rstrip("/")
    clean_path = "/" + str(path or "").lstrip("/")

    query = query or {}

    if not query:
        return f"{clean_base}{clean_path}"

    return f"{clean_base}{clean_path}?{urlencode(query)}"


def render_table(headers: List[str], rows: List[List[Any]]) -> str:
    html_rows = ""

    for row in rows:
        html_rows += "<tr>"
        for cell in row:
            html_rows += f"<td>{cell}</td>"
        html_rows += "</tr>"

    html_headers = "".join([f"<th>{esc(header)}</th>" for header in headers])

    return f"""
    <div class="table-wrap">
        <table>
            <thead>
                <tr>{html_headers}</tr>
            </thead>
            <tbody>
                {html_rows}
            </tbody>
        </table>
    </div>
    """


def render_parameters(parameters: List[Dict[str, Any]]) -> str:
    if not parameters:
        return ""

    rows = []

    for param in parameters:
        rows.append([
            f"<code>{esc(param.get('name'))}</code>",
            esc(param.get("required")),
            f"<code>{esc(param.get('example'))}</code>",
            esc(param.get("description")),
        ])

    return f"""
    <h4>Parameters</h4>
    {render_table(["Name", "Required", "Example", "Description"], rows)}
    """


def render_search_by_options(options: List[Dict[str, Any]]) -> str:
    if not options:
        return ""

    rows = []

    for item in options:
        rows.append([
            f"<code>{esc(item.get('name'))}</code>",
            f"<code>{esc(item.get('example'))}</code>",
            esc(item.get("description")),
        ])

    return f"""
    <h4>Specific Search Options</h4>
    <p class="help-text">
        Use <code>search</code> with <code>search_by</code> when you want to search one selected field only.
    </p>
    {render_table(["search_by", "Example Value", "Description"], rows)}
    """


def generate_curl(method: str, url: str, body: Any = None) -> str:
    method = str(method or "GET").upper()

    if method == "GET":
        return f'''curl -X GET "{url}" \\
  -H "X-API-KEY: YOUR_API_KEY"'''

    body_json = json.dumps(body or {}, indent=2)

    return f'''curl -X {method} "{url}" \\
  -H "X-API-KEY: YOUR_API_KEY" \\
  -H "Content-Type: application/json" \\
  -d '{body_json}' '''


def generate_php(method: str, url: str, body: Any = None) -> str:
    method = str(method or "GET").upper()

    if method == "GET":
        return f'''<?php

$apiKey = "YOUR_API_KEY";
$url = "{url}";

$ch = curl_init($url);

curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
curl_setopt($ch, CURLOPT_HTTPHEADER, [
    "X-API-KEY: " . $apiKey
]);

$response = curl_exec($ch);

if (curl_errno($ch)) {{
    echo "Error: " . curl_error($ch);
}} else {{
    $data = json_decode($response, true);
    print_r($data);
}}

curl_close($ch);
?>'''

    body_json = json.dumps(body or {}, indent=4)

    return f'''<?php

$apiKey = "YOUR_API_KEY";
$url = "{url}";

$payload = {body_json};

$ch = curl_init($url);

curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
curl_setopt($ch, CURLOPT_CUSTOMREQUEST, "{method}");
curl_setopt($ch, CURLOPT_POSTFIELDS, json_encode($payload));
curl_setopt($ch, CURLOPT_HTTPHEADER, [
    "X-API-KEY: " . $apiKey,
    "Content-Type: application/json"
]);

$response = curl_exec($ch);

if (curl_errno($ch)) {{
    echo "Error: " . curl_error($ch);
}} else {{
    $data = json_decode($response, true);
    print_r($data);
}}

curl_close($ch);
?>'''


def generate_python(method: str, url: str, body: Any = None) -> str:
    method = str(method or "GET").upper()

    if method == "GET":
        return f'''import requests

api_key = "YOUR_API_KEY"
url = "{url}"

headers = {{
    "X-API-KEY": api_key
}}

response = requests.get(url, headers=headers)
print(response.json())'''

    body_json = json.dumps(body or {}, indent=4)

    return f'''import requests

api_key = "YOUR_API_KEY"
url = "{url}"

headers = {{
    "X-API-KEY": api_key,
    "Content-Type": "application/json"
}}

payload = {body_json}

response = requests.request("{method}", url, headers=headers, json=payload)
print(response.json())'''


def generate_node(method: str, url: str, body: Any = None) -> str:
    method = str(method or "GET").upper()

    if method == "GET":
        return f'''const apiKey = "YOUR_API_KEY";
const url = "{url}";

const response = await fetch(url, {{
  method: "GET",
  headers: {{
    "X-API-KEY": apiKey
  }}
}});

const data = await response.json();
console.log(data);'''

    body_json = json.dumps(body or {}, indent=2)

    return f'''const apiKey = "YOUR_API_KEY";
const url = "{url}";

const payload = {body_json};

const response = await fetch(url, {{
  method: "{method}",
  headers: {{
    "X-API-KEY": apiKey,
    "Content-Type": "application/json"
  }},
  body: JSON.stringify(payload)
}});

const data = await response.json();
console.log(data);'''

def generate_javascript(method: str, url: str, body: Any = None) -> str:
    method = str(method or "GET").upper()

    if method == "GET":
        return f'''const apiKey = "YOUR_API_KEY";
const url = "{url}";

fetch(url, {{
  method: "GET",
  headers: {{
    "X-API-KEY": apiKey
  }}
}})
  .then(response => response.json())
  .then(data => console.log(data))
  .catch(error => console.error("Error:", error));'''

    body_json = json.dumps(body or {}, indent=2)

    return f'''const apiKey = "YOUR_API_KEY";
const url = "{url}";

const payload = {body_json};

fetch(url, {{
  method: "{method}",
  headers: {{
    "X-API-KEY": apiKey,
    "Content-Type": "application/json"
  }},
  body: JSON.stringify(payload)
}})
  .then(response => response.json())
  .then(data => console.log(data))
  .catch(error => console.error("Error:", error));'''


def generate_java(method: str, url: str, body: Any = None) -> str:
    method = str(method or "GET").upper()

    if method == "GET":
        return f'''import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;

public class LogiKluApiExample {{
    public static void main(String[] args) throws Exception {{
        String apiKey = "YOUR_API_KEY";
        String url = "{url}";

        HttpClient client = HttpClient.newHttpClient();

        HttpRequest request = HttpRequest.newBuilder()
                .uri(URI.create(url))
                .GET()
                .header("X-API-KEY", apiKey)
                .build();

        HttpResponse<String> response = client.send(
                request,
                HttpResponse.BodyHandlers.ofString()
        );

        System.out.println(response.body());
    }}
}}'''

    body_json = json.dumps(body or {}, indent=2).replace('"', '\\"').replace("\n", "\\n")

    return f'''import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;

public class LogiKluApiExample {{
    public static void main(String[] args) throws Exception {{
        String apiKey = "YOUR_API_KEY";
        String url = "{url}";

        String payload = "{body_json}";

        HttpClient client = HttpClient.newHttpClient();

        HttpRequest request = HttpRequest.newBuilder()
                .uri(URI.create(url))
                .method("{method}", HttpRequest.BodyPublishers.ofString(payload))
                .header("X-API-KEY", apiKey)
                .header("Content-Type", "application/json")
                .build();

        HttpResponse<String> response = client.send(
                request,
                HttpResponse.BodyHandlers.ofString()
        );

        System.out.println(response.body());
    }}
}}'''


def generate_dotnet(method: str, url: str, body: Any = None) -> str:
    method = str(method or "GET").upper()

    if method == "GET":
        return f'''using System;
using System.Net.Http;
using System.Threading.Tasks;

class Program
{{
    static async Task Main()
    {{
        string apiKey = "YOUR_API_KEY";
        string url = "{url}";

        using var client = new HttpClient();
        client.DefaultRequestHeaders.Add("X-API-KEY", apiKey);

        HttpResponseMessage response = await client.GetAsync(url);
        string responseBody = await response.Content.ReadAsStringAsync();

        Console.WriteLine(responseBody);
    }}
}}'''

    body_json = json.dumps(body or {}, indent=2).replace('"', '\\"')

    return f'''using System;
using System.Net.Http;
using System.Text;
using System.Threading.Tasks;

class Program
{{
    static async Task Main()
    {{
        string apiKey = "YOUR_API_KEY";
        string url = "{url}";

        string payload = "{body_json}";

        using var client = new HttpClient();
        client.DefaultRequestHeaders.Add("X-API-KEY", apiKey);

        var content = new StringContent(payload, Encoding.UTF8, "application/json");

        HttpResponseMessage response = await client.SendAsync(
            new HttpRequestMessage(new HttpMethod("{method}"), url)
            {{
                Content = content
            }}
        );

        string responseBody = await response.Content.ReadAsStringAsync();

        Console.WriteLine(responseBody);
    }}
}}'''


def generate_ruby(method: str, url: str, body: Any = None) -> str:
    method = str(method or "GET").upper()

    if method == "GET":
        return f'''require "net/http"
require "json"
require "uri"

api_key = "YOUR_API_KEY"
url = URI("{url}")

request = Net::HTTP::Get.new(url)
request["X-API-KEY"] = api_key

response = Net::HTTP.start(url.hostname, url.port, use_ssl: url.scheme == "https") do |http|
  http.request(request)
end

puts JSON.pretty_generate(JSON.parse(response.body))'''

    body_json = json.dumps(body or {}, indent=2)

    return f'''require "net/http"
require "json"
require "uri"

api_key = "YOUR_API_KEY"
url = URI("{url}")

payload = {body_json}

request = Net::HTTP::{method.capitalize}.new(url)
request["X-API-KEY"] = api_key
request["Content-Type"] = "application/json"
request.body = payload.to_json

response = Net::HTTP.start(url.hostname, url.port, use_ssl: url.scheme == "https") do |http|
  http.request(request)
end

puts JSON.pretty_generate(JSON.parse(response.body))'''


def generate_go(method: str, url: str, body: Any = None) -> str:
    method = str(method or "GET").upper()

    if method == "GET":
        return f'''package main

import (
    "fmt"
    "io"
    "net/http"
)

func main() {{
    apiKey := "YOUR_API_KEY"
    url := "{url}"

    req, err := http.NewRequest("GET", url, nil)
    if err != nil {{
        panic(err)
    }}

    req.Header.Set("X-API-KEY", apiKey)

    client := &http.Client{{}}
    resp, err := client.Do(req)
    if err != nil {{
        panic(err)
    }}
    defer resp.Body.Close()

    body, err := io.ReadAll(resp.Body)
    if err != nil {{
        panic(err)
    }}

    fmt.Println(string(body))
}}'''

    body_json = json.dumps(body or {}, indent=2).replace("`", "\\`")

    return f'''package main

import (
    "bytes"
    "fmt"
    "io"
    "net/http"
)

func main() {{
    apiKey := "YOUR_API_KEY"
    url := "{url}"

    payload := []byte(`{body_json}`)

    req, err := http.NewRequest("{method}", url, bytes.NewBuffer(payload))
    if err != nil {{
        panic(err)
    }}

    req.Header.Set("X-API-KEY", apiKey)
    req.Header.Set("Content-Type", "application/json")

    client := &http.Client{{}}
    resp, err := client.Do(req)
    if err != nil {{
        panic(err)
    }}
    defer resp.Body.Close()

    body, err := io.ReadAll(resp.Body)
    if err != nil {{
        panic(err)
    }}

    fmt.Println(string(body))
}}'''


def generate_code_examples(
    method: str,
    url: str,
    body: Any = None,
) -> Dict[str, str]:
    return {
        "curl": generate_curl(method, url, body),
        "php": generate_php(method, url, body),
        "python": generate_python(method, url, body),
        "node": generate_node(method, url, body),
        "javascript": generate_javascript(method, url, body),
        "java": generate_java(method, url, body),
        "dotnet": generate_dotnet(method, url, body),
        "ruby": generate_ruby(method, url, body),
        "go": generate_go(method, url, body),
    }


def render_code_tabs(
    unique_id: str,
    code_examples: Dict[str, str],
) -> str:
    labels = {
        "curl": "cURL",
        "php": "PHP",
        "python": "Python",
        "node": "Node.js",
        "javascript": "JavaScript",
        "java": "Java",
        "dotnet": "C# / .NET",
        "ruby": "Ruby",
        "go": "Go",
    }

    buttons = ""
    panes = ""

    first = True

    for key, label in labels.items():
        code = code_examples.get(key)

        if not code:
            continue

        active_class = "active" if first else ""

        buttons += f"""
        <button type="button" class="tab-btn {active_class}" data-target="{esc(unique_id)}-{esc(key)}">
            {esc(label)}
        </button>
        """

        panes += f"""
        <pre class="code-pane {active_class}" id="{esc(unique_id)}-{esc(key)}"><code>{esc(code)}</code></pre>
        """

        first = False

    return f"""
    <div class="code-tabs">
        <div class="tab-buttons">
            {buttons}
        </div>
        <div class="tab-content">
            {panes}
        </div>
    </div>
    """


def render_examples(
    examples: List[Dict[str, Any]],
    method: str,
    base_url: str,
    endpoint_id: str,
) -> str:
    if not examples:
        return ""

    example_html = "<h4>Examples</h4>"

    for index, example in enumerate(examples):
        path = example.get("path", "")
        query = example.get("query", {})
        body = example.get("body")
        url = build_url(base_url, path, query)

        code_examples = generate_code_examples(
            method=method,
            url=url,
            body=body,
        )

        unique_id = f"{endpoint_id}-example-{index}"

        example_html += f"""
        <div class="example-box">
            <div class="example-title">{esc(example.get("title"))}</div>
            <p>{esc(example.get("description"))}</p>
            {render_code_tabs(unique_id, code_examples)}
        </div>
        """

    return example_html


def render_endpoint(section_id: str, endpoint: Dict[str, Any], base_url: str) -> str:
    method = str(endpoint.get("method") or "GET").upper()
    endpoint_id = endpoint.get("id")
    endpoint_anchor = f"{section_id}-{endpoint_id}"

    return f"""
    <article class="endpoint-card" id="{esc(endpoint_anchor)}">
        <div class="endpoint-head">
            <span class="method-badge {method_class(method)}">{esc(method)}</span>
            <span class="endpoint-path">{esc(endpoint.get("path"))}</span>
        </div>

        <h3>{esc(endpoint.get("title"))}</h3>
        <p class="purpose">{esc(endpoint.get("purpose"))}</p>

        <div class="mini-grid">
            <div>
                <span class="mini-label">Method</span>
                <strong>{esc(method)}</strong>
            </div>
            <div>
                <span class="mini-label">Request Type</span>
                <strong>{esc(endpoint.get("request_type"))}</strong>
            </div>
            <div>
                <span class="mini-label">Authentication</span>
                <strong>Required</strong>
            </div>
        </div>

        {render_parameters(endpoint.get("parameters", []))}
        {render_search_by_options(endpoint.get("search_by_options", []))}
        {render_examples(endpoint.get("examples", []), method, base_url, endpoint_anchor)}
    </article>
    """


def render_sidebar(data: Dict[str, Any]) -> str:
    section_links = ""

    for section in data.get("sections", []):
        section_links += f"""
        <div class="side-section">
            <a class="side-main" href="#{esc(section.get("id"))}">{esc(section.get("title"))}</a>
        """

        for endpoint in section.get("endpoints", []):
            anchor = f"{section.get('id')}-{endpoint.get('id')}"
            section_links += f"""
            <a class="side-sub" href="#{esc(anchor)}">{esc(endpoint.get("title"))}</a>
            """

        section_links += "</div>"

    return f"""
    <aside class="sidebar">
        <div class="brand">
            <div class="brand-mark">LK</div>
            <div>
                <strong>LogiKlu API</strong>
                <span>Usage Guide</span>
            </div>
        </div>

        <nav>
            <a class="side-main" href="#getting-started">Getting Started</a>
            <a class="side-main" href="#authentication">Authentication</a>
            <a class="side-main" href="#response-format">Response Format</a>
            {section_links}
            <a class="side-main" href="#errors">Error Codes</a>
        </nav>
    </aside>
    """


def render_usage_page(data: Dict[str, Any]) -> str:
    base_url = data.get("base_url", "")

    sections_html = ""

    for section in data.get("sections", []):
        endpoints_html = ""

        for endpoint in section.get("endpoints", []):
            endpoints_html += render_endpoint(
                section_id=section.get("id"),
                endpoint=endpoint,
                base_url=base_url,
            )

        sections_html += f"""
        <section class="content-section" id="{esc(section.get("id"))}">
            <div class="section-title">
                <span>Section</span>
                <h2>{esc(section.get("title"))}</h2>
                <p>{esc(section.get("description"))}</p>
            </div>
            {endpoints_html}
        </section>
        """

    auth_headers = data.get("auth", {}).get("headers", [])

    auth_rows = [
        [
            f"<code>{esc(item.get('name'))}</code>",
            esc(item.get("required")),
            esc(item.get("description")),
        ]
        for item in auth_headers
    ]

    error_rows = [
        [
            f"<code>{esc(item.get('code'))}</code>",
            esc(item.get("meaning")),
            esc(item.get("fix")),
        ]
        for item in data.get("errors", [])
    ]

    first_example_url = build_url(base_url, "/accounts", {"limit": 20, "offset": 0})
    first_example_code = generate_code_examples("GET", first_example_url)

    template = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8" />
        <meta name="viewport" content="width=device-width, initial-scale=1.0" />
        <title>{{TITLE}}</title>

        <style>
            :root {
                --blue: #0b5fa5;
                --blue-dark: #084a80;
                --bg: #f4f7fb;
                --text: #1f2937;
                --muted: #667085;
                --line: #e4e7ec;
                --card: #ffffff;
                --green: #17803d;
                --post: #2563eb;
                --patch: #d97706;
                --delete: #dc2626;
            }

            * {
                box-sizing: border-box;
            }

            html {
                scroll-behavior: smooth;
            }

            body {
                margin: 0;
                font-family: Arial, Helvetica, sans-serif;
                background: var(--bg);
                color: var(--text);
                line-height: 1.6;
            }

            a {
                color: inherit;
                text-decoration: none;
            }

            .layout {
                display: flex;
                min-height: 100vh;
            }

            .sidebar {
                width: 290px;
                background: #ffffff;
                border-right: 1px solid var(--line);
                padding: 22px 18px;
                position: sticky;
                top: 0;
                height: 100vh;
                overflow-y: auto;
            }

            .brand {
                display: flex;
                align-items: center;
                gap: 12px;
                padding-bottom: 18px;
                margin-bottom: 18px;
                border-bottom: 1px solid var(--line);
            }

            .brand-mark {
                width: 42px;
                height: 42px;
                border-radius: 12px;
                background: var(--blue);
                color: white;
                display: flex;
                align-items: center;
                justify-content: center;
                font-weight: bold;
            }

            .brand span {
                display: block;
                color: var(--muted);
                font-size: 13px;
            }

            .side-main {
                display: block;
                padding: 10px 12px;
                border-radius: 9px;
                color: #344054;
                font-weight: 700;
                margin-top: 4px;
            }

            .side-main:hover {
                background: #eef6ff;
                color: var(--blue);
            }

            .side-sub {
                display: block;
                padding: 7px 12px 7px 28px;
                font-size: 14px;
                color: var(--muted);
                border-radius: 8px;
            }

            .side-sub:hover {
                background: #f2f4f7;
                color: var(--blue);
            }

            .main {
                flex: 1;
                padding: 32px;
                max-width: 1220px;
            }

            .hero {
                background: linear-gradient(135deg, var(--blue), var(--blue-dark));
                color: #ffffff;
                border-radius: 20px;
                padding: 34px;
                margin-bottom: 26px;
                box-shadow: 0 12px 28px rgba(11, 95, 165, 0.22);
            }

            .hero h1 {
                margin: 0 0 8px;
                font-size: 34px;
            }

            .hero p {
                margin: 0 0 20px;
                opacity: 0.95;
                font-size: 16px;
            }

            .base-url {
                display: inline-block;
                background: rgba(255,255,255,0.15);
                padding: 12px 16px;
                border-radius: 12px;
                font-family: Consolas, Monaco, monospace;
                word-break: break-all;
            }

            .content-section {
                margin-bottom: 30px;
            }

            .section-title {
                margin: 30px 0 16px;
            }

            .section-title span {
                color: var(--blue);
                font-weight: 700;
                font-size: 13px;
                text-transform: uppercase;
                letter-spacing: 0.05em;
            }

            .section-title h2 {
                margin: 4px 0;
                font-size: 27px;
            }

            .section-title p {
                color: var(--muted);
                margin: 0;
            }

            .info-card,
            .endpoint-card {
                background: var(--card);
                border: 1px solid var(--line);
                border-radius: 18px;
                padding: 24px;
                margin-bottom: 22px;
                box-shadow: 0 6px 18px rgba(16, 24, 40, 0.06);
            }

            .info-card h2,
            .endpoint-card h3 {
                margin-top: 0;
            }

            .endpoint-head {
                display: flex;
                align-items: center;
                gap: 10px;
                margin-bottom: 14px;
            }

            .method-badge {
                color: white;
                padding: 5px 10px;
                border-radius: 999px;
                font-size: 12px;
                font-weight: bold;
            }

            .method-get {
                background: var(--green);
            }

            .method-post {
                background: var(--post);
            }

            .method-patch {
                background: var(--patch);
            }

            .method-delete {
                background: var(--delete);
            }

            .method-default {
                background: #475467;
            }

            .endpoint-path {
                font-family: Consolas, Monaco, monospace;
                color: #111827;
                background: #f2f4f7;
                padding: 6px 9px;
                border-radius: 8px;
                font-weight: 700;
            }

            .purpose,
            .help-text {
                color: var(--muted);
            }

            .mini-grid {
                display: grid;
                grid-template-columns: repeat(3, minmax(0, 1fr));
                gap: 12px;
                margin: 16px 0 22px;
            }

            .mini-grid div {
                background: #f8fafc;
                border: 1px solid var(--line);
                padding: 12px;
                border-radius: 12px;
            }

            .mini-label {
                display: block;
                color: var(--muted);
                font-size: 12px;
                margin-bottom: 3px;
            }

            .table-wrap {
                overflow-x: auto;
                margin: 12px 0 22px;
            }

            table {
                width: 100%;
                border-collapse: collapse;
                background: white;
            }

            th {
                background: #eef6ff;
                color: #0b5fa5;
                text-align: left;
                padding: 11px;
                border: 1px solid #d8e6f5;
                font-size: 14px;
            }

            td {
                padding: 11px;
                border: 1px solid var(--line);
                vertical-align: top;
                font-size: 14px;
            }

            code {
                background: #f2f4f7;
                color: #0b5fa5;
                padding: 2px 5px;
                border-radius: 5px;
                font-family: Consolas, Monaco, monospace;
            }

            pre {
                background: #101828;
                color: #f9fafb;
                padding: 16px;
                border-radius: 12px;
                overflow-x: auto;
                white-space: pre-wrap;
                word-break: break-word;
                margin: 0;
            }

            pre code {
                background: transparent;
                color: inherit;
                padding: 0;
            }

            .example-box {
                border: 1px solid var(--line);
                border-radius: 14px;
                padding: 16px;
                margin: 12px 0;
                background: #fcfcfd;
            }

            .example-title {
                font-weight: 700;
                color: #111827;
                margin-bottom: 4px;
            }

            .code-tabs {
                margin-top: 12px;
            }

            .tab-buttons {
                display: flex;
                flex-wrap: wrap;
                gap: 8px;
                margin-bottom: 8px;
            }

            .tab-btn {
                border: 1px solid var(--line);
                background: #ffffff;
                color: #344054;
                padding: 6px 10px;
                border-radius: 999px;
                cursor: pointer;
                font-weight: 700;
                font-size: 12px;
            }

            .tab-btn.active {
                background: var(--blue);
                color: #ffffff;
                border-color: var(--blue);
            }

            .code-pane {
                display: none;
            }

            .code-pane.active {
                display: block;
            }

            .footer {
                text-align: center;
                color: var(--muted);
                font-size: 13px;
                padding: 30px 0;
            }

            @media (max-width: 900px) {
                .layout {
                    display: block;
                }

                .sidebar {
                    width: 100%;
                    height: auto;
                    position: relative;
                }

                .main {
                    padding: 18px;
                }

                .mini-grid {
                    grid-template-columns: 1fr;
                }
            }
        </style>
    </head>

    <body>
        <div class="layout">
            {{SIDEBAR}}

            <main class="main">
                <section class="hero">
                    <h1>{{TITLE}}</h1>
                    <p>{{SUBTITLE}}</p>
                    <div class="base-url">Base URL: {{BASE_URL}}</div>
                </section>

                <section class="info-card" id="getting-started">
                    <h2>Getting Started</h2>
                    <p>To use this API, you need only three things:</p>
                    <ol>
                        <li>The API URL you want to call.</li>
                        <li>Your API key.</li>
                        <li>The parameters you want to send.</li>
                    </ol>
                    <p>Here is the same example in different languages:</p>
                    {{FIRST_EXAMPLE}}
                </section>

                <section class="info-card" id="authentication">
                    <h2>{{AUTH_TITLE}}</h2>
                    <p>{{AUTH_DESCRIPTION}}</p>
                    {{AUTH_TABLE}}
                </section>

                <section class="info-card" id="response-format">
                    <h2>Response Format</h2>
                    <p>Every API response follows the same structure.</p>

                    <h3>Success Example</h3>
                    <pre><code>{{SUCCESS_RESPONSE}}</code></pre>

                    <h3>Error Example</h3>
                    <pre><code>{{ERROR_RESPONSE}}</code></pre>
                </section>

                {{SECTIONS}}

                <section class="info-card" id="errors">
                    <h2>Error Codes</h2>
                    <p>If something is wrong, the API returns an error code and message.</p>
                    {{ERROR_TABLE}}
                </section>

                <div class="footer">
                    LogiKlu Agent API Usage Guide
                </div>
            </main>
        </div>

        <script>
            document.addEventListener("click", function (event) {
                if (!event.target.classList.contains("tab-btn")) {
                    return;
                }

                const targetId = event.target.getAttribute("data-target");
                const wrapper = event.target.closest(".code-tabs");

                if (!wrapper || !targetId) {
                    return;
                }

                wrapper.querySelectorAll(".tab-btn").forEach(function (button) {
                    button.classList.remove("active");
                });

                wrapper.querySelectorAll(".code-pane").forEach(function (pane) {
                    pane.classList.remove("active");
                });

                event.target.classList.add("active");

                const targetPane = document.getElementById(targetId);
                if (targetPane) {
                    targetPane.classList.add("active");
                }
            });
        </script>
    </body>
    </html>
    """

    page = template
    page = page.replace("{{TITLE}}", esc(data.get("title")))
    page = page.replace("{{SUBTITLE}}", esc(data.get("subtitle")))
    page = page.replace("{{BASE_URL}}", esc(base_url))
    page = page.replace("{{SIDEBAR}}", render_sidebar(data))
    page = page.replace("{{FIRST_EXAMPLE}}", render_code_tabs("getting-started-example", first_example_code))
    page = page.replace("{{AUTH_TITLE}}", esc(data.get("auth", {}).get("title")))
    page = page.replace("{{AUTH_DESCRIPTION}}", esc(data.get("auth", {}).get("description")))
    page = page.replace("{{AUTH_TABLE}}", render_table(["Header", "Required", "Description"], auth_rows))
    page = page.replace("{{SUCCESS_RESPONSE}}", json_pretty(data.get("response_format", {}).get("success")))
    page = page.replace("{{ERROR_RESPONSE}}", json_pretty(data.get("response_format", {}).get("error")))
    page = page.replace("{{SECTIONS}}", sections_html)
    page = page.replace("{{ERROR_TABLE}}", render_table(["Error Code", "Meaning", "How to Fix"], error_rows))

    return page