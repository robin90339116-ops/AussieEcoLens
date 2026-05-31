import { Button, Descriptions, Progress, Space, Steps, Tag, Typography, Upload, message } from 'antd';
import { Image as ImageIcon, UploadCloud } from 'lucide-react';
import { useMemo, useState } from 'react';
import {
  normalizeResults,
  pollUploadStatus,
  requestPresignedUrl,
  uploadFileToS3
} from '../api/client';

const { Dragger } = Upload;

const MAX_IMAGE_SIZE = 20 * 1024 * 1024;
const MAX_VIDEO_SIZE = 200 * 1024 * 1024;
const allowedTypes = ['image/jpeg', 'image/png', 'video/mp4', 'video/quicktime'];

const statusIndex = {
  idle: 0,
  presign: 0,
  upload: 1,
  processing: 2,
  complete: 3
};

export default function UploadPage() {
  const [file, setFile] = useState(null);
  const [progress, setProgress] = useState(0);
  const [status, setStatus] = useState('idle');
  const [result, setResult] = useState(null);
  const [error, setError] = useState('');

  const validFile = useMemo(() => {
    if (!file) {
      return false;
    }
    if (!allowedTypes.includes(file.type)) {
      return false;
    }
    const limit = file.type.startsWith('video') ? MAX_VIDEO_SIZE : MAX_IMAGE_SIZE;
    return file.size <= limit;
  }, [file]);

  const beforeUpload = (nextFile) => {
    const limit = nextFile.type.startsWith('video') ? MAX_VIDEO_SIZE : MAX_IMAGE_SIZE;
    if (!allowedTypes.includes(nextFile.type)) {
      message.error('Supported formats: JPG, PNG, MP4, MOV');
      return Upload.LIST_IGNORE;
    }
    if (nextFile.size > limit) {
      message.error(nextFile.type.startsWith('video') ? 'Video limit is 200 MB' : 'Image limit is 20 MB');
      return Upload.LIST_IGNORE;
    }
    setFile(nextFile);
    setResult(null);
    setError('');
    setProgress(0);
    setStatus('idle');
    return false;
  };

  const handleUpload = async () => {
    if (!file || !validFile) {
      return;
    }
    setError('');
    setResult(null);
    try {
      setStatus('presign');
      const presigned = await requestPresignedUrl(file);
      if (presigned.duplicate || presigned.status === 'duplicate') {
        setStatus('complete');
        setResult(presigned.item || presigned.file || presigned);
        message.warning('Duplicate file detected');
        return;
      }

      const uploadUrl = presigned.uploadUrl || presigned.url || presigned.presignedUrl;
      if (!uploadUrl) {
        throw new Error('Presigned upload URL missing from API response');
      }

      setStatus('upload');
      await uploadFileToS3(uploadUrl, file, setProgress);
      setStatus('processing');
      const uploadResult = await pollUploadStatus({
        key: presigned.key || presigned.objectKey,
        file
      });
      setResult(normalizeResults({ items: [uploadResult] })[0] || uploadResult);
      setStatus('complete');
      message.success('Upload complete');
    } catch (uploadError) {
      setError(uploadError.message || 'Upload failed');
      setStatus('idle');
    }
  };

  return (
    <section className="page-grid upload-grid">
      <div className="page-heading">
        <Typography.Title level={2}>Upload media</Typography.Title>
        <Typography.Text type="secondary">Images and videos are stored through presigned S3 upload.</Typography.Text>
      </div>

      <div className="tool-panel">
        <Dragger
          maxCount={1}
          accept=".jpg,.jpeg,.png,.mp4,.mov"
          beforeUpload={beforeUpload}
          onRemove={() => {
            setFile(null);
            setResult(null);
            setProgress(0);
          }}
          fileList={file ? [file] : []}
        >
          <p className="ant-upload-drag-icon">
            <UploadCloud size={34} />
          </p>
          <p className="ant-upload-text">Drop media here or select a file</p>
        </Dragger>

        <Space className="panel-actions">
          <Button
            type="primary"
            icon={<UploadCloud size={17} />}
            disabled={!validFile || status !== 'idle'}
            loading={status !== 'idle' && status !== 'complete'}
            onClick={handleUpload}
          >
            Start upload
          </Button>
          {file && (
            <Typography.Text type="secondary">
              {(file.size / 1024 / 1024).toFixed(2)} MB
            </Typography.Text>
          )}
        </Space>

        <Steps
          size="small"
          current={statusIndex[status]}
          items={[
            { title: 'URL' },
            { title: 'Upload' },
            { title: 'Recognition' },
            { title: 'Done' }
          ]}
        />
        {status === 'upload' && <Progress percent={progress} />}
        {error && <Typography.Text type="danger">{error}</Typography.Text>}
      </div>

      <div className="tool-panel result-panel">
        <Typography.Title level={4}>Recognition result</Typography.Title>
        {result ? (
          <>
            {result.thumbnail_url && result.type !== 'video' ? (
              <img className="result-preview" src={result.thumbnail_url} alt="Uploaded result" />
            ) : (
              <div className="empty-preview">
                <ImageIcon size={34} />
              </div>
            )}
            <Descriptions size="small" column={1}>
              <Descriptions.Item label="Type">{result.type || file?.type || 'media'}</Descriptions.Item>
              <Descriptions.Item label="URL">
                <Typography.Text copyable ellipsis>
                  {result.original_url || result.url || 'Pending'}
                </Typography.Text>
              </Descriptions.Item>
            </Descriptions>
            <Space wrap>
              {Object.entries(result.tags || {}).map(([species, count]) => (
                <Tag key={species} color="green">
                  {species} x {count}
                </Tag>
              ))}
            </Space>
          </>
        ) : (
          <div className="empty-state">No completed upload yet</div>
        )}
      </div>
    </section>
  );
}

