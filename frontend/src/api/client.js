import axios from 'axios';
import { fetchAuthSession } from 'aws-amplify/auth';
import { config } from '../config';

const awsClient = axios.create({ baseURL: config.awsApiBaseUrl });
const gcpClient = axios.create({ baseURL: config.gcpApiBaseUrl || config.awsApiBaseUrl });

export const supportsFileListing = Boolean(config.paths.listFiles);

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

    const originalUrl =
      item.original_access_url ||
      item.originalAccessUrl ||
      item.original_url ||
      item.originalUrl ||
      item.fullUrl ||
      item.mediaUrl ||
      item.url ||
      item.original_raw_url ||
      item.thumbnail_url ||
      item.thumbnailUrl;
    const rawType = String(item.type || item.file_type || '').toLowerCase();
    const type =
      rawType.startsWith('video') || /\.(mp4|mov|webm)(?:$|[?#])/i.test(originalUrl || '')
        ? 'video'
        : 'image';
    const thumbnailUrl =
      item.thumbnail_access_url ||
      item.thumbnailAccessUrl ||
      item.thumbnail_url ||
      item.thumbnailUrl ||
      item.thumbnail ||
      item.previewUrl ||
      item.url ||
      (type === 'image' ? originalUrl : '');

    return {
      ...item,
      id: item.id || item.file_id || item.fileId || originalUrl || `result-${index}`,
      type,
      thumbnail_storage_url:
        item.thumbnail_storage_url ||
        item.thumbnail_raw_url ||
        item.thumbnail_s3_key ||
        item.thumbnailS3Key ||
        item.thumbnail_url ||
        thumbnailUrl,
      original_storage_url:
        item.original_storage_url ||
        item.original_raw_url ||
        item.original_s3_key ||
        item.originalS3Key ||
        item.original_url ||
        originalUrl,
      thumbnail_url: thumbnailUrl,
      original_url: originalUrl,
      url: item.url || originalUrl,
      tags: item.tags || item.detectedTags || {}
    };
  });
};

const getS3Key = (reference) => {
  if (!reference || typeof reference !== 'string') {
    return '';
  }

  const trimmed = reference.trim();
  if (!trimmed) {
    return '';
  }
  if (!trimmed.includes('://')) {
    return trimmed.replace(/^\/+/, '');
  }

  try {
    const url = new URL(trimmed);
    if (url.protocol === 's3:') {
      return url.pathname.replace(/^\/+/, '');
    }

    const host = url.hostname.toLowerCase();
    if (!host.includes('s3') || !host.endsWith('amazonaws.com')) {
      return '';
    }

    const path = decodeURIComponent(url.pathname.replace(/^\/+/, ''));
    if (host === 's3.amazonaws.com' || host.startsWith('s3.')) {
      return path.split('/').slice(1).join('/');
    }
    return path;
  } catch {
    return '';
  }
};

const isTemporaryMediaUrl = (reference) =>
  /^(blob:|data:)/i.test(reference || '') || /[?&]X-Amz-Signature=/i.test(reference || '');

const stripPresignedQuery = (reference) => {
  if (!/[?&]X-Amz-Signature=/i.test(reference || '')) {
    return reference;
  }

  try {
    const url = new URL(reference);
    return `${url.origin}${url.pathname}`;
  } catch {
    return reference;
  }
};

const prepareResultMedia = async (item) => {
  const isVideo = item.type === 'video';
  const thumbnailReference =
    item.thumbnail_s3_key ||
    item.thumbnailS3Key ||
    item.thumbnail_storage_url ||
    item.thumbnail_url;
  const originalReference =
    item.original_s3_key ||
    item.originalS3Key ||
    item.original_storage_url ||
    item.original_url ||
    item.url;

  const [thumbnailUrl, originalUrl] = await Promise.all([
    !isVideo && thumbnailReference
      ? requestDownloadUrl(thumbnailReference).catch(() => item.thumbnail_url)
      : Promise.resolve(item.thumbnail_url),
    isVideo && originalReference
      ? requestDownloadUrl(originalReference).catch(() => item.original_url)
      : Promise.resolve(item.original_url)
  ]);

  return {
    ...item,
    thumbnail_storage_url: item.thumbnail_storage_url || item.thumbnail_url,
    original_storage_url: item.original_storage_url || item.original_url,
    thumbnail_url: thumbnailUrl || item.thumbnail_url,
    original_url: originalUrl || item.original_url,
    url: isVideo ? originalUrl || item.url : item.url
  };
};

export const prepareMediaResults = async (responsePayload) =>
  Promise.all(normalizeResults(responsePayload).map(prepareResultMedia));

const checkDuplicateFile = async (checksum) => {
  if (!config.paths.checkDuplicate) {
    return null;
  }

  try {
    const { data } = await awsClient.post(config.paths.checkDuplicate, {
      checksum
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
  ensureBaseUrl(config.awsApiBaseUrl, 'AWS');

  const checksum = await hashFile(file);
  const duplicate = await checkDuplicateFile(checksum);
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
    filename: file.name,
    content_type: file.type || 'application/octet-stream',
    checksum
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
    uploadHeaders: payload.uploadHeaders || payload.upload_headers || {},
    checksum
  };
}

export async function requestDownloadUrl(s3UrlOrKey) {
  if (!s3UrlOrKey || isTemporaryMediaUrl(s3UrlOrKey)) {
    return s3UrlOrKey;
  }

  const fileKey = getS3Key(s3UrlOrKey);
  if (!fileKey) {
    return s3UrlOrKey;
  }

  ensureBaseUrl(config.awsApiBaseUrl, 'AWS');
  const { data } = await awsClient.post(config.paths.presigned, {
    action: 'GET',
    file_key: fileKey
  });
  const payload = unwrapResponsePayload(data);
  return payload.presigned_url || payload.presignedUrl || payload.url;
}

export async function uploadFileToS3(uploadUrl, file, uploadHeaders = {}, onProgress) {
  await axios.put(uploadUrl, file, {
    headers: {
      'Content-Type': file.type || 'application/octet-stream',
      ...(uploadHeaders || {})
    },
    onUploadProgress: (event) => {
      if (event.total) {
        onProgress?.(Math.round((event.loaded * 100) / event.total));
      }
    }
  });
}

export async function pollUploadStatus({ key, file }) {
  if (!config.paths.uploadStatus) {
    return {
      id: key || file.name,
      type: file.type,
      original_url: key || file.name,
      tags: {},
      processing_pending: true
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
  ensureBaseUrl(config.gcpApiBaseUrl || config.awsApiBaseUrl, 'GCP');
  const { data } = await gcpClient.post(config.paths.queryByTags, { tags, limit: 50 });
  return prepareMediaResults(data);
}

export async function queryBySpecies(species) {
  ensureBaseUrl(config.gcpApiBaseUrl || config.awsApiBaseUrl, 'GCP');
  const { data } = await gcpClient.post(config.paths.queryBySpecies, { species, limit: 50 });
  return prepareMediaResults(data);
}

export async function queryByThumbnailUrl(thumbnailUrl) {
  ensureBaseUrl(config.awsApiBaseUrl, 'AWS');
  const { data } = await awsClient.post(config.paths.thumbnailLookup, {
    thumbnail_url: stripPresignedQuery(thumbnailUrl)
  });
  return prepareMediaResults(data);
}

export async function resolveOriginalUrl(thumbnailUrl) {
  ensureBaseUrl(config.awsApiBaseUrl, 'AWS');
  const { data } = await awsClient.post(config.paths.thumbnailLookup, {
    thumbnail_url: stripPresignedQuery(thumbnailUrl)
  });
  const payload = unwrapResponsePayload(data);
  const originalReference =
    payload.original_s3_key ||
    payload.originalS3Key ||
    payload.original_url ||
    payload.originalUrl ||
    payload.fullUrl ||
    payload.presigned_url ||
    payload.url;
  return requestDownloadUrl(originalReference);
}

export async function queryByUploadedFile(file) {
  ensureBaseUrl(config.awsApiBaseUrl, 'AWS');
  const { data } = await awsClient.post(config.paths.queryByFile, {
    image_base64: await fileToBase64(file),
    filename: file.name,
    content_type: file.type || 'image/jpeg',
    limit: 50
  });
  return prepareMediaResults(data);
}

export async function bulkUpdateTags({ urls, tags, operation }) {
  ensureBaseUrl(config.awsApiBaseUrl, 'AWS');
  const { data } = await awsClient.post(config.paths.tagEdit, {
    urls,
    tags,
    operation
  });
  return unwrapResponsePayload(data);
}

export async function deleteFiles(urls) {
  ensureBaseUrl(config.awsApiBaseUrl, 'AWS');
  const { data } = await awsClient.delete(config.paths.deleteFiles, {
    data: { urls }
  });
  return unwrapResponsePayload(data);
}

export async function listFiles() {
  if (!config.paths.listFiles) {
    throw new Error('File listing API is not configured.');
  }
  ensureBaseUrl(config.awsApiBaseUrl, 'AWS');
  const { data } = await awsClient.get(config.paths.listFiles);
  return prepareMediaResults(data);
}

export async function getSubscriptions(userEmail) {
  ensureBaseUrl(config.awsApiBaseUrl, 'AWS');
  const { data } = await awsClient.get(config.paths.subscriptions, {
    params: { email: userEmail }
  });
  const payload = unwrapResponsePayload(data);
  const records = Array.isArray(payload?.subscriptions) ? payload.subscriptions : [];
  return [
    ...new Set(
      records.flatMap((record) => record?.species_list || record?.species || [])
    )
  ].map((species) => String(species).replaceAll('_', ' '));
}

export async function saveSubscriptions(speciesList, userEmail) {
  ensureBaseUrl(config.awsApiBaseUrl, 'AWS');
  const { data } = await awsClient.post(config.paths.subscriptions, {
    action: 'subscribe',
    email: userEmail,
    species: speciesList
  });
  const payload = unwrapResponsePayload(data);
  const saved = payload?.subscription?.species_list || payload?.subscription?.species;
  return (Array.isArray(saved) ? saved : speciesList).map((species) =>
    String(species).replaceAll('_', ' ')
  );
}

export async function unsubscribeSpecies(species, userEmail) {
  ensureBaseUrl(config.awsApiBaseUrl, 'AWS');
  const { data } = await awsClient.post(config.paths.subscriptions, {
    action: 'unsubscribe',
    email: userEmail,
    species
  });
  const payload = unwrapResponsePayload(data);
  const remaining = payload?.local_subscription?.remaining;
  if (Array.isArray(remaining)) {
    return remaining.map((item) => String(item).replaceAll('_', ' '));
  }
  return getSubscriptions(userEmail);
}
