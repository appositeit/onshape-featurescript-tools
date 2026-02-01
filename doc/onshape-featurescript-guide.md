# Onshape FeatureScript Development Guide

Guide for developing, deploying, and debugging custom FeatureScript features via the Onshape REST API. Written based on practical experience building the Box Panelise feature.

## Directory Layout

```
.
├── featurescripts/
│   └── box_panelise.fs      # FeatureScript source files
├── deploy.py                # CLI tool to push .fs to Onshape
├── doc/                     # This guide
├── pyproject.toml           # Python package config
├── setup.sh                 # Quick setup script
└── onshape_client_config.example.yaml
```

## API Credentials

### Setup

1. Sign in to [Onshape](https://cad.onshape.com)
2. Click your user icon (top right) > **My Account** > **Developer**
3. Click **Create new API key** (ensure Write access is enabled)
4. Copy both keys immediately (the secret key is only shown once)
5. Save to `~/.onshape_client_config.yaml`:

```yaml
default_stack: onshape
onshape:
  base_url: https://cad.onshape.com
  access_key: YOUR_ACCESS_KEY
  secret_key: YOUR_SECRET_KEY
```

### Authentication Methods

**Basic Auth** (used by `deploy.py`): Base64-encode `access_key:secret_key` and pass as `Authorization: Basic <encoded>` header. Simple, works for all endpoints.

**HMAC Auth** (used by `onshape_dxf_exporter`): Signs each request with a nonce, timestamp, and HMAC-SHA256 digest. More secure, required by some enterprise setups. See `~/laser/onshape_dxf_exporter/src/onshape_dxf_exporter/client.py` for implementation.

### Key Permissions

API keys can be read-only or read-write. FeatureScript deployment requires **write access**. If you get `403 Invalid API key state`, regenerate the key with write permissions.

## FeatureScript Basics

### Language Version

Every `.fs` file starts with a version declaration and standard imports:

```featurescript
FeatureScript 1511;
import(path : "onshape/std/common.fs", version : "1511.0");
import(path : "onshape/std/geometry.fs", version : "1511.0");
```

The version number (1511) corresponds to the Onshape library version. Use whatever version the Feature Studio shows when created through the UI. This number increments as Onshape releases updates.

### Feature Structure

```featurescript
annotation { "Feature Type Name" : "My Feature" }
export const myFeature = defineFeature(function(context is Context, id is Id, definition is map)
    precondition
    {
        // UI parameter definitions go here
        annotation { "Name" : "Select body", "Filter" : EntityType.BODY && BodyType.SOLID, "MaxNumberOfPicks" : 1 }
        definition.body is Query;

        annotation { "Name" : "Some length" }
        isLength(definition.length, LENGTH_BOUNDS);

        annotation { "Name" : "Some toggle", "Default" : true }
        definition.toggle is boolean;
    }
    {
        // Feature body — actual geometry operations
    },
    {
        // Default parameter values
        length : 3 * millimeter,
        toggle : true
    });
```

### Parameter Types

| Type | Precondition | Annotation |
|------|-------------|------------|
| Query (body/face) | `definition.x is Query` | `"Filter" : EntityType.BODY && BodyType.SOLID` |
| Length | `isLength(definition.x, BOUNDS)` | Just `"Name"` |
| Boolean | `definition.x is boolean` | `"Default" : true` |
| Integer | `isInteger(definition.x, BOUNDS)` | Just `"Name"` |
| Enum | `definition.x is MyEnum` | Just `"Name"` |

### Length Bounds Spec

```featurescript
export const MY_BOUNDS = {
    (meter)      : [0.0005, 0.003, 0.05],   // [min, default, max]
    (centimeter) : 0.3,                       // default only
    (millimeter) : 3,                         // default only
    (inch)       : 0.125                      // default only
} as LengthBoundSpec;
```

The first entry (meter) defines min/default/max. Other entries are display defaults for those unit systems.

### Common Operations

```featurescript
// Query faces
var faces = qOwnedByBody(body, EntityType.FACE);
var planarFaces = qGeometry(faces, GeometryType.PLANE);
var faceArray = evaluateQuery(context, planarFaces);

// Get face geometry
var plane = evPlane(context, { "face" : someFace });
var area = evArea(context, { "entities" : someFace });

// Bounding box
var bbox = evBox3d(context, { "topology" : body, "tight" : true });

// Extract surface and thicken
opExtractSurface(context, id + "extract", { "faces" : faceQuery });
opThicken(context, id + "thicken", {
    "entities" : qCreatedBy(id + "extract", EntityType.BODY),
    "thickness1" : 3 * millimeter,
    "thickness2" : 0 * meter
});

// Delete bodies
opDeleteBodies(context, id + "delete", { "entities" : bodyQuery });

// Union multiple queries
var combined = qUnion([query1, query2, query3]);

// Error handling
try { /* operation */ }
catch (error) { reportFeatureWarning(context, id, "Something failed"); }

// Fatal error
throw regenError("Bad input", ["parameterName"]);
```

### Gotchas

- **No construction geometry on bodies**: `setProperty` with `PropertyType.CONSTRUCTION` only works on sketch entities, not solid bodies. To hide a body, delete it or leave it for the user to hide manually.
- **Id construction**: Use `id + "name"` for unique sub-operation IDs. For loops, use `id + ("name" ~ i)` where `i` is the index.
- **Value with units**: Always initialize with units: `0 * meter`, not `0`. Arithmetic on values requires matching units.
- **No mutation**: Variables are immutable by default. Use `var` for mutable. Arrays are replaced, not mutated in place: `arr = append(arr, item)`.
- **evaluateQuery returns transient queries**: The face/body queries returned are only valid in the current regen cycle. Don't store them across feature boundaries.

## Deploying FeatureScript

### deploy.py

Push a `.fs` file to a Feature Studio in Onshape:

```bash
cd ~/development/onshape

# Deploy to default target (Box Panelise Feature Studio in ATX Case doc)
python3 deploy.py box_panelise.fs

# Deploy to a specific Feature Studio by URL
python3 deploy.py my_feature.fs --url "https://cad.onshape.com/documents/DID/w/WID/e/EID"

# Deploy to specific IDs
python3 deploy.py my_feature.fs -d DOCUMENT_ID -w WORKSPACE_ID -e ELEMENT_ID
```

The script:
1. Reads the `.fs` file from disk
2. GETs the current Feature Studio to obtain `sourceMicroversion`
3. POSTs the updated source code
4. Reports any compilation errors/warnings with line numbers

### API Endpoints

All endpoints are under `https://cad.onshape.com/api/v6`.

| Operation | Method | Path |
|-----------|--------|------|
| List document elements | GET | `/documents/d/{did}/w/{wid}/elements` |
| Get Feature Studio source | GET | `/featurestudios/d/{did}/w/{wid}/e/{eid}` |
| Update Feature Studio source | **POST** | `/featurestudios/d/{did}/w/{wid}/e/{eid}` |
| Get Feature Studio specs | GET | `/featurestudios/d/{did}/w/{wid}/e/{eid}/specs` |
| List Part Studio features | GET | `/partstudios/d/{did}/w/{wid}/e/{eid}/features` |
| Add feature to Part Studio | POST | `/partstudios/d/{did}/w/{wid}/e/{eid}/features` |
| Update feature in Part Studio | POST | `/partstudios/d/{did}/w/{wid}/e/{eid}/features/featureid/{fid}` |
| Get parts list | GET | `/parts/d/{did}/w/{wid}/e/{eid}` |
| Get mass properties | GET | `/partstudios/d/{did}/w/{wid}/e/{eid}/massproperties` |
| Eval FeatureScript | POST | `/partstudios/d/{did}/w/{wid}/e/{eid}/featurescript` |
| Get bounding boxes | GET | `/partstudios/d/{did}/w/{wid}/e/{eid}/boundingboxes` |

**Key gotcha**: Updating a Feature Studio uses **POST**, not PUT. PUT returns 405. There is no `/contents` suffix on the path.

### Update Payload

```json
{
  "btType": "BTFeatureStudioContents-2239",
  "contents": "FeatureScript 1511;\nimport(...",
  "serializationVersion": "1.2.15",
  "sourceMicroversion": "abc123...",
  "rejectMicroversionSkew": false
}
```

The `sourceMicroversion` must come from a prior GET of the Feature Studio. Setting `rejectMicroversionSkew: false` avoids conflicts if someone else edited the document.

## Adding Features to Part Studios via API

### Namespace Format

When adding a custom feature to a Part Studio, the namespace tells Onshape which Feature Studio defines the feature.

**Same document**: `e{elementId}::m{microversionId}`
```
eba8829e72e3df0405808b342::mbc14c06c02d00d2873fa00e9
```

**Cross-document** (published version): `d{documentId}::v{versionId}::e{elementId}::m{microversionId}`

The microversion ID changes on every edit to the Feature Studio. Get the current one from the Feature Studio GET response.

### Adding a Feature

```json
POST /partstudios/d/{did}/w/{wid}/e/{eid}/features

{
  "btType": "BTFeatureDefinitionCall-1406",
  "feature": {
    "btType": "BTMFeature-134",
    "featureType": "boxPanelise",
    "name": "Box Panelise 1",
    "namespace": "eba8829e72e3df0405808b342::mXXXXXXXXXXXXXXXXXXXXXXXX",
    "parameters": [
      {
        "btType": "BTMParameterQueryList-148",
        "parameterId": "body",
        "queries": [{
          "btType": "BTMIndividualQuery-138",
          "queryString": "query=qCreatedBy(makeId(\"FeatureId\"),EntityType.BODY);"
        }]
      },
      {
        "btType": "BTMParameterQuantity-147",
        "parameterId": "thickness",
        "expression": "3 mm"
      },
      {
        "btType": "BTMParameterBoolean-144",
        "parameterId": "keepOriginal",
        "value": true
      }
    ]
  }
}
```

### Query Strings

To reference geometry created by another feature:
```
query=qCreatedBy(makeId("FufBE3nT7uH8hCW_0"),EntityType.BODY);
```

The feature ID (e.g. `FufBE3nT7uH8hCW_0`) comes from the features list response.

## Debugging FeatureScript

### evalFeatureScript Endpoint

Run arbitrary FeatureScript in the context of a Part Studio:

```json
POST /partstudios/d/{did}/w/{wid}/e/{eid}/featurescript

{
  "btType": "BTFeatureScriptEvalCall-2377",
  "script": "function(context is Context, queries is map) { var faces = evaluateQuery(context, qEverything(EntityType.FACE)); return { \"faceCount\" : size(faces) }; }"
}
```

The response contains the return value under `result.message.value`. This is invaluable for debugging — you can inspect geometry, count entities, check planes, etc. without modifying the Feature Studio.

### Feature States

After adding/updating features, check `featureStates` in the features response:
- `OK` — feature regenerated successfully
- `ERROR` — runtime error (check feature notices for details)
- `INFO` — informational warnings (feature still works)

### Common Debug Pattern

1. Deploy `.fs` with `deploy.py`
2. Check compilation errors in deploy output
3. If runtime ERROR, use `evalFeatureScript` to test individual operations
4. Isolate which operation fails by testing incrementally

## Onshape Document Structure

```
Document
├── Part Studio (elementType: PARTSTUDIO)
│   ├── Features (sketches, extrudes, custom features...)
│   └── Parts (the resulting solid bodies)
├── Assembly (elementType: ASSEMBLY)
├── Feature Studio (elementType: FEATURESTUDIO)
│   └── FeatureScript source code
├── Blob (elementType: BLOB) — uploaded files (images, etc.)
└── Bill of Materials (elementType: BILLOFMATERIALS)
```

Each element has an `id` (element ID, `eid`). The document has a `did`, and the workspace has a `wid`. These three IDs appear in every Onshape URL:
```
https://cad.onshape.com/documents/{did}/w/{wid}/e/{eid}
```

## Included FeatureScripts

### Box Panelise (`featurescripts/box_panelise.fs`)

Decomposes a solid body into overlapping flat panels for laser cutting.

**Parameters:**
- `body` — solid body to panelise
- `thickness` — material thickness (default 3mm)
- `keepOriginal` — keep original body visible (default true)

**Algorithm:**
1. Get all planar faces of the body
2. Group faces by normal direction (tolerance 0.001)
3. For each normal group, find the outermost plane (furthest from body centroid)
4. Collect all face fragments on that outermost plane (handles cutouts)
5. Extract surfaces and thicken inward by material thickness

**Deploy:**
```bash
deploy-featurescript featurescripts/box_panelise.fs --url "https://cad.onshape.com/documents/.../w/.../e/..."
```

## References

- [FeatureScript Language Reference](https://cad.onshape.com/FsDoc/)
- [Onshape REST API Explorer](https://cad.onshape.com/glassworks/explorer)
- Onshape API Keys: sign in to [cad.onshape.com](https://cad.onshape.com), user icon > My Account > Developer
- [FeatureScript Standard Library Source](https://cad.onshape.com/documents/12312312345abcabcabcdeff) (search "onshape-std-library" in public documents)
- [Laser Joint FeatureScript](https://cad.onshape.com/documents/578830e4e4b0e65410f9c34e/w/14918498c2d2dd64c3b253e9/e/dfd5effddfd7f2ecce4b0246) by @lemon1324
