import { Amplify } from 'aws-amplify';

const env = import.meta.env;
const mockFlag = env.VITE_USE_MOCKS;
const apiRootsMissing =
  !env.VITE_AWS_API_BASE_URL && !env.VITE_GCP_API_BASE_URL && !env.VITE_ML_API_BASE_URL;

export const config = {
  awsRegion: env.VITE_AWS_REGION || 'us-east-1',
  cognitoUserPoolId: env.VITE_COGNITO_USER_POOL_ID || '',
  cognitoClientId: env.VITE_COGNITO_CLIENT_ID || '',
  awsApiBaseUrl: env.VITE_AWS_API_BASE_URL || '',
  gcpApiBaseUrl: env.VITE_GCP_API_BASE_URL || '',
  mlApiBaseUrl: env.VITE_ML_API_BASE_URL || '',
  mlApiRequiresAuth: env.VITE_ML_API_REQUIRES_AUTH === 'true',
  useMocks: mockFlag ? mockFlag === 'true' : apiRootsMissing,
  paths: {
    presigned: env.VITE_PRESIGNED_PATH || '/upload/presigned',
    checkDuplicate: env.VITE_UPLOAD_CHECK_DUP_PATH || '/upload/check-dup',
    uploadStatus: env.VITE_UPLOAD_STATUS_PATH || '',
    queryByTags: env.VITE_Q1_PATH || '/query/by-tags',
    queryBySpecies: env.VITE_Q2_PATH || '/query/by-species',
    thumbnailLookup: env.VITE_Q3_PATH || '/query/by-thumbnail',
    queryByFile: env.VITE_Q4_PATH || '/query/by-file',
    mlUpload: env.VITE_ML_UPLOAD_PATH || '/v1/tag/upload',
    tagEdit: env.VITE_Q5_PATH || '/tags/modify',
    deleteFiles: env.VITE_Q6_PATH || '/files',
    listFiles: env.VITE_LIST_FILES_PATH || '/files',
    subscriptions: env.VITE_SUBSCRIPTIONS_PATH || '/notifications/subscribe'
  }
};

export const authConfigured = Boolean(
  config.cognitoUserPoolId && config.cognitoClientId && config.awsRegion
);

if (authConfigured) {
  Amplify.configure({
    Auth: {
      Cognito: {
        userPoolId: config.cognitoUserPoolId,
        userPoolClientId: config.cognitoClientId,
        loginWith: {
          email: true
        }
      }
    }
  });
}
