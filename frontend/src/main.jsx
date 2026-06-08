import React from 'react';
import ReactDOM from 'react-dom/client';
import { BrowserRouter } from 'react-router-dom';
import { ConfigProvider } from 'antd';
import 'antd/dist/reset.css';
import './styles.css';
import App from './App.jsx';
import { AuthProvider } from './context/AuthContext.jsx';

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <ConfigProvider
      theme={{
        token: {
          colorPrimary: '#d95d45',
          colorInfo: '#247a7b',
          colorSuccess: '#247a7b',
          colorWarning: '#c4872f',
          colorError: '#bd3d45',
          colorText: '#20252b',
          colorTextSecondary: '#69727d',
          colorBorder: '#dfe3e8',
          colorBgLayout: '#f3f5f7',
          borderRadius: 6,
          controlHeight: 38,
          fontFamily:
            'Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif'
        },
        components: {
          Button: {
            primaryShadow: 'none',
            defaultShadow: 'none',
            fontWeight: 600
          },
          Menu: {
            itemBg: 'transparent',
            itemColor: '#626b76',
            itemHoverColor: '#20252b',
            itemSelectedColor: '#d95d45',
            horizontalItemSelectedColor: '#d95d45'
          },
          Tabs: {
            itemSelectedColor: '#d95d45',
            itemHoverColor: '#b94a36',
            inkBarColor: '#d95d45'
          }
        }
      }}
    >
      <BrowserRouter>
        <AuthProvider>
          <App />
        </AuthProvider>
      </BrowserRouter>
    </ConfigProvider>
  </React.StrictMode>
);
