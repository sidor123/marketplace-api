#!/bin/sh

set -e

mkdir -p generated
touch generated/__init__.py

datamodel-codegen \
  --disable-timestamp \
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
