package integration_test

import (
	"os/exec"
	"path/filepath"
	"strings"
	"testing"
	"time"

	"github.com/sclevine/spec"
	"github.com/sclevine/spec/report"

	. "github.com/onsi/gomega"
	"github.com/onsi/gomega/format"
)

var helmBuildpack string

// Builder for pack build (shell detect/build; no Python required).
const defaultBuilder = "paketobuildpacks/builder-jammy-base:latest"

func TestIntegration(t *testing.T) {
	Expect := NewWithT(t).Expect
	format.MaxLength = 0

	// Resolve module root (go test runs with cwd = tests/integration, so scripts/ and build/ are under module root).
	moduleRootOut, err := exec.Command("go", "list", "-m", "-f", "{{.Dir}}").Output()
	Expect(err).NotTo(HaveOccurred())
	moduleRoot := strings.TrimSpace(string(moduleRootOut))
	scriptPath := filepath.Join(moduleRoot, "scripts", "package.sh")
	tgzPath := filepath.Join(moduleRoot, "build", "buildpack.tgz")

	cmd := exec.Command("bash", "-c", scriptPath+" --version 0.1.0")
	cmd.Dir = moduleRoot
	output, err := cmd.CombinedOutput()
	Expect(err).NotTo(HaveOccurred(), string(output))

	helmBuildpack, err = filepath.Abs(tgzPath)
	Expect(err).NotTo(HaveOccurred())
	Expect(helmBuildpack).To(BeAnExistingFile())

	SetDefaultEventuallyTimeout(30 * time.Second)

	suite := spec.New("Integration", spec.Report(report.Terminal{}), spec.Parallel())
	suite("Helm", testHelm)
	suite.Run(t)
}
