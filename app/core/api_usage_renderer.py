import html
import json
from typing import Any, Dict, List
from urllib.parse import urlencode
from app.config import settings


def esc(value: Any) -> str:
    if value is None:
        return ""

    return html.escape(str(value))


def method_class(method: str) -> str:
    method_value = str(method or "").upper()

    if method_value == "GET":
        return "m-get"

    if method_value == "POST":
        return "m-post"

    if method_value == "PUT":
        return "m-put"

    if method_value == "PATCH":
        return "m-patch"

    if method_value == "DELETE":
        return "m-delete"

    return "m-default"


def build_url(base_url: str, path: str, query: Dict[str, Any]) -> str:
    clean_base = str(base_url or "").rstrip("/")
    clean_path = "/" + str(path or "").lstrip("/")

    query = query or {}

    if not query:
        return f"{clean_base}{clean_path}"

    return f"{clean_base}{clean_path}?{urlencode(query)}"


def render_code_block(code: str, language_label: str = "Code") -> str:
    return f"""
    <div class="code-wrap">
        <div class="code-toolbar">
            <span class="code-lang">{esc(language_label)}</span>
            <button class="copy-btn" type="button" onclick="copyCode(this)">Copy</button>
        </div>
        <pre><code>{esc(code)}</code></pre>
    </div>
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

        var request = new HttpRequestMessage(new HttpMethod("{method}"), url);
        request.Content = new StringContent(payload, Encoding.UTF8, "application/json");

        HttpResponseMessage response = await client.SendAsync(request);
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
    ruby_method = method.capitalize

    return f'''require "net/http"
require "json"
require "uri"

api_key = "YOUR_API_KEY"
url = URI("{url}")

payload = {body_json}

request = Net::HTTP::{ruby_method}.new(url)
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


def is_oauth_token_url(url_or_path: str) -> bool:
    value = str(url_or_path or "").lower()
    return "/oauth/token" in value


def is_oauth_token_endpoint(endpoint: Dict[str, Any]) -> bool:
    return is_oauth_token_url(endpoint.get("path", ""))


def get_endpoint_auth_type(endpoint: Dict[str, Any]) -> str:
    auth_type = str(endpoint.get("auth_type") or "").strip().lower()

    if auth_type in ("none", "no_auth", "noauth", "public"):
        return "none"

    if auth_type in ("api_key", "x_api_key", "x-api-key", "legacy_api_key"):
        return "api_key"

    if auth_type in ("bearer", "jwt", "jwt_bearer", "oauth", "oauth_jwt"):
        return "bearer"

    if is_oauth_token_endpoint(endpoint):
        return "none"

    return "bearer"


def endpoint_uses_json_body(endpoint: Dict[str, Any]) -> bool:
    method = str(endpoint.get("method") or "GET").upper()
    request_type = str(endpoint.get("request_type") or "").lower()

    if method == "GET":
        return False

    return is_oauth_token_endpoint(endpoint) or "json body" in request_type


def build_body_from_parameters(endpoint: Dict[str, Any]) -> Dict[str, Any]:
    body = {}

    for param in endpoint.get("parameters", []):
        name = param.get("name")

        if name:
            body[str(name)] = param.get("example") or ""

    return body


def get_endpoint_body(endpoint: Dict[str, Any]) -> Dict[str, Any]:
    body = endpoint.get("body")

    if isinstance(body, dict):
        return body

    if endpoint_uses_json_body(endpoint):
        return build_body_from_parameters(endpoint)

    return {}


def get_example_request(endpoint: Dict[str, Any], example: Dict[str, Any]) -> Dict[str, Any]:
    method = str(endpoint.get("method") or "GET").upper()
    path = example.get("path", endpoint.get("path", ""))
    query = dict(example.get("query") or {})
    body = example.get("body")

    if method != "GET" and endpoint_uses_json_body(endpoint):
        if body is None:
            if query:
                body = query
                query = {}
            else:
                body = get_endpoint_body(endpoint)

    return {
        "path": path,
        "query": query,
        "body": body,
    }


def rewrite_code_auth(language: str, code: str, url: str, auth_type: str = "bearer") -> str:
    language = str(language or "").lower()
    auth_type = str(auth_type or "bearer").strip().lower()

    if auth_type in ("none", "no_auth", "noauth") or is_oauth_token_url(url):
        replacements = [
            ('  -H "X-API-KEY: YOUR_API_KEY" \\\\\n', ''),
            ('  -H "X-API-KEY: YOUR_API_KEY"', ''),
            ('$apiKey = "YOUR_API_KEY";\n', ''),
            ('    "X-API-KEY: " . $apiKey,\n', ''),
            ('    "X-API-KEY: " . $apiKey\n', ''),
            ('api_key = "YOUR_API_KEY"\n', ''),
            ('    "X-API-KEY": api_key,\n', ''),
            ('    "X-API-KEY": api_key\n', ''),
            ('const apiKey = "YOUR_API_KEY";\n', ''),
            ('    "X-API-KEY": apiKey,\n', ''),
            ('    "X-API-KEY": apiKey\n', ''),
            ('        String apiKey = "YOUR_API_KEY";\n', ''),
            ('                .header("X-API-KEY", apiKey)\n', ''),
            ('        string apiKey = "YOUR_API_KEY";\n', ''),
            ('        client.DefaultRequestHeaders.Add("X-API-KEY", apiKey);\n', ''),
            ('api_key = "YOUR_API_KEY"\n', ''),
            ('request["X-API-KEY"] = api_key\n', ''),
            ('    apiKey := "YOUR_API_KEY"\n', ''),
            ('    req.Header.Set("X-API-KEY", apiKey)\n', ''),
        ]

        for old, new in replacements:
            code = code.replace(old, new)

        code = code.replace(" " + chr(92) + "\n " + chr(92) + "\n", " " + chr(92) + "\n")
        code = code.replace('headers = {\n}', 'headers = {}')
        return code

    if auth_type in ("api_key", "x_api_key", "x-api-key", "legacy_api_key"):
        return code

    replacements = [
        ('X-API-KEY: YOUR_API_KEY', 'Authorization: Bearer YOUR_ACCESS_TOKEN'),
        ('$apiKey = "YOUR_API_KEY";', '$accessToken = "YOUR_ACCESS_TOKEN";'),
        ('"X-API-KEY: " . $apiKey', '"Authorization: Bearer " . $accessToken'),
        ('api_key = "YOUR_API_KEY"', 'access_token = "YOUR_ACCESS_TOKEN"'),
        ('"X-API-KEY": api_key', '"Authorization": f"Bearer {access_token}"'),
        ('const apiKey = "YOUR_API_KEY";', 'const accessToken = "YOUR_ACCESS_TOKEN";'),
        ('"X-API-KEY": apiKey', '"Authorization": `Bearer ${accessToken}`'),
        ('String apiKey = "YOUR_API_KEY";', 'String accessToken = "YOUR_ACCESS_TOKEN";'),
        ('.header("X-API-KEY", apiKey)', '.header("Authorization", "Bearer " + accessToken)'),
        ('string apiKey = "YOUR_API_KEY";', 'string accessToken = "YOUR_ACCESS_TOKEN";'),
        ('client.DefaultRequestHeaders.Add("X-API-KEY", apiKey);', 'client.DefaultRequestHeaders.Add("Authorization", "Bearer " + accessToken);'),
        ('api_key = "YOUR_API_KEY"', 'access_token = "YOUR_ACCESS_TOKEN"'),
        ('request["X-API-KEY"] = api_key', 'request["Authorization"] = "Bearer #{access_token}"'),
        ('apiKey := "YOUR_API_KEY"', 'accessToken := "YOUR_ACCESS_TOKEN"'),
        ('req.Header.Set("X-API-KEY", apiKey)', 'req.Header.Set("Authorization", "Bearer "+accessToken)'),
    ]

    for old, new in replacements:
        code = code.replace(old, new)

    return code


def generate_code_examples(method: str, url: str, body: Any = None, auth_type: str = "bearer") -> Dict[str, str]:
    examples = {
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

    return {
        language: rewrite_code_auth(language, code, url, auth_type)
        for language, code in examples.items()
    }


def render_language_tabs(unique_id: str, code_examples: Dict[str, str]) -> str:
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
        <button class="tab-btn lang-tab {active_class}" type="button" onclick="switchLangTab(this, '{esc(unique_id)}-{esc(key)}')">
            {esc(label)}
        </button>
        """

        panes += f"""
        <div class="lang-content {active_class}" id="{esc(unique_id)}-{esc(key)}">
            {render_code_block(code, label)}
        </div>
        """

        first = False

    return f"""
    <div class="language-tabs">
        <div class="tabs small-tabs">
            {buttons}
        </div>
        {panes}
    </div>
    """


def render_parameters(endpoint: Dict[str, Any]) -> str:
    parameters = endpoint.get("parameters", [])

    if not parameters:
        return """
        <div class="info-box info-note">
            <span class="info-icon">ℹ</span>
            <div>No parameters are required for this endpoint.</div>
        </div>
        """

    rows = ""

    for param in parameters:
        required_class = "req" if str(param.get("required", "")).lower() == "yes" else "opt"
        required_text = "required" if required_class == "req" else "optional"
        param_type = param.get("type") or "string"

        rows += f"""
        <tr>
            <td><span class="param-name">{esc(param.get("name"))}</span></td>
            <td><span class="param-type">{esc(param_type)}</span></td>
            <td><span class="param-req {required_class}">{esc(required_text)}</span></td>
            <td><code>{esc(param.get("example"))}</code></td>
            <td class="param-desc">{esc(param.get("description"))}</td>
        </tr>
        """

    return f"""
    <table class="params-table">
        <thead>
            <tr>
                <th>Parameter</th>
                <th>Type</th>
                <th>Required</th>
                <th>Example</th>
                <th>Description</th>
            </tr>
        </thead>
        <tbody>
            {rows}
        </tbody>
    </table>
    """
def render_multi_field_filters(endpoint: Dict[str, Any]) -> str:
    filters = endpoint.get("multi_field_filters", [])

    if not filters:
        return ""

    rows = ""

    for item in filters:
        rows += f"""
        <tr>
            <td><span class="param-name">{esc(item.get("name"))}</span></td>
            <td><code>{esc(item.get("example"))}</code></td>
            <td class="param-desc">{esc(item.get("description"))}</td>
        </tr>
        """

    return f"""
    <h4 class="sub-title">Multi-field Filter Options</h4>
    <p class="section-desc small-desc">
        You can filter list APIs using direct query parameters. Multiple filters are combined using AND logic.
        Example: <code>?country=India&amp;industry=Software</code>
    </p>

    <table class="params-table">
        <thead>
            <tr>
                <th>Filter Field</th>
                <th>Example Value</th>
                <th>Description</th>
            </tr>
        </thead>
        <tbody>
            {rows}
        </tbody>
    </table>
    """

def render_search_by_options(endpoint: Dict[str, Any]) -> str:
    options = endpoint.get("search_by_options", [])

    if not options:
        return ""

    rows = ""

    for item in options:
        rows += f"""
        <tr>
            <td><span class="param-name">{esc(item.get("name"))}</span></td>
            <td><code>{esc(item.get("example"))}</code></td>
            <td class="param-desc">{esc(item.get("description"))}</td>
        </tr>
        """

    return f"""
    <h4 class="sub-title">Specific Search Options</h4>
    <p class="section-desc small-desc">
        Use <code>search</code> with <code>search_by</code> when you want to search one selected field only.
    </p>

    <table class="params-table">
        <thead>
            <tr>
                <th>search_by</th>
                <th>Example Value</th>
                <th>Description</th>
            </tr>
        </thead>
        <tbody>
            {rows}
        </tbody>
    </table>
    """


def render_examples(endpoint: Dict[str, Any], base_url: str) -> str:
    examples = endpoint.get("examples", [])
    method = endpoint.get("method", "GET")

    if not examples:
        default_url = build_url(base_url, endpoint.get("path", ""), {})
        code_examples = generate_code_examples(
            method=method,
            url=default_url,
            body=get_endpoint_body(endpoint),
            auth_type=get_endpoint_auth_type(endpoint),
        )

        return render_language_tabs(
            f"{endpoint.get('id')}-default-example",
            code_examples
        )

    output = ""

    for index, example in enumerate(examples):
        request_data = get_example_request(endpoint, example)
        path = request_data.get("path", endpoint.get("path", ""))
        query = request_data.get("query", {})
        body = request_data.get("body")
        url = build_url(base_url, path, query)

        code_examples = generate_code_examples(
            method=method,
            url=url,
            body=body,
            auth_type=get_endpoint_auth_type(endpoint),
        )

        unique_id = f"{endpoint.get('id')}-example-{index}"

        output += f"""
        <div class="example-block">
            <div class="example-title">{esc(example.get("title"))}</div>
            <p class="example-desc">{esc(example.get("description"))}</p>
            {render_language_tabs(unique_id, code_examples)}
        </div>
        """

    return output


def render_response(endpoint: Dict[str, Any]) -> str:
    response_example = endpoint.get("response_example")

    if not response_example:
        response_example = {
            "status": "success",
            "message": f"{endpoint.get('title')} request successful",
            "meta": {},
            "data": {}
        }

    return render_code_block(
        json.dumps(response_example, indent=2, default=str),
        "JSON · Response"
    )


def render_try_out(endpoint: Dict[str, Any], base_url: str) -> str:
    method = str(endpoint.get("method") or "GET").upper()
    path = endpoint.get("path", "")
    parameters = endpoint.get("parameters", [])
    token_endpoint = is_oauth_token_endpoint(endpoint)
    json_body_endpoint = endpoint_uses_json_body(endpoint)
    auth_type = get_endpoint_auth_type(endpoint)

    input_rows = ""

    if token_endpoint:
        for param in parameters:
            name = param.get("name")
            example = param.get("example") or ""
            required = str(param.get("required") or "No").lower() == "yes"
            input_type = "password" if str(name).lower() == "client_secret" else "text"

            input_rows += f"""
            <div class="try-field">
                <label>
                    <span>{esc(name)}</span>
                    <small>{'Required' if required else 'Optional'}</small>
                </label>
                <input
                    type="{esc(input_type)}"
                    data-body-field="{esc(name)}"
                    data-param-required="{'yes' if required else 'no'}"
                    placeholder="{esc(example)}"
                />
                <p>{esc(param.get("description"))}</p>
            </div>
            """
    elif not json_body_endpoint:
        for param in parameters:
            name = param.get("name")
            example = param.get("example") or ""
            required = str(param.get("required") or "No").lower() == "yes"

            input_rows += f"""
            <div class="try-field">
                <label>
                    <span>{esc(name)}</span>
                    <small>{'Required' if required else 'Optional'}</small>
                </label>
                <input
                    type="text"
                    data-param-name="{esc(name)}"
                    data-param-required="{'yes' if required else 'no'}"
                    placeholder="{esc(example)}"
                />
                <p>{esc(param.get("description"))}</p>
            </div>
            """

    body_box = ""

    if method != "GET" and not token_endpoint:
        default_body = json.dumps(get_endpoint_body(endpoint), indent=2)

        body_box = f"""
        <div class="try-field">
            <label>
                <span>JSON Body</span>
                <small>For POST/PATCH/PUT</small>
            </label>
            <textarea data-body-json rows="8">{esc(default_body)}</textarea>
        </div>
        """

    token_output_box = ""

    if token_endpoint:
        auth_note = "Generate a Bearer access token from the current environment. The token will be saved in this browser and can be reused in other Try Out sections."
        auth_box = ""
        submit_label = "Generate Token"
        token_output_box = """
        <div class="try-field" data-generated-token-wrap style="display:none;">
            <label>
                <span>Generated Access Token</span>
                <small>Copy or use in Try Out</small>
            </label>
            <textarea data-generated-token rows="5" readonly></textarea>
            <div style="display:flex;gap:8px;flex-wrap:wrap;margin-top:8px;">
                <button type="button" class="try-btn" onclick="copyGeneratedToken(this)">Copy Token</button>
                <button type="button" class="try-btn" onclick="applyGeneratedTokenToBearerFields(this)">Use Token in This Page</button>
            </div>
            <p>This token is stored only in your browser localStorage for this documentation page.</p>
        </div>
        """
    elif auth_type == "none":
        auth_note = "This endpoint uses No Auth. Send only Content-Type: application/json and the JSON body."
        auth_box = ""
        submit_label = "Send Request"
    elif auth_type == "api_key":
        auth_note = "Enter your legacy X-API-KEY, then click Send Request."
        auth_box = """
        <div class="try-field">
            <label>
                <span>API Key</span>
                <small>Required</small>
            </label>
            <input type="password" data-api-key placeholder="YOUR_API_KEY" />
        </div>
        """
        submit_label = "Send Request"
    else:
        auth_note = "Enter a Bearer access token generated from /oauth/token, or click Use Saved Token if already generated on this page."
        auth_box = """
        <div class="try-field">
            <label>
                <span>Bearer Access Token</span>
                <small>Required</small>
            </label>
            <input type="password" data-access-token placeholder="YOUR_ACCESS_TOKEN" />
            <div style="display:flex;gap:8px;flex-wrap:wrap;margin-top:8px;">
                <button type="button" class="copy-btn" onclick="useSavedBearerToken(this)">Use Saved Token</button>
                <button type="button" class="copy-btn" onclick="clearSavedBearerToken(this)">Clear Saved Token</button>
            </div>
            <p>Generate a token from the /oauth/token Try Out section first, or paste one manually.</p>
        </div>
        """
        submit_label = "Send Request"

    try_grid = ""

    if input_rows:
        try_grid = f"""
        <div class="try-grid">
            {input_rows}
        </div>
        """

    return f"""
    <div class="tryout-box"
         data-method="{esc(method)}"
         data-path="{esc(path)}"
         data-base-url="{esc(base_url)}"
         data-auth-type="{esc(auth_type)}"
         data-token-endpoint="{'yes' if token_endpoint else 'no'}">

        <div class="info-box info-note">
            <span class="info-icon">ℹ</span>
            <div>
                {esc(auth_note)}
                The real API response will appear below.
            </div>
        </div>

        {auth_box}

        {try_grid}

        {body_box}

        <button type="button" class="try-btn" onclick="sendTryOutRequest(this)">
            {esc(submit_label)}
        </button>

        <div class="try-url">
            <span>Request URL</span>
            <code data-request-url>{esc(base_url)}{esc(path)}</code>
        </div>

        {token_output_box}

        <div class="code-wrap try-response-wrap">
            <div class="code-toolbar">
                <span class="code-lang">Live Response</span>
                <button class="copy-btn" type="button" onclick="copyCode(this)">Copy</button>
            </div>
            <pre><code data-try-response>Click "{esc(submit_label)}" to see response here.</code></pre>
        </div>
    </div>
    """

def render_endpoint_card(section_id: str, endpoint: Dict[str, Any], base_url: str, open_default: bool = False) -> str:
    endpoint_id = f"{section_id}-{endpoint.get('id')}"
    method = str(endpoint.get("method") or "GET").upper()
    open_class = "open" if open_default else ""

    return f"""
    <div class="endpoint-card {open_class}" id="{esc(endpoint_id)}">
        <div class="endpoint-header" onclick="toggleCard(this)">
            <span class="method-tag {method_class(method)}">{esc(method)}</span>
            <span class="endpoint-path">{esc(endpoint.get("path"))}</span>
            <span class="endpoint-desc">{esc(endpoint.get("title"))}</span>
            <span class="endpoint-toggle">▾</span>
        </div>

        <div class="endpoint-body">
            <div class="info-box info-tip">
                <span class="info-icon">✦</span>
                <div>{esc(endpoint.get("purpose"))}</div>
            </div>

            <div class="tabs endpoint-tabs">
                <button class="tab-btn active" type="button" onclick="switchEndpointTab(this, '{esc(endpoint_id)}-request')">Request</button>
                <button class="tab-btn" type="button" onclick="switchEndpointTab(this, '{esc(endpoint_id)}-params')">{esc(endpoint.get("request_type", "Parameters"))}</button>
                <button class="tab-btn" type="button" onclick="switchEndpointTab(this, '{esc(endpoint_id)}-response')">Response</button>
                <button class="tab-btn" type="button" onclick="switchEndpointTab(this, '{esc(endpoint_id)}-tryout')">Try Out</button>
            </div>

            <div id="{esc(endpoint_id)}-request" class="endpoint-tab-content active">
                {render_examples(endpoint, base_url)}
            </div>

           <div id="{esc(endpoint_id)}-params" class="endpoint-tab-content">
                {render_parameters(endpoint)}
                {render_multi_field_filters(endpoint)}
                {render_search_by_options(endpoint)}
            </div>

            <div id="{esc(endpoint_id)}-response" class="endpoint-tab-content">
                {render_response(endpoint)}
            </div>

            <div id="{esc(endpoint_id)}-tryout" class="endpoint-tab-content">
                {render_try_out(endpoint, base_url)}
            </div>
        </div>
    </div>
    """


def render_sidebar(data: Dict[str, Any]) -> str:
    section_html = ""

    for section in data.get("sections", []):
        section_id = section.get("id")

        endpoint_links = ""

        for endpoint in section.get("endpoints", []):
            endpoint_anchor = f"{section_id}-{endpoint.get('id')}"
            method = str(endpoint.get("method") or "GET").upper()

            endpoint_links += f"""
            <a class="nav-item child-nav" onclick="scrollToSection('{esc(endpoint_anchor)}')">
                <span class="nav-method {method_class(method)}">{esc(method)}</span>{esc(endpoint.get("path"))}
            </a>
            """

        section_html += f"""
        <div class="nav-group api-nav-group open">
            <button class="nav-group-toggle" type="button" onclick="toggleMenuGroup(this)">
                <span>{esc(section.get("title"))}</span>
                <span class="menu-arrow">▾</span>
            </button>
            <div class="nav-children">
                <a class="nav-item section-nav" onclick="scrollToSection('{esc(section_id)}')">Overview</a>
                {endpoint_links}
            </div>
        </div>
        """

    return f"""
    <nav class="sidebar">
        <div class="sidebar-header">
            <a class="logo" onclick="scrollToSection('overview')">
                <img src="/static/images/logiklu-logo.png" alt="LogiKlu" />
            </a>
            <div class="sidebar-version">Agent API · REST</div>
        </div>

        <div class="nav-group">
            <div class="nav-group-label">Getting Started</div>
            <a class="nav-item active" onclick="scrollToSection('overview')">Overview</a>
            <a class="nav-item" onclick="scrollToSection('environments')">Environments</a>
            <a class="nav-item" onclick="scrollToSection('authentication')">Authentication</a>
            <a class="nav-item" onclick="scrollToSection('response-format')">Response Format</a>
            <a class="nav-item" onclick="scrollToSection('quick-start')">Quick Start</a>
            <a class="nav-item" onclick="scrollToSection('api-logging')">API Logging</a>
            <a class="nav-item" onclick="scrollToSection('errors')">Error Handling</a>
        </div>

        {section_html}
    </nav>
    """


def render_sections(data: Dict[str, Any]) -> str:
    base_url = data.get("base_url", "")
    output = ""
    section_number = 4

    for section_index, section in enumerate(data.get("sections", [])):
        endpoint_cards = ""

        for endpoint_index, endpoint in enumerate(section.get("endpoints", [])):
            endpoint_cards += render_endpoint_card(
                section_id=section.get("id"),
                endpoint=endpoint,
                base_url=base_url,
                open_default=(section_index == 0 and endpoint_index == 0)
            )

        output += f"""
        <div class="section" id="{esc(section.get("id"))}">
            <div class="section-header">
                <span class="section-num">{section_number:02d}</span>
                <h2 class="section-title">{esc(section.get("title"))}</h2>
            </div>
            <p class="section-desc">{esc(section.get("description"))}</p>
            {endpoint_cards}
        </div>
        """

        section_number += 1

    return output


def render_error_codes(data: Dict[str, Any]) -> str:
    rows = ""

    for item in data.get("errors", []):
        rows += f"""
        <div class="response-item">
            <span class="status-code s4">{esc(item.get("code"))}</span>
            <div>
                <strong>{esc(item.get("meaning"))}</strong><br>
                <span>{esc(item.get("fix"))}</span>
            </div>
        </div>
        """

    return rows

def get_current_environment_name(data: Dict[str, Any] = None) -> str:
    data = data or {}
    runtime_base_url = str(data.get("runtime_base_url") or "").lower()

    if "127.0.0.1" in runtime_base_url or "localhost" in runtime_base_url:
        return "Local"

    if "sandboxapi" in runtime_base_url:
        return "Sandbox"

    api_env = str(getattr(settings, "API_ENV", "production") or "production").strip().lower()

    if api_env == "sandbox":
        return "Sandbox"

    return "Production"


def get_current_base_url(data: Dict[str, Any]) -> str:
    runtime_base_url = str(data.get("runtime_base_url") or "").strip().rstrip("/")

    if runtime_base_url:
        return runtime_base_url

    api_env = str(getattr(settings, "API_ENV", "production") or "production").strip().lower()

    if api_env == "sandbox":
        return data.get("sandbox_base_url") or data.get("base_url") or ""

    if api_env == "local":
        return data.get("local_base_url") or "http://127.0.0.1:8000"

    return data.get("base_url") or ""

def render_environments(data: Dict[str, Any]) -> str:
    environment_name = get_current_environment_name(data)
    base_url = get_current_base_url(data)

    description = "Use this sandbox environment for testing API integration before production release."

    if environment_name == "Production":
        description = "Use this production environment for live API calls."

    return f"""
    <div class="section" id="environments">
        <div class="section-header">
            <span class="section-num">00</span>
            <h2 class="section-title">Environment</h2>
        </div>

        <p class="section-desc">
            This documentation page shows the base URL for the current API environment only.
        </p>

        <div class="base-url-box">
            <span class="base-url-label">{esc(environment_name)} API</span>
            <span class="base-url-value">{esc(base_url)}</span>
        </div>

        <div class="info-box info-note">
            <span class="info-icon">ℹ</span>
            <div>{esc(description)}</div>
        </div>
    </div>
    """
def render_logging_section(data: Dict[str, Any]) -> str:
    logging_data = data.get("logging", {})

    if not logging_data:
        return ""

    fields = ""

    for field in logging_data.get("logged_fields", []):
        fields += f"""
        <tr>
            <td><span class="param-name">{esc(field)}</span></td>
            <td class="param-desc">Stored internally for audit and troubleshooting.</td>
        </tr>
        """

    return f"""
    <div class="section" id="api-logging">
        <div class="section-header">
            <span class="section-num">98</span>
            <h2 class="section-title">{esc(logging_data.get("title"))}</h2>
        </div>

        <p class="section-desc">
            {esc(logging_data.get("description"))}
        </p>

        <div class="info-box info-note">
            <span class="info-icon">ℹ</span>
            <div>
                Sandbox and production logs are stored separately for audit, troubleshooting, and support.
                Internal storage details are not exposed in this developer guide.
            </div>
        </div>

        <table class="params-table">
            <thead>
                <tr>
                    <th>Logged Field</th>
                    <th>Description</th>
                </tr>
            </thead>
            <tbody>
                {fields}
            </tbody>
        </table>
    </div>
    """


def render_usage_page(data: Dict[str, Any]) -> str:
    base_url = get_current_base_url(data)
    first_example_url = build_url(base_url, data.get("quick_start_path", "/focus/account-intelligence"), data.get("quick_start_query", {"page": 1, "per_page": 10}))
    first_example_code = generate_code_examples("GET", first_example_url, auth_type=data.get("quick_start_auth_type", "bearer"))

    template = """
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{{TITLE}}</title>

<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;600;700&family=Syne:wght@400;500;600;700;800&display=swap" rel="stylesheet">

<style>
:root {
    --bg: #0a0b0f;
    --bg2: #111318;
    --bg3: #181b22;
    --bg4: #1e2230;
    --border: #2a2f3d;
    --border2: #3a4055;
    --text: #e8eaf0;
    --muted: #7a8099;
    --accent: #00e5a0;
    --accent2: #0099ff;
    --accent3: #ff6b6b;
    --accent4: #ffb347;
    --purple: #a78bfa;
    --code-bg: #0d1117;
    --tag-get: #00e5a0;
    --tag-post: #0099ff;
    --tag-put: #ffb347;
    --tag-delete: #ff6b6b;
    --tag-patch: #a78bfa;
}

*, *::before, *::after {
    box-sizing: border-box;
    margin: 0;
    padding: 0;
}

html {
    scroll-behavior: smooth;
}

body {
    background: var(--bg);
    color: var(--text);
    font-family: 'Syne', sans-serif;
    font-size: 15px;
    line-height: 1.7;
    min-height: 100vh;
}

.layout {
    display: flex;
    min-height: 100vh;
}

.sidebar {
    width: 280px;
    min-width: 280px;
    background: var(--bg2);
    border-right: 1px solid var(--border);
    position: sticky;
    top: 0;
    height: 100vh;
    overflow-y: auto;
    padding: 0 0 2rem;
    flex-shrink: 0;
}

.sidebar::-webkit-scrollbar {
    width: 4px;
}

.sidebar::-webkit-scrollbar-thumb {
    background: var(--border2);
    border-radius: 4px;
}

.sidebar-header {
    padding: 1.25rem 1.25rem 1rem;
    border-bottom: 1px solid var(--border);
    margin-bottom: 0.5rem;
}

.logo {
    display: block;
    cursor: pointer;
}

.logo img {
    max-width: 190px;
    height: auto;
    display: block;
}

.sidebar-version {
    font-family: 'JetBrains Mono', monospace;
    font-size: 11px;
    color: var(--muted);
    margin-top: 8px;
}

.nav-group {
    padding: 0.75rem 0;
    border-bottom: 1px solid rgba(42, 47, 61, 0.65);
}

.nav-group-label {
    font-size: 10px;
    font-weight: 600;
    letter-spacing: 1.5px;
    text-transform: uppercase;
    color: var(--muted);
    padding: 0.25rem 1.5rem 0.5rem;
}

.nav-group-toggle {
    width: 100%;
    background: none;
    border: none;
    color: var(--text);
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 0.55rem 1.5rem;
    cursor: pointer;
    font-family: 'Syne', sans-serif;
    font-weight: 700;
    font-size: 13.5px;
}

.nav-group-toggle:hover {
    background: var(--bg3);
    color: var(--accent);
}

.menu-arrow {
    transition: transform 0.2s;
    color: var(--muted);
}

.api-nav-group:not(.open) .menu-arrow {
    transform: rotate(-90deg);
}

.api-nav-group:not(.open) .nav-children {
    display: none;
}

.nav-item {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 0.4rem 1.5rem;
    font-size: 13.5px;
    color: var(--muted);
    text-decoration: none;
    transition: color 0.15s, background 0.15s;
    border-left: 2px solid transparent;
    cursor: pointer;
}

.nav-item:hover {
    color: var(--text);
    background: var(--bg3);
}

.nav-item.active {
    color: var(--accent);
    border-left-color: var(--accent);
    background: rgba(0,229,160,0.05);
}

.child-nav {
    padding-left: 1.5rem;
}

.section-nav {
    padding-left: 2rem;
    font-size: 12.5px;
}

.nav-method {
    font-family: 'JetBrains Mono', monospace;
    font-size: 9px;
    font-weight: 700;
    padding: 2px 5px;
    border-radius: 3px;
    min-width: 42px;
    text-align: center;
}

.m-get {
    background: rgba(0,229,160,0.15);
    color: var(--tag-get);
}

.m-post {
    background: rgba(0,153,255,0.15);
    color: var(--tag-post);
}

.m-put {
    background: rgba(255,179,71,0.15);
    color: var(--tag-put);
}

.m-delete {
    background: rgba(255,107,107,0.15);
    color: var(--tag-delete);
}

.m-patch {
    background: rgba(167,139,250,0.15);
    color: var(--tag-patch);
}

.main {
    flex: 1;
    overflow-y: auto;
    padding: 0;
}

.hero {
    background: linear-gradient(135deg, var(--bg2) 0%, #0d1020 100%);
    border-bottom: 1px solid var(--border);
    padding: 4rem 4rem 3rem;
    position: relative;
    overflow: hidden;
}

.hero::before {
    content: '';
    position: absolute;
    top: -80px;
    right: -80px;
    width: 300px;
    height: 300px;
    background: radial-gradient(circle, rgba(0,229,160,0.08) 0%, transparent 70%);
    border-radius: 50%;
}

.hero::after {
    content: '';
    position: absolute;
    bottom: -60px;
    left: 20%;
    width: 200px;
    height: 200px;
    background: radial-gradient(circle, rgba(0,153,255,0.06) 0%, transparent 70%);
    border-radius: 50%;
}

.hero-eyebrow {
    font-family: 'JetBrains Mono', monospace;
    font-size: 11px;
    font-weight: 500;
    color: var(--accent);
    letter-spacing: 2px;
    text-transform: uppercase;
    margin-bottom: 1rem;
}

.hero h1 {
    font-size: 42px;
    font-weight: 800;
    letter-spacing: -1.5px;
    line-height: 1.15;
    margin-bottom: 1rem;
    background: linear-gradient(135deg, #e8eaf0 30%, #7a8099);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
}

.hero-sub {
    font-size: 16px;
    color: var(--muted);
    max-width: 650px;
    line-height: 1.7;
    margin-bottom: 2rem;
}

.hero-meta {
    display: flex;
    gap: 1rem;
    flex-wrap: wrap;
}

.hero-badge {
    display: flex;
    align-items: center;
    gap: 6px;
    font-family: 'JetBrains Mono', monospace;
    font-size: 12px;
    color: var(--muted);
    background: var(--bg3);
    border: 1px solid var(--border);
    border-radius: 6px;
    padding: 6px 12px;
}

.hero-badge span {
    color: var(--accent);
}

.content {
    padding: 3rem 4rem;
    max-width: 1100px;
}

.section {
    margin-bottom: 4rem;
    padding-bottom: 3rem;
    border-bottom: 1px solid var(--border);
    scroll-margin-top: 24px;
}

.section:last-of-type {
    border-bottom: none;
}

.section-header {
    display: flex;
    align-items: center;
    gap: 12px;
    margin-bottom: 0.75rem;
    padding-bottom: 0.75rem;
    border-bottom: 1px solid var(--border);
}

.section-num {
    font-family: 'JetBrains Mono', monospace;
    font-size: 11px;
    color: var(--accent);
    background: rgba(0,229,160,0.1);
    border: 1px solid rgba(0,229,160,0.2);
    border-radius: 4px;
    padding: 2px 8px;
    min-width: 36px;
    text-align: center;
}

.section-title {
    font-size: 22px;
    font-weight: 700;
    letter-spacing: -0.5px;
    color: var(--text);
}

.section-desc {
    font-size: 14px;
    color: var(--muted);
    margin-bottom: 1.5rem;
    line-height: 1.7;
}

.small-desc {
    margin-bottom: 1rem;
}

.sub-title {
    margin: 1.5rem 0 0.4rem;
    font-size: 16px;
}

.endpoint-card {
    background: var(--bg2);
    border: 1px solid var(--border);
    border-radius: 12px;
    margin-bottom: 1.5rem;
    overflow: hidden;
    transition: border-color 0.2s;
    scroll-margin-top: 24px;
}

.endpoint-card:hover {
    border-color: var(--border2);
}

.endpoint-header {
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 1rem 1.25rem;
    border-bottom: 1px solid var(--border);
    cursor: pointer;
    user-select: none;
    background: var(--bg3);
}

.endpoint-header:hover {
    background: var(--bg4);
}

.method-tag {
    font-family: 'JetBrains Mono', monospace;
    font-size: 11px;
    font-weight: 700;
    padding: 4px 10px;
    border-radius: 5px;
    min-width: 56px;
    text-align: center;
    letter-spacing: 0.5px;
}

.endpoint-path {
    font-family: 'JetBrains Mono', monospace;
    font-size: 14px;
    color: var(--text);
    font-weight: 500;
    flex: 1;
}

.endpoint-desc {
    font-size: 13px;
    color: var(--muted);
}

.endpoint-toggle {
    color: var(--muted);
    font-size: 16px;
    transition: transform 0.2s;
    min-width: 16px;
}

.endpoint-card.open .endpoint-toggle {
    transform: rotate(180deg);
}

.endpoint-body {
    display: none;
    padding: 1.25rem;
}

.endpoint-card.open .endpoint-body {
    display: block;
}

.tabs {
    display: flex;
    gap: 0;
    border-bottom: 1px solid var(--border);
    margin-bottom: 1.25rem;
    flex-wrap: wrap;
}

.tab-btn {
    font-family: 'JetBrains Mono', monospace;
    font-size: 12px;
    font-weight: 500;
    padding: 0.5rem 1rem;
    background: none;
    border: none;
    border-bottom: 2px solid transparent;
    color: var(--muted);
    cursor: pointer;
    transition: all 0.15s;
    margin-bottom: -1px;
    letter-spacing: 0.3px;
}

.tab-btn:hover {
    color: var(--text);
}

.tab-btn.active {
    color: var(--accent);
    border-bottom-color: var(--accent);
}

.small-tabs {
    margin-bottom: 0.75rem;
}

.lang-tab {
    font-size: 11px;
    padding: 0.45rem 0.75rem;
}

.endpoint-tab-content,
.lang-content {
    display: none;
}

.endpoint-tab-content.active,
.lang-content.active {
    display: block;
}

.code-wrap {
    position: relative;
    border-radius: 8px;
    overflow: hidden;
    border: 1px solid var(--border);
    margin-bottom: 1rem;
}

.code-toolbar {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 0.5rem 0.75rem;
    background: #0d1117;
    border-bottom: 1px solid var(--border);
}

.code-lang {
    font-family: 'JetBrains Mono', monospace;
    font-size: 11px;
    color: var(--muted);
    letter-spacing: 0.5px;
}

.copy-btn {
    font-family: 'JetBrains Mono', monospace;
    font-size: 11px;
    color: var(--muted);
    background: none;
    border: 1px solid var(--border);
    border-radius: 4px;
    padding: 3px 10px;
    cursor: pointer;
    transition: all 0.15s;
}

.copy-btn:hover {
    color: var(--accent);
    border-color: rgba(0,229,160,0.4);
}

.copy-btn.copied {
    color: var(--accent);
}

pre {
    background: var(--code-bg);
    padding: 1.25rem;
    overflow-x: auto;
    margin: 0;
    font-family: 'JetBrains Mono', monospace;
    font-size: 13px;
    line-height: 1.75;
    white-space: pre;
}

pre code {
    font-family: inherit;
    color: var(--text);
}

.params-table {
    width: 100%;
    border-collapse: collapse;
    font-size: 13px;
    margin-bottom: 1rem;
}

.params-table th {
    font-family: 'JetBrains Mono', monospace;
    font-size: 10px;
    font-weight: 600;
    letter-spacing: 1px;
    text-transform: uppercase;
    color: var(--muted);
    text-align: left;
    padding: 0.5rem 0.75rem;
    background: var(--bg3);
    border-bottom: 1px solid var(--border);
}

.params-table td {
    padding: 0.6rem 0.75rem;
    border-bottom: 1px solid var(--border);
    vertical-align: top;
}

.params-table tr:hover td {
    background: var(--bg3);
}

.param-name {
    font-family: 'JetBrains Mono', monospace;
    color: var(--accent2);
    font-size: 12.5px;
}

.param-type {
    font-family: 'JetBrains Mono', monospace;
    font-size: 11px;
    color: var(--purple);
    background: rgba(167,139,250,0.1);
    padding: 2px 6px;
    border-radius: 3px;
}

.param-req {
    font-size: 10px;
    font-family: 'JetBrains Mono', monospace;
    padding: 2px 6px;
    border-radius: 3px;
    font-weight: 600;
}

.req {
    background: rgba(255,107,107,0.1);
    color: var(--accent3);
}

.opt {
    background: rgba(122,128,153,0.1);
    color: var(--muted);
}

.param-desc {
    color: var(--muted);
    font-size: 13px;
}

.response-list {
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
    margin-bottom: 1rem;
}

.response-item {
    display: flex;
    align-items: flex-start;
    gap: 10px;
    padding: 0.65rem 0.75rem;
    background: var(--bg3);
    border-radius: 6px;
    border: 1px solid var(--border);
    font-size: 13px;
}

.status-code {
    font-family: 'JetBrains Mono', monospace;
    font-size: 11px;
    font-weight: 700;
    padding: 2px 8px;
    border-radius: 4px;
    min-width: 44px;
    text-align: center;
    white-space: nowrap;
}

.s2 {
    background: rgba(0,229,160,0.1);
    color: var(--accent);
}

.s4 {
    background: rgba(255,107,107,0.1);
    color: var(--accent3);
}

.s5 {
    background: rgba(255,179,71,0.1);
    color: var(--accent4);
}

.info-box {
    display: flex;
    gap: 12px;
    padding: 1rem 1.25rem;
    border-radius: 8px;
    margin-bottom: 1.25rem;
    font-size: 13.5px;
    line-height: 1.6;
}

.info-icon {
    font-size: 16px;
    flex-shrink: 0;
    margin-top: 2px;
}

.info-note {
    background: rgba(0,153,255,0.07);
    border: 1px solid rgba(0,153,255,0.2);
    color: #a0c4f5;
}

.info-warn {
    background: rgba(255,179,71,0.07);
    border: 1px solid rgba(255,179,71,0.2);
    color: #f5d08a;
}

.info-tip {
    background: rgba(0,229,160,0.07);
    border: 1px solid rgba(0,229,160,0.2);
    color: #80f0cb;
}

.base-url-box {
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 0.875rem 1.25rem;
    background: var(--bg2);
    border: 1px solid var(--border);
    border-left: 3px solid var(--accent);
    border-radius: 8px;
    margin-bottom: 1.5rem;
}

.base-url-label {
    font-family: 'JetBrains Mono', monospace;
    font-size: 11px;
    color: var(--muted);
    text-transform: uppercase;
    letter-spacing: 1px;
    min-width: 80px;
}

.base-url-value {
    font-family: 'JetBrains Mono', monospace;
    font-size: 13.5px;
    color: var(--accent);
    font-weight: 500;
}

.auth-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 1rem;
    margin-bottom: 1.5rem;
}

.auth-card {
    padding: 1.25rem;
    background: var(--bg2);
    border: 1px solid var(--border);
    border-radius: 10px;
}

.auth-card-title {
    font-size: 14px;
    font-weight: 600;
    color: var(--text);
    margin-bottom: 0.5rem;
}

.auth-card-desc {
    font-size: 13px;
    color: var(--muted);
    line-height: 1.6;
}

.example-block {
    border: 1px solid var(--border);
    background: var(--bg2);
    border-radius: 10px;
    padding: 1rem;
    margin-bottom: 1.25rem;
}

.example-title {
    font-weight: 700;
    margin-bottom: 0.2rem;
}

.example-desc {
    font-size: 13px;
    color: var(--muted);
    margin-bottom: 0.8rem;
}

.tryout-box {
    background: var(--bg2);
    border: 1px solid var(--border);
    border-radius: 10px;
    padding: 1rem;
}

.try-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 1rem;
}

.try-field {
    margin-bottom: 1rem;
}

.try-field label {
    display: flex;
    justify-content: space-between;
    gap: 12px;
    margin-bottom: 0.35rem;
    font-size: 13px;
    color: var(--text);
    font-weight: 600;
}

.try-field label small {
    color: var(--muted);
    font-family: 'JetBrains Mono', monospace;
    font-size: 10px;
}

.try-field input,
.try-field textarea {
    width: 100%;
    background: var(--code-bg);
    border: 1px solid var(--border);
    color: var(--text);
    border-radius: 7px;
    padding: 0.7rem 0.8rem;
    font-family: 'JetBrains Mono', monospace;
    font-size: 13px;
    outline: none;
}

.try-field input:focus,
.try-field textarea:focus {
    border-color: var(--accent);
}

.try-field p {
    margin-top: 0.3rem;
    color: var(--muted);
    font-size: 12px;
}

.try-btn {
    border: none;
    background: var(--accent);
    color: #06110d;
    font-weight: 800;
    padding: 0.75rem 1.2rem;
    border-radius: 8px;
    cursor: pointer;
    font-family: 'Syne', sans-serif;
    margin-bottom: 1rem;
}

.try-btn:hover {
    filter: brightness(1.08);
}

.try-url {
    background: var(--bg3);
    border: 1px solid var(--border);
    padding: 0.75rem;
    border-radius: 8px;
    margin-bottom: 1rem;
}

.try-url span {
    display: block;
    color: var(--muted);
    font-size: 11px;
    text-transform: uppercase;
    letter-spacing: 1px;
    margin-bottom: 0.25rem;
}

.try-url code {
    font-family: 'JetBrains Mono', monospace;
    color: var(--accent);
    word-break: break-all;
}

.try-response-wrap {
    margin-bottom: 0;
}

.page-footer {
    margin-top: 4rem;
    padding-top: 2rem;
    border-top: 1px solid var(--border);
    font-size: 13px;
    color: var(--muted);
    display: flex;
    justify-content: space-between;
    align-items: center;
}

@media (max-width: 980px) {
    .sidebar {
        display: none;
    }

    .hero {
        padding: 2rem 1.5rem;
    }

    .content {
        padding: 2rem 1.5rem;
    }

    .auth-grid,
    .try-grid {
        grid-template-columns: 1fr;
    }

    .endpoint-header {
        align-items: flex-start;
        flex-wrap: wrap;
    }

    .endpoint-desc {
        width: 100%;
    }
}
</style>
</head>

<body>
<div class="layout">

{{SIDEBAR}}

<main class="main">

    <div class="hero" id="overview">
        <div class="hero-eyebrow">Documentation</div>
        <h1>{{TITLE}}</h1>
        <p class="hero-sub">{{SUBTITLE}}</p>

        <div class="hero-meta">
            <div class="hero-badge">{{ENV_NAME}} URL <span>{{BASE_URL}}</span></div>
            <div class="hero-badge">Format <span>JSON</span></div>
            <div class="hero-badge">Auth <span>{{AUTH_BADGE}}</span></div>
            <div class="hero-badge">TLS <span>Required</span></div>
        </div>
    </div>

    <div class="content">

         {{ENVIRONMENTS}}

        <div class="section" id="authentication">
            <div class="section-header">
                <span class="section-num">01</span>
                <h2 class="section-title">Authentication</h2>
            </div>

            <p class="section-desc">
                Protected APIs use OAuth 2.0 Client Credentials with a short-lived Bearer JWT.
                First call <code>/oauth/token</code> with your client credentials, then send
                <code>Authorization: Bearer &lt;access_token&gt;</code> on protected API requests.
                The legacy <code>X-API-KEY</code> header remains supported for backward compatibility.
            </p>

            <div class="base-url-box">
                <span class="base-url-label">Base URL</span>
                <span class="base-url-value">{{BASE_URL}}</span>
            </div>

            <div class="auth-grid">
                <div class="auth-card">
                    <div class="auth-card-title">OAuth Token Endpoint</div>
                    <div class="auth-card-desc">
                        Call <code>POST /oauth/token</code> with <code>client_id</code>, <code>client_secret</code>, and <code>grant_type=client_credentials</code>. This endpoint uses No Auth.
                    </div>
                </div>
                <div class="auth-card">
                    <div class="auth-card-title">Bearer Token Header</div>
                    <div class="auth-card-desc">
                        Send the returned access token as <code>Authorization: Bearer &lt;access_token&gt;</code>. Tokens expire after the configured lifetime, currently 900 seconds.
                    </div>
                </div>
            </div>

            {{AUTH_CODE}}

            <div class="info-box info-warn">
                <span class="info-icon">⚠</span>
                <div>Never expose your client secret, access token, or legacy API key in public frontend code or public repositories.</div>
            </div>
        </div>

        <div class="section" id="response-format">
            <div class="section-header">
                <span class="section-num">02</span>
                <h2 class="section-title">Response Format</h2>
            </div>

            <p class="section-desc">
                Every API response follows the same simple structure: status, message, meta, and data.
            </p>

            {{SUCCESS_CODE}}

            {{ERROR_CODE}}
        </div>

        <div class="section" id="quick-start">
            <div class="section-header">
                <span class="section-num">03</span>
                <h2 class="section-title">Quick Start</h2>
            </div>

            <p class="section-desc">
                This example fetches the first page of Focus Account Intelligence using Bearer token authentication. Select the language you use and copy the code.
            </p>

            {{QUICK_START_CODE}}
        </div>

        {{SECTIONS}}

        {{LOGGING_SECTION}}

        <div class="section" id="errors">
            <div class="section-header">
                <span class="section-num">99</span>
                <h2 class="section-title">Error Handling</h2>
            </div>

            <p class="section-desc">
                If something is wrong, the API returns an error code and a message explaining what happened.
            </p>

            <div class="response-list">
                <div class="response-item"><span class="status-code s2">200</span> OK — Request succeeded</div>
                <div class="response-item"><span class="status-code s4">400</span> Bad Request — Invalid or missing parameters</div>
                <div class="response-item"><span class="status-code s4">401</span> Unauthorized — Missing or invalid Bearer token / API key</div>
                <div class="response-item"><span class="status-code s4">403</span> Forbidden — Client is not allowed to access this data</div>
                <div class="response-item"><span class="status-code s4">404</span> Not Found — Requested account/contact/intelligence record does not exist</div>
                <div class="response-item"><span class="status-code s5">500</span> Server Error — Unexpected internal error</div>
            </div>

            <div class="response-list">
                {{ERROR_CODES}}
            </div>
        </div>

        <div class="page-footer">
            <span>LogiKlu Agent API Guide</span>
            <span>Last updated 2026</span>
        </div>

    </div>
</main>
</div>

<script>
function toggleCard(header) {
    const card = header.closest('.endpoint-card');
    if (!card) return;
    card.classList.toggle('open');
}

function toggleMenuGroup(button) {
    const group = button.closest('.api-nav-group');
    if (!group) return;
    group.classList.toggle('open');
}

function switchEndpointTab(button, targetId) {
    const body = button.closest('.endpoint-body');
    if (!body) return;

    body.querySelectorAll('.endpoint-tabs .tab-btn').forEach(function(btn) {
        btn.classList.remove('active');
    });

    body.querySelectorAll('.endpoint-tab-content').forEach(function(content) {
        content.classList.remove('active');
    });

    button.classList.add('active');

    const target = document.getElementById(targetId);
    if (target) {
        target.classList.add('active');
    }
}

function switchLangTab(button, targetId) {
    const wrapper = button.closest('.language-tabs');
    if (!wrapper) return;

    wrapper.querySelectorAll('.lang-tab').forEach(function(btn) {
        btn.classList.remove('active');
    });

    wrapper.querySelectorAll('.lang-content').forEach(function(content) {
        content.classList.remove('active');
    });

    button.classList.add('active');

    const target = document.getElementById(targetId);
    if (target) {
        target.classList.add('active');
    }
}

function copyCode(button) {
    const wrap = button.closest('.code-wrap');
    if (!wrap) return;

    const code = wrap.querySelector('pre');
    if (!code) return;

    navigator.clipboard.writeText(code.innerText).then(function() {
        button.textContent = 'Copied!';
        button.classList.add('copied');

        setTimeout(function() {
            button.textContent = 'Copy';
            button.classList.remove('copied');
        }, 1600);
    });
}

function scrollToSection(id) {
    const element = document.getElementById(id);
    if (!element) return;

    element.scrollIntoView({
        behavior: 'smooth',
        block: 'start'
    });

    document.querySelectorAll('.nav-item').forEach(function(item) {
        item.classList.remove('active');
    });

    if (window.event && window.event.currentTarget) {
        window.event.currentTarget.classList.add('active');
    }
}

function getRuntimeBaseUrl(box) {
    // The Try Out tool must always call the same host where the documentation is opened.
    // Example:
    // https://sandboxapi.logiklu.com/usage  -> https://sandboxapi.logiklu.com
    // https://api.logiklu.com/usage         -> https://api.logiklu.com
    // http://127.0.0.1:8000/usage          -> http://127.0.0.1:8000
    return window.location.origin;
}

function getSavedBearerToken() {
    try {
        return localStorage.getItem('logiklu_usage_access_token') || '';
    } catch (error) {
        return '';
    }
}

function saveBearerToken(token) {
    try {
        localStorage.setItem('logiklu_usage_access_token', token || '');
    } catch (error) {}
}

function clearSavedBearerToken(button) {
    saveBearerToken('');
    document.querySelectorAll('[data-access-token]').forEach(function(input) {
        input.value = '';
    });

    if (button) {
        button.textContent = 'Cleared';
        setTimeout(function() {
            button.textContent = 'Clear Saved Token';
        }, 1200);
    }
}

function applyGeneratedTokenToBearerFields(button) {
    const token = getSavedBearerToken();

    if (!token) {
        alert('No generated token found. Generate a token first.');
        return;
    }

    document.querySelectorAll('[data-access-token]').forEach(function(input) {
        input.value = token;
    });

    if (button) {
        button.textContent = 'Applied';
        setTimeout(function() {
            button.textContent = 'Use Token in This Page';
        }, 1200);
    }
}

function useSavedBearerToken(button) {
    const token = getSavedBearerToken();
    const box = button.closest('.tryout-box');
    const input = box ? box.querySelector('[data-access-token]') : null;

    if (!token) {
        alert('No saved token found. Generate a token from /oauth/token first.');
        return;
    }

    if (input) {
        input.value = token;
    }

    button.textContent = 'Token Applied';
    setTimeout(function() {
        button.textContent = 'Use Saved Token';
    }, 1200);
}

function copyGeneratedToken(button) {
    const box = button.closest('.tryout-box');
    const tokenBox = box ? box.querySelector('[data-generated-token]') : null;
    const token = tokenBox ? tokenBox.value.trim() : getSavedBearerToken();

    if (!token) {
        alert('No token available to copy.');
        return;
    }

    navigator.clipboard.writeText(token).then(function() {
        button.textContent = 'Copied!';
        setTimeout(function() {
            button.textContent = 'Copy Token';
        }, 1200);
    });
}

function buildTryOutUrl(box) {
    let baseUrl = getRuntimeBaseUrl(box);
    let path = box.getAttribute('data-path') || '';
    let method = box.getAttribute('data-method') || 'GET';

    const params = new URLSearchParams();
    const inputs = box.querySelectorAll('[data-param-name]');

    inputs.forEach(function(input) {
        const name = input.getAttribute('data-param-name');
        const value = input.value.trim();

        if (!name || value === '') {
            return;
        }

        const pathToken = '{' + name + '}';

        if (path.includes(pathToken)) {
            path = path.replace(pathToken, encodeURIComponent(value));
        } else if (method === 'GET') {
            params.append(name, value);
        }
    });

    let url = baseUrl.replace(/\/$/, '') + '/' + path.replace(/^\//, '');

    const queryString = params.toString();

    if (queryString) {
        url += '?' + queryString;
    }

    return url;
}

function buildTokenEndpointBody(box) {
    const payload = {};
    const inputs = box.querySelectorAll('[data-body-field]');

    inputs.forEach(function(input) {
        const name = input.getAttribute('data-body-field');
        const value = input.value.trim() || input.getAttribute('placeholder') || '';

        if (name) {
            payload[name] = value;
        }
    });

    if (!payload.grant_type) {
        payload.grant_type = 'client_credentials';
    }

    return payload;
}

function handleTokenGenerationResponse(box, data) {
    let token = '';

    if (data && typeof data === 'object') {
        if (data.access_token) {
            token = data.access_token;
        } else if (data.response && data.response.access_token) {
            token = data.response.access_token;
        } else if (data.data && data.data.access_token) {
            token = data.data.access_token;
        }
    }

    if (!token) {
        return;
    }

    saveBearerToken(token);

    const wrap = box.querySelector('[data-generated-token-wrap]');
    const tokenBox = box.querySelector('[data-generated-token]');

    if (wrap) {
        wrap.style.display = 'block';
    }

    if (tokenBox) {
        tokenBox.value = token;
    }

    document.querySelectorAll('[data-access-token]').forEach(function(input) {
        if (!input.value.trim()) {
            input.value = token;
        }
    });
}

async function sendTryOutRequest(button) {
    const box = button.closest('.tryout-box');

    if (!box) {
        return;
    }

    const responseBox = box.querySelector('[data-try-response]');
    const requestUrlBox = box.querySelector('[data-request-url]');
    const method = box.getAttribute('data-method') || 'GET';
    const authType = box.getAttribute('data-auth-type') || 'bearer';
    const isTokenEndpoint = box.getAttribute('data-token-endpoint') === 'yes';

    const url = buildTryOutUrl(box);

    requestUrlBox.textContent = url;
    responseBox.textContent = 'Loading...';

    const headers = {};

    if (authType === 'bearer') {
        const tokenInput = box.querySelector('[data-access-token]');
        const accessToken = tokenInput ? tokenInput.value.trim() : '';

        if (!accessToken) {
            responseBox.textContent = JSON.stringify({
                status: 'error',
                message: 'Please enter Bearer access token first or generate a token from /oauth/token.'
            }, null, 2);
            return;
        }

        headers['Authorization'] = 'Bearer ' + accessToken;
    } else if (authType === 'api_key') {
        const apiKeyInput = box.querySelector('[data-api-key]');
        const apiKey = apiKeyInput ? apiKeyInput.value.trim() : '';

        if (!apiKey) {
            responseBox.textContent = JSON.stringify({
                status: 'error',
                message: 'Please enter API key first.'
            }, null, 2);
            return;
        }

        headers['X-API-KEY'] = apiKey;
    }

    const options = {
        method: method,
        headers: headers
    };

    if (method !== 'GET') {
        headers['Content-Type'] = 'application/json';

        if (isTokenEndpoint) {
            options.body = JSON.stringify(buildTokenEndpointBody(box));
        } else {
            const bodyBox = box.querySelector('[data-body-json]');
            const bodyText = bodyBox ? bodyBox.value.trim() : '{}';

            try {
                options.body = JSON.stringify(JSON.parse(bodyText || '{}'));
            } catch (error) {
                responseBox.textContent = JSON.stringify({
                    status: 'error',
                    message: 'Invalid JSON body.',
                    detail: error.message
                }, null, 2);
                return;
            }
        }
    }

    try {
        const response = await fetch(url, options);
        const contentType = response.headers.get('content-type') || '';

        let data;

        if (contentType.includes('application/json')) {
            data = await response.json();
        } else {
            data = await response.text();
        }

        responseBox.textContent = JSON.stringify({
            http_status: response.status,
            response: data
        }, null, 2);

        if (isTokenEndpoint && response.ok) {
            handleTokenGenerationResponse(box, data);
        }

    } catch (error) {
        responseBox.textContent = JSON.stringify({
            status: 'error',
            message: 'Request failed.',
            detail: error.message
        }, null, 2);
    }
}
</script>

</body>
</html>
    """

    auth_example = f"""# Step 1: Generate access token - No Auth
POST {base_url}/oauth/token
Content-Type: application/json

{{
  "client_id": "YOUR_CLIENT_ID",
  "client_secret": "YOUR_CLIENT_SECRET",
  "grant_type": "client_credentials"
}}

# Step 2: Use token for protected APIs
GET {base_url}/focus/account-intelligence?page=1&per_page=10
Authorization: Bearer YOUR_ACCESS_TOKEN"""

    if data.get("show_legacy_api_key"):
        auth_example += f"""

# Legacy/backward-compatible API-key authentication
GET {base_url}/focus/account-intelligence?page=1&per_page=10
X-API-KEY: YOUR_API_KEY"""

    page = template
    page = page.replace("{{TITLE}}", esc(data.get("title")))
    page = page.replace("{{SUBTITLE}}", esc(data.get("subtitle")))
    page = page.replace("{{BASE_URL}}", esc(base_url))
    page = page.replace("{{ENV_NAME}}", esc(get_current_environment_name(data)))
    page = page.replace("{{AUTH_BADGE}}", esc(data.get("auth_badge", "OAuth JWT")))
    page = page.replace("{{SIDEBAR}}", render_sidebar(data))
    page = page.replace("{{AUTH_CODE}}", render_code_block(auth_example, "OAuth / JWT Flow"))
    page = page.replace("{{SUCCESS_CODE}}", render_code_block(json.dumps(data.get("response_format", {}).get("success", {}), indent=2), "JSON · Success Response"))
    page = page.replace("{{ERROR_CODE}}", render_code_block(json.dumps(data.get("response_format", {}).get("error", {}), indent=2), "JSON · Error Response"))
    page = page.replace("{{QUICK_START_CODE}}", render_language_tabs("quick-start-example", first_example_code))
    page = page.replace("{{ENVIRONMENTS}}", render_environments(data))
    page = page.replace("{{SECTIONS}}", render_sections(data))
    page = page.replace("{{LOGGING_SECTION}}", render_logging_section(data))
    page = page.replace("{{ERROR_CODES}}", render_error_codes(data))

    return page