# Security Policy

## Reporting a Vulnerability

If you discover a security vulnerability in RuleShield Hermes, please report it responsibly. **Do not open a public GitHub issue for security vulnerabilities.**

Send your report to: **security@ruleshield.dev**

Include the following in your report:

- A description of the vulnerability and its potential impact.
- Steps to reproduce the issue, including any relevant configuration or input.
- The component affected (proxy, cache, rules engine, dashboard, or other).
- Your suggested fix, if you have one.

## What Constitutes a Security Issue

The following are considered security issues and should be reported privately:

- **API key or credential exposure** -- any path that could leak provider API keys, configuration secrets, or user credentials through logs, error messages, or API responses.
- **Injection attacks** -- prompt injection, command injection, or any input that causes the proxy to execute unintended operations.
- **Authentication or authorization bypass** -- any way to access protected endpoints, metrics, or configuration without proper credentials.
- **Cache poisoning** -- manipulating cached responses to serve incorrect or malicious content to other users.
- **Rule engine bypass** -- crafting input that circumvents rule matching in a way that could cause unexpected cost or behavior.
- **Denial of service** -- input that causes the proxy to crash, hang, or consume excessive resources.
- **Dashboard vulnerabilities** -- XSS, CSRF, or other web security issues in the SvelteKit dashboard.

## Response Timeline

| Step | Timeframe |
|------|-----------|
| Acknowledgment of your report | Within 48 hours |
| Initial assessment and severity classification | Within 72 hours |
| Fix developed and tested | Within 7 days for critical issues |
| Patch released | Coordinated with reporter |

For critical vulnerabilities, we may release an out-of-band patch. For lower-severity issues, the fix will be included in the next scheduled release.

## Scope

This policy covers the following components of RuleShield Hermes:

- **Proxy server** (`ruleshield/proxy.py`) -- the FastAPI application that intercepts and routes LLM requests.
- **Cache layer** (`ruleshield/cache.py`) -- semantic and exact-match response caching.
- **Rules engine** (`ruleshield/rules.py`) -- rule matching and canned response logic.
- **Smart router** (`ruleshield/router.py`) -- complexity-based model routing.
- **Configuration and CLI** (`ruleshield/cli.py`, `ruleshield/config.py`) -- initialization and settings management.
- **Dashboard** (`dashboard/`) -- the SvelteKit monitoring and management UI.
- **Integrations** (`ruleshield/integrations/`) -- Slack notifications and other external service connectors.

## Disclosure Policy

We follow coordinated disclosure. Once a fix is available, we will:

1. Notify the reporter that the fix is ready.
2. Release the patched version.
3. Publish a security advisory on GitHub with credit to the reporter (unless anonymity is requested).

We ask that you do not disclose the vulnerability publicly until a fix has been released.

## Thank You

We appreciate the security research community's efforts in helping keep RuleShield Hermes and its users safe. Reporters who follow responsible disclosure will be credited in the security advisory unless they prefer to remain anonymous.
