/*
    Box Panelise

    Takes a solid body and decomposes it into separate overlapping flat panels
    suitable for laser cutting. The panels overlap at corners, ready for the
    Laser Joint feature (AUTO mode) to create finger joints.

    Version 1.0 - 2026-02-01 - Initial implementation
*/

FeatureScript 1511;
import(path : "onshape/std/common.fs", version : "1511.0");
import(path : "onshape/std/geometry.fs", version : "1511.0");

export const MATERIAL_THICKNESS_BOUNDS =
{
    (meter)      : [0.0005, 0.003, 0.05],
    (centimeter) : 0.3,
    (millimeter) : 3,
    (inch)       : 0.125
} as LengthBoundSpec;

annotation { "Feature Type Name" : "Box Panelise" }
export const boxPanelise = defineFeature(function(context is Context, id is Id, definition is map)
    precondition
    {
        annotation { "Name" : "Body to panelise",
                     "Filter" : EntityType.BODY && BodyType.SOLID,
                     "MaxNumberOfPicks" : 1 }
        definition.body is Query;

        annotation { "Name" : "Material thickness" }
        isLength(definition.thickness, MATERIAL_THICKNESS_BOUNDS);

        annotation { "Name" : "Keep original body", "Default" : true }
        definition.keepOriginal is boolean;
    }
    {
        // Get all planar faces of the selected body
        var allFaces = qOwnedByBody(definition.body, EntityType.FACE);
        var planarFaces = qGeometry(allFaces, GeometryType.PLANE);

        var faceArray = evaluateQuery(context, planarFaces);

        if (size(faceArray) < 4)
        {
            throw regenError("Body must have at least 4 planar faces to panelise.", ["body"]);
        }

        // Compute the centroid of the body's bounding box to determine inward direction
        var bbox = evBox3d(context, {
                "topology" : definition.body,
                "tight" : true
        });
        var bodyCentroid = (bbox.minCorner + bbox.maxCorner) / 2;

        // Group faces by normal direction, keeping only the largest face per direction.
        // This filters out cutout side-faces and internal faces, leaving only the
        // main outer wall faces.
        var normalTolerance = 0.001; // dot product threshold for "same direction"
        var normalGroups = []; // array of { normal, faces[] }

        for (var i = 0; i < size(faceArray); i += 1)
        {
            var face = faceArray[i];
            var facePlane = evPlane(context, { "face" : face });
            var normal = facePlane.normal;

            // Find if this normal matches an existing group
            var foundGroup = false;
            for (var g = 0; g < size(normalGroups); g += 1)
            {
                var groupNormal = normalGroups[g].normal;
                // Check if normals are parallel (same direction)
                var d = dot(normal, groupNormal);
                if (abs(d - 1.0) < normalTolerance)
                {
                    normalGroups[g].faces = append(normalGroups[g].faces, face);
                    foundGroup = true;
                    break;
                }
            }

            if (!foundGroup)
            {
                normalGroups = append(normalGroups, { "normal" : normal, "faces" : [face] });
            }
        }

        if (size(normalGroups) < 4)
        {
            throw regenError("Body must have at least 4 distinct face directions to panelise.", ["body"]);
        }

        // For each normal group, find the outermost plane and collect ALL faces on it.
        // This ensures a wall with cutouts gets all its fragments selected, while
        // recessed cutout-bottom faces (on a different plane) are excluded.
        var panelFaceGroups = []; // array of { faces[], normal }
        var planeTolerance = 0.0001 * meter; // tolerance for "same plane offset"

        for (var g = 0; g < size(normalGroups); g += 1)
        {
            var groupNormal = normalGroups[g].normal;
            var faces = normalGroups[g].faces;

            // Compute plane offset for each face (distance from origin along normal)
            var offsets = [];
            for (var f = 0; f < size(faces); f += 1)
            {
                var facePlane = evPlane(context, { "face" : faces[f] });
                var offset = dot(facePlane.origin, groupNormal);
                offsets = append(offsets, offset);
            }

            // Find the outermost offset (furthest from centroid along normal)
            var centroidOffset = dot(bodyCentroid, groupNormal);
            var outermostOffset = offsets[0];
            for (var f = 1; f < size(offsets); f += 1)
            {
                if (abs(offsets[f] - centroidOffset) > abs(outermostOffset - centroidOffset))
                {
                    outermostOffset = offsets[f];
                }
            }

            // Collect all faces at the outermost offset
            var outerFaces = [];
            for (var f = 0; f < size(faces); f += 1)
            {
                if (abs(offsets[f] - outermostOffset) < planeTolerance)
                {
                    outerFaces = append(outerFaces, faces[f]);
                }
            }

            panelFaceGroups = append(panelFaceGroups, {
                "faces" : outerFaces,
                "normal" : groupNormal
            });
        }

        var numPanels = size(panelFaceGroups);

        // For each panel face group, extract all faces and thicken inward
        for (var i = 0; i < numPanels; i += 1)
        {
            var faces = panelFaceGroups[i].faces;

            // Get the plane from the first face in the group
            var facePlane = evPlane(context, {
                    "face" : faces[0]
            });

            // Determine inward direction: compare face normal with vector from
            // face origin to body centroid
            var toCentroid = bodyCentroid - facePlane.origin;
            var dotProduct = dot(toCentroid, facePlane.normal);

            // Set thickness on the side that points inward
            var thickness1 = 0 * meter;
            var thickness2 = 0 * meter;
            if (dotProduct > 0)
            {
                thickness1 = definition.thickness;
            }
            else
            {
                thickness2 = definition.thickness;
            }

            // Extract all faces in this group as surface bodies
            // Use qUnion to pass all face fragments for this wall
            var faceQuery = faces[0];
            for (var f = 1; f < size(faces); f += 1)
            {
                faceQuery = qUnion([faceQuery, faces[f]]);
            }
            opExtractSurface(context, id + ("extract" ~ i), {
                    "faces" : faceQuery
            });

            // Thicken the extracted surface into a solid panel
            try
            {
                opThicken(context, id + ("thicken" ~ i), {
                        "entities" : qCreatedBy(id + ("extract" ~ i), EntityType.BODY),
                        "thickness1" : thickness1,
                        "thickness2" : thickness2
                });
            }
            catch (error)
            {
                // If thicken fails, clean up the extracted surface and continue
                opDeleteBodies(context, id + ("cleanupFail" ~ i), {
                        "entities" : qCreatedBy(id + ("extract" ~ i), EntityType.BODY)
                });
                reportFeatureWarning(context, id, "Could not create panel for face " ~ i);
                continue;
            }

            // Delete the intermediate surface body (opThicken creates a new solid,
            // but the original sheet may still exist)
            var sheetBodies = qCreatedBy(id + ("extract" ~ i), EntityType.BODY)
                              ->qBodyType(BodyType.SHEET);
            if (size(evaluateQuery(context, sheetBodies)) > 0)
            {
                opDeleteBodies(context, id + ("cleanupSheet" ~ i), {
                        "entities" : sheetBodies
                });
            }
        }

        // Handle the original body
        if (!definition.keepOriginal)
        {
            opDeleteBodies(context, id + "deleteOriginal", {
                    "entities" : definition.body
            });
        }
    },
    {
        // Default values
        thickness : 3 * millimeter,
        keepOriginal : true
    });
