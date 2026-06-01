import { Button, Empty, Form, Input, Modal, Space, Table, Tag, Typography, message } from 'antd';
import { RefreshCw, Trash2 } from 'lucide-react';
import { useMemo, useState } from 'react';
import { deleteFiles, getErrorMessage, listFiles } from '../api/client';

const parseLines = (value = '') =>
  value
    .split(/\n+/)
    .map((line) => line.trim())
    .filter(Boolean);

export default function DeleteFiles() {
  const [rows, setRows] = useState([]);
  const [selectedKeys, setSelectedKeys] = useState([]);
  const [loading, setLoading] = useState(false);
  const [confirmOpen, setConfirmOpen] = useState(false);

  const selectedUrls = useMemo(
    () => rows.filter((row) => selectedKeys.includes(row.key)).map((row) => row.url),
    [rows, selectedKeys]
  );

  const loadCurrentFiles = async () => {
    setLoading(true);
    try {
      const files = await listFiles();
      setRows(
        files.map((file) => ({
          key: file.id || file.thumbnail_url || file.original_url || file.url,
          url: file.thumbnail_url || file.original_url || file.url,
          type: file.type || 'media',
          tags: file.tags || {}
        }))
      );
      setSelectedKeys([]);
    } catch (error) {
      message.error(getErrorMessage(error, 'Could not load files'));
    } finally {
      setLoading(false);
    }
  };

  const addManualUrls = ({ urlsText }) => {
    const urls = parseLines(urlsText);
    setRows(
      urls.map((url) => ({
        key: url,
        url,
        type: /\.(mp4|mov|webm)$/i.test(url) ? 'video' : 'image',
        tags: {}
      }))
    );
    setSelectedKeys(urls);
  };

  const confirmDelete = async () => {
    setLoading(true);
    try {
      await deleteFiles(selectedUrls);
      message.success(`Deleted ${selectedUrls.length} file${selectedUrls.length === 1 ? '' : 's'}`);
      setRows((current) => current.filter((row) => !selectedKeys.includes(row.key)));
      setSelectedKeys([]);
      setConfirmOpen(false);
    } catch (error) {
      message.error(getErrorMessage(error, 'Delete failed'));
    } finally {
      setLoading(false);
    }
  };

  return (
    <section className="page-grid single-column">
      <div className="page-heading">
        <Typography.Title level={2}>Delete media</Typography.Title>
        <Typography.Text type="secondary">Remove selected records, originals, and thumbnails.</Typography.Text>
      </div>

      <div className="tool-panel">
        <Space className="panel-actions" wrap>
          <Button icon={<RefreshCw size={17} />} loading={loading} onClick={loadCurrentFiles}>
            Load my files
          </Button>
          <Button
            danger
            type="primary"
            icon={<Trash2 size={17} />}
            disabled={!selectedUrls.length}
            onClick={() => setConfirmOpen(true)}
          >
            Delete selected
          </Button>
        </Space>

        <Form layout="vertical" onFinish={addManualUrls}>
          <Form.Item name="urlsText" label="Manual URL list">
            <Input.TextArea rows={4} placeholder="One URL per line" />
          </Form.Item>
          <Button htmlType="submit">Use manual list</Button>
        </Form>

        {rows.length ? (
          <Table
            rowSelection={{
              selectedRowKeys: selectedKeys,
              onChange: setSelectedKeys
            }}
            dataSource={rows}
            pagination={{ pageSize: 6 }}
            columns={[
              {
                title: 'URL',
                dataIndex: 'url',
                render: (url) => (
                  <Typography.Text copyable ellipsis className="table-url">
                    {url}
                  </Typography.Text>
                )
              },
              { title: 'Type', dataIndex: 'type', width: 100 },
              {
                title: 'Tags',
                dataIndex: 'tags',
                render: (tags) => (
                  <Space wrap>
                    {Object.keys(tags || {}).map((tag) => (
                      <Tag color="green" key={tag}>
                        {tag}
                      </Tag>
                    ))}
                  </Space>
                )
              }
            ]}
          />
        ) : (
          <Empty description="No files loaded" />
        )}
      </div>

      <Modal
        title="Confirm deletion"
        open={confirmOpen}
        okText="Delete"
        okButtonProps={{ danger: true, loading }}
        onOk={confirmDelete}
        onCancel={() => setConfirmOpen(false)}
      >
        <Typography.Paragraph>
          {selectedUrls.length} selected file{selectedUrls.length === 1 ? '' : 's'} will be removed.
        </Typography.Paragraph>
      </Modal>
    </section>
  );
}
