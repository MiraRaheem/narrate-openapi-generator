#!/usr/bin/env python3
"""Generate the unified NARRATE Blueprint OpenAPI contract.

By default, ontology classes and metadata are fetched from the running BMS.
For an offline refresh, pass an existing generated contract with --seed-json;
its class schemas are retained while the API operations are rebuilt.
"""

import argparse
import copy
import json
import os
import re
import sys
from pathlib import Path
from urllib.parse import quote
from urllib.request import Request, urlopen


DEFAULT_BASE_URL = "https://narrate-webapp-tcxs.onrender.com"
SPEC_VERSION = "1.1.0"
DEFAULT_OUTPUT = Path("narrate_openapi.json")
DEFAULT_WEB_OUTPUT = Path("src/main/webapp/openapi.json")


def safe_schema_name(name):
    return re.sub(r"[^A-Za-z0-9_.-]", "_", name)


def operation_name(prefix, class_name=None):
    if class_name is None:
        return prefix
    suffix = re.sub(r"[^A-Za-z0-9]", " ", class_name)
    suffix = "".join(part[:1].upper() + part[1:] for part in suffix.split())
    return prefix + suffix


def fetch_json(base_url, path):
    request = Request(
        f"{base_url.rstrip('/')}{path}",
        headers={"Accept": "application/json"},
    )
    with urlopen(request, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def fetch_metadata(base_url):
    class_response = fetch_json(base_url, "/api/classes")
    classes = class_response.get("classes")
    if not isinstance(classes, list):
        raise RuntimeError("GET /api/classes did not return a classes array")

    metadata_by_class = {}
    for class_name in classes:
        encoded_name = quote(str(class_name), safe="")
        metadata = fetch_json(base_url, f"/api/query/metadata/{encoded_name}")
        if not isinstance(metadata, dict) or metadata.get("error"):
            raise RuntimeError(f"Metadata retrieval failed for class {class_name}")
        metadata_by_class[str(class_name)] = metadata
        print(f"Loaded metadata for {class_name}")
    return metadata_by_class


def class_schema(class_name, metadata):
    numeric_properties = set(metadata.get("numericProperties", []))
    enumerated_properties = metadata.get("enumeratedProperties", {})
    properties = {}

    for item in metadata.get("dataProperties", []):
        property_name = item.get("name")
        if not property_name:
            continue
        schema = {"type": "number" if property_name in numeric_properties else "string"}
        if item.get("comment"):
            schema["description"] = item["comment"]
        if item.get("order") is not None:
            schema["x-display-order"] = item["order"]
        properties[property_name] = schema

    for property_name in numeric_properties:
        properties.setdefault(property_name, {"type": "number"})

    for property_name, values in enumerated_properties.items():
        properties[property_name] = {"type": "string", "enum": values}

    for property_name, description in metadata.get("objectProperties", {}).items():
        schema = {"type": "array", "items": {"type": "string"}}
        if description:
            schema["description"] = description
        properties[property_name] = schema

    for property_name, rules in metadata.get("cardinalities", {}).items():
        if property_name in properties:
            properties[property_name]["x-cardinality"] = {
                "min": rules.get("min", 0),
                "max": rules.get("max", "N"),
            }

    schema = {"type": "object", "properties": properties}
    if class_name == "ProductType":
        schema["description"] = "Catalogue definition for a product type; it describes a product offering, not one physical manufactured unit."
    elif class_name == "ManufacturedProduct":
        schema["description"] = "A physical manufactured product instance associated with a ProductType catalogue definition."
    return schema


def class_names_from_seed(document):
    names = set()
    for path in document.get("paths", {}):
        match = re.fullmatch(r"/api/([^/{}]+)", path)
        if match and match.group(1) != "classes":
            names.add(match.group(1))
    schemas = document.get("components", {}).get("schemas", {})
    result = {}
    for name in sorted(names):
        schema = copy.deepcopy(schemas.get(safe_schema_name(name), {"type": "object", "properties": {}}))
        if name == "ProductType":
            schema["description"] = "Catalogue definition for a product type; it describes a product offering, not one physical manufactured unit."
        elif name == "ManufacturedProduct":
            schema["description"] = "A physical manufactured product instance associated with a ProductType catalogue definition."
        result[name] = schema
    return result


def property_filter_schema():
    return {
        "type": "object",
        "description": "Map ontology property local names to one value or an array of values. Numeric expressions such as >=1000 and <50 are supported by the legacy semantic query API.",
        "additionalProperties": {
            "oneOf": [
                {"type": "string"},
                {"type": "number"},
                {"type": "array", "items": {"oneOf": [{"type": "string"}, {"type": "number"}]}},
            ]
        },
    }


def metadata_schemas():
    return {
        "ClassMetadataResponse": {
            "type": "object",
            "required": ["class", "dataProperties", "objectProperties", "numericProperties", "enumeratedProperties", "cardinalities"],
            "properties": {
                "class": {"type": "string"},
                "dataProperties": {"type": "array", "items": {"$ref": "#/components/schemas/DataPropertyMetadata"}},
                "objectProperties": {"type": "object", "additionalProperties": {"type": "string"}},
                "numericProperties": {"type": "array", "items": {"type": "string"}},
                "enumeratedProperties": {"type": "object", "additionalProperties": {"type": "array", "items": {"type": "string"}}},
                "cardinalities": {"type": "object", "additionalProperties": {"type": "object", "additionalProperties": {"type": "integer"}}},
            },
        },
        "DataPropertyMetadata": {
            "type": "object",
            "required": ["name", "comment", "order"],
            "properties": {"name": {"type": "string"}, "comment": {"type": "string"}, "order": {"type": "integer"}},
        },
    }


def query_schemas():
    value_filter = property_filter_schema()
    return {
        "PropertyFilters": value_filter,
        "SemanticQueryRequest": {
            "type": "object",
            "required": ["className"],
            "additionalProperties": False,
            "properties": {
                "className": {"type": "string", "description": "Ontology class local name. Retrieve its metadata first."},
                "dataProperties": value_filter,
                "objectProperties": value_filter,
                "includeFuzzy": {"type": "boolean", "default": False},
                "fuzzyThreshold": {"type": "number", "minimum": 0, "maximum": 1, "default": 0.7},
            },
        },
        "SemanticQueryResponse": {
            "type": "object",
            "properties": {
                "status": {"type": "string", "enum": ["success", "error"]},
                "matchedIndividuals": {"type": "array", "items": {"type": "string"}},
                "similarityNotes": {"type": "object", "additionalProperties": {"type": "object", "additionalProperties": {"type": "string"}}},
                "message": {"type": "string"},
            },
        },
        "PropertyValues": {"type": "object", "additionalProperties": {"type": "array", "items": {"type": "string"}}},
        "FullIndividualResponse": {
            "type": "object",
            "required": ["instance", "data"],
            "properties": {"instance": {"type": "string"}, "data": {"$ref": "#/components/schemas/PropertyValues"}},
        },
        "EntityDetailResponse": {
            "type": "object",
            "required": ["class", "instance", "data"],
            "properties": {
                "class": {"type": "string"},
                "instance": {"type": "string"},
                "data": {"type": "object", "additionalProperties": {"type": "string"}},
            },
        },
        "ClassInstanceListResponse": {
            "type": "object",
            "required": ["class", "count", "instances"],
            "properties": {
                "class": {"type": "string"},
                "count": {"type": "integer", "minimum": 0},
                "instances": {"type": "array", "items": {"type": "string"}},
            },
        },
        "WritePropertyValue": {
            "type": "object",
            "required": ["property", "value"],
            "properties": {"property": {"type": "string"}, "value": {"type": "string"}},
        },
        "CreateIndividualRequest": {
            "type": "object",
            "required": ["individualName"],
            "properties": {
                "individualName": {"type": "string"},
                "dataProperties": {"type": "array", "items": {"$ref": "#/components/schemas/WritePropertyValue"}},
                "objectProperties": {"type": "array", "items": {"$ref": "#/components/schemas/WritePropertyValue"}},
            },
        },
        "UpdateIndividualRequest": {
            "type": "object",
            "properties": {
                "dataProperties": {"type": "array", "items": {"$ref": "#/components/schemas/WritePropertyValue"}},
                "objectProperties": {"type": "array", "items": {"$ref": "#/components/schemas/WritePropertyValue"}},
            },
        },
        "OperationResult": {
            "type": "object",
            "properties": {"status": {"type": "string"}, "message": {"type": "string"}},
        },
        "ErrorResponse": {
            "type": "object",
            "properties": {"error": {"type": "string"}, "detail": {"type": "string"}, "message": {"type": "string"}},
        },
        "AdvancedQueryRequest": {
            "type": "object",
            "required": ["className"],
            "additionalProperties": False,
            "properties": {
                "className": {"type": "string", "description": "Class local name. Retrieve metadata first."},
                "filters": {
                    "type": "object",
                    "properties": {"dataProperties": value_filter, "objectProperties": value_filter},
                    "additionalProperties": False,
                },
                "dataProperties": {"allOf": [value_filter], "description": "Legacy flat-filter form; filters.dataProperties is preferred."},
                "objectProperties": {"allOf": [value_filter], "description": "Legacy flat-filter form; filters.objectProperties is preferred."},
                "mode": {"type": "string", "enum": ["records", "count", "aggregate"], "default": "records"},
                "select": {"type": "array", "items": {"type": "string"}, "uniqueItems": True},
                "orderBy": {
                    "oneOf": [
                        {"type": "string"},
                        {"type": "object", "required": ["property"], "properties": {"property": {"type": "string"}, "direction": {"type": "string", "enum": ["asc", "desc"], "default": "asc"}}, "additionalProperties": False},
                    ]
                },
                "limit": {"type": "integer", "minimum": 1, "maximum": 1000, "default": 100},
                "offset": {"type": "integer", "minimum": 0, "default": 0},
                "includeFuzzy": {"type": "boolean", "default": False},
                "fuzzyThreshold": {"type": "number", "minimum": 0, "maximum": 1, "default": 0.7},
                "aggregates": {"type": "array", "items": {"$ref": "#/components/schemas/AggregateSpec"}},
            },
        },
        "AggregateSpec": {
            "type": "object",
            "required": ["function"],
            "additionalProperties": False,
            "properties": {
                "function": {"type": "string", "enum": ["count", "sum", "avg", "min", "max"]},
                "property": {"type": "string", "description": "Required for sum, avg, min, and max; optional for count."},
                "as": {"type": "string"},
            },
        },
        "AdvancedQueryError": {
            "type": "object",
            "required": ["status", "message"],
            "properties": {"status": {"type": "string", "enum": ["error"]}, "message": {"type": "string"}, "detail": {"type": "string"}},
        },
        "PaginationMetadata": {
            "type": "object",
            "required": ["limit", "offset", "returned", "totalMatches", "hasMore", "nextOffset"],
            "properties": {
                "limit": {"type": "integer"},
                "offset": {"type": "integer"},
                "returned": {"type": "integer"},
                "totalMatches": {"type": "integer"},
                "hasMore": {"type": "boolean"},
                "nextOffset": {"type": "integer", "nullable": True},
            },
        },
        "AdvancedRecordsResponse": {
            "type": "object",
            "required": ["status", "class", "mode", "totalMatches", "records", "pagination"],
            "properties": {
                "status": {"type": "string", "enum": ["success"]},
                "class": {"type": "string"},
                "mode": {"type": "string", "enum": ["records"]},
                "totalMatches": {"type": "integer", "minimum": 0},
                "records": {"type": "array", "items": {"type": "object", "required": ["id", "data"], "properties": {"id": {"type": "string"}, "data": {"$ref": "#/components/schemas/PropertyValues"}}}},
                "pagination": {"$ref": "#/components/schemas/PaginationMetadata"},
            },
        },
        "AdvancedCountResponse": {
            "type": "object",
            "required": ["status", "class", "mode", "totalMatches", "count"],
            "properties": {
                "status": {"type": "string", "enum": ["success"]},
                "class": {"type": "string"},
                "mode": {"type": "string", "enum": ["count"]},
                "totalMatches": {"type": "integer", "minimum": 0},
                "count": {"type": "integer", "minimum": 0},
            },
        },
        "AdvancedAggregateResponse": {
            "type": "object",
            "required": ["status", "class", "mode", "totalMatches", "aggregates", "aggregationScope"],
            "properties": {
                "status": {"type": "string", "enum": ["success"]},
                "class": {"type": "string"},
                "mode": {"type": "string", "enum": ["aggregate"]},
                "totalMatches": {"type": "integer", "minimum": 0},
                "aggregates": {"type": "object", "additionalProperties": {"type": "number", "nullable": True}},
                "aggregationScope": {"type": "string"},
            },
        },
        "AdvancedQueryResponse": {
            "oneOf": [
                {"$ref": "#/components/schemas/AdvancedRecordsResponse"},
                {"$ref": "#/components/schemas/AdvancedCountResponse"},
                {"$ref": "#/components/schemas/AdvancedAggregateResponse"},
            ],
            "discriminator": {
                "propertyName": "mode",
                "mapping": {"records": "#/components/schemas/AdvancedRecordsResponse", "count": "#/components/schemas/AdvancedCountResponse", "aggregate": "#/components/schemas/AdvancedAggregateResponse"},
            },
        },
    }


def add_operation(spec, path, method, operation):
    spec["paths"].setdefault(path, {})[method] = operation


def api_error_response(description="Invalid request"):
    return {
        "description": description,
        "content": {"application/json": {"schema": {"$ref": "#/components/schemas/AdvancedQueryError"}}},
    }


def build_spec(base_url, class_schemas):
    spec = {
        "openapi": "3.0.3",
        "info": {
            "title": "NARRATE Blueprint Unified API",
            "version": SPEC_VERSION,
            "description": (
                "Unified ontology-driven API contract for the NARRATE Blueprint ecosystem. "
                "Clients should retrieve class metadata before constructing semantic queries. "
                "ProductType is a catalogue definition; ManufacturedProduct is a physical manufactured instance."
            ),
        },
        "servers": [{"url": base_url.rstrip("/"), "description": "Blueprint API base URL"}],
        "tags": [
            {"name": "Ontology metadata", "description": "Discover ontology classes and their queryable properties."},
            {"name": "Semantic query", "description": "Find, page, sort, select, or aggregate ontology individuals."},
            {"name": "Entity details", "description": "Read or modify ontology individuals."},
        ],
        "paths": {},
        "components": {"schemas": {}},
    }
    schemas = spec["components"]["schemas"]
    schemas.update(metadata_schemas())
    schemas.update(query_schemas())
    for name, schema in class_schemas.items():
        schemas[safe_schema_name(name)] = schema

    add_operation(spec, "/api/classes", "get", {
        "tags": ["Ontology metadata"],
        "operationId": "listOntologyClasses",
        "summary": "List all ontology classes",
        "responses": {"200": {"description": "Ontology class local names", "content": {"application/json": {"schema": {"type": "object", "required": ["classes", "count"], "properties": {"classes": {"type": "array", "items": {"type": "string"}}, "count": {"type": "integer"}}}}}}},
        "x-imc-operation-role": "discover-ontology-classes",
        "x-imc-response-mapping": {"classNames": "classes", "classCount": "count"},
    })

    add_operation(spec, "/api/query/metadata/{className}", "get", {
        "tags": ["Ontology metadata"],
        "operationId": "getClassMetadata",
        "summary": "Retrieve Blueprint class metadata",
        "description": "Retrieve this metadata before forming a semantic query. It lists queryable data/object properties, numeric and enumerated properties, and cardinalities.",
        "parameters": [{"name": "className", "in": "path", "required": True, "description": "Case-sensitive ontology class local name.", "schema": {"type": "string"}}],
        "responses": {"200": {"description": "Class metadata", "content": {"application/json": {"schema": {"$ref": "#/components/schemas/ClassMetadataResponse"}}}}},
        "x-imc-operation-role": "discover-class-metadata",
        "x-imc-request-mapping": {"className": "path.className"},
        "x-imc-response-mapping": {"dataProperties": "dataProperties", "objectProperties": "objectProperties", "numericProperties": "numericProperties", "enumeratedProperties": "enumeratedProperties", "cardinalities": "cardinalities"},
    })

    legacy_examples = {
        "numericExpressions": {"summary": "Numeric comparison expressions", "value": {"className": "ProductType", "dataProperties": {"hasProductPrice": ">=1000", "hasProductCost": "<50"}}},
        "combinedFilters": {"summary": "Combined data and object filters", "value": {"className": "ManufacturedProduct", "dataProperties": {"hasManufacturedQuantity": ">=5"}, "objectProperties": {"isInstanceOfProductType": "ProductType_NORDIKA"}}},
        "fuzzyMatching": {"summary": "Fuzzy matching", "value": {"className": "ProductType", "dataProperties": {"hasProductName": "Cot Nordika Wood"}, "includeFuzzy": True, "fuzzyThreshold": 0.7}},
    }
    add_operation(spec, "/api/query", "post", {
        "tags": ["Semantic query"],
        "operationId": "queryIndividuals",
        "summary": "Semantically filter Blueprint individuals",
        "description": "Filters individuals by data and object-property values. Retrieve class metadata first. Numeric expressions such as >=1000 and <50 and optional fuzzy text matching are supported. The legacy endpoint returns matching identifiers; use /api/v2/query for full records, paging, sorting, selection, or aggregation.",
        "requestBody": {"required": True, "content": {"application/json": {"schema": {"$ref": "#/components/schemas/SemanticQueryRequest"}, "examples": legacy_examples}}},
        "responses": {"200": {"description": "Query results. The current legacy implementation can also return an error object with HTTP 200.", "content": {"application/json": {"schema": {"$ref": "#/components/schemas/SemanticQueryResponse"}, "example": {"status": "success", "matchedIndividuals": ["ManufacturedProduct_1"], "similarityNotes": {}}}}}},
        "x-imc-operation-role": "semantic-filter",
        "x-imc-request-mapping": {"className": "body.className", "dataPropertyFilters": "body.dataProperties", "objectPropertyFilters": "body.objectProperties", "fuzzyMatchingEnabled": "body.includeFuzzy", "fuzzySimilarityThreshold": "body.fuzzyThreshold"},
        "x-imc-response-mapping": {"matchedIdentifiers": "matchedIndividuals", "similarityNotes": "similarityNotes"},
    })

    add_operation(spec, "/api/full/{id}", "get", {
        "tags": ["Entity details"],
        "operationId": "getFullIndividualDetails",
        "summary": "Get full multi-valued individual details",
        "parameters": [{"name": "id", "in": "path", "required": True, "description": "Individual local name.", "schema": {"type": "string"}}],
        "responses": {
            "200": {"description": "All available property values for the individual", "content": {"application/json": {"schema": {"$ref": "#/components/schemas/FullIndividualResponse"}}}},
            "404": {"description": "Individual not found", "content": {"application/json": {"schema": {"$ref": "#/components/schemas/ErrorResponse"}}}},
        },
        "x-imc-operation-role": "retrieve-entity-details",
        "x-imc-request-mapping": {"individualIdentifier": "path.id"},
        "x-imc-response-mapping": {"individualIdentifier": "instance", "propertyValues": "data"},
    })

    advanced_request_examples = {
        "pagedRecords": {"summary": "Select, sort, and page product records", "value": {"className": "ManufacturedProduct", "filters": {"dataProperties": {"hasManufacturedQuantity": "5"}, "objectProperties": {}}, "mode": "records", "select": ["hasManufacturedQuantity", "isInstanceOfProductType"], "orderBy": {"property": "hasManufacturedQuantity", "direction": "asc"}, "limit": 10, "offset": 0}},
        "countOnly": {"summary": "Count matches without returning records", "value": {"className": "ManufacturedProduct", "filters": {"dataProperties": {"hasManufacturedQuantity": "5"}}, "mode": "count"}},
        "aggregates": {"summary": "Aggregate over all matching records", "value": {"className": "ManufacturedProduct", "filters": {"dataProperties": {"hasManufacturedQuantity": ">=1"}}, "mode": "aggregate", "aggregates": [{"function": "sum", "property": "hasManufacturedQuantity", "as": "totalQuantity"}, {"function": "count", "as": "individualCount"}]}},
    }
    add_operation(spec, "/api/v2/query", "post", {
        "tags": ["Semantic query"],
        "operationId": "advancedSemanticQuery",
        "summary": "Query, page, sort, select, or aggregate individuals",
        "description": "Additive query endpoint; POST /api/query remains unchanged. Records mode returns property details and pagination metadata. Count mode returns count without records. Aggregate mode supports count, sum, avg, min, and max across all matching individuals; limit and offset do not apply to aggregation. Properties are validated against declarations for the selected class.",
        "requestBody": {"required": True, "content": {"application/json": {"schema": {"$ref": "#/components/schemas/AdvancedQueryRequest"}, "examples": advanced_request_examples}}},
        "responses": {
            "200": {"description": "Records, count, or aggregate results according to mode", "content": {"application/json": {"schema": {"$ref": "#/components/schemas/AdvancedQueryResponse"}, "examples": {
                "records": {"value": {"status": "success", "class": "ManufacturedProduct", "mode": "records", "totalMatches": 122, "records": [{"id": "ManufacturedProduct_1", "data": {"hasManufacturedQuantity": ["5"], "isInstanceOfProductType": ["http://example.org/ontology#ProductType_NORDIKA"]}}], "pagination": {"limit": 10, "offset": 0, "returned": 1, "totalMatches": 122, "hasMore": True, "nextOffset": 1}}},
                "count": {"value": {"status": "success", "class": "ManufacturedProduct", "mode": "count", "totalMatches": 122, "count": 122}},
                "aggregate": {"value": {"status": "success", "class": "ManufacturedProduct", "mode": "aggregate", "totalMatches": 122, "aggregates": {"totalQuantity": 610, "individualCount": 122}, "aggregationScope": "all matching individuals; limit and offset are not applied"}},
            }}}},
            "400": api_error_response("Unknown class/property or invalid query parameters"),
            "500": api_error_response("Unexpected query or server error"),
        },
        "x-imc-operation-role": "advanced-semantic-query",
        "x-imc-request-mapping": {"className": "body.className", "filters": "body.filters", "requestedProperties": "body.select", "sortPropertyAndDirection": "body.orderBy", "pageSize": "body.limit", "pageOffset": "body.offset", "resultMode": "body.mode", "aggregateSpecifications": "body.aggregates"},
        "x-imc-response-mapping": {"matchingIndividualCount": "totalMatches", "recordIdentifiersAndProperties": "records[].id,data", "paginationMetadata": "pagination", "aggregateValues": "aggregates"},
    })

    add_operation(spec, "/api/{className}", "get", {
        "tags": ["Entity details"],
        "operationId": "listClassIndividuals",
        "summary": "List individuals in a class",
        "description": "Returns all matching individual identifiers without pagination. Use /api/v2/query for paged results.",
        "parameters": [{"name": "className", "in": "path", "required": True, "schema": {"type": "string"}}],
        "responses": {"200": {"description": "Class individual identifiers", "content": {"application/json": {"schema": {"$ref": "#/components/schemas/ClassInstanceListResponse"}}}}},
        "x-imc-operation-role": "list-class-individuals",
        "x-imc-request-mapping": {"className": "path.className"},
        "x-imc-response-mapping": {"individualIdentifiers": "instances", "individualCount": "count"},
    })
    add_operation(spec, "/api/{className}", "post", {
        "tags": ["Entity details"], "operationId": "createClassIndividual", "summary": "Create an individual",
        "parameters": [{"name": "className", "in": "path", "required": True, "schema": {"type": "string"}}],
        "requestBody": {"required": True, "content": {"application/json": {"schema": {"$ref": "#/components/schemas/CreateIndividualRequest"}}}},
        "responses": {"200": {"description": "Creation result", "content": {"application/json": {"schema": {"$ref": "#/components/schemas/OperationResult"}}}}, "400": api_error_response("Invalid creation request")},
    })

    add_operation(spec, "/api/{className}/{instanceId}", "get", {
        "tags": ["Entity details"], "operationId": "getIndividualDetails", "summary": "Get an individual's details",
        "parameters": [{"name": "className", "in": "path", "required": True, "schema": {"type": "string"}}, {"name": "instanceId", "in": "path", "required": True, "schema": {"type": "string"}}],
        "responses": {"200": {"description": "Single-value property map", "content": {"application/json": {"schema": {"$ref": "#/components/schemas/EntityDetailResponse"}}}}, "404": {"description": "Individual not found", "content": {"application/json": {"schema": {"$ref": "#/components/schemas/ErrorResponse"}}}}},
    })
    add_operation(spec, "/api/{className}/{instanceId}", "put", {
        "tags": ["Entity details"], "operationId": "updateIndividual", "summary": "Update an individual's properties",
        "parameters": [{"name": "className", "in": "path", "required": True, "schema": {"type": "string"}}, {"name": "instanceId", "in": "path", "required": True, "schema": {"type": "string"}}],
        "requestBody": {"required": True, "content": {"application/json": {"schema": {"$ref": "#/components/schemas/UpdateIndividualRequest"}}}},
        "responses": {"200": {"description": "Update result", "content": {"application/json": {"schema": {"$ref": "#/components/schemas/OperationResult"}}}}, "400": api_error_response("Invalid update request")},
    })
    add_operation(spec, "/api/{className}/{instanceId}", "delete", {
        "tags": ["Entity details"], "operationId": "deleteIndividual", "summary": "Delete an individual",
        "parameters": [{"name": "className", "in": "path", "required": True, "schema": {"type": "string"}}, {"name": "instanceId", "in": "path", "required": True, "schema": {"type": "string"}}],
        "responses": {"200": {"description": "Deletion result", "content": {"application/json": {"schema": {"$ref": "#/components/schemas/OperationResult"}}}}, "404": {"description": "Individual not found", "content": {"application/json": {"schema": {"$ref": "#/components/schemas/ErrorResponse"}}}}, "400": api_error_response("Invalid delete request")},
    })

    return spec


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default=os.environ.get("NARRATE_BASE_URL", DEFAULT_BASE_URL), help="BMS origin/context URL used for metadata discovery and the OpenAPI server URL")
    parser.add_argument("--seed-json", type=Path, help="Reuse class schemas from an existing OpenAPI JSON file instead of making network requests")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT, help=f"Generated contract path (default: {DEFAULT_OUTPUT})")
    parser.add_argument("--web-output", type=Path, default=DEFAULT_WEB_OUTPUT, help=f"Copy served by the web app (default: {DEFAULT_WEB_OUTPUT})")
    parser.add_argument("--no-web-copy", action="store_true", help="Do not write the packaged web copy")
    return parser.parse_args()


def main():
    args = parse_args()
    if args.seed_json:
        with args.seed_json.open(encoding="utf-8") as source:
            seed = json.load(source)
        class_schemas = class_names_from_seed(seed)
        if not class_schemas:
            raise RuntimeError("The seed document did not contain generated class routes")
        print(f"Reusing schemas for {len(class_schemas)} classes from {args.seed_json}")
    else:
        metadata_by_class = fetch_metadata(args.base_url)
        class_schemas = {name: class_schema(name, metadata) for name, metadata in metadata_by_class.items()}

    document = build_spec(args.base_url, class_schemas)
    output_text = json.dumps(document, indent=2, ensure_ascii=False) + "\n"
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(output_text, encoding="utf-8")
    print(f"Generated {args.output} ({len(class_schemas)} class schemas)")

    if not args.no_web_copy:
        args.web_output.parent.mkdir(parents=True, exist_ok=True)
        args.web_output.write_text(output_text, encoding="utf-8")
        print(f"Updated web-served copy at {args.web_output}")


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(f"OpenAPI generation failed: {error}", file=sys.stderr)
        raise SystemExit(1)
