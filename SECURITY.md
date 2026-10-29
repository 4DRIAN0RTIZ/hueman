# Security Policy

## Supported versions

Only the latest release receives security fixes.

## Reporting a vulnerability

Please do not open a public issue. Report it privately through GitHub's
private vulnerability reporting: open the repository's **Security** tab and
choose **Report a vulnerability**.

Include the affected version, steps to reproduce, and the impact you see.
You can expect an acknowledgement and a first assessment; fixes land in a
patch release once confirmed, and you will be credited if you wish.

## Scope

hueman writes files and runs best-effort `reload` / `post_apply` commands
that are defined in the user's own configuration. That configuration is
trusted input: running commands you wrote yourself is not a vulnerability.
Issues such as path escapes from palette or template names, or commands
executed from untrusted palette data, are in scope.
