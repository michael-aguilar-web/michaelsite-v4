# Avatar prototype

`avatar-v12.blend` is the current local Blender scene. The homepage loads its
export at `public/models/avatar.glb?v=12`. Previous scenes and their frozen
turnarounds remain available locally for comparison. No changes are deployed
until the user requests a commit and push.

The repository includes the finished v12 Blender scene, its turnaround, the
reference and logo, and modeling/export scripts. Earlier scenes, savepoints,
and generated validation data stay local. A fresh checkout can edit and export
v12 directly; replaying older modeling passes requires their local input files.

`concept.png` is the approved reference sheet. `bean-logo.jpg` is the supplied,
unchanged hoodie artwork. The logo is embedded as a texture in the GLB, without
extruded lettering. Reference boards and guide objects are excluded from the
web export. All work in this pass was performed locally.

## Accepted save point

V6 is preserved at `savepoints/v6`, including the editable scene, self-contained
GLB, turnaround and rotation renders, and its two modeling scripts. The
`manifest.json` records their SHA-256 hashes. The original `avatar-v6.blend`
and `avatar-v6.glb` also remain unchanged. Save points are local and ignored by
Git; saving this checkpoint did not create a commit.

## Twelfth pass: remove sleeve seam artifacts

- Preserve v11 at `savepoints/v11` with its scene, export, renders, source,
  and a SHA-256 manifest.
- Remove the four thin decorative sleeve strips. Their partially embedded
  surfaces created doubled and broken seam lines during rotation.
- Keep every remaining mesh, material assignment, UV, and transform identical
  to v11, including the refined sleeve and hood shapes and accepted head.
- Check all 24 garment angles and the established reference views.

`clean-avatar-seams.py` reads v11 and writes v12. `refinement-v12.json`
checks preservation during editing; `preservation-v12.json` checks all 16
retained parts independently from the rendered geometry.
`validation/shoulder-details-v11-v12.png` compares the result with v11.

## Eleventh pass: shoulders and full rotation

- Preserve v10 at `savepoints/v10`, including its model, render, modeling
  script, and homepage files with a SHA-256 manifest.
- Round the sleeves forward and join them to the torso as one closed fabric
  surface. Fit fine seams to that surface instead of overlapping sleeve parts.
- Center the hood on the back, soften its folded edge, and arch the lower
  edge over the shoulder caps. Fit the outer cloth around the shoulders while
  retaining their rounded shape.
- Preserve all nine head and facial meshes exactly. Keep the supplied logo
  artwork and UVs unchanged, reseating the print on the refined torso.
- Validate reference views, both rear shoulder transitions, and close-ups
  at 24 angles around the spin. Keep the homepage's framing and interactions.

`refine-avatar-shoulders.py` reads v10 and builds v11. The paired comparison is
`validation/shoulder-details-v10-v11.png`. Full clothing checks are shown in
`validation/clothing-front-v11.png` and `clothing-rear-v11.png`.
`preservation-v11.json` independently checks the rendered head geometry;
`refinement-v11.json` checks the continuous garment topology and logo UVs.
`clothing-contact-v11.json` locates hood/shirt joins around the turntable.
These intersection samples are diagnostics, not a claim that all intentional
overlap inside the layered neckline has been removed.

## Tenth pass: hoodie

- Preserve the accepted v9 in `savepoints/v9`, including the scene, GLB,
  renders, hair scripts, and a SHA-256 manifest.
- Lock the entire head, hair, face, ears, body, sleeves, logo, and their
  materials. Only the hood, drawstrings, and cord tips change.
- Round the front V and shoulder rim, broaden the hanging rear panel, and
  roll its outside down from the neckline. Add a faint curved rear seam.
- Embed both drawstring roots inside the collar and curve the cords onto
  the chest. Move their rounded caps to the hanging ends.
- Compare fixed reference views and a full rotation, and verify the locked
  parts independently from the geometry written by the renderer.

`refine-avatar-hoodie.py` starts from v9 and writes v10. Its report verifies
that each root is buried deeper than the cord radius. The separate
`validation/preservation-v10.json` checks that all 15 locked parts retain
identical vertices and faces. `validation/hoodie-details-v9-v10.png` compares
the reference, saved v9, and refined v10 at the same framing.

## Ninth pass: hair detail

- Preserve v8 in `savepoints/v8`, with its scene, GLB, renders, modeling script,
  and SHA-256 manifest. The original v8 files remain unchanged.
- Fill the recess under the left swept fringe with a rounded solid backing,
  joined into the cap. This softens the abrupt side step without remeshing
  the accepted front surface.
- Add five tapered swept forms and shallow grooves to the side and back.
  The relief is mesh geometry, so it works in the existing web viewer.
- Lock the front-facing vertices, and constrain new relief to remain inside
  the saved front silhouettes. Keep the face, ears, head, hoodie, materials,
  and logo unchanged.

`detail-avatar-hair.py` starts from v8 and uses `avatar-side-fillet.py` to build
v9. `validation/hair-details-v8-v9.png` compares the front, left side, and back.
`validation/front-preservation-v9.json` measures the two protected front views.

## Eighth pass: sides and nape

- Preserve v7 in `savepoints/v7`, including its scene, GLB, renders, scripts,
  and a SHA-256 manifest. The original v7 files remain unchanged as well.
- Lock the geometry visible from the straight-on and approved portrait views.
  Determine visibility against the whole avatar, including the face and ears.
- Smooth the skull behind the ears into the neck and soften the hidden cap
  and fringe roots. Carry the lower hair with the skull deformation so the
  two surfaces keep their existing fit and shell thickness.
- Continue the hairline behind the ears along the skull into the nape, covering
  the exposed scalp bulge, and round the resulting transition.
- Keep ears, facial marks, clothing, cowlicks, and the visible fringe intact.

`refine-avatar-back.py` always starts from v7 and writes v8. The separate
`refine-avatar-hair.py` script still reconstructs v7 from v6. All earlier
models and scripts remain available as save points.

`validation/refinement-v8.json` checks that the protected vertices did not
move. `validation/front-preservation-v8.json` compares both front silhouettes
with v7; the few changed edge pixels are under 0.1% of the hair mask.
`validation/ear-transitions-v7-v8.png` shows the front and both rear-side angles.

## Seventh pass: hair

- Trace the swept fringe as curved outlines that turn back at the tips, keeping
  the narrow notches lost by a per-column silhouette.
- Taper the edge thickness and fit the locks' depth against the forehead.
- Apply the same depth shaping to the supporting cap to keep the surface
  continuous where the fringe joins it.
- Restore the small swept crown lip and give the longer flick a fuller curve.
- Retain the v6 head, face, clothing, materials, and skull-fitting nape.

`refine-avatar-hair.py` starts from v6 and saves v7. The version-specific hair
builder is `avatar-hair-v7.py`; the previous modeling scripts are untouched.

## Sixth pass: side profile

- Replace the pinched rear skull with a continuous cheek-to-neck profile,
  retaining the front hemisphere and facial landmarks.
- Rebuild the hair cap with its lower rim fitted directly to the skull, so
  both side views keep a connected nape rather than an overhanging shell.
- Smooth the transition between the front fringe and the side cap.
- Check the three reference views and eight positions around a full rotation.

The sixth pass starts from the preserved v5 scene. Its fitted cap is an opt-in
mode in `avatar-surface-details.py`; rebuilding v5 still uses its original mode.

## Fifth pass

- Fit the face and clothing with a smooth deformation cage and measured masks.
- Lift the traced front hair outline onto a curved surface and join it to a
  rounded rear volume. Refine the nape and smooth the crown connection.
- Align the eye line, smile, and ear placement with the portrait reference.
- Rebuild the collar with a shallower front fold and a hanging rear hood.
- Match the smaller, lower logo placement and round the drawstring ends.
- Adjust the skin, hair, and hoodie materials against the reference renders.

The front reference is the main target; the side and rear views constrain depth
and proportion. The result remains a modeled interpretation of the generated
concept, rather than an exact reconstruction of an existing 3D asset.

## Validation

`validation/hoodie-details-v11-v12.png` compares the reference, v11, and v12
using identical camera positions. `validation/rotation-v12.png` shows eight
actual Blender renders. `turnaround-v12.png` is the current three-view render. Earlier evidence remains
available under its original filenames.

The JSON reports in `validation` record silhouette overlap, mesh integrity,
export bounds, and GLB checks. Overlap measures visible regions, not artistic
fidelity. The hair is one closed surface; the GLB embeds its single logo image
and has no external image, camera, or reference-board dependencies. Browser
lighting can differ from the studio renders.

## Rebuild

Run from the repository root with Blender 5.2:

```sh
/Applications/Blender.app/Contents/MacOS/Blender --background --python-exit-code 1 --python scripts/clean-avatar-seams.py
/Applications/Blender.app/Contents/MacOS/Blender --background --python-exit-code 1 --python scripts/export-avatar.py -- v12
/Applications/Blender.app/Contents/MacOS/Blender --background --python-exit-code 1 --python scripts/render-avatar-validation.py -- v12 --rotation --extra-angles=120,240
/Applications/Blender.app/Contents/MacOS/Blender --background --python-exit-code 1 --python scripts/render-avatar-clothing.py -- v12
/Applications/Blender.app/Contents/MacOS/Blender --background --python-exit-code 1 --python scripts/render-avatar-turnaround.py -- v12
```

The current seam cleanup starts from `avatar-v11.blend`. The shoulder pass
starts from `avatar-v10.blend`; the earlier hoodie
pass starts from v9. The earlier hair-detail
pass starts from v8; the side refinement starts from v7; the fringe refinement starts from v6.
`fix-avatar-profile.py` reconstructs v6 from v5; the earlier
`refine-avatar.py` reconstructs v5 from v4 and its frozen fitted vertices.
The export command writes a local draft, `avatar-v12.glb`; it does not replace
the public model automatically.

`scripts/compare-avatar.py v8 v9` rebuilds the comparison sheets with Python,
NumPy, and Pillow. `scripts/compare-avatar-transitions.py v8 v9 --hair` generates the
front/side/back comparisons, rotation sheet, and front-preservation measurements.
`scripts/fit-avatar-silhouettes.py` contains the fitting code and
uses the small C++ rasterizer in `scripts/avatar-raster.cpp`. Earlier modeling
passes are retained in their original scripts.

Rebuilding replaces the corresponding local scene and renders. Save manual
Blender edits under another filename first. Background scripts leave other
open Blender scenes alone.

## Homepage behavior

The existing model-viewer controls remain: horizontal dragging, automatic
rotation with a three-second restart delay, reduced-motion handling, and the
original portrait fallback. Click, tap, or Space toggles the photo and model;
each transition resets the model to face forward. Holding still reveals the
hidden wiki; moving more than six pixels cancels the hold. Enter also reveals
the wiki, while arrow keys rotate the model.
