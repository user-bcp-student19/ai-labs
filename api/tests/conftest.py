import os

from tests.helpers import TEST_JWT_AUDIENCE, TEST_JWT_ISSUER, TEST_JWT_SECRET

os.environ["JWT_SECRET"] = TEST_JWT_SECRET
os.environ["JWT_ISSUER"] = TEST_JWT_ISSUER
os.environ["JWT_AUDIENCE"] = TEST_JWT_AUDIENCE
