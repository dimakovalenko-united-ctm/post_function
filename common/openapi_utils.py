#!/usr/bin/env python
from typing import List, Dict
import os
import copy
import re

def update_refs(obj):
    """
    Recursively updates all $ref references from #/components/schemas to #/definitions.
    Removes unsupported keywords like 'anyOf'.
    """
    if isinstance(obj, dict):
        # Create a list of keys to modify
        keys_to_modify = []
        for key, value in obj.items():
            if key == "$ref" and value.startswith("#/components/schemas"):
                obj[key] = value.replace("#/components/schemas", "#/definitions")
            elif key == "anyOf":
                # Mark the 'anyOf' key for removal
                keys_to_modify.append(key)
            else:
                update_refs(value)
        
        # Remove 'anyOf' keys after iteration
        for key in keys_to_modify:
            if len(obj["anyOf"]) == 1 and "type" in obj["anyOf"][0]:
                obj["type"] = obj["anyOf"][0]["type"]
            del obj["anyOf"]
    elif isinstance(obj, list):
        for item in obj:
            update_refs(item)

def substitute_at_position(openapi: dict, index: str, substitution: List[str | dict] | None):
    """
    Substitutes a key-value pair at a specific position in a dictionary.
    """
    if index in openapi.keys():
        pos = list(openapi.keys()).index(index)
        items = list(openapi.items())
        items.pop(pos)
        if substitution:
            items.insert(pos, (substitution[0], substitution[1]))
        openapi = dict(items)
    return openapi

def fix_parameter_schema(parameter):
    """
    Fix parameters by moving schema properties to parameter level for non-body parameters.
    In Swagger 2.0, only body parameters should have a schema, other parameter types 
    should have type/format directly at the parameter level.
    """
    if parameter.get("in") != "body" and "schema" in parameter:
        schema = parameter.pop("schema")
        # Copy schema properties to parameter level
        if "type" in schema:
            parameter["type"] = schema["type"]
        if "format" in schema:
            parameter["format"] = schema["format"]
        if "enum" in schema:
            parameter["enum"] = schema["enum"]
        if "default" in schema:
            parameter["default"] = schema["default"]
        if "minimum" in schema:
            parameter["minimum"] = schema["minimum"]
        if "maximum" in schema:
            parameter["maximum"] = schema["maximum"]
        # Add any other properties as needed
    return parameter

def redefine_paths(openapi: dict):
    """
    Redefines paths to make them compatible with Swagger 2.0.
    """
    METHODS = ['get', 'post', 'put', 'patch', 'delete']
    paths = openapi['paths']
    new_paths = {}
    for path in paths:
        new_path = path
        new_paths[new_path] = paths[path]
        
        # Extract path parameters (e.g., {item_id}) from the path string
        path_parameters = re.findall(r"\{(\w+)\}", new_path)
        
        for method in METHODS:
            if method in new_paths[new_path]:
                # Remove security and APIKeyHeader in paths
                new_paths[new_path][method] = substitute_at_position(new_paths[new_path][method], "security", None)
                
                # Handle parameters
                if "parameters" not in new_paths[new_path][method]:
                    new_paths[new_path][method]["parameters"] = []
                
                # Add path parameters to the parameters array
                for param_name in path_parameters:
                    param_exists = any(
                        param.get("name") == param_name and param.get("in") == "path"
                        for param in new_paths[new_path][method]["parameters"]
                    )
                    if not param_exists:
                        # Extract type and format from schema if available
                        param_type = "string"  # Default type
                        param_format = None
                        if "parameters" in paths[path] and any(p["name"] == param_name for p in paths[path].get("parameters", [])):
                            param_schema = next((p for p in paths[path]["parameters"] if p["name"] == param_name), {})
                            if "schema" in param_schema:
                                param_type = param_schema["schema"].get("type", "string")
                                param_format = param_schema["schema"].get("format")
                            else:
                                param_type = param_schema.get("type", "string")
                                param_format = param_schema.get("format")
                        
                        # Create the parameter object without a schema, directly with type
                        param_object = {
                            "name": param_name,
                            "in": "path",
                            "required": True,
                            "type": param_type
                        }
                        if param_format:
                            param_object["format"] = param_format
                        
                        new_paths[new_path][method]["parameters"].append(param_object)
                
                # Fix all parameters
                for parameter_index, parameter in enumerate(new_paths[new_path][method]["parameters"]):
                    # Fix schema issue in non-body parameters
                    new_paths[new_path][method]["parameters"][parameter_index] = fix_parameter_schema(parameter)
                    
                    # Convert gte with minimum and lte with maximum
                    if "gte" in parameter:
                        new_paths[new_path][method]["parameters"][parameter_index] = substitute_at_position(
                            parameter, "gte", ["minimum", parameter["gte"]]
                        )
                    if "lte" in parameter:
                        new_paths[new_path][method]["parameters"][parameter_index] = substitute_at_position(
                            parameter, "lte", ["maximum", parameter["lte"]]
                        )
                
                # Convert requestBody to body parameter
                if "requestBody" in new_paths[new_path][method]:
                    request_body = new_paths[new_path][method].pop("requestBody")
                    for content_type in request_body.get("content", {}):
                        schema = request_body["content"][content_type].get("schema", {})
                        update_refs(schema)  # Ensure $ref references are updated
                        new_paths[new_path][method]["parameters"].append({
                            "name": "body",
                            "in": "body",
                            "required": request_body.get("required", False),
                            "schema": schema
                        })
                        break  # Use the first supported content type
                
                # Handle responses
                for response in new_paths[new_path][method]["responses"]:
                    response_obj = new_paths[new_path][method]["responses"][response]
                    if "content" in response_obj:
                        for content_type in response_obj["content"]:
                            schema = response_obj["content"][content_type].get("schema")
                            if schema:
                                response_obj["schema"] = schema
                                break
                        del response_obj["content"]
    
    openapi['paths'] = new_paths
    return openapi

def redefine_definitions(openapi: dict):
    """
    Redefines definitions (schemas) to make them compatible with Swagger 2.0.
    """
    if "definitions" in openapi:
        for definition in openapi["definitions"]:
            # Replace const with enum
            if "const" in openapi["definitions"][definition]:
                openapi["definitions"][definition]["enum"] = [openapi["definitions"][definition]["const"]]
                del openapi["definitions"][definition]["const"]
            
            # Replace examples with example
            if "examples" in openapi["definitions"][definition]:
                openapi["definitions"][definition]["example"] = openapi["definitions"][definition]["examples"][0]
                del openapi["definitions"][definition]["examples"]
    return openapi

def get_env_var(key, default=None):
    """
    Retrieves an environment variable and raises an error if it is missing.
    """
    value = os.environ.get(key, default)
    if not value:
        print(f"Warning: Missing environment variable: {key}. Using default value.")
    return value

def add_custom_gcp_entries(openapi: dict):
    """
    Adds custom GCP-specific entries to the OpenAPI document.
    """
    openapi["swagger"] = "2.0"
    openapi["host"] = get_env_var("SERVICE_URL", "default-service-url")
    openapi["schemes"] = ["https"]
    openapi["security"] = [{"firebase": []}]
    openapi["x-google-backend"] = {"address": get_env_var("X_GOOGLE_BACKEND", "default-backend-address")}
    openapi["x-google-endpoints"] = [{"name": get_env_var("X_GOOGLE_ENDPOINTS", "default-endpoint"), "allowCors": True}]
    openapi["securityDefinitions"] = {
        "firebase": {
            "authorizationUrl": "",
            "flow": "implicit",
            "type": "oauth2",
            "x-google-issuer": f"https://securetoken.google.com/{get_env_var('AUTHENTICATION_PROJECT_ID', 'default-project-id')}",
            "x-google-jwks_uri": "https://www.googleapis.com/service_accounts/v1/metadata/x509/securetoken@system.gserviceaccount.com",
            "x-google-audiences": get_env_var("AUTHENTICATION_PROJECT_ID", "default-project-id")
        }
    }
    if "components" in openapi:
        openapi["definitions"] = openapi.pop("components", {}).get("schemas", {})
    openapi = redefine_paths(openapi)
    openapi = redefine_definitions(openapi)
    return openapi

def transform_to_swagger_2(openapi_spec: Dict, add_gcp_entries=False) -> Dict:
    """
    Transforms the OpenAPI 3.0.0 specification into a Swagger 2.X-compatible format.
    """
    try:
        # Create a deep copy of the input specification
        openapi_spec_copy = copy.deepcopy(openapi_spec)
        
        # Redefine paths and definitions
        openapi_spec_copy = redefine_paths(openapi_spec_copy)
        openapi_spec_copy = redefine_definitions(openapi_spec_copy)
        
        # Add custom GCP-specific entries if needed
        if add_gcp_entries:
            openapi_spec_copy = add_custom_gcp_entries(openapi_spec_copy)
        
        # Convert OpenAPI 3.0.0-specific fields to Swagger 2.X equivalents
        if "components" in openapi_spec_copy:
            openapi_spec_copy["definitions"] = openapi_spec_copy.pop("components", {}).get("schemas", {})
        
        # Update all $ref references
        update_refs(openapi_spec_copy)
        
        # Remove OpenAPI 3.0.0-specific fields like "openapi" version
        openapi_spec_copy.pop("openapi", None)
        
        # Add Swagger 2.X version field
        openapi_spec_copy["swagger"] = "2.0"
        
        return openapi_spec_copy
    except Exception as e:
        print(f"Error during transformation: {e}")
        raise