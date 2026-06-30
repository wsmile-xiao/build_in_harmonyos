# saml2aws

CLI tool for AWS SAML authentication - login to AWS using SAML identity providers.

## Description
saml2aws is a command line tool that helps with SAML access to the AWS token service. It enables users to authenticate with a SAML 2.0 Identity Provider (IdP) and obtain temporary AWS credentials via AWS STS.

## Key Features
- SAML login to AWS via multiple IdP providers (Okta, AzureAD, ADFS, etc.)
- Credential process support for AWS CLI
- Browser-based authentication
- Session management and credential caching

## OpenHarmony Build Notes
- Build system: Go (custom)
- CGO_ENABLED=0 (static binary, U2F/HID disabled due to sockaddr_storage conflict)
- Version injection via source code modification
- ELF-signed for OpenHarmony execution

## Available Versions
| Version | Status | Notes |
|---------|--------|-------|
| homebrew (2.36.19) | published | Static binary, CGO_ENABLED=0 |

## Homepage
https://github.com/Versent/saml2aws
