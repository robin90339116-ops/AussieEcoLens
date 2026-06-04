# Aussie EcoLens — API Gateway Setup

Owner: Ruitong Yang (ryan0099)
Last updated: 2026-06-04

> Built in account ryan0099 (983018774467), region us-east-1.

---

## 1. What's done

- REST API created: **EcoLensAPI**, ID = `66h13afw3g`
- Cognito Authorizer created: **CognitoAuth** (type COGNITO_USER_POOLS), linked to user pool `us-east-1_lb6SisPnD`
- Resource tree created (paths only, no methods yet):

```
/
├── /upload
│   ├── /presigned
│   └── /check-dup
├── /query
│   ├── /by-tags
│   ├── /by-species
│   ├── /by-thumbnail
│   └── /by-file
├── /tags/modify
├── /files
└── /notifications/subscribe
```

- Methods: none yet (methods require the Lambda functions to exist first).

## 2. Key IDs

| Item | Value |
|------|-------|
| API ID | `66h13afw3g` |
| Authorizer name | CognitoAuth |
| User Pool (linked) | `us-east-1_lb6SisPnD` |
| Region | us-east-1 |

> Resource IDs are stored in the cloud. Query anytime with:
> ```
> aws apigateway get-resources --rest-api-id 66h13afw3g --region us-east-1 --query 'items[*].[path,id]' --output text
> ```

---

## 3. upload/presigned endpoint (updated 2026-06-04)

The "Methods: none yet" line in Section 1 is outdated: the POST method on /upload/presigned is now live, integrated with EcoLens-Presigned (Lambda Proxy), protected by the Cognito authorizer, CORS configured, deployed to prod.

Invoke URL:
https://66h13afw3g.execute-api.us-east-1.amazonaws.com/prod/upload/presigned

How to call (frontend):
- Header: Authorization: Bearer <IdToken from login>
- Body: {"filename": "xxx.jpg", "content_type": "image/jpeg"}
- Returns: upload_url, file_key, bucket
- PUT the file directly to upload_url to upload to S3

Tested: without token returns 401, with token returns 200 with the upload URL. Working.
