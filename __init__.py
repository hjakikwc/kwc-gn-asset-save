# KWC GN Asset Save (C)2026 Hayano
#
# ##### BEGIN GPL LICENSE BLOCK #####
#
# This program is free software:
# you can redistribute it and/or modify it under the terms of
# the GNU General Public License as published by the Free Software Foundation,
# either version 3 of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY;
# without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
# See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along with this program.
# If not, see <https://www.gnu.org/licenses/>.
#
# ##### END GPL LICENCE BLOCK #####

"""Save a selected Geometry Nodes tree into an Asset Library as a clean .blend."""

from __future__ import annotations

import os
import re
from pathlib import Path

import bpy
from bpy.props import (
    BoolProperty,
    EnumProperty,
    StringProperty,
)
from bpy.types import AddonPreferences, Operator, Panel


_MANIFEST_PATH = Path(__file__).with_name("blender_manifest.toml")
_INVALID_FILENAME = re.compile(r'[<>:"/\\|?*\x00-\x1f]+')


def _read_addon_version() -> str:
    try:
        for line in _MANIFEST_PATH.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if stripped.startswith("version") and "=" in stripped:
                return stripped.split("=", 1)[1].strip().strip('"').strip("'")
    except OSError:
        pass
    return "?.?.?"


ADDON_VERSION = _read_addon_version()
PANEL_CATEGORY = "KWC"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _is_geometry_node_tree(nt: bpy.types.NodeTree) -> bool:
    return getattr(nt, "bl_idname", "") == "GeometryNodeTree"


def _geometry_node_trees() -> list[bpy.types.NodeTree]:
    return [nt for nt in bpy.data.node_groups if _is_geometry_node_tree(nt)]


def _safe_filename(name: str) -> str:
    cleaned = name.replace(" ", "_")
    cleaned = _INVALID_FILENAME.sub("_", cleaned).strip(" .")
    return cleaned or "GeometryNodes"


def _asset_library_items(self, context):
    prefs = context.preferences.filepaths
    items = []
    for i, lib in enumerate(prefs.asset_libraries):
        label = lib.name or f"Library {i + 1}"
        path = lib.path or "(no path)"
        items.append((str(i), label, path))
    if not items:
        items.append(("-1", "(No Asset Libraries)", "Add one in Preferences > File Paths"))
    return items


def _node_tree_items(self, context):
    trees = _geometry_node_trees()
    items = [(nt.name, nt.name, nt.name) for nt in trees]
    if not items:
        items.append(("", "(No Geometry Node trees)", ""))
    return items


def _default_tree_name(context) -> str:
    space = getattr(context, "space_data", None)
    edit_tree = getattr(space, "edit_tree", None) if space else None
    if edit_tree and _is_geometry_node_tree(edit_tree):
        return edit_tree.name

    obj = context.object
    if obj is not None:
        for mod in obj.modifiers:
            if mod.type == "NODES" and getattr(mod, "node_group", None):
                return mod.node_group.name

    trees = _geometry_node_trees()
    return trees[0].name if trees else ""


def _resolve_library(context, library_index: str):
    prefs = context.preferences.filepaths
    try:
        index = int(library_index)
    except (TypeError, ValueError):
        return None
    if index < 0 or index >= len(prefs.asset_libraries):
        return None
    return prefs.asset_libraries[index]


def _collect_nested_groups(root: bpy.types.NodeTree) -> set[bpy.types.NodeTree]:
    """Collect nested node groups for reporting; write() expands them itself."""
    found: set[bpy.types.NodeTree] = set()
    stack = [root]
    while stack:
        tree = stack.pop()
        if tree in found:
            continue
        found.add(tree)
        for node in tree.nodes:
            child = getattr(node, "node_tree", None)
            if child is not None and child not in found:
                stack.append(child)
    return found


# ---------------------------------------------------------------------------
# Preferences
# ---------------------------------------------------------------------------


class KWC_GNAS_AddonPreferences(AddonPreferences):
    bl_idname = __package__

    default_library: EnumProperty(
        name="Default Asset Library",
        description="Pre-selected Asset Library when opening the save dialog",
        items=_asset_library_items,
    )
    default_subfolder: StringProperty(
        name="Default Subfolder",
        description="Optional subfolder under the selected Asset Library path",
        default="",
    )
    mark_nested_groups: BoolProperty(
        name="Mark Nested Groups as Assets",
        description="Also mark nested node groups as assets (can clutter the library)",
        default=False,
    )
    keep_marks_in_current_file: BoolProperty(
        name="Keep Asset Marks in Current File",
        description="Leave Mark as Asset on the trees in this file after export",
        default=True,
    )
    compress: BoolProperty(
        name="Compress .blend",
        description="Write a compressed blend file",
        default=True,
    )

    def draw(self, context):
        layout = self.layout
        layout.label(text=f"KWC GN Asset Save  v{ADDON_VERSION}")
        layout.prop(self, "default_library")
        layout.prop(self, "default_subfolder")
        layout.prop(self, "mark_nested_groups")
        layout.prop(self, "keep_marks_in_current_file")
        layout.prop(self, "compress")


def _prefs(context) -> KWC_GNAS_AddonPreferences:
    return context.preferences.addons[__package__].preferences


# ---------------------------------------------------------------------------
# Operator
# ---------------------------------------------------------------------------


class KWC_GNAS_OT_save_to_library(Operator):
    bl_idname = "kwc_gn_asset_save.save_to_library"
    bl_label = "Save Geometry Nodes to Asset Library"
    bl_description = (
        "Write only the selected Geometry Nodes tree (plus its dependencies) "
        "into a .blend under an Asset Library folder, marked as an asset"
    )
    bl_options = {"REGISTER"}

    node_tree_name: EnumProperty(
        name="Geometry Nodes",
        description="Geometry Nodes tree to export",
        items=_node_tree_items,
    )
    library_index: EnumProperty(
        name="Asset Library",
        description="Destination Asset Library (Preferences > File Paths)",
        items=_asset_library_items,
    )
    subfolder: StringProperty(
        name="Subfolder",
        description="Optional folder under the Asset Library path",
        default="",
    )
    filename: StringProperty(
        name="File Name",
        description="Output .blend file name (without path)",
        default="",
        subtype="FILE_NAME",
    )
    mark_nested_groups: BoolProperty(
        name="Mark Nested Groups as Assets",
        default=False,
    )
    keep_marks_in_current_file: BoolProperty(
        name="Keep Asset Marks in Current File",
        default=True,
    )
    compress: BoolProperty(
        name="Compress .blend",
        default=True,
    )
    overwrite: BoolProperty(
        name="Overwrite Existing",
        description="Replace the destination file if it already exists",
        default=False,
    )

    def invoke(self, context, event):
        prefs = _prefs(context)
        self.library_index = prefs.default_library
        self.subfolder = prefs.default_subfolder
        self.mark_nested_groups = prefs.mark_nested_groups
        self.keep_marks_in_current_file = prefs.keep_marks_in_current_file
        self.compress = prefs.compress

        default_name = _default_tree_name(context)
        if default_name:
            self.node_tree_name = default_name
            if not self.filename:
                self.filename = _safe_filename(default_name)

        return context.window_manager.invoke_props_dialog(self, width=420)

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False

        layout.prop(self, "node_tree_name")
        layout.prop(self, "library_index")
        layout.prop(self, "subfolder")
        layout.prop(self, "filename")

        col = layout.column(heading="Options")
        col.prop(self, "mark_nested_groups")
        col.prop(self, "keep_marks_in_current_file")
        col.prop(self, "compress")
        col.prop(self, "overwrite")

        lib = _resolve_library(context, self.library_index)
        box = layout.box()
        if lib is None:
            box.label(text="No Asset Library selected", icon="ERROR")
        else:
            dest = self._destination_path(lib)
            box.label(text="Destination:", icon="ASSET_MANAGER")
            box.label(text=dest)

    def _destination_path(self, lib) -> str:
        name = _safe_filename(self.filename or self.node_tree_name or "GeometryNodes")
        if not name.lower().endswith(".blend"):
            name = f"{name}.blend"
        parts = [lib.path]
        sub = (self.subfolder or "").strip().strip("/\\")
        if sub:
            parts.append(sub)
        parts.append(name)
        return os.path.normpath(os.path.join(*parts))

    def execute(self, context):
        lib = _resolve_library(context, self.library_index)
        if lib is None or not lib.path:
            self.report({"ERROR"}, "Asset Library is not configured (Preferences > File Paths)")
            return {"CANCELLED"}

        tree = bpy.data.node_groups.get(self.node_tree_name)
        if tree is None or not _is_geometry_node_tree(tree):
            self.report({"ERROR"}, "Geometry Nodes tree not found")
            return {"CANCELLED"}

        filepath = self._destination_path(lib)
        if os.path.exists(filepath) and not self.overwrite:
            self.report(
                {"ERROR"},
                f"File already exists (enable Overwrite): {filepath}",
            )
            return {"CANCELLED"}

        dest_dir = os.path.dirname(filepath)
        try:
            os.makedirs(dest_dir, exist_ok=True)
        except OSError as exc:
            self.report({"ERROR"}, f"Cannot create folder: {exc}")
            return {"CANCELLED"}

        nested = _collect_nested_groups(tree)
        to_mark = set(nested) if self.mark_nested_groups else {tree}
        previously_assets = {nt for nt in to_mark if nt.asset_data is not None}

        for nt in to_mark:
            if nt.asset_data is None:
                nt.asset_mark()

        try:
            # libraries.write expands nested groups / linked deps automatically.
            bpy.data.libraries.write(
                filepath,
                {tree},
                fake_user=True,
                compress=self.compress,
            )
        except Exception as exc:  # noqa: BLE001 - surface Blender write errors
            self.report({"ERROR"}, f"Write failed: {exc}")
            return {"CANCELLED"}
        finally:
            if not self.keep_marks_in_current_file:
                for nt in to_mark:
                    if nt not in previously_assets and nt.asset_data is not None:
                        nt.asset_clear()

        nested_count = max(0, len(nested) - 1)
        self.report(
            {"INFO"},
            f"Saved '{tree.name}' (+{nested_count} nested) → {filepath}",
        )
        return {"FINISHED"}


# ---------------------------------------------------------------------------
# UI
# ---------------------------------------------------------------------------


class KWC_GNAS_PT_panel(Panel):
    bl_label = "GN Asset Save"
    bl_idname = "KWC_GNAS_PT_panel"
    bl_space_type = "NODE_EDITOR"
    bl_region_type = "UI"
    bl_category = PANEL_CATEGORY

    @classmethod
    def poll(cls, context):
        space = context.space_data
        return space is not None and space.tree_type == "GeometryNodeTree"

    def draw(self, context):
        layout = self.layout
        tree = getattr(context.space_data, "edit_tree", None)

        col = layout.column(align=True)
        if tree is not None:
            col.label(text=tree.name, icon="NODETREE")
        else:
            col.label(text="No active Geometry Nodes tree", icon="INFO")

        layout.operator(
            KWC_GNAS_OT_save_to_library.bl_idname,
            icon="ASSET_MANAGER",
            text="Save to Asset Library…",
        )


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------


classes = (
    KWC_GNAS_AddonPreferences,
    KWC_GNAS_OT_save_to_library,
    KWC_GNAS_PT_panel,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
