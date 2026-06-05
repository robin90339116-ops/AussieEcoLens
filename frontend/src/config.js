import { Amplify } from 'aws-amplify';

const env = import.meta.env;
const mockFlag = env.VITE_USE_MOCKS;

export const config = {
  awsRegion: env.VITE_AWS_REGION || 'us-east-1',
  cognitoUserPoolId: env.VITE_COGNITO_USER_POOL_ID || '',
  cognitoClientId: env.VITE_COGNITO_CLIENT_ID || '',
  awsApiBaseUrl: env.VITE_AWS_API_BASE_URL || '',
  gcpApiBaseUrl: env.VITE_GCP_API_BASE_URL || '',
  useMocks: mockFlag === 'true',
  paths: {
    presigned: env.VITE_PRESIGNED_PATH || '/upload/presigned',
    checkDuplicate: env.VITE_UPLOAD_CHECK_DUP_PATH || '/upload/check-dup',
    uploadStatus: env.VITE_UPLOAD_STATUS_PATH || '',
    queryByTags: env.VITE_Q1_PATH || '/query/by-tags',
    queryBySpecies: env.VITE_Q2_PATH || '/query/by-species',
    thumbnailLookup: env.VITE_Q3_PATH || '/query/by-thumbnail',
    queryByFile: env.VITE_Q4_PATH || '/query/by-file',
    tagEdit: env.VITE_Q5_PATH || '/tags/modify',
    deleteFiles: env.VITE_Q6_PATH || '/files',
    listFiles: env.VITE_LIST_FILES_PATH || '',
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
