# NARRATE Blueprint Unified OpenAPI Contract

This repository generates and packages an OpenAPI contract for the NARRATE Blueprint Management System. The contract describes the generic entity APIs, metadata discovery, the legacy semantic query, and the additive advanced query endpoint.

## Source and generated files

- `generate_openapi.py` is the contract generator.
- `narrate_openapi.json` is the generated contract intended for GitHub, Swagger Editor, Postman, and the ADIMME/API Registry.
- `src/main/webapp/openapi.json` is a synchronized copy served by the web application at `/openapi.json` after deployment.

Commit the generator, README, and generated JSON together so the published contract and its generator stay in sync. Import `narrate_openapi.json` into the API Registry after reviewing the generated result.

## Generate from a running BMS

Requirement: Python 3.9+ (the generator uses only the standard library).

```bash
python generate_openapi.py
```

The default server is `https://narrate-webapp-tcxs.onrender.com`. The generator reads `/api/classes`, then fetches `/api/query/metadata/{className}` for each class and generates ontology-derived schemas. Override the base URL when needed:

```bash
python generate_openapi.py --base-url http://localhost:8081/OntologyWebApp
```

You can also set `NARRATE_BASE_URL` instead of passing `--base-url`.

## Regenerate without network access

An existing generated contract can supply class-schema snapshots while the generator rebuilds the operation documentation:

```bash
python generate_openapi.py --seed-json "narrate_openapi.json"
```

For a one-time seed from an earlier generated contract, pass its path with `--seed-json`. This preserves the available class schemas but does not refresh them from live ontology metadata.

To generate only the root contract and not the web-served copy:

```bash
python generate_openapi.py --no-web-copy
```

## Documented query APIs

### Metadata discovery

`GET /api/classes` lists ontology classes. Retrieve `GET /api/query/metadata/{className}` before creating semantic filters; the metadata response describes data properties, object properties, numeric and enumerated properties, and cardinality constraints.

### Legacy semantic query

`POST /api/query` returns matching individual identifiers and fuzzy-match notes. It accepts `className`, `dataProperties`, `objectProperties`, `includeFuzzy`, and `fuzzyThreshold`. Numeric comparison expressions such as `>=1000` and `<50` are supported. This operation retains its existing response format.

### Advanced semantic query

`POST /api/v2/query` is additive and leaves the legacy API unchanged. It supports:

- `mode: "records"` to return individual identifiers and property details.
- `select` to choose returned properties.
- `orderBy`, `limit`, and `offset` to sort and page record results.
- `mode: "count"` to return the number of matches without records.
- `mode: "aggregate"` with `count`, `sum`, `avg`, `min`, or `max` specifications.
- Validation errors for unknown classes and unknown or inapplicable properties.

The API currently reports the match total as `totalMatches`. Record pagination limits the response, but the current implementation evaluates and loads the matching records before slicing a page. Aggregations run over all matching records and ignore `limit`/`offset`. Grouped aggregates and paginated relationship expansion are not currently implemented.

### Product type versus manufactured product

`ProductType` describes a product catalogue definition (for example, a model or offering). `ManufacturedProduct` identifies a physical manufactured instance associated with a product type. The two classes should not be treated as interchangeable.

## Validate and publish

The generator writes OpenAPI 3.0.3 JSON. Check the generated JSON in Swagger Editor and make sure the server URL, metadata, examples, and response names match the deployed API before publishing. The custom `x-imc-*` operation extensions describe client-facing roles and request/response field mappings; they do not change API behavior.

After review, commit `generate_openapi.py`, `README.md`, and `narrate_openapi.json` together. The generator also updates `src/main/webapp/openapi.json`, which is included in the WAR and served at `/openapi.json`.
