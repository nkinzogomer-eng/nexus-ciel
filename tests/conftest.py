import os

# Synthetic providers are enabled only inside the test process. Production API
# startup requires an explicitly configured real provider endpoint.
os.environ.setdefault("NEXUS_TEST_MODE", "1")
