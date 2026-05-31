import { Layout, Menu, Space, Typography, Button, Tag } from 'antd';
import {
  Bell,
  LogOut,
  Search,
  Tags,
  Trash2,
  UploadCloud
} from 'lucide-react';
import { Outlet, useLocation, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

const { Header, Content } = Layout;

const navItems = [
  { key: '/upload', label: 'Upload', icon: <UploadCloud size={17} /> },
  { key: '/search', label: 'Search', icon: <Search size={17} /> },
  { key: '/tag-manage', label: 'Tags', icon: <Tags size={17} /> },
  { key: '/delete', label: 'Delete', icon: <Trash2 size={17} /> },
  { key: '/subscribe', label: 'Subscribe', icon: <Bell size={17} /> }
];

export default function AppShell() {
  const navigate = useNavigate();
  const location = useLocation();
  const { user, logout, mockAuth } = useAuth();
  const selectedKey =
    navItems.find((item) => location.pathname.startsWith(item.key))?.key || '/upload';

  const handleLogout = async () => {
    await logout();
    navigate('/login');
  };

  return (
    <Layout className="app-layout">
      <Header className="app-header">
        <Space className="brand" onClick={() => navigate('/upload')} role="button">
          <span className="brand-mark">AE</span>
          <div>
            <Typography.Text strong>Aussie EcoLens</Typography.Text>
            <Typography.Text type="secondary" className="brand-caption">
              Wildlife media console
            </Typography.Text>
          </div>
        </Space>

        <Menu
          className="main-menu"
          mode="horizontal"
          selectedKeys={[selectedKey]}
          items={navItems}
          onClick={({ key }) => navigate(key)}
        />

        <Space className="user-cluster">
          {mockAuth && <Tag color="gold">Mock</Tag>}
          <Typography.Text className="user-email">{user?.email}</Typography.Text>
          <Button
            title="Sign out"
            icon={<LogOut size={16} />}
            onClick={handleLogout}
          >
            Sign out
          </Button>
        </Space>
      </Header>
      <Content className="app-content">
        <Outlet />
      </Content>
    </Layout>
  );
}

