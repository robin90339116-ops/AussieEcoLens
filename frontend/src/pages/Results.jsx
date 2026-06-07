import { Button, Empty, Image as AntImage, Modal, Space, Tag, Typography, message } from 'antd';
import { ExternalLink, Eye, Image as ImageIcon, PlayCircle } from 'lucide-react';
import { useEffect, useMemo, useState } from 'react';
import { useLocation } from 'react-router-dom';
import { getErrorMessage, requestDownloadUrl } from '../api/client';

const readStoredResults = () => {
  try {
    return JSON.parse(sessionStorage.getItem('aussie-ecolens-results') || 'null');
  } catch {
    return null;
  }
};

export default function Results() {
  const location = useLocation();
  const stored = readStoredResults();
  const title = location.state?.title || stored?.title || 'Results';
  const items = useMemo(() => location.state?.items || stored?.items || [], [location.state, stored]);
  const [modalUrl, setModalUrl] = useState('');
  const [loadingUrl, setLoadingUrl] = useState('');

  useEffect(() => {
    if (location.state?.items) {
      sessionStorage.setItem('aussie-ecolens-results', JSON.stringify(location.state));
    }
  }, [location.state]);

  const handleOpenImage = async (item) => {
    // Resolve the full-size image directly from the original storage reference
    // via a fresh presigned GET URL. This avoids the fragile thumbnail-URL
    // exact-match lookup (Q3), which 404s when the stored thumbnail_url differs
    // from the displayed (presigned) one.
    const originalReference =
      item.original_s3_key ||
      item.originalS3Key ||
      item.original_storage_url ||
      item.original_url ||
      item.url ||
      item.thumbnail_storage_url ||
      item.thumbnail_url;
    if (!originalReference) {
      message.error('No preview URL is available for this result');
      return;
    }
    setLoadingUrl(item.id || originalReference);
    try {
      const originalUrl = await requestDownloadUrl(originalReference);
      setModalUrl(originalUrl);
    } catch (error) {
      message.error(getErrorMessage(error, 'Could not load full-size image'));
    } finally {
      setLoadingUrl('');
    }
  };

  return (
    <section className="page-grid single-column">
      <div className="page-heading">
        <Typography.Title level={2}>{title}</Typography.Title>
        <Typography.Text type="secondary">{items.length} matching files</Typography.Text>
      </div>

      {items.length === 0 ? (
        <div className="tool-panel">
          <Empty description="No results" />
        </div>
      ) : (
        <div className="gallery-grid">
          {items.map((item) => {
            const isVideo = item.type === 'video';
            const previewUrl = item.thumbnail_url || item.url || item.original_url;
            const originalUrl = item.original_url || item.url;
            const storageUrl =
              item.thumbnail_storage_url ||
              item.original_storage_url ||
              item.thumbnail_s3_key ||
              item.original_s3_key ||
              previewUrl;

            return (
              <article className="media-card" key={item.id || previewUrl}>
                <div className="media-frame">
                  {isVideo ? (
                    <div className="video-tile">
                      <PlayCircle size={42} />
                      <Typography.Text>Video file</Typography.Text>
                    </div>
                  ) : (
                    previewUrl ? (
                      <AntImage src={previewUrl} alt="Wildlife thumbnail" preview={false} />
                    ) : (
                      <div className="video-tile">
                        <ImageIcon size={42} />
                        <Typography.Text>Detected tags</Typography.Text>
                      </div>
                    )
                  )}
                </div>
                <div className="media-card-body">
                  <Space wrap>
                    {Object.entries(item.tags || {}).map(([species, count]) => (
                      <Tag color="green" key={species}>
                        {species} x {count}
                      </Tag>
                    ))}
                  </Space>
                  <Space className="card-actions">
                    {isVideo && originalUrl ? (
                      <Button
                        href={originalUrl}
                        target="_blank"
                        rel="noreferrer"
                        icon={<ExternalLink size={16} />}
                      >
                        Open
                      </Button>
                    ) : !isVideo && previewUrl ? (
                      <Button
                        loading={loadingUrl === (item.id || previewUrl)}
                        icon={<Eye size={16} />}
                        onClick={() => handleOpenImage(item)}
                      >
                        Full image
                      </Button>
                    ) : (
                      <Typography.Text type="secondary">No media URL</Typography.Text>
                    )}
                    <Typography.Text copyable ellipsis className="copy-url">
                      {storageUrl || item.original_key || item.file_id || 'No media URL'}
                    </Typography.Text>
                  </Space>
                </div>
              </article>
            );
          })}
        </div>
      )}

      <Modal
        title="Full-size image"
        open={Boolean(modalUrl)}
        footer={null}
        onCancel={() => setModalUrl('')}
        width={920}
      >
        {modalUrl && <img className="modal-image" src={modalUrl} alt="Full-size wildlife media" />}
      </Modal>
    </section>
  );
}
