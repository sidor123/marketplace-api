#!/bin/bash

set -e

mkdir -p generated

datamodel-codegen \
  --input openapi/products.yaml \
  --input-file-type openapi \
  --output generated/schemas.py \
  --output-model-type pydantic_v2.BaseModel \
  --field-constraints \
  --use-standard-collections \
  --use-schema-description \
  --use-title-as-name \
  --snake-case-field \
  --target-python-version 3.11 \
  --collapse-root-models \
  --use-default \
  --use-default-kwarg \
  --enum-field-as-literal one
