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
  return session.tokens?.idToken?.toString() || session.tokens?.accessToken?.toString() || '';
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

const hasResultShape = (payload) =>
  Boolean(
    payload &&
      (Array.isArray(payload) ||
        payload.items ||
        payload.results ||
        payload.files ||
        payload.matches ||
        payload.file_id ||
        payload.fileId ||
        payload.original_url ||
        payload.thumbnail_url ||
        payload.tags ||
        payload.predictions)
  );

const unwrapResponsePayload = (payload) => {
  if (typeof payload?.body === 'string') {
    try {
      const parsed = JSON.parse(payload.body);
      return !hasResultShape(parsed) && hasResultShape(parsed?.data) ? parsed.data : parsed;
    } catch {
      return payload;
    }
  }
  const unwrapped = payload?.body && typeof payload.body === 'object' ? payload.body : payload;
  return !hasResultShape(unwrapped) && hasResultShape(unwrapped?.data) ? unwrapped.data : unwrapped;
};

const sha256Hex = async (buffer) => {
  if (!globalThis.crypto?.subtle) {
    throw new Error('SHA-256 hashing requires a secure browser context with Web Crypto support.');
  }
  const digest = await globalThis.crypto.subtle.digest('SHA-256', buffer);
  return Array.from(new Uint8Array(digest))
    .map((byte) => byte.toString(16).padStart(2, '0'))
    .join('');
};

const hashFile = async (file) => {
  const buffer = await file.arrayBuffer();
  return sha256Hex(buffer);
};

const fileToBase64 = (file) =>
  new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => {
      const result = String(reader.result || '');
      resolve(result.includes(',') ? result.split(',')[1] : result);
    };
    reader.onerror = () => reject(reader.error || new Error('Could not read file'));
    reader.readAsDataURL(file);
  });

const subscriptionsKey = (userEmail) => `aussie-ecolens-subscriptions:${userEmail || 'current-user'}`;

const readCachedSubscriptions = (userEmail) => {
  if (typeof window === 'undefined') {
    return [];
  }
  try {
    const cached = window.localStorage.getItem(subscriptionsKey(userEmail));
    const parsed = cached ? JSON.parse(cached) : [];
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
};

const writeCachedSubscriptions = (userEmail, speciesList) => {
  const next = [...new Set(speciesList)].filter(Boolean);
  if (typeof window !== 'undefined') {
    try {
      window.localStorage.setItem(subscriptionsKey(userEmail), JSON.stringify(next));
    } catch {
      // UI cache is best effort; the API request above is the source of truth.
    }
  }
  return next;
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
      file_hash: fileHash,
      checksum: fileHash
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
    file_hash: fileHash,
    checksum: fileHash
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
  const { data } = await gcpClient.post(config.paths.queryByTags, { tags, limit: 50 });
  return normalizeResults(data);
}

export async function queryBySpecies(species) {
  if (config.useMocks) {
    return normalizeResults(await mockQueryBySpecies(species));
  }
  ensureBaseUrl(config.gcpApiBaseUrl || config.awsApiBaseUrl, 'GCP');
  const { data } = await gcpClient.post(config.paths.queryBySpecies, { species, limit: 50 });
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
  const { data } = await awsClient.post(config.paths.queryByFile, {
    image_base64: await fileToBase64(file),
    content_type: file.type || 'image/jpeg',
    limit: 50
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
  const results = await Promise.all(
    urls.map(async (url) => {
      const { data } = await awsClient.delete(config.paths.deleteFiles, {
        data: { url }
      });
      return unwrapResponsePayload(data);
    })
  );
  return {
    deleted: results.length,
    results
  };
}

export async function listFiles() {
  if (config.useMocks) {
    return normalizeResults(await mockListFiles());
  }
  if (!config.paths.listFiles) {
    return [];
  }
  ensureBaseUrl(config.awsApiBaseUrl, 'AWS');
  const { data } = await awsClient.get(config.paths.listFiles);
  return normalizeResults(data);
}

export async function getSubscriptions(userEmail) {
  if (config.useMocks) {
    return mockGetSubscriptions();
  }
  return readCachedSubscriptions(userEmail);
}

export async function saveSubscriptions(speciesList, userEmail) {
  if (config.useMocks) {
    return mockSaveSubscriptions(speciesList);
  }
  ensureBaseUrl(config.awsApiBaseUrl, 'AWS');
  await awsClient.post(config.paths.subscriptions, {
    action: 'subscribe',
    user_email: userEmail,
    species_list: speciesList
  });
  return writeCachedSubscriptions(userEmail, speciesList);
}

export async function unsubscribeSpecies(species, userEmail) {
  if (config.useMocks) {
    return mockUnsubscribeSpecies(species);
  }
  ensureBaseUrl(config.awsApiBaseUrl, 'AWS');
  await awsClient.post(config.paths.subscriptions, {
    action: 'unsubscribe',
    user_email: userEmail,
    species_list: [species]
  });
  const remaining = readCachedSubscriptions(userEmail).filter((item) => item !== species);
  return writeCachedSubscriptions(userEmail, remaining);
}
