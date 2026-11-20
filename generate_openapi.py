import requests
import json

BASE_URL = "https://narrate-webapp-tcxs.onrender.com"

# =========================================================
# OPENAPI BASE
# =========================================================

openapi = {
    "openapi": "3.0.0",

    "info": {
        "title": "NARRATE Blueprint Unified API",
        "version": "1.0.0",
        "description": (
            "Unified ontology-driven API contract for the "
            "NARRATE Blueprint ecosystem."
        )
    },

    "servers": [
        {
            "url": BASE_URL
        }
    ],

    "paths": {},

    "components": {
        "schemas": {}
    }
}


# =========================================================
# HELPERS
# =========================================================

def safe_schema_name(name):
    return name.replace(" ", "_")


def add_path(path, method, content):
    if path not in openapi["paths"]:
        openapi["paths"][path] = {}

    openapi["paths"][path][method] = content


# =========================================================
# STATIC ENDPOINTS
# =========================================================

# ---------------------------------------------------------
# GET /api/classes
# ---------------------------------------------------------

add_path(
    "/api/classes",
    "get",
    {
        "summary": "Get all ontology classes",

        "responses": {
            "200": {
                "description": "List of ontology classes",

                "content": {
                    "application/json": {
                        "schema": {
                            "type": "object",

                            "properties": {
                                "classes": {
                                    "type": "array",

                                    "items": {
                                        "type": "string"
                                    }
                                },

                                "count": {
                                    "type": "integer"
                                }
                            }
                        }
                    }
                }
            }
        }
    }
)

# ---------------------------------------------------------
# GET /api/query/metadata/{className}
# ---------------------------------------------------------

add_path(
    "/api/query/metadata/{className}",
    "get",
    {
        "summary": "Get ontology metadata for class",

        "parameters": [
            {
                "name": "className",
                "in": "path",
                "required": True,

                "schema": {
                    "type": "string"
                }
            }
        ],

        "responses": {
            "200": {
                "description": "Ontology metadata"
            }
        }
    }
)

# ---------------------------------------------------------
# POST /api/query
# ---------------------------------------------------------

add_path(
    "/api/query",
    "post",
    {
        "summary": "Execute semantic ontology query",

        "description": (
            "Executes ontology-guided semantic queries "
            "across Blueprint entities and relationships."
        ),

        "requestBody": {
            "required": True,

            "content": {
                "application/json": {
                    "schema": {
                        "type": "object"
                    }
                }
            }
        },

        "responses": {
            "200": {
                "description": "Semantic query results"
            }
        }
    }
)

# ---------------------------------------------------------
# GET /api/full/{id}
# ---------------------------------------------------------

add_path(
    "/api/full/{id}",
    "get",
    {
        "summary": "Get full multi-valued details for individual",

        "parameters": [
            {
                "name": "id",
                "in": "path",
                "required": True,

                "schema": {
                    "type": "string"
                }
            }
        ],

        "responses": {
            "200": {
                "description": "Expanded individual details"
            }
        }
    }
)

# =========================================================
# GET ALL CLASSES
# =========================================================

classes_url = f"{BASE_URL}/api/classes"

response = requests.get(classes_url)

response.raise_for_status()

classes = response.json()["classes"]

print(f"Found {len(classes)} ontology classes")


# =========================================================
# PROCESS EACH CLASS
# =========================================================

for class_name in classes:

    print(f"Processing {class_name}")

    schema_name = safe_schema_name(class_name)

    metadata_url = f"{BASE_URL}/api/query/metadata/{class_name}"

    try:

        metadata = requests.get(metadata_url).json()

        # =================================================
        # CREATE SCHEMA
        # =================================================

        schema = {
            "type": "object",
            "properties": {}
        }

        # -------------------------------------------------
        # DATA PROPERTIES
        # -------------------------------------------------

        for prop in metadata.get("dataProperties", []):

            prop_name = prop.get("name")

            schema["properties"][prop_name] = {
                "type": "string"
            }

            comment = prop.get("comment")

            if comment:
                schema["properties"][prop_name]["description"] = comment

        # -------------------------------------------------
        # NUMERIC PROPERTIES
        # -------------------------------------------------

        for prop in metadata.get("numericProperties", []):

            schema["properties"][prop] = {
                "type": "number"
            }

        # -------------------------------------------------
        # ENUMERATED PROPERTIES
        # -------------------------------------------------

        for prop, values in metadata.get(
            "enumeratedProperties", {}
        ).items():

            schema["properties"][prop] = {
                "type": "string",
                "enum": values
            }

        # -------------------------------------------------
        # OBJECT PROPERTIES
        # -------------------------------------------------

        for relation, description in metadata.get(
            "objectProperties", {}
        ).items():

            schema["properties"][relation] = {
                "type": "array",

                "items": {
                    "type": "string"
                },

                "description": description
            }

        # -------------------------------------------------
        # CARDINALITIES
        # -------------------------------------------------

        cardinalities = metadata.get("cardinalities", {})

        for prop, rules in cardinalities.items():

            if prop in schema["properties"]:

                schema["properties"][prop]["x-cardinality"] = {
                    "min": rules.get("min", 0),
                    "max": rules.get("max", "N")
                }

        # =================================================
        # REGISTER SCHEMA
        # =================================================

        openapi["components"]["schemas"][schema_name] = schema

        # =================================================
        # GET /api/{className}
        # =================================================

        add_path(
            f"/api/{class_name}",
            "get",
            {
                "summary": f"Get all {class_name} instances",

                "responses": {
                    "200": {

                        "description": (
                            f"List of {class_name} instances"
                        ),

                        "content": {
                            "application/json": {

                                "schema": {
                                    "type": "object",

                                    "properties": {

                                        "class": {
                                            "type": "string"
                                        },

                                        "count": {
                                            "type": "integer"
                                        },

                                        "instances": {

                                            "type": "array",

                                            "items": {
                                                "type": "string"
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }
        )

        # =================================================
        # GET /api/{className}/{id}
        # =================================================

        add_path(
            f"/api/{class_name}/{{id}}",
            "get",
            {
                "summary": f"Get {class_name} instance details",

                "parameters": [
                    {
                        "name": "id",
                        "in": "path",
                        "required": True,

                        "schema": {
                            "type": "string"
                        }
                    }
                ],

                "responses": {
                    "200": {

                        "description": (
                            f"{class_name} instance details"
                        ),

                        "content": {
                            "application/json": {

                                "schema": {
                                    "type": "object",

                                    "properties": {

                                        "class": {
                                            "type": "string"
                                        },

                                        "instance": {
                                            "type": "string"
                                        },

                                        "data": {
                                            "$ref": (
                                                f"#/components/schemas/"
                                                f"{schema_name}"
                                            )
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }
        )

        # =================================================
        # POST /api/{className}
        # =================================================

        add_path(
            f"/api/{class_name}",
            "post",
            {
                "summary": f"Create {class_name} instance",

                "requestBody": {
                    "required": True,

                    "content": {
                        "application/json": {

                            "schema": {
                                "$ref": (
                                    f"#/components/schemas/"
                                    f"{schema_name}"
                                )
                            }
                        }
                    }
                },

                "responses": {
                    "200": {
                        "description": (
                            f"{class_name} created"
                        )
                    }
                }
            }
        )

        # =================================================
        # PUT /api/{className}/{id}
        # =================================================

        add_path(
            f"/api/{class_name}/{{id}}",
            "put",
            {
                "summary": f"Update {class_name} instance",

                "parameters": [
                    {
                        "name": "id",
                        "in": "path",
                        "required": True,

                        "schema": {
                            "type": "string"
                        }
                    }
                ],

                "requestBody": {
                    "required": True,

                    "content": {
                        "application/json": {

                            "schema": {
                                "$ref": (
                                    f"#/components/schemas/"
                                    f"{schema_name}"
                                )
                            }
                        }
                    }
                },

                "responses": {
                    "200": {
                        "description": (
                            f"{class_name} updated"
                        )
                    }
                }
            }
        )

        # =================================================
        # DELETE /api/{className}/{id}
        # =================================================

        add_path(
            f"/api/{class_name}/{{id}}",
            "delete",
            {
                "summary": f"Delete {class_name} instance",

                "parameters": [
                    {
                        "name": "id",
                        "in": "path",
                        "required": True,

                        "schema": {
                            "type": "string"
                        }
                    }
                ],

                "responses": {
                    "200": {
                        "description": (
                            f"{class_name} deleted"
                        )
                    }
                }
            }
        )

    except Exception as e:

        print(f"Error processing {class_name}: {e}")


# =========================================================
# EXPORT JSON
# =========================================================

with open("narrate_openapi.json", "w") as f:

    json.dump(openapi, f, indent=2)

print("Generated narrate_openapi.json")
