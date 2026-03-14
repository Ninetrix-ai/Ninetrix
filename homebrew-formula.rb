# This file is auto-updated by release-cli.yml after each PyPI publish.
# It lives in github.com/Ninetrix-ai/homebrew-tap as Formula/ninetrix.rb

class Ninetrix < Formula
  desc "Build and run AI agents as containers"
  homepage "https://ninetrix.io"
  url "https://files.pythonhosted.org/packages/source/n/ninetrix/ninetrix-VERSION.tar.gz"
  sha256 "SHA256_PLACEHOLDER"
  license "Apache-2.0"

  depends_on "python@3.12"

  def install
    # Create isolated virtualenv so ninetrix doesn't conflict with system packages
    venv = virtualenv_create(libexec, "python3.12")
    venv.pip_install_and_link buildpath
  end

  test do
    system bin/"ninetrix", "--version"
  end
end
