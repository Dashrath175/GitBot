# Security and account isolation

GitBot requires GitHub CLI authentication for installation. It does not support putting personal access tokens in Git remote URLs or command-line arguments.

Before installation succeeds, the selected account must match the GitHub API identity; the selected private repository must match its owner and node ID; and Git credential access to that exact remote must succeed. A mismatch stops the install.

Never paste tokens into GitBot configuration, commits, issue bodies, shell history, or bug reports. `Dashrath175/GitBot` is a product repository and is never a valid automation target.
