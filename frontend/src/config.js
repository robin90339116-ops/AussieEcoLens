import { Amplify } from 'aws-amplify';

const env = import.meta.env;
const mockFlag = env.VITE_USE_MOCKS;
const apiRootsMissing = !env.VITE_AWS_API_BASE_URL && !env.VITE_GCP_API_BASE_URL;

export const config = {
  awsRegion: env.VITE_AWS_REGION || 'ap-southeast-2',
  cognitoUserPoolId: env.VITE_COGNITO_USER_POOL_ID || '',
  cognitoClientId: env.VITE_COGNITO_CLIENT_ID || '',
  awsApiBaseUrl: env.VITE_AWS_API_BASE_URL || '',
  gcpApiBaseUrl: env.VITE_GCP_API_BASE_URL || '',
  useMocks: mockFlag ? mockFlag === 'true' : apiRootsMissing,
  paths: {
    presigned: env.VITE_PRESIGNED_PATH || '/presigned-url',
    uploadStatus: env.VITE_UPLOAD_STATUS_PATH || '/files/status',
    queryByTags: env.VITE_Q1_PATH || '/query/tags',
    queryBySpecies: env.VITE_Q2_PATH || '/query/species',
    thumbnailLookup: env.VITE_Q3_PATH || '/query/thumbnail',
    queryByFile: env.VITE_Q4_PATH || '/query/file',
    tagEdit: env.VITE_Q5_PATH || '/tags/bulk',
    deleteFiles: env.VITE_Q6_PATH || '/files/delete',
    listFiles: env.VITE_LIST_FILES_PATH || '/files',
    subscriptions: env.VITE_SUBSCRIPTIONS_PATH || '/subscriptions'
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
