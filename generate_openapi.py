import argparse
import json
from pathlib import Path

BASE_URL = "https://narrate-webapp-tcxs.onrender.com"

parser = argparse.ArgumentParser(description="Generate the NARRATE Blueprint OpenAPI contract.")
parser.add_argument("--seed-json", help="Reuse classes, schemas, and CRUD paths from an existing generated contract (offline mode).")
args = parser.parse_args()

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


def add_advanced_query_contract():
    schemas = openapi["components"]["schemas"]
    schemas.update({
        "AdvancedQueryRequest": {
            "type": "object", "required": ["className"], "additionalProperties": False,
            "properties": {
                "className": {"type": "string", "description": "Ontology class local name."},
                "filters": {"type": "object", "properties": {
                    "dataProperties": {"type": "object", "additionalProperties": {"oneOf": [{"type": "string"}, {"type": "number"}]}},
                    "objectProperties": {"type": "object", "additionalProperties": {"oneOf": [{"type": "string"}, {"type": "number"}]}}
                }, "additionalProperties": False},
                "mode": {"type": "string", "enum": ["records", "count", "aggregate"], "default": "records"},
                "select": {"type": "array", "items": {"type": "string"}, "uniqueItems": True},
                "orderBy": {"oneOf": [{"type": "string"}, {"type": "object", "required": ["property"], "properties": {"property": {"type": "string"}, "direction": {"type": "string", "enum": ["asc", "desc"], "default": "asc"}}, "additionalProperties": False}]},
                "limit": {"type": "integer", "minimum": 1, "maximum": 1000, "default": 100},
                "offset": {"type": "integer", "minimum": 0, "default": 0},
                "aggregates": {"type": "array", "items": {"$ref": "#/components/schemas/AggregateSpec"}}
            }
        },
        "AggregateSpec": {"type": "object", "required": ["function"], "additionalProperties": False, "properties": {
            "function": {"type": "string", "enum": ["count", "sum", "avg", "min", "max"]},
            "property": {"type": "string"}, "as": {"type": "string"}
        }},
        "AdvancedQueryError": {"type": "object", "properties": {"status": {"type": "string", "enum": ["error"]}, "message": {"type": "string"}, "detail": {"type": "string"}}},
        "AdvancedQueryResponse": {"oneOf": [
            {"type": "object", "required": ["status", "class", "mode", "totalMatches", "records", "pagination"], "properties": {
                "status": {"type": "string", "enum": ["success"]}, "class": {"type": "string"}, "mode": {"type": "string", "enum": ["records"]},
                "totalMatches": {"type": "integer", "minimum": 0}, "records": {"type": "array", "items": {"type": "object", "required": ["id", "data"], "properties": {"id": {"type": "string"}, "data": {"type": "object", "additionalProperties": {"type": "array", "items": {"type": "string"}}}}}},
                "pagination": {"type": "object", "required": ["limit", "offset", "returned", "totalMatches", "hasMore", "nextOffset"], "properties": {"limit": {"type": "integer"}, "offset": {"type": "integer"}, "returned": {"type": "integer"}, "totalMatches": {"type": "integer"}, "hasMore": {"type": "boolean"}, "nextOffset": {"type": "integer", "nullable": True}}}
            }},
            {"type": "object", "required": ["status", "class", "mode", "totalMatches", "count"], "properties": {"status": {"type": "string", "enum": ["success"]}, "class": {"type": "string"}, "mode": {"type": "string", "enum": ["count"]}, "totalMatches": {"type": "integer", "minimum": 0}, "count": {"type": "integer", "minimum": 0}}},
            {"type": "object", "required": ["status", "class", "mode", "totalMatches", "aggregates", "aggregationScope"], "properties": {"status": {"type": "string", "enum": ["success"]}, "class": {"type": "string"}, "mode": {"type": "string", "enum": ["aggregate"]}, "totalMatches": {"type": "integer", "minimum": 0}, "aggregates": {"type": "object", "additionalProperties": {"type": "number", "nullable": True}}, "aggregationScope": {"type": "string"}}}
        ], "discriminator": {"propertyName": "mode"}}
    })
    add_path("/api/v2/query", "post", {
        "operationId": "advancedSemanticQuery", "summary": "Query, page, sort, select, or aggregate individuals",
        "description": "Additive semantic query endpoint. Records mode returns selected property details with pagination; count mode returns only the match count; aggregate mode supports count, sum, avg, min, and max. Aggregation applies to all matching individuals, independent of limit and offset. Class and property names are validated.",
        "requestBody": {"required": True, "content": {"application/json": {"schema": {"$ref": "#/components/schemas/AdvancedQueryRequest"}, "examples": {
            "pagedRecords": {"summary": "Select, sort, and page ManufacturedProduct records", "value": {"className": "ManufacturedProduct", "filters": {"dataProperties": {"hasManufacturedQuantity": "5"}}, "mode": "records", "select": ["hasManufacturedQuantity", "isInstanceOfProductType"], "orderBy": {"property": "hasManufacturedQuantity", "direction": "asc"}, "limit": 10, "offset": 0}},
            "countOnly": {"summary": "Count matching products", "value": {"className": "ManufacturedProduct", "filters": {"dataProperties": {"hasManufacturedQuantity": "5"}}, "mode": "count"}},
            "aggregate": {"summary": "Aggregate quantity", "value": {"className": "ManufacturedProduct", "mode": "aggregate", "aggregates": [{"function": "sum", "property": "hasManufacturedQuantity", "as": "totalQuantity"}]}}
        }}}},
        "responses": {
            "200": {"description": "Records, count, or aggregate results according to mode", "content": {"application/json": {"schema": {"$ref": "#/components/schemas/AdvancedQueryResponse"}, "examples": {
                "records": {"value": {"status": "success", "class": "ManufacturedProduct", "mode": "records", "totalMatches": 122, "records": [{"id": "ManufacturedProduct_1", "data": {"hasManufacturedQuantity": ["5"]}}], "pagination": {"limit": 10, "offset": 0, "returned": 1, "totalMatches": 122, "hasMore": True, "nextOffset": 1}}},
                "count": {"value": {"status": "success", "class": "ManufacturedProduct", "mode": "count", "totalMatches": 122, "count": 122}},
                "aggregate": {"value": {"status": "success", "class": "ManufacturedProduct", "mode": "aggregate", "totalMatches": 122, "aggregates": {"totalQuantity": 610}, "aggregationScope": "all matching individuals; limit and offset are not applied"}}
            }}}},
            "400": {"description": "Unknown class/property or invalid parameters", "content": {"application/json": {"schema": {"$ref": "#/components/schemas/AdvancedQueryError"}}}},
            "500": {"description": "Unexpected server error", "content": {"application/json": {"schema": {"$ref": "#/components/schemas/AdvancedQueryError"}}}}
        },
        "x-imc-operation-role": "advanced-semantic-query",
        "x-imc-request-mapping": {"className": "body.className", "filters": "body.filters", "requestedProperties": "body.select", "sortPropertyAndDirection": "body.orderBy", "pageSize": "body.limit", "pageOffset": "body.offset", "resultMode": "body.mode", "aggregateSpecifications": "body.aggregates"},
        "x-imc-response-mapping": {"matchingIndividualCount": "totalMatches", "recordIdentifiersAndProperties": "records[].id,data", "paginationMetadata": "pagination", "aggregateValues": "aggregates"}
    })


add_advanced_query_contract()


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

if args.seed_json:
    seed_path = Path(args.seed_json)
    with seed_path.open(encoding="utf-8") as seed_file:
        seed_spec = json.load(seed_file)
    # Preserve the source contract's ontology schemas and generated per-class CRUD paths.
    openapi["components"]["schemas"].update(seed_spec.get("components", {}).get("schemas", {}))
    for seed_path_name, operations in seed_spec.get("paths", {}).items():
        if seed_path_name != "/api/v2/query":
            openapi["paths"][seed_path_name] = operations
    classes = []
    print(f"Loaded existing contract from {args.seed_json}")
else:
    import requests
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

sample_output = Path("sample_output")
sample_output.mkdir(exist_ok=True)
with (sample_output / "narrate_openapi.json").open("w", encoding="utf-8") as f:
    json.dump(openapi, f, indent=2)

print("Generated narrate_openapi.json")
