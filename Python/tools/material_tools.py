"""
Material Tools for Unreal MCP.

This module provides tools for creating and editing materials via Python in Unreal Engine.
"""

import logging
from typing import Dict, List, Any, Optional
from mcp.server.fastmcp import FastMCP, Context

logger = logging.getLogger("UnrealMCP")

# MaterialProperty mapping: short name -> unreal enum value
MATERIAL_PROPERTIES = {
    "base_color": "MP_BASE_COLOR",
    "metallic": "MP_METALLIC",
    "roughness": "MP_ROUGHNESS",
    "emissive_color": "MP_EMISSIVE_COLOR",
    "opacity": "MP_OPACITY",
    "normal": "MP_NORMAL",
    "ambient_occlusion": "MP_AMBIENT_OCCLUSION",
    "specular": "MP_SPECULAR",
    "world_position_offset": "MP_WORLD_POSITION_OFFSET",
    "subsurface_color": "MP_SUBSURFACE_COLOR",
}


def register_material_tools(mcp: FastMCP):
    """Register material tools with the MCP server."""

    # ----------------------------------------------------------------
    # Material Asset CRUD
    # ----------------------------------------------------------------

    @mcp.tool()
    def create_material(
        ctx: Context, name: str, path: str = "/Game/Materials"
    ) -> Dict[str, Any]:
        """
        Create a new Material asset.

        Args:
            name: Material asset name (e.g. "M_PBR")
            path: Content Browser path (default "/Game/Materials")

        Returns:
            Dict with success status and material path
        """
        from unreal_mcp_server import get_unreal_connection

        try:
            unreal_conn = get_unreal_connection()
            if not unreal_conn:
                return {
                    "success": False,
                    "message": "Failed to connect to Unreal Engine",
                }

            code = f"""
import unreal
tools = unreal.AssetToolsHelpers.get_asset_tools()
mat = tools.create_asset("{name}", "{path}", unreal.Material, unreal.MaterialFactoryNew())
if mat:
    print(f"OK:{{mat.get_path_name()}}")
else:
    print("FAIL:Could not create material")
"""
            response = unreal_conn.send_command("execute_python", {"code": code})
            if not response:
                return {"success": False, "message": "No response from Unreal"}

            result_data = response.get("result", {})
            output = (
                result_data.get("output", "").strip()
                if isinstance(result_data, dict)
                else str(result_data)
            )

            if output.startswith("OK:"):
                return {"success": True, "material_path": output[3:]}
            return {"success": False, "message": output.replace("FAIL:", "")}

        except Exception as e:
            logger.error(f"Error creating material: {e}")
            return {"success": False, "message": str(e)}

    @mcp.tool()
    def delete_material(ctx: Context, material_path: str) -> Dict[str, Any]:
        """
        Delete a Material asset.

        Args:
            material_path: Full asset path (e.g. "/Game/Materials/M_PBR")

        Returns:
            Dict with success status
        """
        from unreal_mcp_server import get_unreal_connection

        try:
            unreal_conn = get_unreal_connection()
            if not unreal_conn:
                return {
                    "success": False,
                    "message": "Failed to connect to Unreal Engine",
                }

            code = f"""
import unreal
asset_path = "{material_path}.{material_path.split("/")[-1]}"
if unreal.EditorAssetLibrary.does_asset_exist(asset_path):
    unreal.EditorAssetLibrary.delete_asset(asset_path)
    print("OK:Deleted")
else:
    print("FAIL:Asset not found")
"""
            response = unreal_conn.send_command("execute_python", {"code": code})
            if not response:
                return {"success": False, "message": "No response from Unreal"}

            result_data = response.get("result", {})
            output = (
                result_data.get("output", "").strip()
                if isinstance(result_data, dict)
                else str(result_data)
            )

            if output.startswith("OK:"):
                return {"success": True}
            return {"success": False, "message": output.replace("FAIL:", "")}

        except Exception as e:
            logger.error(f"Error deleting material: {e}")
            return {"success": False, "message": str(e)}

    # ----------------------------------------------------------------
    # Material Expression Nodes
    # ----------------------------------------------------------------

    @mcp.tool()
    def add_material_scalar_param(
        ctx: Context,
        material_path: str,
        parameter_name: str,
        default_value: float = 0.0,
        connect_to: str = "",
        position: List[int] = None,
    ) -> Dict[str, Any]:
        """
        Add a Scalar Parameter node to a material and optionally connect it to a material property.

        Args:
            material_path: Material asset path (e.g. "/Game/Materials/M_PBR")
            parameter_name: Name of the parameter
            default_value: Default float value
            connect_to: Material property to connect to (e.g. "roughness", "metallic", "opacity", "specular", "ambient_occlusion"). Leave empty to skip connection.
            position: Node position [x, y] in material graph

        Returns:
            Dict with success status
        """
        from unreal_mcp_server import get_unreal_connection

        return _add_material_param(
            unreal_conn_getter=get_unreal_connection,
            material_path=material_path,
            param_type="scalar",
            parameter_name=parameter_name,
            default_value=default_value,
            connect_to=connect_to,
            position=position,
        )

    @mcp.tool()
    def add_material_vector_param(
        ctx: Context,
        material_path: str,
        parameter_name: str,
        default_value: List[float] = None,
        connect_to: str = "",
        position: List[int] = None,
    ) -> Dict[str, Any]:
        """
        Add a Vector Parameter node to a material and optionally connect it to a material property.

        Args:
            material_path: Material asset path (e.g. "/Game/Materials/M_PBR")
            parameter_name: Name of the parameter
            default_value: Default color [r, g, b, a] (0.0-1.0, default [0.5, 0.5, 0.5, 1.0])
            connect_to: Material property to connect to (e.g. "base_color", "emissive_color"). Leave empty to skip.
            position: Node position [x, y] in material graph

        Returns:
            Dict with success status
        """
        from unreal_mcp_server import get_unreal_connection

        if default_value is None:
            default_value = [0.5, 0.5, 0.5, 1.0]
        return _add_material_param(
            unreal_conn_getter=get_unreal_connection,
            material_path=material_path,
            param_type="vector",
            parameter_name=parameter_name,
            default_value=default_value,
            connect_to=connect_to,
            position=position,
        )

    @mcp.tool()
    def add_material_texture_param(
        ctx: Context,
        material_path: str,
        parameter_name: str,
        connect_to: str = "",
        output_name: str = "RGB",
        position: List[int] = None,
    ) -> Dict[str, Any]:
        """
        Add a Texture Sample Parameter 2D node to a material and optionally connect it to a material property.

        Args:
            material_path: Material asset path (e.g. "/Game/Materials/M_PBR")
            parameter_name: Name of the parameter
            connect_to: Material property to connect to (e.g. "normal", "base_color"). Leave empty to skip.
            output_name: Output pin name (default "RGB", use "R"/"G"/"B"/"A" for single channel)
            position: Node position [x, y] in material graph

        Returns:
            Dict with success status
        """
        from unreal_mcp_server import get_unreal_connection

        return _add_material_param(
            unreal_conn_getter=get_unreal_connection,
            material_path=material_path,
            param_type="texture",
            parameter_name=parameter_name,
            connect_to=connect_to,
            output_name=output_name,
            position=position,
        )

    @mcp.tool()
    def add_material_multiply_node(
        ctx: Context,
        material_path: str,
        input_a: str,
        input_b: str,
        connect_to: str = "",
        position: List[int] = None,
    ) -> Dict[str, Any]:
        """
        Add a Multiply node and connect two existing expressions to its A/B inputs, optionally connecting the result to a material property.

        Args:
            material_path: Material asset path
            input_a: Parameter name of the expression connecting to input A
            input_b: Parameter name of the expression connecting to input B
            connect_to: Material property to connect the multiply output to. Leave empty to skip.
            position: Node position [x, y] in material graph

        Returns:
            Dict with success status
        """
        from unreal_mcp_server import get_unreal_connection

        try:
            unreal_conn = get_unreal_connection()
            if not unreal_conn:
                return {
                    "success": False,
                    "message": "Failed to connect to Unreal Engine",
                }

            pos = position or [0, 0]
            connect_code = ""
            if connect_to:
                prop_enum = MATERIAL_PROPERTIES.get(connect_to.lower())
                if not prop_enum:
                    return {
                        "success": False,
                        "message": f"Unknown property '{connect_to}'. Available: {list(MATERIAL_PROPERTIES.keys())}",
                    }
                connect_code = f"mml.connect_material_property(mul, '', unreal.MaterialProperty.{prop_enum})"

            code = f"""
import unreal
mat = unreal.load_asset("{material_path}")
mml = unreal.MaterialEditingLibrary

# Find expressions by parameter name
def find_expr(m, name):
    for e in mml.get_material_expressions(m):
        try:
            if e.get_editor_property("parameter_name") == name:
                return e
        except:
            pass
    return None

expr_a = find_expr(mat, "{input_a}")
expr_b = find_expr(mat, "{input_b}")
if not expr_a:
    print("FAIL:Could not find expression '{input_a}'")
elif not expr_b:
    print("FAIL:Could not find expression '{input_b}'")
else:
    mul = mml.create_material_expression(mat, unreal.MaterialExpressionMultiply, {pos[0]}, {pos[1]})
    mml.connect_material_expressions(expr_a, "", mul, "A")
    mml.connect_material_expressions(expr_b, "", mul, "B")
    {connect_code}
    print("OK:Multiply node created")
"""
            response = unreal_conn.send_command("execute_python", {"code": code})
            if not response:
                return {"success": False, "message": "No response from Unreal"}

            result_data = response.get("result", {})
            output = (
                result_data.get("output", "").strip()
                if isinstance(result_data, dict)
                else str(result_data)
            )

            if output.startswith("OK:"):
                return {"success": True, "message": "Multiply node created"}
            return {"success": False, "message": output.replace("FAIL:", "")}

        except Exception as e:
            logger.error(f"Error adding multiply node: {e}")
            return {"success": False, "message": str(e)}

    @mcp.tool()
    def add_material_expression(
        ctx: Context,
        material_path: str,
        expression_type: str,
        properties: Dict[str, Any] = None,
        connect_to: str = "",
        output_name: str = "",
        position: List[int] = None,
    ) -> Dict[str, Any]:
        """
        Add a generic material expression node with arbitrary properties.

        Args:
            material_path: Material asset path
            expression_type: UE class name without prefix, e.g. "MaterialExpressionAdd", "MaterialExpressionPower", "MaterialExpressionClamp"
            properties: Dict of property_name -> value to set on the expression
            connect_to: Material property to connect to (optional)
            output_name: Output pin name for connection (default "" = first output)
            position: Node position [x, y]

        Returns:
            Dict with success status
        """
        from unreal_mcp_server import get_unreal_connection

        try:
            unreal_conn = get_unreal_connection()
            if not unreal_conn:
                return {
                    "success": False,
                    "message": "Failed to connect to Unreal Engine",
                }

            pos = position or [0, 0]
            props_code = ""
            if properties:
                for k, v in properties.items():
                    if isinstance(v, str):
                        props_code += f'\nexpr.set_editor_property("{k}", "{v}")'
                    elif isinstance(v, (int, float)):
                        props_code += f'\nexpr.set_editor_property("{k}", {v})'
                    elif isinstance(v, list):
                        props_code += f'\nexpr.set_editor_property("{k}", unreal.LinearColor({v[0]}, {v[1]}, {v[2]}, {v[3] if len(v) > 3 else 1.0}))'

            connect_code = ""
            if connect_to:
                prop_enum = MATERIAL_PROPERTIES.get(connect_to.lower())
                if not prop_enum:
                    return {
                        "success": False,
                        "message": f"Unknown property '{connect_to}'. Available: {list(MATERIAL_PROPERTIES.keys())}",
                    }
                connect_code = f"\nmml.connect_material_property(expr, '{output_name}', unreal.MaterialProperty.{prop_enum})"

            code = f"""
import unreal
mat = unreal.load_asset("{material_path}")
mml = unreal.MaterialEditingLibrary
cls = getattr(unreal, "{expression_type}", None)
if not cls:
    print("FAIL:Unknown expression type '{expression_type}'")
else:
    expr = mml.create_material_expression(mat, cls, {pos[0]}, {pos[1]})
    {props_code}
    {connect_code}
    print("OK:Expression created")
"""
            response = unreal_conn.send_command("execute_python", {"code": code})
            if not response:
                return {"success": False, "message": "No response from Unreal"}

            result_data = response.get("result", {})
            output = (
                result_data.get("output", "").strip()
                if isinstance(result_data, dict)
                else str(result_data)
            )

            if output.startswith("OK:"):
                return {"success": True}
            return {"success": False, "message": output.replace("FAIL:", "")}

        except Exception as e:
            logger.error(f"Error adding expression: {e}")
            return {"success": False, "message": str(e)}

    # ----------------------------------------------------------------
    # Connection Helpers
    # ----------------------------------------------------------------

    @mcp.tool()
    def connect_material_property(
        ctx: Context,
        material_path: str,
        parameter_name: str,
        property_name: str,
        output_name: str = "",
    ) -> Dict[str, Any]:
        """
        Connect an existing material expression (by parameter name) to a material property.

        Args:
            material_path: Material asset path
            parameter_name: The parameter_name of the expression to connect from
            property_name: Target material property (e.g. "base_color", "roughness", "normal")
            output_name: Output pin name (default "" = first output, use "RGB" for texture samples)

        Returns:
            Dict with success status
        """
        from unreal_mcp_server import get_unreal_connection

        try:
            unreal_conn = get_unreal_connection()
            if not unreal_conn:
                return {
                    "success": False,
                    "message": "Failed to connect to Unreal Engine",
                }

            prop_enum = MATERIAL_PROPERTIES.get(property_name.lower())
            if not prop_enum:
                return {
                    "success": False,
                    "message": f"Unknown property '{property_name}'. Available: {list(MATERIAL_PROPERTIES.keys())}",
                }

            code = f"""
import unreal
mat = unreal.load_asset("{material_path}")
mml = unreal.MaterialEditingLibrary
for e in mfl.get_material_expressions(mat):
    try:
        if e.get_editor_property("parameter_name") == "{parameter_name}":
            result = mml.connect_material_property(e, "{output_name}", unreal.MaterialProperty.{prop_enum})
            print(f"OK:{{result}}" if result else "FAIL:connect_material_property returned False")
            break
    except:
        pass
else:
    print("FAIL:Expression '{parameter_name}' not found")
"""
            # Fix typo: mfl -> mml
            code = code.replace("mfl.", "mml.")

            response = unreal_conn.send_command("execute_python", {"code": code})
            if not response:
                return {"success": False, "message": "No response from Unreal"}

            result_data = response.get("result", {})
            output = (
                result_data.get("output", "").strip()
                if isinstance(result_data, dict)
                else str(result_data)
            )

            if output.startswith("OK:"):
                return {"success": True}
            return {"success": False, "message": output.replace("FAIL:", "")}

        except Exception as e:
            logger.error(f"Error connecting material property: {e}")
            return {"success": False, "message": str(e)}

    # ----------------------------------------------------------------
    # Compile / Save / Info
    # ----------------------------------------------------------------

    @mcp.tool()
    def compile_and_save_material(ctx: Context, material_path: str) -> Dict[str, Any]:
        """
        Compile and save a material asset.

        Args:
            material_path: Material asset path (e.g. "/Game/Materials/M_PBR")

        Returns:
            Dict with success status
        """
        from unreal_mcp_server import get_unreal_connection

        try:
            unreal_conn = get_unreal_connection()
            if not unreal_conn:
                return {
                    "success": False,
                    "message": "Failed to connect to Unreal Engine",
                }

            code = f"""
import unreal
mat = unreal.load_asset("{material_path}")
if not mat:
    print("FAIL:Material not found")
else:
    mml = unreal.MaterialEditingLibrary
    mml.recompile_material(mat)
    unreal.EditorAssetLibrary.save_asset(mat.get_path_name(), only_if_is_dirty=False)
    print("OK:Compiled and saved")
"""
            response = unreal_conn.send_command("execute_python", {"code": code})
            if not response:
                return {"success": False, "message": "No response from Unreal"}

            result_data = response.get("result", {})
            output = (
                result_data.get("output", "").strip()
                if isinstance(result_data, dict)
                else str(result_data)
            )

            if output.startswith("OK:"):
                return {"success": True}
            return {"success": False, "message": output.replace("FAIL:", "")}

        except Exception as e:
            logger.error(f"Error compiling material: {e}")
            return {"success": False, "message": str(e)}

    @mcp.tool()
    def get_material_info(ctx: Context, material_path: str) -> Dict[str, Any]:
        """
        Get information about a material: parameter names, connections, expression count.

        Args:
            material_path: Material asset path (e.g. "/Game/Materials/M_PBR")

        Returns:
            Dict with material info including scalar_params, vector_params, texture_params, connections
        """
        from unreal_mcp_server import get_unreal_connection

        try:
            unreal_conn = get_unreal_connection()
            if not unreal_conn:
                return {
                    "success": False,
                    "message": "Failed to connect to Unreal Engine",
                }

            code = f"""
import unreal
import json
mat = unreal.load_asset("{material_path}")
if not mat:
    print("FAIL:Material not found")
else:
    mml = unreal.MaterialEditingLibrary
    info = {{
        "path": mat.get_path_name(),
        "scalar_params": mml.get_scalar_parameter_names(mat),
        "vector_params": mml.get_vector_parameter_names(mat),
        "texture_params": mml.get_texture_parameter_names(mat),
        "num_expressions": mml.get_num_material_expressions(mat),
    }}
    # Check connections
    connections = {{}}
    prop_map = {{
        "base_color": unreal.MaterialProperty.MP_BASE_COLOR,
        "metallic": unreal.MaterialProperty.MP_METALLIC,
        "roughness": unreal.MaterialProperty.MP_ROUGHNESS,
        "emissive_color": unreal.MaterialProperty.MP_EMISSIVE_COLOR,
        "opacity": unreal.MaterialProperty.MP_OPACITY,
        "normal": unreal.MaterialProperty.MP_NORMAL,
        "ao": unreal.MaterialProperty.MP_AMBIENT_OCCLUSION,
        "specular": unreal.MaterialProperty.MP_SPECULAR,
    }}
    for name, prop in prop_map.items():
        node = mml.get_material_property_input_node(mat, prop)
        if node:
            out_name = mml.get_material_property_input_node_output_name(mat, prop)
            try:
                pname = node.get_editor_property("parameter_name")
            except:
                pname = node.get_name()
            connections[name] = {{"node": pname, "output": out_name}}
    info["connections"] = connections
    print("JSON:" + json.dumps(info))
"""
            response = unreal_conn.send_command("execute_python", {"code": code})
            if not response:
                return {"success": False, "message": "No response from Unreal"}

            result_data = response.get("result", {})
            output = (
                result_data.get("output", "").strip()
                if isinstance(result_data, dict)
                else str(result_data)
            )

            if output.startswith("JSON:"):
                import json

                info = json.loads(output[5:])
                info["success"] = True
                return info
            return {"success": False, "message": output.replace("FAIL:", "")}

        except Exception as e:
            logger.error(f"Error getting material info: {e}")
            return {"success": False, "message": str(e)}

    @mcp.tool()
    def create_pbr_material(
        ctx: Context,
        name: str,
        path: str = "/Game/Materials",
        base_color: List[float] = None,
        metallic: float = 0.0,
        roughness: float = 0.5,
        emissive_color: List[float] = None,
        emissive_intensity: float = 0.0,
        opacity: float = 1.0,
        include_normal_map: bool = True,
        include_ao: bool = True,
    ) -> Dict[str, Any]:
        """
        Create a complete PBR material with all standard parameters pre-wired.

        Creates: Base Color, Metallic, Roughness, Emissive (Color * Intensity), Opacity,
        Normal Map (texture slot), Ambient Occlusion parameters, all connected and compiled.

        Args:
            name: Material name (e.g. "M_PBR_Metal")
            path: Content Browser path (default "/Game/Materials")
            base_color: Default base color [r, g, b, a] (default [0.8, 0.8, 0.8, 1.0])
            metallic: Default metallic value (default 0.0)
            roughness: Default roughness value (default 0.5)
            emissive_color: Default emissive color [r, g, b, a] (default [0, 0, 0, 1])
            emissive_intensity: Default emissive intensity (default 0.0)
            opacity: Default opacity (default 1.0)
            include_normal_map: Include normal map texture parameter (default True)
            include_ao: Include ambient occlusion parameter (default True)

        Returns:
            Dict with success status and material path
        """
        from unreal_mcp_server import get_unreal_connection

        try:
            unreal_conn = get_unreal_connection()
            if not unreal_conn:
                return {
                    "success": False,
                    "message": "Failed to connect to Unreal Engine",
                }

            if base_color is None:
                base_color = [0.8, 0.8, 0.8, 1.0]
            if emissive_color is None:
                emissive_color = [0.0, 0.0, 0.0, 1.0]

            bc = base_color
            ec = emissive_color

            code = f"""
import unreal
tools = unreal.AssetToolsHelpers.get_asset_tools()
mat = tools.create_asset("{name}", "{path}", unreal.Material, unreal.MaterialFactoryNew())
if not mat:
    print("FAIL:Could not create material")
else:
    mml = unreal.MaterialEditingLibrary

    # Base Color
    p = mml.create_material_expression(mat, unreal.MaterialExpressionVectorParameter, -800, 600)
    p.set_editor_property("parameter_name", "Base Color")
    p.set_editor_property("default_value", unreal.LinearColor({bc[0]}, {bc[1]}, {bc[2]}, {bc[3]}))
    mml.connect_material_property(p, "", unreal.MaterialProperty.MP_BASE_COLOR)

    # Metallic
    p = mml.create_material_expression(mat, unreal.MaterialExpressionScalarParameter, -800, 400)
    p.set_editor_property("parameter_name", "Metallic")
    p.set_editor_property("default_value", {metallic})
    mml.connect_material_property(p, "", unreal.MaterialProperty.MP_METALLIC)

    # Roughness
    p = mml.create_material_expression(mat, unreal.MaterialExpressionScalarParameter, -800, 200)
    p.set_editor_property("parameter_name", "Roughness")
    p.set_editor_property("default_value", {roughness})
    mml.connect_material_property(p, "", unreal.MaterialProperty.MP_ROUGHNESS)

    # Emissive Color * Intensity
    p_emi = mml.create_material_expression(mat, unreal.MaterialExpressionVectorParameter, -800, -200)
    p_emi.set_editor_property("parameter_name", "Emissive Color")
    p_emi.set_editor_property("default_value", unreal.LinearColor({ec[0]}, {ec[1]}, {ec[2]}, {ec[3]}))

    p_int = mml.create_material_expression(mat, unreal.MaterialExpressionScalarParameter, -800, -400)
    p_int.set_editor_property("parameter_name", "Emissive Intensity")
    p_int.set_editor_property("default_value", {emissive_intensity})

    mul = mml.create_material_expression(mat, unreal.MaterialExpressionMultiply, -400, -300)
    mml.connect_material_expressions(p_emi, "", mul, "A")
    mml.connect_material_expressions(p_int, "", mul, "B")
    mml.connect_material_property(mul, "", unreal.MaterialProperty.MP_EMISSIVE_COLOR)

    # Opacity
    p = mml.create_material_expression(mat, unreal.MaterialExpressionScalarParameter, -800, 0)
    p.set_editor_property("parameter_name", "Opacity")
    p.set_editor_property("default_value", {opacity})
    mml.connect_material_property(p, "", unreal.MaterialProperty.MP_OPACITY)
"""
            if include_normal_map:
                code += """
    # Normal Map
    p = mml.create_material_expression(mat, unreal.MaterialExpressionTextureSampleParameter2D, -800, 800)
    p.set_editor_property("parameter_name", "Normal Map")
    mml.connect_material_property(p, "RGB", unreal.MaterialProperty.MP_NORMAL)
"""
            if include_ao:
                code += """
    # Ambient Occlusion
    p = mml.create_material_expression(mat, unreal.MaterialExpressionScalarParameter, -800, -600)
    p.set_editor_property("parameter_name", "Ambient Occlusion")
    p.set_editor_property("default_value", 1.0)
    mml.connect_material_property(p, "", unreal.MaterialProperty.MP_AMBIENT_OCCLUSION)
"""
            code += """
    mml.recompile_material(mat)
    unreal.EditorAssetLibrary.save_asset(mat.get_path_name(), only_if_is_dirty=False)
    print(f"OK:" + mat.get_path_name())
"""
            response = unreal_conn.send_command("execute_python", {"code": code})
            if not response:
                return {"success": False, "message": "No response from Unreal"}

            result_data = response.get("result", {})
            output = (
                result_data.get("output", "").strip()
                if isinstance(result_data, dict)
                else str(result_data)
            )

            if output.startswith("OK:"):
                return {"success": True, "material_path": output[3:]}
            return {"success": False, "message": output.replace("FAIL:", "")}

        except Exception as e:
            logger.error(f"Error creating PBR material: {e}")
            return {"success": False, "message": str(e)}

    logger.info("Material tools registered successfully")


# ----------------------------------------------------------------
# Internal helper
# ----------------------------------------------------------------


def _add_material_param(
    unreal_conn_getter,
    material_path: str,
    param_type: str,
    parameter_name: str,
    default_value=None,
    connect_to: str = "",
    output_name: str = "",
    position: List[int] = None,
) -> Dict[str, Any]:
    """Internal helper to add a parameter expression and optionally connect it."""
    try:
        unreal_conn = unreal_conn_getter()
        if not unreal_conn:
            return {"success": False, "message": "Failed to connect to Unreal Engine"}

        pos = position or [-800, 0]

        # Build expression creation code
        if param_type == "scalar":
            val = default_value if default_value is not None else 0.0
            expr_code = f"""
    expr = mml.create_material_expression(mat, unreal.MaterialExpressionScalarParameter, {pos[0]}, {pos[1]})
    expr.set_editor_property("parameter_name", "{parameter_name}")
    expr.set_editor_property("default_value", {val})
"""
        elif param_type == "vector":
            if default_value is None:
                default_value = [0.5, 0.5, 0.5, 1.0]
            v = default_value
            expr_code = f"""
    expr = mml.create_material_expression(mat, unreal.MaterialExpressionVectorParameter, {pos[0]}, {pos[1]})
    expr.set_editor_property("parameter_name", "{parameter_name}")
    expr.set_editor_property("default_value", unreal.LinearColor({v[0]}, {v[1]}, {v[2]}, {v[3]}))
"""
        elif param_type == "texture":
            expr_code = f"""
    expr = mml.create_material_expression(mat, unreal.MaterialExpressionTextureSampleParameter2D, {pos[0]}, {pos[1]})
    expr.set_editor_property("parameter_name", "{parameter_name}")
"""
        else:
            return {"success": False, "message": f"Unknown param_type: {param_type}"}

        # Build connection code
        connect_code = ""
        if connect_to:
            prop_enum = MATERIAL_PROPERTIES.get(connect_to.lower())
            if not prop_enum:
                return {
                    "success": False,
                    "message": f"Unknown property '{connect_to}'. Available: {list(MATERIAL_PROPERTIES.keys())}",
                }
            out_pin = output_name if output_name else ""
            connect_code = f'\n    mml.connect_material_property(expr, "{out_pin}", unreal.MaterialProperty.{prop_enum})'

        code = f"""
import unreal
mat = unreal.load_asset("{material_path}")
if not mat:
    print("FAIL:Material not found")
else:
    mml = unreal.MaterialEditingLibrary
{expr_code}{connect_code}
    print("OK:Parameter added")
"""
        response = unreal_conn.send_command("execute_python", {"code": code})
        if not response:
            return {"success": False, "message": "No response from Unreal"}

        result_data = response.get("result", {})
        output = (
            result_data.get("output", "").strip()
            if isinstance(result_data, dict)
            else str(result_data)
        )

        if output.startswith("OK:"):
            return {"success": True, "message": f"Parameter '{parameter_name}' added"}
        return {"success": False, "message": output.replace("FAIL:", "")}

    except Exception as e:
        logger.error(f"Error adding material param: {e}")
        return {"success": False, "message": str(e)}
