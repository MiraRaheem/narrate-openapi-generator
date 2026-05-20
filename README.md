# NARRATE Blueprint Unified OpenAPI Generator

## Overview

This utility automatically generates a unified OpenAPI/Swagger specification for the NARRATE Blueprint ecosystem using the ontology metadata APIs exposed by the Blueprint platform.

The generator dynamically discovers:

- Ontology classes
- Data properties
- Object properties
- Numeric properties
- Enumerated properties
- Cardinality constraints

and transforms them into a machine-readable OpenAPI contract.

The purpose of this generator is to provide the IMC and related NARRATE components with a unified, discoverable, and up-to-date API specification without requiring manual maintenance of static schemas.

---

# Generated Output

The script generates:

```text
narrate_openapi.json
```

which contains:

- OpenAPI 3.0 specification
- Ontology-derived schemas
- Generic CRUD endpoints
- Metadata discovery endpoints
- Semantic query endpoints

The generated file can be imported directly into:

- Swagger Editor
- Swagger UI
- Postman
- API Gateway tools
- IMC integration tooling

---

# Supported Endpoints

The generated OpenAPI contract documents the following Blueprint APIs.

---

## Ontology Discovery

### Get ontology classes

```http
GET /api/classes
```

Returns all ontology classes available in the Blueprint.

---

### Get ontology metadata

```http
GET /api/query/metadata/{className}
```

Returns semantic metadata for a class including:

- data properties
- object properties
- enumerations
- cardinalities
- numeric properties

---

# Generic Entity APIs

---

## Get all instances of a class

```http
GET /api/{className}
```

Example:

```http
GET /api/Product
```

---

## Get individual details

```http
GET /api/{className}/{id}
```

Example:

```http
GET /api/Product/Product_1
```

---

## Get full multi-valued details

```http
GET /api/full/{id}
```

Returns expanded details including multi-valued properties.

---

# CRUD Operations

---

## Create instance

```http
POST /api/{className}
```

---

## Update instance

```http
PUT /api/{className}/{id}
```

---

## Delete instance

```http
DELETE /api/{className}/{id}
```

---

# Semantic Query API

---

## Execute semantic query

```http
POST /api/query
```

This endpoint forwards semantic ontology-driven queries to the Blueprint query engine.

---

# Architecture

The generator follows a metadata-driven approach.

```text
Ontology Metadata API
        ↓
Metadata Extraction
        ↓
Dynamic OpenAPI Schema Generation
        ↓
Unified Swagger/OpenAPI Contract
```

This ensures that the generated specification remains synchronized with ontology evolution without requiring manual schema rewriting.

---

# Requirements

Python 3.9+

Required package:

```bash
pip install requests
```

---

# Configuration

Update the Blueprint server URL inside the script:

```python
BASE_URL = "https://narrate-webapp-tcxs.onrender.com"
```

---

# Usage

Run:

```bash
python generate_openapi.py
```

The generated OpenAPI file will be saved as:

```text
narrate_openapi.json
```

---

# Import into Swagger Editor

You can validate and visualize the generated contract using:

https://editor.swagger.io/

Simply paste the generated JSON content into the editor.

---

# Notes

- The OpenAPI schemas are generated dynamically from ontology metadata.
- No manual endpoint enumeration is required.
- The generated schemas automatically adapt to ontology evolution.
- Object properties are represented as arrays of related entity identifiers.
- Cardinality constraints are included as custom OpenAPI extensions.

---

# Purpose within NARRATE

This generator is intended to support:

- IMC integration
- Dynamic Blueprint discovery
- AI-assisted query orchestration
- Unified API governance
- Cross-work-package interoperability

while maintaining synchronization with the underlying ontology structure.

---

# Maintainers

NARRATE Blueprint Team
