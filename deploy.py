#!/usr/bin/env python3
"""Deploy a FeatureScript file to an Onshape Feature Studio via the REST API.

Usage:
    deploy-featurescript <file.fs> --url <onshape-url>
    deploy-featurescript <file.fs> -d DID -w WID -e EID

Reads credentials from ~/.onshape_client_config.yaml
"""

import argparse
import base64
import json
import sys
import urllib.request
import urllib.error
from pathlib import Path

import yaml

CONFIG_PATH = Path.home() / ".onshape_client_config.yaml"


def load_credentials():
    """Load API credentials from ~/.onshape_client_config.yaml"""
    if not CONFIG_PATH.exists():
        print(
            f"Error: credentials file not found: {CONFIG_PATH}\n"
            f"Copy onshape_client_config.example.yaml to {CONFIG_PATH} and add your API keys.\n"
            f"Get keys at: https://cad.onshape.com (My Account > Developer)",
            file=sys.stderr,
        )
        sys.exit(1)

    with open(CONFIG_PATH) as f:
        config = yaml.safe_load(f)

    stack = config.get("default_stack", "onshape")
    stack_config = config[stack]

    access_key = stack_config["access_key"]
    secret_key = stack_config["secret_key"]
    base_url = stack_config.get("base_url", "https://cad.onshape.com")

    if "YOUR_" in access_key or "YOUR_" in secret_key:
        print(
            f"Error: placeholder API keys detected in {CONFIG_PATH}\n"
            f"Replace YOUR_ACCESS_KEY_HERE and YOUR_SECRET_KEY_HERE with your actual keys.\n"
            f"Get keys at: https://cad.onshape.com (My Account > Developer)",
            file=sys.stderr,
        )
        sys.exit(1)

    creds = base64.b64encode(f"{access_key}:{secret_key}".encode()).decode()
    return base_url, creds


def api_request(base_url, creds, method, path, body=None):
    """Make an authenticated Onshape API request."""
    url = f"{base_url}/api/v6{path}"
    data = json.dumps(body).encode() if body else None

    req = urllib.request.Request(
        url,
        data=data,
        method=method,
        headers={
            "Authorization": f"Basic {creds}",
            "Accept": "application/json",
            "Content-Type": "application/json",
        },
    )

    try:
        resp = urllib.request.urlopen(req)
        return resp.status, json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        body_text = e.read().decode()
        try:
            return e.code, json.loads(body_text)
        except json.JSONDecodeError:
            return e.code, {"message": body_text}


def get_feature_studio_contents(base_url, creds, did, wid, eid):
    """GET the current contents of a Feature Studio."""
    path = f"/featurestudios/d/{did}/w/{wid}/e/{eid}"
    return api_request(base_url, creds, "GET", path)


def update_feature_studio_contents(base_url, creds, did, wid, eid, source, source_microversion):
    """POST updated contents to a Feature Studio."""
    path = f"/featurestudios/d/{did}/w/{wid}/e/{eid}"
    body = {
        "btType": "BTFeatureStudioContents-2239",
        "contents": source,
        "serializationVersion": "1.2.15",
        "sourceMicroversion": source_microversion,
        "rejectMicroversionSkew": False,
    }
    return api_request(base_url, creds, "POST", path, body)


def parse_document_url(url):
    """Parse an Onshape document URL into did, wid, eid.

    Accepts URLs like:
        https://cad.onshape.com/documents/{did}/w/{wid}/e/{eid}
    """
    parts = url.rstrip("/").split("/")
    try:
        did = parts[parts.index("documents") + 1]
        wid = parts[parts.index("w") + 1]
        eid = parts[parts.index("e") + 1]
    except (ValueError, IndexError):
        print(
            f"Error: could not parse Onshape URL: {url}\n"
            f"Expected format: https://cad.onshape.com/documents/DID/w/WID/e/EID",
            file=sys.stderr,
        )
        sys.exit(1)
    return did, wid, eid


def main():
    parser = argparse.ArgumentParser(
        description="Deploy a FeatureScript file to an Onshape Feature Studio",
        epilog="Example: deploy-featurescript box_panelise.fs --url https://cad.onshape.com/documents/.../w/.../e/...",
    )
    parser.add_argument("file", help="Path to .fs file to deploy")
    parser.add_argument("--url", "-u", help="Onshape Feature Studio URL")
    parser.add_argument("--document-id", "-d", help="Document ID")
    parser.add_argument("--workspace-id", "-w", help="Workspace ID")
    parser.add_argument("--element-id", "-e", help="Feature Studio element ID")
    args = parser.parse_args()

    if args.url:
        did, wid, eid = parse_document_url(args.url)
    elif args.document_id and args.workspace_id and args.element_id:
        did, wid, eid = args.document_id, args.workspace_id, args.element_id
    else:
        parser.error("Provide either --url or all of --document-id, --workspace-id, --element-id")

    # Read the FeatureScript source
    fs_path = Path(args.file)
    if not fs_path.exists():
        print(f"Error: file not found: {fs_path}", file=sys.stderr)
        sys.exit(1)

    source = fs_path.read_text()
    print(f"Read {len(source)} chars from {fs_path}")

    # Load credentials
    base_url, creds = load_credentials()
    print(f"Using API at {base_url}")

    # Get current contents to obtain sourceMicroversion
    print("Getting current Feature Studio contents...")
    status, data = get_feature_studio_contents(base_url, creds, did, wid, eid)
    if status != 200:
        msg = data.get("message", data)
        if status == 403:
            print(
                f"Error: access denied (HTTP 403). Your API key may be read-only.\n"
                f"Regenerate it with Write permissions at: https://cad.onshape.com (My Account > Developer)",
                file=sys.stderr,
            )
        else:
            print(f"Error getting contents (HTTP {status}): {msg}", file=sys.stderr)
        sys.exit(1)

    source_microversion = data["sourceMicroversion"]
    print(f"Current microversion: {source_microversion}")

    # Update contents
    print("Deploying FeatureScript...")
    status, data = update_feature_studio_contents(base_url, creds, did, wid, eid, source, source_microversion)
    if status != 200:
        print(f"Error deploying (HTTP {status}): {data.get('message', data)}", file=sys.stderr)
        sys.exit(1)

    # Check for notices (compilation errors/warnings)
    notices = data.get("notices", [])

    if notices:
        print(f"\nFeatureScript compilation returned {len(notices)} notice(s):")
        for notice in notices:
            level = notice.get("level", "INFO")
            msg = notice.get("message", "")
            line = notice.get("startLineNumber", "?")
            print(f"  [{level}] line {line}: {msg}")

        errors = [n for n in notices if n.get("level") == "ERROR"]
        if errors:
            print(f"\n{len(errors)} error(s) found. Feature will not work until fixed.", file=sys.stderr)
            sys.exit(1)
    else:
        print("Deployed successfully. No compilation errors.")

    print(f"New microversion: {data.get('sourceMicroversion', 'unknown')}")


if __name__ == "__main__":
    main()
