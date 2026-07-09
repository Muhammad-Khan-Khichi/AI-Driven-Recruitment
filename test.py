from qdrant_client import QdrantClient

qdrant_client = QdrantClient(
    url="https://4af69d91-a7e4-41fd-b11a-1e69db9e9be5.eu-west-1-0.aws.cloud.qdrant.io:6333", 
    api_key="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJhY2Nlc3MiOiJtIiwic3ViamVjdCI6ImFwaS1rZXk6NTg5ZTY5MWQtNDQzOC00MTI3LThmMTUtOTdkNjAxMmYxMWY3In0.wTPzdTks6CFloYj670_G0IV5BrJ-x4GCoNC2xgPGino",
)

print(qdrant_client.get_collections())