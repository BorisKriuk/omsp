# Security Policy

## Supported Versions

| Version | Supported          |
|---------|--------------------|
| 1.0.x   | ✅ Active support  |
| < 1.0   | ❌ Not supported   |

## 🔐 Reporting a Vulnerability

We take security issues seriously. If you discover a security vulnerability, **please do NOT open a public GitHub issue.**

Instead, report it responsibly through one of these channels:

- **Email:** kriuk.boris@gmail.com
- **GitHub Private Advisory:** [Create a private security advisory](../../security/advisories/new)

### What to Include

- A clear description of the vulnerability.
- Steps to reproduce the issue.
- The potential impact or severity.
- Any suggested fix or mitigation (optional but appreciated).

### Response Timeline

| Action                        | Timeframe       |
|-------------------------------|-----------------|
| Acknowledgment of report      | Within 48 hours |
| Initial assessment            | Within 5 days   |
| Patch or mitigation released  | Within 30 days  |

## 🛡️ Security Best Practices for Users

- Always use the **latest release** to benefit from security patches.
- Never commit secrets, API keys, or credentials to the repository.
- Use environment variables (`.env`) for sensitive configuration.
- When deploying with Docker, follow the principle of least privilege.
- Regularly review and rotate any tokens or keys used with this project.

## 🏷️ Disclosure Policy

- We follow **coordinated disclosure** — we will work with reporters to understand and fix the issue before any public disclosure.
- Credit will be given to reporters (unless they prefer anonymity) in the release notes once the fix is published.

---

Thank you for helping keep this project and its users safe. 🙏
