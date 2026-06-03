import axios from 'axios';
import { fetchAuthSession } from 'aws-amplify/auth';
import { config } from '../config';
import {
  mockBulkUpdateTags,
  mockDeleteFiles,
  mockGetSubscriptions,
  mockListFiles,
  mockPollUploadStatus,
  mockQueryBySpecies,
  mockQueryByTags,
  mockQueryByUploadedFile,
  mockRequestPresignedUrl,
  mockResolveOriginalUrl,
  mockSaveSubscriptions,
  mockUnsubscribeSpecies,
  mockUploadFileToS3
} from './mock';

const awsClient = axios.create({ baseURL: config.awsApiBaseUrl });
const gcpClient = axios.create({ baseURL: config.gcpApiBaseUrl || config.awsApiBaseUrl });

const getToken = async (forceRefresh = false) => {
  const session = await fetchAuthSession({ forceRefresh });
  return session.tokens?.accessToken?.toString() || session.tokens?.idToken?.toString() || '';
};

const attachAuth = async (request) => {
  const token = await getToken();
  if (token) {
    request.headers.Authorization = `Bearer ${token}`;
  }
  return request;
};

awsClient.interceptors.request.use(attachAuth);
gcpClient.interceptors.request.use(attachAuth);

const retryWithFreshToken = async (error) => {
  const originalRequest = error.config;

  if (error.response?.status !== 401 || !originalRequest || originalRequest._authRetry) {
    return Promise.reject(error);
  }

  originalRequest._authRetry = true;
  const token = await getToken(true);
  if (token) {
    originalRequest.headers = originalRequest.headers || {};
    originalRequest.headers.Authorization = `Bearer ${token}`;
  }
  return axios(originalRequest);
};

awsClient.interceptors.response.use((response) => response, retryWithFreshToken);
gcpClient.interceptors.response.use((response) => response, retryWithFreshToken);

const ensureBaseUrl = (baseUrl, provider) => {
  if (!baseUrl) {
    throw new Error(`${provider} API base URL is missing. Set it in frontend/.env.`);
  }
};

const unwrapResponsePayload = (payload) => {
  if (typeof payload?.body === 'string') {
    try {
      return JSON.parse(payload.body);
    } catch {
      return payload;
    }
  }
  return payload?.body && typeof payload.body === 'object' ? payload.body : payload;
};

const hashFile = async (file) => {
  const buffer = await file.arrayBuffer();
  const digest = await crypto.subtle.digest('SHA-256', buffer);
  return [...new Uint8Array(digest)].map((byte) => byte.toString(16).padStart(2, '0')).join('');
};

export const getErrorMessage = (error, fallback = 'Request failed') => {
  if (typeof error === 'string') {
    return error;
  }

  const data = error?.response?.data;
  if (typeof data === 'string') {
    return data;
  }
  const payload = unwrapResponsePayload(data);

  return (
    payload?.message ||
    payload?.error ||
    payload?.detail ||
    error?.message ||
    fallback
  );
};

export const normalizeResults = (responsePayload) => {
  const payload = unwrapResponsePayload(responsePayload);
  const singleMetadata =
    payload &&
    !Array.isArray(payload) &&
    payload.status !== 'error' &&
    (payload.file_id || payload.fileId || payload.original_url || payload.thumbnail_url || payload.tags || payload.predictions);

  const rawItems =
    payload?.items ||
    payload?.results ||
    payload?.files ||
    payload?.matches ||
    (singleMetadata ? [payload] : null) ||
    (Array.isArray(payload) ? payload : []);

  return rawItems.map((item, index) => {
    if (typeof item === 'string') {
      return {
        id: item,
        type: /\.(mp4|mov|webm)$/i.test(item) ? 'video' : 'image',
        url: item,
        thumbnail_url: item,
        original_url: item,
        tags: {}
      };
    }

    const thumbnailUrl =
      item.thumbnail_url || item.thumbnailUrl || item.thumbnail || item.previewUrl || item.url;
    const originalUrl =
      item.original_url || item.originalUrl || item.fullUrl || item.mediaUrl || item.url || thumbnailUrl;
    const type =
      item.type ||
      item.file_type ||
      (/\.(mp4|mov|webm)$/i.test(originalUrl || '') ? 'video' : 'image');

    return {
      ...item,
      id: item.id || item.file_id || item.fileId || originalUrl || `result-${index}`,
      type,
      thumbnail_url: thumbnailUrl,
      original_url: originalUrl,
      url: item.url || originalUrl,
      tags: item.tags || item.detectedTags || {}
    };
  });
};

const checkDuplicateFile = async (file, fileHash) => {
  if (!config.paths.checkDuplicate) {
    return null;
  }

  try {
    const { data } = await awsClient.post(config.paths.checkDuplicate, {
      file_hash: fileHash
    });
    return unwrapResponsePayload(data);
  } catch (error) {
    if (error.response?.status === 409) {
      return unwrapResponsePayload(error.response.data);
    }
    throw error;
  }
};

export const tagsArrayToObject = (rows) =>
  rows.reduce((acc, row) => {
    if (row?.species) {
      acc[row.species] = Number(row.count || 1);
    }
    return acc;
  }, {});

export async function requestPresignedUrl(file) {
  if (config.useMocks) {
    return mockRequestPresignedUrl(file);
  }
  ensureBaseUrl(config.awsApiBaseUrl, 'AWS');

  const fileHash = await hashFile(file);
  const duplicate = await checkDuplicateFile(file, fileHash);
  if (duplicate?.duplicate) {
    const existingFile = duplicate.existing_file || duplicate.existingFile;
    return {
      ...duplicate,
      duplicate: true,
      original_url: existingFile,
      url: existingFile,
      tags: {}
    };
  }

  const { data } = await awsClient.post(config.paths.presigned, {
    action: 'PUT',
    filename: file.name,
    content_type: file.type || 'application/octet-stream',
    file_hash: fileHash
  });
  const payload = unwrapResponsePayload(data);
  return {
    ...payload,
    uploadUrl:
      payload.uploadUrl ||
      payload.upload_url ||
      payload.presignedUrl ||
      payload.presigned_url ||
      payload.url,
    key: payload.key || payload.file_key || payload.objectKey,
    fileHash
  };
}

export async function requestDownloadUrl(s3UrlOrKey) {
  if (config.useMocks) {
    return s3UrlOrKey;
  }
  ensureBaseUrl(config.awsApiBaseUrl, 'AWS');
  const { data } = await awsClient.post(config.paths.presigned, {
    action: 'GET',
    s3_url: s3UrlOrKey
  });
  const payload = unwrapResponsePayload(data);
  return payload.presigned_url || payload.presignedUrl || payload.url;
}

export async function uploadFileToS3(uploadUrl, file, onProgress) {
  if (config.useMocks || uploadUrl?.startsWith('mock://')) {
    return mockUploadFileToS3(uploadUrl, file, onProgress);
  }
  await axios.put(uploadUrl, file, {
    headers: {
      'Content-Type': file.type || 'application/octet-stream'
    },
    onUploadProgress: (event) => {
      if (event.total) {
        onProgress?.(Math.round((event.loaded * 100) / event.total));
      }
    }
  });
}

export async function pollUploadStatus({ key, file }) {
  if (config.useMocks) {
    return mockPollUploadStatus(file);
  }
  if (!config.paths.uploadStatus) {
    return {
      id: key || file.name,
      type: file.type,
      original_url: key || file.name,
      tags: {}
    };
  }
  ensureBaseUrl(config.awsApiBaseUrl, 'AWS');
  const { data } = await awsClient.get(config.paths.uploadStatus, {
    params: {
      key,
      fileName: file.name
    }
  });
  const payload = unwrapResponsePayload(data);
  return payload?.item || payload?.file || payload;
}

export async function queryByTags(tags) {
  if (config.useMocks) {
    return normalizeResults(await mockQueryByTags(tags));
  }
  ensureBaseUrl(config.gcpApiBaseUrl || config.awsApiBaseUrl, 'GCP');
  const { data } = await gcpClient.post(config.paths.queryByTags, { tags });
  return normalizeResults(data);
}

export async function queryBySpecies(species) {
  if (config.useMocks) {
    return normalizeResults(await mockQueryBySpecies(species));
  }
  ensureBaseUrl(config.gcpApiBaseUrl || config.awsApiBaseUrl, 'GCP');
  const { data } = await gcpClient.post(config.paths.queryBySpecies, { species });
  return normalizeResults(data);
}

export async function resolveOriginalUrl(thumbnailUrl) {
  if (config.useMocks) {
    return mockResolveOriginalUrl(thumbnailUrl);
  }
  ensureBaseUrl(config.awsApiBaseUrl, 'AWS');
  const { data } = await awsClient.post(config.paths.thumbnailLookup, { thumbnail_url: thumbnailUrl });
  const payload = unwrapResponsePayload(data);
  return payload.original_url || payload.originalUrl || payload.fullUrl || payload.presigned_url || payload.url;
}

export async function queryByUploadedFile(file) {
  if (config.useMocks) {
    return normalizeResults(await mockQueryByUploadedFile(file));
  }
  ensureBaseUrl(config.awsApiBaseUrl, 'AWS');
  const formData = new FormData();
  formData.append('file', file);
  const { data } = await awsClient.post(config.paths.queryByFile, formData, {
    headers: { 'Content-Type': 'multipart/form-data' }
  });
  return normalizeResults(data);
}

export async function bulkUpdateTags({ urls, tags, operation }) {
  if (config.useMocks) {
    return mockBulkUpdateTags({ urls, tags, operation });
  }
  ensureBaseUrl(config.awsApiBaseUrl, 'AWS');
  const { data } = await awsClient.post(config.paths.tagEdit, {
    urls,
    tags,
    operation
  });
  return unwrapResponsePayload(data);
}

export async function deleteFiles(urls) {
  if (config.useMocks) {
    return mockDeleteFiles(urls);
  }
  ensureBaseUrl(config.awsApiBaseUrl, 'AWS');
  const { data } = await awsClient.post(config.paths.deleteFiles, { urls });
  return unwrapResponsePayload(data);
}

export async function listFiles() {
  if (config.useMocks) {
    return normalizeResults(await mockListFiles());
  }
  ensureBaseUrl(config.awsApiBaseUrl, 'AWS');
  const { data } = await awsClient.get(config.paths.listFiles);
  return normalizeResults(data);
}

export async function getSubscriptions() {
  if (config.useMocks) {
    return mockGetSubscriptions();
  }
  ensureBaseUrl(config.awsApiBaseUrl, 'AWS');
  const { data } = await awsClient.get(config.paths.subscriptions);
  const payload = unwrapResponsePayload(data);
  return payload.species || payload.subscriptions || payload.items || [];
}

export async function saveSubscriptions(speciesList) {
  if (config.useMocks) {
    return mockSaveSubscriptions(speciesList);
  }
  ensureBaseUrl(config.awsApiBaseUrl, 'AWS');
  const { data } = await awsClient.post(config.paths.subscriptions, { species: speciesList });
  return unwrapResponsePayload(data);
}

export async function unsubscribeSpecies(species) {
  if (config.useMocks) {
    return mockUnsubscribeSpecies(species);
  }
  ensureBaseUrl(config.awsApiBaseUrl, 'AWS');
  const { data } = await awsClient.delete(config.paths.subscriptions, { data: { species } });
  return unwrapResponsePayload(data);
}
