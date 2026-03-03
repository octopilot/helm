package integration_test

import (
	"fmt"
	"os"
	"testing"

	"github.com/paketo-buildpacks/occam"
	"github.com/sclevine/spec"

	. "github.com/onsi/gomega"
	. "github.com/paketo-buildpacks/occam/matchers"
)

func testHelm(t *testing.T, context spec.G, it spec.S) {
	var (
		Expect     = NewWithT(t).Expect
		Eventually = NewWithT(t).Eventually

		pack   occam.Pack
		docker occam.Docker
	)

	it.Before(func() {
		pack = occam.NewPack().WithVerbose().WithNoColor()
		docker = occam.NewDocker()
	})

	context("when building a chart", func() {
		var (
			image     occam.Image
			container occam.Container
			name      string
			source    string
		)

		it.Before(func() {
			var err error
			name, err = occam.RandomName()
			Expect(err).NotTo(HaveOccurred())
		})

		it.After(func() {
			if container.ID != "" {
				_ = docker.Container.Remove.Execute(container.ID)
			}
			_ = docker.Volume.Remove.Execute(occam.CacheVolumeNames(name))
			if image.ID != "" {
				_ = docker.Image.Remove.Execute(image.ID)
			}
			if source != "" {
				Expect(os.RemoveAll(source)).To(Succeed())
			}
		})

		it("detects and builds successfully", func() {
			var err error
			source, err = occam.Source("chartTemplate")
			Expect(err).NotTo(HaveOccurred())

			var logs fmt.Stringer
			t.Log("Pack build starting (first run may take several minutes for builder image pull and lifecycle)...")
			image, logs, err = pack.Build.
				WithPullPolicy("if-not-present").
				WithBuilder(defaultBuilder).
				WithBuildpacks(helmBuildpack).
				Execute(name, source)
			Expect(err).ToNot(HaveOccurred(), logs.String)

			Expect(logs).To(ContainLines(ContainSubstring("Octopilot Helm Buildpack")))
			Expect(logs).To(ContainLines(ContainSubstring("Packaging Helm chart")))

			container, err = docker.Container.Run.
				WithEntrypoint("sh").
				WithCommand(`-c 'test -f /layers/octopilot_helm/helm-chart/chart/integration-test-chart-0.1.0.tgz && echo OK'`).
				Execute(image.ID)
			Expect(err).NotTo(HaveOccurred())

			Eventually(func() (string, error) {
				logs, err := docker.Container.Logs.Execute(container.ID)
				if err != nil {
					return "", err
				}
				return logs.String(), nil
			}).Should(ContainSubstring("OK"))
		})
	})
}
