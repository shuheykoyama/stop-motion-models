# Repository Instructions

## Purpose

This repository contains procedurally generated, 3D-printable props for stop-motion animation. Each motif has seven physical variants representing a continuous visual transformation. Reverse playback is handled during video editing, not by generating additional models.

The current motifs are a deforming capped marker, a pebble-relief sheet, and a cup with changing wall thickness.

- Consult `docs/specification.md` for motif-specific dimensions and design decisions when it exists.
- Keep temporary plans and frequently changing specifications out of this file.

## Environment and Tooling

### Blender

- Target **Blender 4.5 LTS** and its Python API (`bpy`).
- Verify the installed Blender version before using version-specific APIs.
- Use **Blender MCP** for interactive scene inspection and operations when available.
- Keep geometry generation reproducible through Blender Python scripts independently of MCP.
- Ensure the MCP add-on is installed and enabled in the active Blender 4.5 environment, not only in an older Blender installation.
- Execute `bpy` scripts using Blender's bundled Python, for example `blender --background --python scripts/pen.py`.
- Do not assume `bpy` is available in the project's uv virtual environment.
- Do not modify Blender's bundled Python environment without approval.

### Python and Dependencies

- Use **mise exclusively for Python runtime version management**.
- Treat `mise.toml` as the source of truth for the project's Python version.
- Use **uv** for project dependencies, virtual environments, lockfiles, and Python command execution.
- Use `uv run` for project Python scripts and checks.
- Use `uv add` and `uv remove` to manage dependencies.
- Use `uvx` for isolated Python CLI tools.
- When creating or recreating the project environment, use the Python interpreter provided by mise. Prefer `UV_PYTHON_PREFERENCE=only-system uv sync --python "$(mise which python)"`.
- Maintain `pyproject.toml` and `uv.lock`. Commit dependency lockfile changes when authorized.
- Do not create `.python-version`; Python version selection belongs to mise.
- Never commit `.venv/`.
- Do not use bare `pip`, Poetry, Conda, or another dependency manager for this project.
- Add dependencies only when justified by actual requirements. Avoid unnecessary tools and packages.

### Blender MCP

- Treat Blender MCP as an external Codex tool, separate from the project's uv environment.
- Use its existing uvx-based configuration when available.
- Prefer the mise-managed Python interpreter when configuring Python for MCP, but do not silently modify existing MCP registrations.
- Do not change MCP installation paths, permissions, or safety settings without approval.
- Report connection or compatibility problems rather than bypassing restrictions.

## Workflow and Ownership

- Store reproducible model generators in `scripts/`.
- Store editable Blender scenes (`.blend`) in `models/`.
- Store exported STL files in `exports/`.
- Store rendered previews and visual comparisons in `previews/`.
- Treat Python generators as the source of truth for script-generated geometry.
- Expose meaningful shape parameters and use fixed random seeds where randomness is needed.
- Generate all seven variants of each motif from one shared procedural definition.
- Maintain consistent coordinates, orientation, reference surfaces, and unchanged features across variants to prevent visible jumps during stop-motion playback.
- Prefer Blender built-ins and straightforward Python implementations.
- Follow **KISS, YAGNI, and DRY**. Avoid speculative abstractions, unnecessary frameworks, and premature optimization.
- Preserve hand-edited and user-authored assets. Regenerate only known script-owned outputs within the requested scope; ask before overwriting files with unclear provenance.

## Print-Ready Geometry

- Target FDM printing on a **Bambu Lab X1 Carbon**.
- Limit the workflow to model generation, validation, previews, and export. The user handles slicing, printer operation, and physical testing.
- Express all physical dimensions in **millimeters**.
- STL does not encode units. Export vertex coordinates at millimeter scale and verify the resulting bounding-box dimensions.
- Produce one independently printable, connected, closed solid per intended model.
- Apply relevant modifiers before export.
- Ensure surface relief and deformation exist as actual geometry, not only as material, shader, or bump-map effects.
- Validate changed STL outputs for dimensions, watertight/manifold status, face orientation, degenerate faces, and disconnected components.
- Check self-intersections and minimum feature thickness when suitable validation methods are available.
- Do not claim that printability is guaranteed or physically tested.
- Explicitly report failed, unavailable, or inconclusive validation checks.

## Stop-Motion Previews and Exports

- Name variants consistently as `frame-01` through `frame-07`.
- Maintain a stable coordinate system and consistent reference position for every variant of a motif.
- Use consistent camera position, framing, scale, and lighting for visual comparisons.
- Default to an elevated oblique camera angle unless a task specifies otherwise.
- Prioritize visual continuity between consecutive frames.
- Export only the variants requested for the current task.
- After geometry changes, inspect relevant previews and validate the corresponding exported STL files.
- Report output paths, measured dimensions, validation results, and unresolved issues.

## Boundaries

- Do not operate Bambu Studio, send print jobs, or control printer hardware unless explicitly requested.
- Do not disable Blender MCP safety controls or bypass agent security restrictions.
- Do not silently modify local development environment settings.
- Do not commit or push changes without explicit authorization.
- Do not delete user-authored files or overwrite assets with unclear provenance without approval.
- Keep temporary implementation instructions and motif-specific requirements in task descriptions or specification documents, not in this file.
