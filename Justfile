# Helm buildpack – default: list recipes
default:
    @just --list

# Build Go integration test binary (does not run tests)
build:
    go build ./tests/integration/...

# Run Go integration tests (packages buildpack via init_test then runs helm tests)
# Requires: Docker, scripts/package.sh. Use from buildpacks/helm directory.
test:
    go test -v -timeout 30m ./tests/integration/...

# Run Python unit tests (pytest)
pytest:
    pytest tests/unit -v
