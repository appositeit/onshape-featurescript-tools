# Onshape Laser Tools

Design, export, convert, and cut — a complete pipeline from Onshape CAD to laser cutter.

## Pipeline Overview

```
Onshape CAD         DXF File           G-code File        Laser Cutter
┌──────────┐       ┌──────────┐       ┌──────────┐       ┌──────────┐
│ Design   │──────>│  Export  │──────>│ Convert  │──────>│  Upload  │
│ + Panel  │ DXF   │  .dxf    │ G-code│  .gcode  │ WiFi  │  + Cut   │
│ + Joint  │Export  │          │       │          │       │          │
└──────────┘       └──────────┘       └──────────┘       └──────────┘
 Box Panelise      onshape_dxf_       dxf2gcode          fluidnc-upload
 Laser Joint       exporter*
 deploy-featurescript
```

\* DXF export uses [onshape_dxf_exporter](https://github.com/Verusio/onshape_dxf_exporter) (separate install).

## Tools Included

| Tool | Purpose | Install |
|------|---------|---------|
| **Box Panelise** | FeatureScript: decompose solid into overlapping flat panels | Add to Onshape toolbar |
| **deploy-featurescript** | Push `.fs` files to Onshape Feature Studios via REST API | `pip install -e .` |
| **dxf2gcode** | Convert DXF files to laser cutting G-code | `pip install -e .` |
| **fluidnc-upload** | Upload G-code to FluidNC controllers over WiFi | `pip install -e .` |

## Quick Start

### 1. Use Box Panelise in Onshape (no install needed)

Add it directly to your Onshape toolbar:

1. Open any Part Studio in Onshape
2. Right-click the feature toolbar > **Add custom features**
3. Paste this URL:
   ```
   https://cad.onshape.com/documents/d5cbe7ac763a9b5cd7157012/v/36a761cffd49e0b3cc803485/e/bb4062cf99d0ba6b42abdeac
   ```
4. Select **Box Panelise** and click **Add**

### 2. Install CLI Tools

```bash
git clone https://github.com/appositeit/onshape-featurescript-tools.git
cd onshape-featurescript-tools

# Set up virtual environment and install
./setup.sh

# Or manually:
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

### 3. Configure Onshape API Keys

Required only for `deploy-featurescript`. See [API Keys](#api-keys) below.

## Box Panelise

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

Works on any convex solid with planar faces. Cutouts and holes are preserved in the panels.

**Typical workflow:**
1. Model your enclosure as a solid body in Onshape
2. Add cutouts (ventilation holes, ports, etc.)
3. Apply **Box Panelise** to create panels
4. Apply **Laser Joint** (AUTO mode) to all panels for finger joints
5. Export each panel face as DXF for laser cutting

## deploy-featurescript

Push FeatureScript `.fs` files to Onshape Feature Studios via the REST API.

```bash
# Deploy by URL (copy from browser address bar)
deploy-featurescript featurescripts/box_panelise.fs \
  --url "https://cad.onshape.com/documents/DOC_ID/w/WORKSPACE_ID/e/ELEMENT_ID"

# Or specify IDs directly
deploy-featurescript featurescripts/box_panelise.fs \
  -d DOCUMENT_ID -w WORKSPACE_ID -e ELEMENT_ID
```

The tool reads the `.fs` source, pushes it to the Feature Studio, and reports any compilation errors with line numbers.

## dxf2gcode

Convert DXF files to G-code for laser cutting. Supports LINE, CIRCLE, ARC, and LWPOLYLINE entities.

```bash
# Basic conversion
dxf2gcode panel.dxf

# Set laser power and feed rate
dxf2gcode panel.dxf -o panel.gcode -p 800 -f 3000

# With header/footer for machine startup/shutdown
dxf2gcode panel.dxf --header examples/gcode/header.gcode --footer examples/gcode/footer.gcode
```

**Options:**
- `-o, --output` — Output file (default: `<input>.gcode`)
- `-p, --power` — Laser power S value (default: 1000)
- `-f, --feed` — Feed rate in mm/min (default: 6000)
- `-r, --rapid` — Rapid travel rate in mm/min (default: 6000)
- `--header` — G-code file to prepend (machine startup sequence)
- `--footer` — G-code file to append (machine shutdown sequence)
- `--no-header` — Skip header even if specified
- `--no-footer` — Skip footer even if specified

### Header and Footer Templates

Example templates are provided in `examples/gcode/`. Customise these for your machine:

**header.gcode** — Machine startup (units, positioning, safety):
```gcode
G21         ; Set units to millimeters
G90         ; Absolute positioning
M5 S0       ; Ensure laser is off
G0 F6000    ; Set rapid travel speed
G1 F1000    ; Set default cutting speed
```

**footer.gcode** — Machine shutdown (laser off, return home):
```gcode
M5          ; Turn off laser
G0 X0 Y0    ; Return to home position
M2          ; End program
```

The templates include notes on FluidNC `$HTTP=` commands for IoT integration (e.g. triggering Home Assistant to control cooling, ventilation, or air assist).

## fluidnc-upload

Upload G-code files to a [FluidNC](https://github.com/bdring/FluidNC) controller (ESP32-based CNC/laser controller) over WiFi.

```bash
# Upload to FluidNC on the local network
fluidnc-upload panel.gcode --host 192.168.1.100

# Upload multiple files
fluidnc-upload *.gcode --host laser.local

# Upload to flash instead of SD card
fluidnc-upload panel.gcode --host 192.168.1.100 --flash
```

**Options:**
- `--host` — FluidNC hostname or IP (default: localhost)
- `--port` — FluidNC port (default: 80)
- `--flash` — Upload to flash filesystem instead of SD card

The tool automatically replaces existing files with the same name on the controller.

## DXF Export from Onshape

To export DXF files from Onshape, use [onshape_dxf_exporter](https://github.com/Verusio/onshape_dxf_exporter). It exports individual part faces as DXF files via the Onshape API — useful for getting laser-ready 2D profiles from your 3D parts.

Install it separately:
```bash
pip install onshape_dxf_exporter
```

## API Keys

Required for `deploy-featurescript` and `onshape_dxf_exporter`.

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

An example config is included as `onshape_client_config.example.yaml`.

**Security notes:**
- Never commit your actual API keys to version control
- Set file permissions: `chmod 600 ~/.onshape_client_config.yaml`
- If a key is compromised, delete it in My Account > Developer and create a new one

## Project Structure

```
.
├── featurescripts/
│   └── box_panelise.fs               # FeatureScript source
├── deploy.py                          # FeatureScript deployment tool
├── dxf2gcode.py                       # DXF to G-code converter
├── fluidnc_upload.py                  # FluidNC file uploader
├── examples/
│   └── gcode/
│       ├── header.gcode               # Machine startup template
│       └── footer.gcode               # Machine shutdown template
├── doc/
│   └── onshape-featurescript-guide.md # FeatureScript development guide
├── pyproject.toml                     # Python package config
├── setup.sh                           # Quick setup script
├── onshape_client_config.example.yaml # Example API config
└── LICENSE                            # MIT License
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
