# Aussie EcoLens — Authentication Module (Cognito) Setup

Owner: Ruitong Yang (ryan0099)
Last updated: 2026-06-02

---

## 1. Overview

User registration, login, and JWT token issuance are implemented with AWS Cognito.
The frontend obtains a JWT after login and includes it when calling the API; the backend verifies the JWT to confirm the user's identity.

> The current configuration is set up in the test account ryan0099 (983018774467) to verify that the flow works.
> The final account will be decided during the integration phase; if it differs, rebuild using the commands in Section 3.

---

## 2. Key Configuration Values

| Item | Value |
|------|-------|
| Region | `us-east-1` |
| User Pool ID | `us-east-1_lb6SisPnD` |
| App Client ID | `fvmq1uralbq80r9q7nrnonh73` |
| Hosted UI Domain | `us-east-1lb6sispnd.auth.us-east-1.amazoncognito.com` |
| Client Secret | None (SPA public client) |

---

## 3. Rebuild + Verification Steps

> Prerequisite: AWS CLI credentials are refreshed and `aws sts get-caller-identity` succeeds.

### 3.1 Register a test user
```bash
aws cognito-idp sign-up \
  --client-id fvmq1uralbq80r9q7nrnonh73 \
  --username testuser@example.com \
  --password '<PASSWORD>' \
  --user-attributes Name=email,Value=testuser@example.com Name=given_name,Value=Test Name=family_name,Value=User
```

### 3.2 Manually confirm the user
> The Learner Lab's SES is in sandbox mode, so the verification email cannot be sent. Use the admin command to confirm directly.
```bash
aws cognito-idp admin-confirm-sign-up \
  --user-pool-id us-east-1_lb6SisPnD \
  --username testuser@example.com
```

### 3.3 Enable password-based login (CLI testing only)
> SPA clients do not enable USER_PASSWORD_AUTH by default. This is enabled here for command-line testing;
> the frontend uses SRP / Hosted UI and is not affected.
```bash
aws cognito-idp update-user-pool-client \
  --user-pool-id us-east-1_lb6SisPnD \
  --client-id fvmq1uralbq80r9q7nrnonh73 \
  --explicit-auth-flows ALLOW_USER_PASSWORD_AUTH ALLOW_REFRESH_TOKEN_AUTH ALLOW_USER_SRP_AUTH
```

### 3.4 Log in to obtain a JWT
```bash
aws cognito-idp initiate-auth \
  --client-id fvmq1uralbq80r9q7nrnonh73 \
  --auth-flow USER_PASSWORD_AUTH \
  --auth-parameters USERNAME=testuser@example.com,PASSWORD='<PASSWORD>'
```
A response containing `AuthenticationResult` with `IdToken` / `AccessToken` / `RefreshToken` indicates success.
The IdToken is the JWT; it expires in 1 hour by default and is reissued on each login.
