import {
  Button,
  Form,
  Input,
  InputNumber,
  Select,
  Space,
  Tabs,
  Typography,
  Upload,
  message
} from 'antd';
import { FileSearch, Plus, Search, UploadCloud, X } from 'lucide-react';
import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  getErrorMessage,
  queryBySpecies,
  queryByTags,
  queryByThumbnailUrl,
  queryByUploadedFile,
  tagsArrayToObject
} from '../api/client';
import { speciesOptions } from '../data/species';

export default function SearchPage() {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(false);
  const [queryFile, setQueryFile] = useState(null);

  const goToResults = (title, items) => {
    sessionStorage.setItem('aussie-ecolens-results', JSON.stringify({ title, items }));
    navigate('/results', { state: { title, items } });
  };

  const handleTagQuery = async ({ rows }) => {
    const tags = tagsArrayToObject(rows || []);
    if (!Object.keys(tags).length) {
      message.error('Add at least one species');
      return;
    }
    setLoading(true);
    try {
      const items = await queryByTags(tags);
      goToResults('Tag count query', items);
    } catch (error) {
      message.error(getErrorMessage(error, 'Query failed'));
    } finally {
      setLoading(false);
    }
  };

  const handleSpeciesQuery = async ({ species }) => {
    setLoading(true);
    try {
      const items = await queryBySpecies(species);
      goToResults('Species query', items);
    } catch (error) {
      message.error(getErrorMessage(error, 'Query failed'));
    } finally {
      setLoading(false);
    }
  };

  const handleFileQuery = async () => {
    if (!queryFile) {
      message.error('Select a query image');
      return;
    }
    setLoading(true);
    try {
      const items = await queryByUploadedFile(queryFile);
      goToResults('Uploaded file query', items);
    } catch (error) {
      message.error(getErrorMessage(error, 'Query failed'));
    } finally {
      setLoading(false);
    }
  };

  const handleThumbnailQuery = async ({ thumbnailUrl }) => {
    setLoading(true);
    try {
      const items = await queryByThumbnailUrl(thumbnailUrl.trim());
      goToResults('Thumbnail URL lookup', items);
    } catch (error) {
      message.error(getErrorMessage(error, 'Thumbnail lookup failed'));
    } finally {
      setLoading(false);
    }
  };

  return (
    <section className="page-grid single-column">
      <div className="page-heading">
        <Typography.Title level={2}>Search media</Typography.Title>
        <Typography.Text type="secondary">Find stored media by tags, species, thumbnail URL, or a query image.</Typography.Text>
      </div>

      <div className="tool-panel">
        <Tabs
          defaultActiveKey="tags"
          items={[
            {
              key: 'tags',
              label: 'Tags and counts',
              children: (
                <Form
                  layout="vertical"
                  onFinish={handleTagQuery}
                  initialValues={{ rows: [{ species: 'common wombat', count: 1 }] }}
                >
                  <Form.List name="rows">
                    {(fields, { add, remove }) => (
                      <>
                        {fields.map(({ key, ...field }) => (
                          <div className="query-row" key={key}>
                            <Form.Item
                              {...field}
                              name={[field.name, 'species']}
                              rules={[{ required: true, message: 'Select species' }]}
                            >
                              <Select
                                showSearch
                                options={speciesOptions}
                                optionFilterProp="label"
                                placeholder="Species"
                              />
                            </Form.Item>
                            <Form.Item
                              {...field}
                              name={[field.name, 'count']}
                              rules={[{ required: true, message: 'Count' }]}
                            >
                              <InputNumber min={1} max={99} />
                            </Form.Item>
                            <Button
                              title="Remove row"
                              icon={<X size={16} />}
                              onClick={() => remove(field.name)}
                            />
                          </div>
                        ))}
                        <Button icon={<Plus size={16} />} onClick={() => add({ count: 1 })}>
                          Add species
                        </Button>
                      </>
                    )}
                  </Form.List>
                  <Button
                    type="primary"
                    htmlType="submit"
                    loading={loading}
                    icon={<Search size={17} />}
                    className="form-submit"
                  >
                    Run AND query
                  </Button>
                </Form>
              )
            },
            {
              key: 'species',
              label: 'Species',
              children: (
                <Form layout="vertical" onFinish={handleSpeciesQuery}>
                  <Form.Item
                    name="species"
                    label="Species"
                    rules={[{ required: true, message: 'Select species' }]}
                  >
                    <Select
                      showSearch
                      options={speciesOptions}
                      optionFilterProp="label"
                      placeholder="Species"
                    />
                  </Form.Item>
                  <Button type="primary" htmlType="submit" loading={loading} icon={<Search size={17} />}>
                    Search species
                  </Button>
                </Form>
              )
            },
            {
              key: 'thumbnail',
              label: 'Thumbnail URL',
              children: (
                <Form
                  layout="vertical"
                  onFinish={handleThumbnailQuery}
                  className="thumbnail-query-form"
                >
                  <Form.Item
                    name="thumbnailUrl"
                    label="Thumbnail URL"
                    rules={[
                      { required: true, message: 'Enter a thumbnail URL' },
                      { type: 'url', message: 'Enter a valid URL' }
                    ]}
                  >
                    <Input placeholder="https://.../thumbnails/example.jpg" />
                  </Form.Item>
                  <Button type="primary" htmlType="submit" loading={loading} icon={<Search size={17} />}>
                    Find original
                  </Button>
                </Form>
              )
            },
            {
              key: 'file',
              label: 'Query image',
              children: (
                <div className="query-file-panel">
                  <Upload
                    maxCount={1}
                    accept=".jpg,.jpeg,.png"
                    beforeUpload={(file) => {
                      setQueryFile(file);
                      return false;
                    }}
                    onRemove={() => setQueryFile(null)}
                    fileList={queryFile ? [queryFile] : []}
                  >
                    <Button icon={<UploadCloud size={17} />}>Select image</Button>
                  </Upload>
                  <Button
                    type="primary"
                    loading={loading}
                    icon={<FileSearch size={17} />}
                    onClick={handleFileQuery}
                  >
                    Match by detected tags
                  </Button>
                </div>
              )
            }
          ]}
        />
      </div>
    </section>
  );
}
