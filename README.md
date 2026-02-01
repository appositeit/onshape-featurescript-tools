# Onshape FeatureScript Tools

Custom FeatureScript features for Onshape CAD, with a command-line deployment tool. Designed for laser cutting workflows.

## Features

### Box Panelise

Decomposes a solid body into separate overlapping flat panels for laser cutting. The panels overlap at corners, ready for the [Laser Joint](https://cad.onshape.com/documents/578830e4e4b0e65410f9c34e/w/14918498c2d2dd64c3b253e9/e/dfd5effddfd7f2ecce4b0246) feature (AUTO mode) to create finger joints.

**Parameters:**
- **Body to panelise** — select a solid body
- **Material thickness** — panel thickness (default 3mm, range 0.5mm–50mm)
- **Keep original body** — keep the original solid visible (default: on)

**How it works:**
1. Groups all planar faces by normal direction
2. For each direction, selects the outermost plane (ignoring cutout recesses)
3. Collects all face fragments on that plane (preserving cutout holes)
4. Extracts each face group as a surface and thickens it inward

Works on any convex solid with planar faces — not just rectangular boxes. Cutouts and holes in faces are preserved in the panels.

### Deploy Tool

Command-line tool to push `.fs` files to Onshape Feature Studios via the REST API. No more copy/pasting FeatureScript source in the browser.

## Installation

### Prerequisites

- Python 3.8+
- An [Onshape](https://cad.onshape.com) account (free or paid)
- Onshape API keys (see [API Keys](#api-keys) below)

### Quick Start

```bash
git clone <this-repo>
cd onshape-featurescript-tools

# Set up virtual environment and install dependencies
./setup.sh

# Configure API keys
cp onshape_client_config.example.yaml ~/.onshape_client_config.yaml
# Edit the file with your API keys (see below)
```

### Manual Setup

If you prefer not to use the setup script:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

## API Keys

The deploy tool authenticates with Onshape using API key pairs.

### Getting API Keys

1. Sign in to [Onshape](https://cad.onshape.com)
2. Click your user icon (top right) > **My Account**
3. Go to the **Developer** section
4. Click **Create new API key**
5. Give it a name (e.g. "FeatureScript Deploy")
6. Under permissions, ensure **Write** access is enabled (read-only keys cannot deploy)
7. Click **Create**
8. **Copy both the Access Key and Secret Key immediately** — the secret key is only shown once

### Saving API Keys

Create `~/.onshape_client_config.yaml`:

```yaml
default_stack: onshape
onshape:
  base_url: https://cad.onshape.com
  access_key: YOUR_ACCESS_KEY_HERE
  secret_key: YOUR_SECRET_KEY_HERE
```

An example config file is included as `onshape_client_config.example.yaml`.

**Security notes:**
- Never commit your actual API keys to version control
- The config file should only be readable by your user: `chmod 600 ~/.onshape_client_config.yaml`
- If a key is compromised, delete it immediately in My Account > Developer and create a new one

## Usage

### Deploying FeatureScript

First, create a Feature Studio in your Onshape document (right-click in the tab bar, "Create Feature Studio").

Then deploy a `.fs` file to it:

```bash
# Activate the virtual environment
source .venv/bin/activate

# Deploy to a Feature Studio by URL
deploy-featurescript featurescripts/box_panelise.fs \
  --url "https://cad.onshape.com/documents/YOUR_DOC_ID/w/YOUR_WORKSPACE_ID/e/YOUR_ELEMENT_ID"

# Or specify IDs directly
deploy-featurescript featurescripts/box_panelise.fs \
  -d DOCUMENT_ID -w WORKSPACE_ID -e ELEMENT_ID
```

The tool will:
1. Read the `.fs` source file
2. Push it to the Feature Studio via the Onshape API
3. Report any compilation errors with line numbers

After deploying, the feature appears in the Part Studio's feature menu (under the Feature Studio's name).

### Using Box Panelise in Onshape

1. Deploy `box_panelise.fs` to a Feature Studio in your document
2. Open a Part Studio containing a solid body
3. Click the feature menu and select **Box Panelise**
4. Select the solid body, set material thickness
5. Click the green checkmark
6. Apply **Laser Joint** (AUTO mode) to the resulting panels for finger joints

## Project Structure

```
.
├── featurescripts/
│   └── box_panelise.fs      # FeatureScript source files
├── deploy.py                 # Deployment tool source
├── doc/
│   └── onshape-featurescript-guide.md  # Development guide
├── pyproject.toml            # Python package config
├── setup.sh                  # Quick setup script
└── onshape_client_config.example.yaml  # Example API config
```

## Development Guide

See [doc/onshape-featurescript-guide.md](doc/onshape-featurescript-guide.md) for detailed documentation on:
- FeatureScript language reference and gotchas
- Onshape REST API endpoints
- Debugging with `evalFeatureScript`
- Namespace format for custom features
- Adding features to Part Studios programmatically

## License

MIT License. See [LICENSE](LICENSE).
