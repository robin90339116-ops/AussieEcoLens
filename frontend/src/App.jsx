import { Navigate, Route, Routes } from 'react-router-dom';
import AppShell from './components/AppShell';
import ProtectedRoute from './components/ProtectedRoute';
import DeleteFiles from './pages/DeleteFiles';
import Login from './pages/Login';
import NewPassword from './pages/NewPassword';
import Results from './pages/Results';
import SearchPage from './pages/SearchPage';
import Signup from './pages/Signup';
import Subscribe from './pages/Subscribe';
import TagManage from './pages/TagManage';
import UploadPage from './pages/UploadPage';
import VerifyEmail from './pages/VerifyEmail';

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route path="/signup" element={<Signup />} />
      <Route path="/verify" element={<VerifyEmail />} />
      <Route path="/new-password" element={<NewPassword />} />
      <Route element={<ProtectedRoute />}>
        <Route element={<AppShell />}>
          <Route path="/" element={<Navigate to="/upload" replace />} />
          <Route path="/upload" element={<UploadPage />} />
          <Route path="/search" element={<SearchPage />} />
          <Route path="/results" element={<Results />} />
          <Route path="/tag-manage" element={<TagManage />} />
          <Route path="/delete" element={<DeleteFiles />} />
          <Route path="/subscribe" element={<Subscribe />} />
        </Route>
      </Route>
      <Route path="*" element={<Navigate to="/upload" replace />} />
    </Routes>
  );
}

